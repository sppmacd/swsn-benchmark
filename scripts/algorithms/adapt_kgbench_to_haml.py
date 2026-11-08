#!/usr/bin/env python3
"""Convert a KGBench graph to a leakage-safe HAML dataset layout.

HAML consumes ``data/<name>/train.txt``, ``valid.txt`` and ``test.txt`` and
then expects ``data/<name>.pkl``. Its upstream ``data2pkl`` combines all three
splits into the training graph and does not create ``ind_test_graph``. This
adapter writes the pickle directly so that:

* ``train_graph.train`` contains only training edges and its valid/test lists
  are empty, preventing subgraph-generation leakage;
* ``ind_test_graph`` contains train/validation/test edges for evaluation;
* every entity and relation occurring in validation/test is already present in
  the training graph, as required by HAML's transductive evaluator.

The split is a deterministic link-prediction smoke-test split. It is not an
official KGBench split, whose labels are for node classification.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import random
from pathlib import Path

from kgbench import load


def label(mapping, index):
    item = mapping[int(index)]
    if isinstance(item, (tuple, list)):
        item = item[0]
    return str(item)


def entry_label(item):
    if isinstance(item, (tuple, list)):
        item = item[0]
    return safe_label(item)


def write_lines(path, triples):
    with path.open("w", encoding="utf-8", newline="") as handle:
        for head, relation, tail in triples:
            handle.write("{}\t{}\t{}\n".format(head, relation, tail))


def compact_label(value, max_length=4096):
    value = str(value)
    if len(value) <= max_length:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return "<large-literal sha256={} length={}>".format(digest, len(value))


def safe_label(value):
    """Return one parser-safe, deterministic label for a HAML text file."""
    value = str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")
    if not value.strip():
        value = "<empty>"
    return compact_label(value)


def split_edges(triples, num_entities, num_relations, seed, validation_fraction, test_fraction):
    shuffled = list(triples)
    random.Random(seed).shuffle(shuffled)

    # Reserve edges that cover every entity and relation in train. This keeps
    # HAML's transductive evaluation from indexing unseen validation/test IDs.
    # Find the first shuffled edge covering each entity/relation in one pass.
    # Scanning all edges separately for every entity is quadratic on dmg777k.
    train_indices = set()
    unseen_entities = set(range(num_entities))
    unseen_relations = set(range(num_relations))
    for index, (head, relation, tail) in enumerate(shuffled):
        if head in unseen_entities:
            unseen_entities.remove(head)
            train_indices.add(index)
        if tail in unseen_entities:
            unseen_entities.remove(tail)
            train_indices.add(index)
        if relation in unseen_relations:
            unseen_relations.remove(relation)
            train_indices.add(index)
        if not unseen_entities and not unseen_relations:
            break

    train = [triple for index, triple in enumerate(shuffled) if index in train_indices]
    remaining = [triple for index, triple in enumerate(shuffled) if index not in train_indices]
    validation_count = int(len(triples) * validation_fraction)
    test_count = int(len(triples) * test_fraction)
    if remaining:
        validation_count = min(max(validation_count, 1), len(remaining))
        test_count = min(max(test_count, 1), len(remaining) - validation_count)
    else:
        validation_count = 0
        test_count = 0

    valid = remaining[:validation_count]
    test = remaining[validation_count:validation_count + test_count]
    train.extend(remaining[validation_count + test_count:])
    return train, valid, test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="aifb", help="KGBench dataset name")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="HAML data/<dataset> directory")
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--test-fraction", type=float, default=0.05)
    args = parser.parse_args()

    if args.validation_fraction < 0 or args.test_fraction < 0:
        parser.error("split fractions must be non-negative")
    if args.validation_fraction + args.test_fraction >= 1:
        parser.error("validation_fraction + test_fraction must be below 1")

    print("Loading {}...".format(args.dataset), flush=True)
    data = load(args.dataset, final=False)
    raw_triples = list(dict.fromkeys(tuple(int(value) for value in row) for row in data.triples))
    used_entities = sorted({value for triple in raw_triples for value in (triple[0], triple[2])})
    entity_reindex = {old: new for new, old in enumerate(used_entities)}

    raw_relations = sorted({triple[1] for triple in raw_triples})
    relation_reindex = {old: new for new, old in enumerate(raw_relations)}
    triples = [
        (entity_reindex[head], relation_reindex[relation], entity_reindex[tail])
        for head, relation, tail in raw_triples
    ]
    train, valid, test = split_edges(
        triples,
        num_entities=len(used_entities),
        num_relations=len(raw_relations),
        seed=args.seed,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
    )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    write_lines(output_dir / "train.txt", [
        (entry_label(data.i2e[used_entities[head]]), entry_label(data.i2r[raw_relations[relation]]),
         entry_label(data.i2e[used_entities[tail]]))
        for head, relation, tail in train
    ])
    write_lines(output_dir / "valid.txt", [
        (entry_label(data.i2e[used_entities[head]]), entry_label(data.i2r[raw_relations[relation]]),
         entry_label(data.i2e[used_entities[tail]]))
        for head, relation, tail in valid
    ])
    write_lines(output_dir / "test.txt", [
        (entry_label(data.i2e[used_entities[head]]), entry_label(data.i2r[raw_relations[relation]]),
         entry_label(data.i2e[used_entities[tail]]))
        for head, relation, tail in test
    ])

    # The split is intentionally duplicated only in the ind_test_graph. The
    # train_graph used by HAML subgraph generation contains train edges only.
    save_data = {
        "train_graph": {"train": train, "valid": [], "test": []},
        "ind_test_graph": {"train": train, "valid": valid, "test": test},
    }
    pickle_path = output_dir.parent / (output_dir.name + ".pkl")
    with pickle_path.open("wb") as handle:
        pickle.dump(save_data, handle, protocol=4)

    with (output_dir / "entity_mapping.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["haml_entity_id", "kgbenc_entity_id", "annotation", "entity"])
        for haml_id, original_id in enumerate(used_entities):
            item = data.i2e[original_id]
            annotation = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else "unknown"
            writer.writerow([haml_id, original_id, safe_label(annotation), safe_label(item[0])])

    with (output_dir / "relation_mapping.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["haml_relation_id", "kgbenc_relation_id", "relation"])
        for haml_id, original_id in enumerate(raw_relations):
            writer.writerow([haml_id, original_id, safe_label(data.i2r[original_id])])

    manifest = {
        "dataset": args.dataset,
        "entities": len(used_entities),
        "relations": len(raw_relations),
        "unique_triples": len(triples),
        "split": {
            "train": len(train),
            "validation": len(valid),
            "test": len(test),
            "seed": args.seed,
            "validation_fraction": args.validation_fraction,
            "test_fraction": args.test_fraction,
            "meaning": "synthetic deterministic link-prediction smoke split; not official KGBench node classification",
        },
        "leakage_policy": "train_graph contains train edges only; ind_test_graph stores held-out validation/test edges",
        "haml_data_files": ["train.txt", "valid.txt", "test.txt"],
        "pickle": pickle_path.name,
        "source_entity_ids": "KGBench integer IDs preserved in entity_mapping.tsv",
        "large_literal_policy": "literals longer than 4096 chars are represented by hash/length in the mapping; source KGBench retains the full value",
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)

    print("Created {}".format(output_dir))
    print("  entities: {}, relations: {}, triples: {}".format(
        len(used_entities), len(raw_relations), len(triples)
    ))
    print("  train/valid/test: {}/{}/{}".format(len(train), len(valid), len(test)))
    print("  pickle: {}".format(pickle_path))


if __name__ == "__main__":
    main()
