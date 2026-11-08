# Algorithm reproduction

This directory records reproduction attempts and integration checks for
location-aware embedding methods. A method is marked as reproduced only when
the original implementation has been run successfully on its original data.

| Method | Test owner | Official implementation | Original run | Embedding export | KGBench/GEval integration | Integration difficulty |
| --- | --- | --- | --- | --- | --- | --- |
| SE-KGE | swsn-benchmark team | [gengchenmai/se-kge](https://github.com/gengchenmai/se-kge) | Validated through 3,000 iterations on DBGeo; full upstream run is still in progress | Exported from the checkpoint as 25,980 entity vectors in 7 types, dimension 64 | `dmg777k` typed graph/one-edge adapter generated and loaded by Python 2.7; geographic training/evaluation remains | High |
| HAML | swsn-benchmark team | [LawrenceXieZ/HAML](https://github.com/LawrenceXieZ/HAML) | CPU smoke test on a synthetic AIFB link split succeeded; clean upstream checkout is incomplete | Exported 8,285 graph-conditioned vectors of dimension 16 from the smoke checkpoint | AIFB and `dmg777k` conversion adapters validated; official evaluation remains | High |

See [se-kge.md](se-kge.md) for the commit, dependency list, reproduction command,
observed blockers, and the proposed adapter boundary.

See [haml.md](haml.md) for the source audit, CPU smoke test, checkpoint
export, KGBench adapter, and upstream compatibility blockers.

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

To also extract WGS84 centroids from the GeoSPARQL WKT literals, use a separate
output directory and add `--with-geo`:

```text
uv run python scripts/algorithms/adapt_kgbench_to_se_kge.py \
  --dataset dmg777k \
  --output-dir out/algorithms/se-kge/dmg777k-adapter-geo \
  --type-mode rdf \
  --seed 777 \
  --with-geo
```

The Python 2.7 helper `scripts/algorithms/sample_se_kge_geo_queries.py` can then
write bounded 2/3-chain query-format smoke tests. Their empty negative lists
make them unsuitable for final metrics.

For a trained SE-KGE checkpoint, the legacy environment can export vectors
with:

```text
python scripts/algorithms/export_se_kge_embeddings.py \
  --checkpoint /home/pawel/se-kge-checkpoints/backup/<checkpoint>.pth \
  --graph-data /home/pawel/se-kge/graphqa/dbgeo/graph_data.pkl \
  --entity-map /home/pawel/se-kge/graphqa/dbgeo/entity2id.txt \
  --output /home/pawel/se-kge-checkpoints/embeddings.tsv
```
