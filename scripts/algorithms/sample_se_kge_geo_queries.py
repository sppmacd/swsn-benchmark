#!/usr/bin/env python
"""Sample a bounded, structural SE-KGE geographic multi-edge query set.

Run this script with the Python 2.7 environment used by the upstream SE-KGE
checkout. It deliberately creates empty negative lists and therefore validates
only the query-file format; it is not suitable for metrics.
"""

from __future__ import print_function

import argparse
import random
import os
import sys

try:
    import cPickle as pickle
except ImportError:
    import pickle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--se-kge-root", required=True, help="upstream SE-KGE checkout")
    parser.add_argument("--data-dir", required=True, help="adapter directory containing graph_data.pkl")
    parser.add_argument("--num-test-queries", type=int, default=100)
    parser.add_argument("--num-validation-queries", type=int, default=20)
    parser.add_argument("--embed-dim", type=int, default=10)
    args = parser.parse_args()

    graphqa_dir = os.path.join(os.path.abspath(args.se_kge_root), "graphqa")
    if graphqa_dir not in sys.path:
        sys.path.insert(0, graphqa_dir)

    from netquery.data_utils import load_queries, pickle_load
    from netquery.dbgeo.data_utils import load_graph

    data_dir = os.path.abspath(args.data_dir)
    if not data_dir.endswith(os.sep):
        data_dir += os.sep
    id2geo_path = os.path.join(data_dir, "id2geo.pkl")
    if not os.path.exists(id2geo_path):
        raise RuntimeError("{} is missing; run the adapter with --with-geo first".format(id2geo_path))

    graph = load_graph(data_dir, args.embed_dim)[0]
    raw_id2geo = pickle_load(id2geo_path)
    # The upstream sampler indexes node2type, which only contains nodes that
    # occur in the training adjacency lists. A geometry can legitimately be
    # present only in a held-out edge, so remove those candidates first.
    id2geo = {
        entity_id: point
        for entity_id, point in raw_id2geo.items()
        if entity_id in graph.node2type
    }
    # The upstream sampler has no attempt limit. Keep only nodes with at least
    # three outgoing geographic neighbours, which is sufficient for the 2/3
    # edge smoke queries and prevents an endless rejection loop on isolated
    # geometry nodes.
    arity_candidates = {
        entity_id
        for entity_id, mode in graph.get_nodes_by_arity(3, id2geo)
    }
    id2geo = {
        entity_id: point
        for entity_id, point in id2geo.items()
        if entity_id in arity_candidates
    }
    print("geographic candidates: {} -> {} after training-graph filter and arity filter".format(
        len(raw_id2geo), len(id2geo)
    ))
    if not id2geo:
        raise RuntimeError("no geographic training nodes support 2/3-edge queries")

    candidate_ids = list(id2geo.keys())

    def sample_queries(query_type, count, seed):
        random.seed(seed)
        queries = []
        attempts = 0
        max_attempts = max(100, count * 100)
        while len(queries) < count and attempts < max_attempts:
            entity_id = random.choice(candidate_ids)
            mode = graph.node2type[entity_id]
            try:
                query = graph.sample_query_subgraph_bytype(
                    query_type, start_node=(entity_id, mode)
                )
            except (KeyError, IndexError, ValueError):
                query = None
            if query is not None:
                # Empty negatives intentionally make this a loader smoke test.
                queries.append((query, [], None))
            attempts += 1
        return queries, attempts

    for split, count, seed in (
        ("val", args.num_validation_queries, 1001),
        ("test", args.num_test_queries, 2001),
    ):
        for arity in (2, 3):
            query_type = "{}-chain".format(arity)
            queries, attempts = sample_queries(query_type, count, seed + arity)
            if len(queries) != count:
                raise RuntimeError(
                    "sampled {} of {} {} queries after {} attempts".format(
                        len(queries), count, query_type, attempts
                    )
                )
            output = os.path.join(data_dir, "{}_queries_{}-geo.pkl".format(split, arity))
            with open(output, "wb") as handle:
                pickle.dump(queries, handle, protocol=2)
            loaded = load_queries(output)
            print("{}: {} queries ({} attempts; loader read {})".format(
                os.path.basename(output), len(queries), attempts, len(loaded)
            ))


if __name__ == "__main__":
    main()
