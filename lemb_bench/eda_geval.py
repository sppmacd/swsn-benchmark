import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from shapely import Point
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
GEVAL_ROOT = REPO_ROOT / "submodules" / "Evaluation-Framework" / "evaluation_framework"

GEORSS_POINT = "http://www.georss.org/georss/point"
CLASSIFICATION_KEY = "DBpedia_URI15"
CLASSIFICATION_LABEL = "label"
REGRESSION_KEY = "DBpedia_URI15"
REGRESSION_LABEL = "rating"
CLUSTERING_LABEL = "cluster"


@dataclass
class DumpScan:
    triples: int = 0
    triples_by_file: dict = field(default_factory=dict)
    iris: set = field(default_factory=set)
    blank_nodes: set = field(default_factory=set)
    literals: set = field(default_factory=set)
    predicates: set = field(default_factory=set)
    geo_nodes: set = field(default_factory=set)
    invalid_geo_literals: int = 0


def parse_ttl_statement(line: str):
    """Parse a single line of a ttl file.

    E.g <http://dbpedia.org/resource/Albedo> <http://purl.org/dc/terms/subject> <http://dbpedia.org/resource/Category:Scattering,_absorption_and_radiative_transfer_(optics)> .
    """
    if not line or line[0] == "#":
        return None

    if line[0] == "<":
        subject_end = line.find(">")
        if subject_end < 0:
            return None
        subject = line[1:subject_end]
        subject_is_blank = False
        cursor = subject_end + 1
    elif line.startswith("_:"):
        subject_end = line.find(" ", 2)
        if subject_end < 0:
            return None
        subject = line[2:subject_end]
        subject_is_blank = True
        cursor = subject_end
    else:
        return None

    predicate_start = line.find("<", cursor)
    if predicate_start < 0:
        return None
    predicate_end = line.find(">", predicate_start)
    if predicate_end < 0:
        return None
    predicate = line[predicate_start + 1 : predicate_end]
    cursor = predicate_end + 1

    while cursor < len(line) and line[cursor].isspace():
        cursor += 1
    if cursor >= len(line):
        return None

    if line[cursor] == "<":
        object_end = line.find(">", cursor)
        if object_end < 0:
            return None
        object_kind = "iri"
        obj = line[cursor + 1 : object_end]
    elif line.startswith("_:", cursor):
        object_end = line.find(" ", cursor)
        if object_end < 0:
            object_end = len(line)
        object_kind = "blank"
        obj = line[cursor + 2 : object_end]
    else:
        object_kind = "literal"
        obj = line[cursor:].rstrip("\r\n")
        if obj.endswith("."):
            obj = obj[:-1].rstrip()

    return subject_is_blank, subject, predicate, object_kind, obj


def scan_dump(dump: Path) -> DumpScan:
    """Compute general statistics of a given ttl data dump."""
    scan = DumpScan()
    files = sorted(dump.glob("*.ttl")) if dump.is_dir() else [dump]
    if not files:
        raise SystemExit(f"no .ttl files found in {dump}")

    for file in files:
        count = 0
        with file.open(encoding="utf-8") as handle:
            for line in tqdm(handle, desc=file.name, unit="triples"):
                parsed = parse_ttl_statement(line)
                if parsed is None:
                    continue
                subject_is_blank, subject, predicate, object_kind, obj = parsed
                count += 1

                scan.predicates.add(predicate)
                if subject_is_blank:
                    scan.blank_nodes.add(subject)
                else:
                    scan.iris.add(subject)

                if object_kind == "iri":
                    scan.iris.add(obj)
                elif object_kind == "blank":
                    scan.blank_nodes.add(obj)
                else:
                    scan.literals.add(obj)
                    if predicate == GEORSS_POINT and obj.startswith('"'):
                        # e.g <http://dbpedia.org/resource/Algeria> <http://www.georss.org/georss/point> "36.7 3.216666666666667".
                        coordinates = obj[1 : obj.rfind('"')].split(" ", 1)
                        if len(coordinates) == 2:
                            latitude, longitude = coordinates
                            try:
                                # mirrors submodules/GeoRDF2Vec/data_preparation/data_preparation_dbpedia.py
                                Point(longitude, latitude)
                                scan.geo_nodes.add(subject)
                            except Exception:
                                scan.invalid_geo_literals += 1
                        else:
                            scan.invalid_geo_literals += 1

        scan.triples_by_file[file.name] = count
        scan.triples += count

    return scan


