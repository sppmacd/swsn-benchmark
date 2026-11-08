#!/usr/bin/env python3
"""Build a loader-compatible SE-KGE graph from a KGBench dataset.

This is an integration/compatibility adapter, not a KGBench link-prediction
benchmark. KGBench provides a node-classification split, while SE-KGE expects
typed graph edges and query files. The adapter therefore creates a deterministic
edge split and records that fact in ``manifest.json``.

The generated graph intentionally contains no geographic metadata. It is meant
to answer the first integration question: can the SE-KGE graph/query loader
read a KGBench graph? Geographic training and comparable benchmark evaluation
require a separate mapping from KGBench entities to coordinates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import random
import re
from collections import defaultdict
from pathlib import Path

from kgbench import load


RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
ENTITY_TYPE = "Entity"


def mapping_label(mapping, index):
    """Return the label part of a KGBench i2e/i2r entry."""
    item = mapping[int(index)]
    if isinstance(item, (tuple, list)):
        item = item[0]
    return str(item)


def sanitize_type(value):
    """Turn an RDF class/datatype into a stable ASCII SE-KGE mode name."""
    value = str(value)
    if value in ("iri", "blank_node"):
        return "IRI" if value == "iri" else "BlankNode"
    if value == "none":
        return "Literal_none"
    if value.startswith("@"):
        value = "lang_" + value[1:]
    tail = re.split(r"[/#:]", value)[-1]
    tail = re.sub(r"[^A-Za-z0-9]+", "_", tail).strip("_")
    return tail or "Unknown"


def make_unique_type_names(values):
    """Give class labels readable, collision-free mode names."""
    result = {}
    used = {}
    for value in sorted(set(values)):
        base = "RDF_" + sanitize_type(value)
        name = base
        if name in used and used[name] != value:
            digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
            name = "{}_{}".format(base, digest)
        used[name] = value
        result[value] = name
    return result


def entity_fallback_type(annotation):
    """Use KGBench's annotation when an entity has no rdf:type statement."""
    if annotation == "iri":
        return "IRI"
    if annotation == "blank_node":
        return "BlankNode"
    annotation_name = sanitize_type(annotation)
    if annotation_name.startswith("Literal_"):
        return annotation_name
    return "Literal_{}".format(annotation_name)


def build_entity_types(data, triples, type_mode):
    """Assign exactly one SE-KGE mode to every KGBench entity."""
    if type_mode == "generic":
        return [ENTITY_TYPE] * len(data.i2e), {"generic": True}

    type_relation_ids = {
        relation_id
        for relation_id, relation in enumerate(data.i2r)
        if str(relation) == RDF_TYPE
    }
    rdf_classes = defaultdict(set)
    for subject, predicate, object_ in triples:
        if predicate in type_relation_ids:
            rdf_classes[subject].add(mapping_label(data.i2e, object_))

    class_names = make_unique_type_names(
        value for values in rdf_classes.values() for value in values
    )
    entity_types = []
    for entity_id, item in enumerate(data.i2e):
        annotation = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else "none"
        classes = sorted(rdf_classes.get(entity_id, ()))
        if classes:
            entity_types.append(class_names[classes[0]])
        else:
            entity_types.append(entity_fallback_type(annotation))

    return entity_types, {
        "rdf_type_relation_ids": sorted(type_relation_ids),
        "rdf_class_count": len(class_names),
        "rdf_classes": class_names,
    }


def serialize_edge(edge, negative_samples):
    """Serialize one edge in the format consumed by netquery.Query."""
    return (("1-chain", edge), negative_samples, None)


def dump_pickle(value, path):
    with path.open("wb") as handle:
        # Protocol 2 is readable by the Python 2.7 cPickle used by SE-KGE.
        pickle.dump(value, handle, protocol=2)


