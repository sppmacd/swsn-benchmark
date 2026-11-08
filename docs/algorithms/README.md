# Algorithm reproduction

This directory records reproduction attempts and integration checks for
location-aware embedding methods. A method is marked as reproduced only when
the original implementation has been run successfully on its original data.

| Method | Test owner | Official implementation | Original run | Embedding export | KGBench/GEval integration | Integration difficulty |
| --- | --- | --- | --- | --- | --- | --- |
| SE-KGE | swsn-benchmark team | [gengchenmai/se-kge](https://github.com/gengchenmai/se-kge) | Validated through 3,000 iterations on DBGeo; full upstream run is still in progress | Exported from the checkpoint as 25,980 entity vectors in 7 types, dimension 64 | KGBench triples exported; direct SE-KGE training integration still requires typed graph/query/geographic adapters | High |

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

For a trained SE-KGE checkpoint, the legacy environment can export vectors
with:

```text
python scripts/algorithms/export_se_kge_embeddings.py \
  --checkpoint /home/pawel/se-kge-checkpoints/backup/<checkpoint>.pth \
  --graph-data /home/pawel/se-kge/graphqa/dbgeo/graph_data.pkl \
  --entity-map /home/pawel/se-kge/graphqa/dbgeo/entity2id.txt \
  --output /home/pawel/se-kge-checkpoints/embeddings.tsv
```
