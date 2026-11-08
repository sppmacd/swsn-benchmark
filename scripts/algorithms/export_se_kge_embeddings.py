#!/usr/bin/env python
"""Export SE-KGE per-type entity embeddings with stable DBGeo identifiers.

This script is intended to run in the legacy Python 2.7 SE-KGE environment.
The upstream graph loader adds a sentinel node to every per-type map and then
allocates one extra embedding row. Entity vectors are therefore read from
rows 1..N; the remaining two rows do not represent DBGeo entities.
"""

from __future__ import print_function

import argparse
import io
import os

try:
    import cPickle as pickle
except ImportError:
    import pickle

import torch


PREFIX = "enc.feat_enc.feat-"
SUFFIX = ".weight"


def read_entity_map(path):
    entities = {}
    with io.open(path, "r", encoding="utf-8") as handle:
        next(handle)
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue
            entity, index = line.rsplit("\t", 1)
            entities[int(index)] = entity
    return entities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--graph-data", required=True)
    parser.add_argument("--entity-map", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    state = torch.load(args.checkpoint, map_location="cpu")
    with open(args.graph_data, "rb") as handle:
        _, _, node_maps, _ = pickle.load(handle)
    entities = read_entity_map(args.entity_map)

    matrices = {}
    for key, value in state.items():
        if key.startswith(PREFIX) and key.endswith(SUFFIX):
            mode = key[len(PREFIX) : -len(SUFFIX)]
            matrices[mode] = value

    if not matrices:
        raise SystemExit("No per-type entity embedding matrices found in checkpoint")

    modes = sorted(matrices)
    dimensions = sorted(set(int(matrices[mode].size(1)) for mode in modes))
    if len(dimensions) != 1:
        raise SystemExit("Embedding dimensions are inconsistent: {}".format(dimensions))
    dimension = dimensions[0]

    parent = os.path.dirname(os.path.abspath(args.output))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)

    with io.open(args.output, "w", encoding="utf-8", newline="") as handle:
        header = [u"entity_id", u"entity_type", u"entity"]
        header.extend(u"dim_{}".format(i) for i in range(dimension))
        handle.write(u"\t".join(header) + u"\n")

        rows = 0
        for mode in modes:
            matrix = matrices[mode].data.cpu().numpy()
            node_ids = node_maps[mode]
            if matrix.shape[0] != len(node_ids) + 2:
                raise SystemExit(
                    "Matrix/map size mismatch for {}: {} vs {}".format(
                        mode, matrix.shape[0], len(node_ids) + 2
                    )
                )
            for local_index, entity_id in enumerate(node_ids):
                if int(entity_id) not in entities:
                    raise SystemExit("Missing entity identifier for global id {}".format(entity_id))
                values = [
                    u"{}".format(float(value))
                    for value in matrix[local_index + 1]
                ]
                row = [
                    u"{}".format(int(entity_id)),
                    mode,
                    entities[int(entity_id)],
                ] + values
                handle.write(u"\t".join(row) + u"\n")
                rows += 1

    print(
        "Exported {} entities, {} types, dimension {} to {}".format(
            rows, len(modes), dimension, args.output
        )
    )


if __name__ == "__main__":
    main()