def pct(part: int, whole: int) -> float:
    return 100.0 * part / whole if whole else 0.0


def number_of_nodes(scan: DumpScan) -> dict:
    return {"count": len(scan.iris) + len(scan.blank_nodes)}


def number_and_pct_of_term_kinds(scan: DumpScan) -> dict:
    total = len(scan.iris) + len(scan.blank_nodes) + len(scan.literals)
    kinds = {
        "iri": len(scan.iris),
        "blank_node": len(scan.blank_nodes),
        "literal": len(scan.literals),
    }
    return {
        name: {"count": count, "pct": round(pct(count, total), 4)}
        for name, count in kinds.items()
    }


def number_of_relation_types(scan: DumpScan) -> dict:
    return {"count": len(scan.predicates)}


def number_of_relations(scan: DumpScan) -> dict:
    return {
        "count": scan.triples,
        "by_file": dict(sorted(scan.triples_by_file.items())),
    }


def pct_of_nodes_with_geographical_data(scan: DumpScan) -> dict:
    nodes = len(scan.iris) + len(scan.blank_nodes)
    return {
        "count": len(scan.geo_nodes),
        "pct": round(pct(len(scan.geo_nodes), nodes), 4),
        "invalid_literals": scan.invalid_geo_literals,
    }


def data_source(dump: Path) -> dict:
    scan = scan_dump(dump)
    return {
        "nodes": number_of_nodes(scan),
        "term_kinds": number_and_pct_of_term_kinds(scan),
        "relation_types": number_of_relation_types(scan),
        "relations": number_of_relations(scan),
        "geographical_nodes": pct_of_nodes_with_geographical_data(scan),
    }


def classification_dataset(path: Path, total_nodes: int) -> dict:
    frame = pd.read_csv(path, sep="\t", encoding="utf-8")
    labels = frame[CLASSIFICATION_LABEL].dropna()
    counts = labels.value_counts().sort_index()
    labeled_rows = int(counts.sum())

    labeled_entities = int(
        frame.loc[labels.index, CLASSIFICATION_KEY].dropna().nunique()
    )

    return {
        "classes": int(counts.size),
        "labels": {
            str(label): {
                "count": int(count),
                "pct": round(pct(int(count), labeled_rows), 4),
            }
            for label, count in counts.items()
        },
        "labeled_entities": labeled_entities,
        "labeled_entities_pct": round(pct(labeled_entities, total_nodes), 6),
    }


def classification_labels(total_nodes: int) -> dict:
    data_dir = GEVAL_ROOT / "Classification" / "data"
    return {
        path.stem: classification_dataset(path, total_nodes)
        for path in sorted(data_dir.glob("*.tsv"))
    }


def regression_dataset(path: Path, out: Path, total_nodes: int) -> dict:
    frame = pd.read_csv(path, sep="\t", encoding="utf-8")
    ratings = pd.to_numeric(frame[REGRESSION_LABEL], errors="coerce").dropna()
    labeled_rows = ratings.index

    labeled_entities = int(frame.loc[labeled_rows, REGRESSION_KEY].dropna().nunique())

    bins = min(50, max(1, int(ratings.nunique())))
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.hist(ratings.to_numpy(), bins=bins)
    axis.set_title(f"{path.stem} rating distribution (n={len(ratings)})")
    axis.set_xlabel(REGRESSION_LABEL)
    axis.set_ylabel("entities")
    figure.tight_layout()
    histogram = f"regression_{path.stem}_rating_histogram.png"
    figure.savefig(out / histogram, dpi=150)
    plt.close(figure)

    return {
        "histogram": histogram,
        "labeled_entities": labeled_entities,
        "labeled_entities_pct": round(pct(labeled_entities, total_nodes), 6),
    }


