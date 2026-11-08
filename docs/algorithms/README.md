# Algorithm reproduction

This directory records reproduction attempts and integration checks for
location-aware embedding methods. A method is marked as reproduced only when
the original implementation has been run successfully on its original data.

| Method | Test owner | Official implementation | Original run | Embedding export | KGBench/GEval integration | Integration difficulty |
| --- | --- | --- | --- | --- | --- | --- |
| SE-KGE | swsn-benchmark team | [gengchenmai/se-kge](https://github.com/gengchenmai/se-kge) | Validated through 3,000 iterations on DBGeo; full upstream run is still in progress | Exported from the checkpoint as 25,980 entity vectors in 7 types, dimension 64 | `dmg777k` typed graph/one-edge adapter generated and loaded by Python 2.7; geographic training/evaluation remains | High |

See [se-kge.md](se-kge.md) for the commit, dependency list, reproduction command,
observed blockers, and the proposed adapter boundary.

The shared KGBench export command is:

```text
uv run python -m lemb_bench.export_kgbench \
  --dataset dmg777k \
  --output data/dmg777k/triples.csv
```

The CSV is an interchange format for inspection and adapter development. It
is not claimed to be a complete SE-KGE input format: SE-KGE also expects
pickled graph structures, typed node maps, split/query files, and geographic
metadata.

The first-stage `dmg777k → SE-KGE` compatibility adapter can be generated with:

```text
uv run python scripts/algorithms/adapt_kgbench_to_se_kge.py \
  --dataset dmg777k \
  --output-dir out/algorithms/se-kge/dmg777k-adapter \
  --type-mode rdf \
  --seed 777
```

It creates a loader-compatible typed graph and one-edge query files. Its
90/5/5 edge split is synthetic and its negative lists are placeholders, so the
output is for integration testing rather than benchmark metrics. Geographic
metadata and multi-edge queries are intentionally not generated yet.

For a trained SE-KGE checkpoint, the legacy environment can export vectors
with:

```text
python scripts/algorithms/export_se_kge_embeddings.py \
  --checkpoint /home/pawel/se-kge-checkpoints/backup/<checkpoint>.pth \
  --graph-data /home/pawel/se-kge/graphqa/dbgeo/graph_data.pkl \
  --entity-map /home/pawel/se-kge/graphqa/dbgeo/entity2id.txt \
  --output /home/pawel/se-kge-checkpoints/embeddings.tsv
```