def write_mapping_files(output_dir, data, entity_types):
    with (output_dir / "entity2type.tsv").open("w", encoding="utf-8", newline="") as handle:
        # Do not copy the full KGBench labels here. dmg777k contains large
        # base64 image literals; the original labels remain available through
        # KGBench's nodes.int.csv and are not needed by the SE-KGE loader.
        handle.write("entity_id\tannotation\tse_kge_type\n")
        for entity_id, item in enumerate(data.i2e):
            annotation = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else "none"
            handle.write("{}\t{}\t{}\n".format(entity_id, annotation, entity_types[entity_id]))

    with (output_dir / "relation2id.tsv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("forward_id\tinverse_id\tlabel\n")
        for relation_id, relation in enumerate(data.i2r):
            handle.write("{}\t{}\t{}\n".format(2 * relation_id, 2 * relation_id + 1, relation))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="dmg777k", help="KGBench dataset name or local archive")
    parser.add_argument("--output-dir", type=Path, required=True, help="SE-KGE data directory to create")
    parser.add_argument("--seed", type=int, default=777, help="seed for the synthetic edge split")
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--test-fraction", type=float, default=0.05)
    parser.add_argument(
        "--type-mode",
        choices=("rdf", "generic"),
        default="rdf",
        help="use rdf:type plus annotation fallback, or one generic Entity mode",
    )
    args = parser.parse_args()

    if args.validation_fraction < 0 or args.test_fraction < 0:
        parser.error("split fractions must be non-negative")
    if args.validation_fraction + args.test_fraction >= 1:
        parser.error("validation_fraction + test_fraction must be below 1")

    print("Loading {}...".format(args.dataset), flush=True)
    data = load(args.dataset, final=False)
    triples = [tuple(int(value) for value in row) for row in data.triples]
    triples = list(dict.fromkeys(triples))

    entity_types, type_metadata = build_entity_types(data, triples, args.type_mode)
    relation_count = len(data.i2r)
    relation_ids = {relation_id: (str(2 * relation_id), str(2 * relation_id + 1))
                    for relation_id in range(relation_count)}
    relation_inverse = {
        2 * relation_id: 2 * relation_id + 1
        for relation_id in range(relation_count)
    }
    relation_inverse.update({value: key for key, value in relation_inverse.items()})

    shuffled = list(triples)
    random.Random(args.seed).shuffle(shuffled)
    validation_count = int(len(shuffled) * args.validation_fraction)
    test_count = int(len(shuffled) * args.test_fraction)
    valid_triples = shuffled[:validation_count]
    test_triples = shuffled[validation_count:validation_count + test_count]
    train_triples = shuffled[validation_count + test_count:]

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # SE-KGE stores each relation and its inverse as a separate template.
    # The graph itself contains only train edges; validation/test edges are
    # kept out to prevent leakage when the adapter is used for a smoke test.
    all_templates = set()
    for subject, relation, object_ in triples:
        forward_id, inverse_id = relation_ids[relation]
        all_templates.add((entity_types[subject], forward_id, entity_types[object_]))
        all_templates.add((entity_types[object_], inverse_id, entity_types[subject]))

    adjacency = {template: defaultdict(set) for template in all_templates}
    for subject, relation, object_ in train_triples:
        forward_id, inverse_id = relation_ids[relation]
        forward = (entity_types[subject], forward_id, entity_types[object_])
        inverse = (entity_types[object_], inverse_id, entity_types[subject])
        adjacency[forward][subject].add(object_)
        adjacency[inverse][object_].add(subject)

    node_maps = defaultdict(list)
    for entity_id, entity_type in enumerate(entity_types):
        node_maps[entity_type].append(entity_id)

    relations = defaultdict(list)
    for head_type, relation_id, tail_type in sorted(all_templates):
        relations[head_type].append((tail_type, relation_id))

    graph_data = (dict(relations), adjacency, dict(node_maps), relation_inverse)
    dump_pickle(graph_data, output_dir / "graph_data.pkl")

    dump_pickle(train_triples, output_dir / "train_triples.pkl")
    dump_pickle(valid_triples, output_dir / "valid_triples.pkl")
    dump_pickle(test_triples, output_dir / "test_triples.pkl")

    # Empty negative lists make the files loadable without inventing a
    # benchmark-specific negative-sampling policy. They are deliberately not
    # suitable for final evaluation.
    dump_pickle(
        [serialize_edge((s, (entity_types[s], relation_ids[r][0], entity_types[o]), o), None)
         for s, r, o in train_triples],
        output_dir / "train_edges.pkl",
    )
    dump_pickle(
        [serialize_edge((s, (entity_types[s], relation_ids[r][0], entity_types[o]), o), [])
         for s, r, o in valid_triples],
        output_dir / "val_edges.pkl",
    )
    dump_pickle(
        [serialize_edge((s, (entity_types[s], relation_ids[r][0], entity_types[o]), o), [])
         for s, r, o in test_triples],
        output_dir / "test_edges.pkl",
    )
    write_mapping_files(output_dir, data, entity_types)

    manifest = {
        "dataset": args.dataset,
        "entities": len(data.i2e),
        "relations": len(data.i2r),
        "unique_triples": len(triples),
        "split": {
            "train": len(train_triples),
            "validation": len(valid_triples),
            "test": len(test_triples),
            "seed": args.seed,
            "validation_fraction": args.validation_fraction,
            "test_fraction": args.test_fraction,
            "meaning": "synthetic deterministic edge split; not the KGBench node-classification split",
        },
        "type_mode": args.type_mode,
        "type_count": len(node_maps),
        "types": {key: len(value) for key, value in sorted(node_maps.items())},
        "relation_templates": len(all_templates),
        "geographic_metadata": False,
        "geographic_note": "KGBench coordinates were not inferred; id2geo/id2extent files are intentionally absent.",
        "negative_samples": "empty placeholders in val_edges.pkl/test_edges.pkl; do not use for final metrics",
        "next_step": "provide a coordinate mapping and generate SE-KGE multi-edge/geographic query files before training",
        "type_metadata": type_metadata,
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    print("Created {}".format(output_dir))
    print("  entities: {}, triples: {} (train {}, valid {}, test {})".format(
        len(data.i2e), len(triples), len(train_triples), len(valid_triples), len(test_triples)
    ))
    print("  SE-KGE modes: {}, relation templates: {}".format(len(node_maps), len(all_templates)))
    print("  geographic metadata: absent (intentional compatibility-only adapter)")


if __name__ == "__main__":
    main()