def regression_labels(out: Path, total_nodes: int) -> dict:
    data_dir = GEVAL_ROOT / "Regression" / "data"
    return {
        path.stem: regression_dataset(path, out, total_nodes)
        for path in sorted(data_dir.glob("*.tsv"))
    }


def clustering_dataset(path: Path) -> dict:
    frame = pd.read_csv(path, sep="\t", encoding="utf-8")
    return {"clusters": int(frame[CLUSTERING_LABEL].nunique(dropna=True))}


def clustering_labels() -> dict:
    data_dir = GEVAL_ROOT / "Clustering" / "data"
    return {
        path.stem: clustering_dataset(path) for path in sorted(data_dir.glob("*.tsv"))
    }


def render_report(results: dict) -> str:
    source = results["data_source"]
    term_names = {"iri": "IRI", "blank_node": "Blank node", "literal": "Literal"}
    lines = [
        "# GEval EDA",
        "",
        "## Data source",
        "",
        f"- Nodes: {source['nodes']['count']}",
        f"- Relation types: {source['relation_types']['count']}",
        f"- Relations: {source['relations']['count']}",
        f"- Nodes with geographical data (having a valid GeoRSS Point relation): {source['geographical_nodes']['count']} "
        f"({source['geographical_nodes']['pct']:.4f}%)",
        "",
        "| Term kind | Count | % of distinct terms |",
        "| --- | ---: | ---: |",
    ]
    for name in ("iri", "blank_node", "literal"):
        stats = source["term_kinds"][name]
        lines.append(f"| {term_names[name]} | {stats['count']} | {stats['pct']:.4f}% |")
    lines += [
        "",
        "| Dump file | Relations |",
        "| --- | ---: |",
    ]
    for name, count in source["relations"]["by_file"].items():
        lines.append(f"| `{name}` | {count} |")

    lines += [
        "",
        "## Classification",
        "",
        "| Dataset | Classes | Labels | Labeled entities | % of nodes |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for dataset, stats in results["classification"].items():
        labels = sum(count["count"] for count in stats["labels"].values())
        lines.append(
            f"| {dataset} | {stats['classes']} | {labels} | "
            f"{stats['labeled_entities']} | {stats['labeled_entities_pct']:.6f}% |"
        )
    for dataset, stats in results["classification"].items():
        lines += [
            "",
            f"### {dataset}",
            "",
            "| Class | Labels | % of labels |",
            "| --- | ---: | ---: |",
        ]
        for label, count in stats["labels"].items():
            lines.append(f"| {label} | {count['count']} | {count['pct']:.4f}% |")

    lines += [
        "",
        "## Regression",
        "",
        "| Dataset | Labeled entities | % of nodes | Histogram |",
        "| --- | ---: | ---: | --- |",
    ]
    for dataset, stats in results["regression"].items():
        lines.append(
            f"| {dataset} | {stats['labeled_entities']} | "
            f"{stats['labeled_entities_pct']:.6f}% | `{stats['histogram']}` |"
        )

    lines += [
        "",
        "## Clustering",
        "",
        "| Dataset | Clusters |",
        "| --- | ---: |",
    ]
    for dataset, stats in results["clustering"].items():
        lines.append(f"| {dataset} | {stats['clusters']} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-d", type=Path, required=True, help="DBPedia dump directory")
    parser.add_argument("-o", type=Path, required=True, help="output directory")
    arguments = parser.parse_args()

    out = arguments.o
    out.mkdir(parents=True, exist_ok=True)

    print("Analyzing data source", file=sys.stderr)
    source = data_source(arguments.d)
    total_nodes = source["nodes"]["count"]

    print("Analyzing classification labels", file=sys.stderr)
    classification = classification_labels(total_nodes)
    print("Analyzing regression labels", file=sys.stderr)
    regression = regression_labels(out, total_nodes)
    print("Analyzing clustering labels", file=sys.stderr)
    clustering = clustering_labels()

    results = {
        "data_source": source,
        "classification": classification,
        "regression": regression,
        "clustering": clustering,
    }

    print("Writing outputs", file=sys.stderr)
    (out / "results.json").write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = render_report(results)
    (out / "report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
