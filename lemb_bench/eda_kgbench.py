import argparse
import contextlib
import sys
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
from kgbench import load
from kgbench.urls import URLS


def load_splits(dataset: str):
    with contextlib.redirect_stdout(sys.stderr), warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        data = load(dataset, final=False)
    return data, data.training, data.withheld


def short(mapping, index: int, width: int = 70) -> str:
    entry = mapping[int(index)]
    text = entry[0] if isinstance(entry, tuple) else entry
    text = str(text).replace("\n", " ").strip()
    return text if len(text) <= width else text[: width - 3] + "..."


def sample_entities(splits, count: int, rng: np.random.Generator):
    base, rem = divmod(count, len(splits))
    picked = []
    for i, (name, rows) in enumerate(splits):
        take = min(base + (1 if i < rem else 0), len(rows))
        if take:
            for j in rng.choice(len(rows), size=take, replace=False):
                picked.append((name, int(rows[j, 0]), int(rows[j, 1])))
    return picked


IRI_PREFIXES = ("http://", "https://", "ftp://", "file:", "urn:", "mailto:")


def classify(label, annotation: str, legacy: bool) -> str:
    # see also: https://rdflib.readthedocs.io/en/latest/rdf_terms/
    if legacy:
        text = str(label)
        if text.startswith("_:"):
            return "blank"
        return "iri" if text.startswith(IRI_PREFIXES) else "none"
    if annotation == "iri":
        return "iri"
    if annotation == "blank_node":
        return "blank"
    return "none"


def counter_to_percent(c):
    total = sum(v for k, v in c.items())
    return {int(k): f"{v} ({round(v * 100 / total, 2)}%)" for k, v in c.items()}


def render(dataset: str, data, splits, count: int) -> str:
    train, val = (rows for _, rows in splits)
    rng = np.random.default_rng(0)
    total = data.num_entities
    legacy = not any(ann == "iri" for _, ann in data.i2e)
    kinds = Counter(classify(label, ann, legacy) for label, ann in data.i2e)
    labeled = np.unique(np.concatenate([train[:, 0], val[:, 0]]))
    labeled_kinds = Counter(classify(*data.i2e[i], legacy) for i in labeled)
    class_distribution_train = counter_to_percent(Counter(data.training[:, 1]))
    class_distribution_test = counter_to_percent(Counter(data.withheld[:, 1]))
    out = [
        f"{dataset}: {data.num_entities} nodes, {data.num_relations} relations, "
        f"{len(data.triples)} triples, {data.num_classes} classes",
        f"node kinds:  {100 * kinds['iri'] / total:5.2f}% iri   "
        f"{100 * kinds['blank'] / total:5.2f}% blank   {100 * kinds['none'] / total:5.2f}% none",
        f"labeled:     {100 * labeled_kinds['iri'] / total:5.2f}% iri   "
        f"{100 * labeled_kinds['blank'] / total:5.2f}% blank   "
        f"{100 * labeled_kinds['none'] / total:5.2f}% none   {100 * len(labeled) / total:5.2f}% total",
        f"split sizes: train={len(train)}, val={len(val)}",
        f"{class_distribution_train=}",
        f"{class_distribution_test=}",
        "",
        "labeled entities (split, entity, class):",
    ]
    for split, entity, cls in sample_entities(splits, count, rng):
        out.append(f"  [{split:5}] {short(data.i2e, entity)}  ->  class {cls}")

    n = min(count, len(data.triples))
    picks = rng.choice(len(data.triples), size=n, replace=False)
    out += ["", f"random triples (subject, relation, object):"]
    for i in picks:
        s, r, o = data.triples[i]
        out.append(
            f"  {short(data.i2e, s)}  -[{short(data.i2r, r, 45)}]->  {short(data.i2e, o)}"
        )
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        required=True,
        help="directory for the per-dataset samples",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for dataset in sorted(URLS):
        try:
            data, train, val = load_splits(dataset)
            text = render(dataset, data, [("train", train), ("val", val)], 10)
            path = args.out_dir / f"{dataset}.txt"
            path.write_text(text)
            print(f"wrote {path}", file=sys.stderr)
            del data
        except Exception as e:
            print(f"{dataset}: failed: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
