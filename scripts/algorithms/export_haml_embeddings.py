#!/usr/bin/env python3
"""Export HAML entity embeddings from a trained checkpoint.

HAML does not keep a global entity embedding matrix. ``EntInit`` creates edge
features from relation parameters and ``RGCN`` computes node representations
for the supplied support graph. This exporter therefore reconstructs the
training graph, runs those two modules once, and writes the resulting global
node representations. The output is a graph-conditioned embedding export,
not a direct copy of a checkpoint parameter.
"""

from __future__ import print_function

import argparse
import csv
import pickle
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def load_entity_names(path):
    if path is None:
        return {}
    names = {}
    with open(str(path), "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            names[int(row["haml_entity_id"])] = row.get("entity", "")
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--haml-root", type=Path, required=True,
                        help="external HAML checkout containing ent_init_model.py and rgcn_model.py")
    parser.add_argument("--data-pkl", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--entity-map", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--emb-dim", type=int, required=True)
    parser.add_argument("--num-layers", type=int, required=True)
    parser.add_argument("--num-bases", type=int, required=True)
    parser.add_argument("--gpu", default="cpu")
    args = parser.parse_args()

    haml_root = str(args.haml_root)
    if haml_root not in sys.path:
        sys.path.insert(0, haml_root)

    import torch
    from ent_init_model import EntInit
    from rgcn_model import RGCN
    from utils import get_g_bidir

    device = torch.device(args.gpu)
    with open(str(args.data_pkl), "rb") as handle:
        data = pickle.load(handle)
    train_triples = data["train_graph"]["train"]
    if not train_triples:
        raise RuntimeError("train_graph.train is empty")

    num_rel = max(int(triple[1]) for triple in train_triples) + 1
    num_entities = max(max(int(triple[0]), int(triple[2])) for triple in train_triples) + 1
    model_args = SimpleNamespace(
        ent_dim=args.emb_dim,
        rel_dim=args.emb_dim,
        num_rel=num_rel,
        num_layers=args.num_layers,
        num_bases=args.num_bases,
        gpu=args.gpu,
    )

    state = torch.load(str(args.checkpoint), map_location=device)
    ent_init = EntInit(model_args).to(device)
    rgcn = RGCN(model_args).to(device)
    ent_init.load_state_dict(state["ent_init"])
    rgcn.load_state_dict(state["rgcn"])
    ent_init.eval()
    rgcn.eval()

    graph = get_g_bidir(torch.LongTensor(train_triples), model_args).to(device)
    with torch.no_grad():
        ent_init(graph)
        vectors = rgcn(graph).detach().cpu().numpy()

    if vectors.shape != (num_entities, args.emb_dim):
        raise RuntimeError("unexpected embedding shape: {}".format(vectors.shape))
    if not np.isfinite(vectors).all():
        raise RuntimeError("embedding export contains NaN or Inf")

    names = load_entity_names(args.entity_map)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["entity_id", "entity"] + ["dim_{}".format(i) for i in range(args.emb_dim)])
        for entity_id, vector in enumerate(vectors):
            writer.writerow([entity_id, names.get(entity_id, str(entity_id))] +
                            ["{:.10g}".format(float(value)) for value in vector])

    print("Exported {} entities with dimension {} to {}".format(
        vectors.shape[0], vectors.shape[1], args.output
    ))


if __name__ == "__main__":
    main()
