# SE-KGE — Reproduction and benchmark integration

## 1. Algorithm

- Paper: [SE-KGE: A Location-Aware Knowledge Graph Embedding Model for Geographic Question Answering and Spatial Semantic Lifting](https://arxiv.org/abs/2004.14171)
- Implementation: [github.com/gengchenmai/se-kge](https://github.com/gengchenmai/se-kge)
- License: Apache-2.0 (as stated by the upstream repository)
- Commit inspected: `0e5a630a8403d4c7965de0f71e2e22b95f7be7bd`

## 2. Environment

The benchmark repository uses Python 3.12.10. The reproduction was executed
in WSL2/Ubuntu with the isolated legacy environment:

- Python `2.7.18`
- PyTorch `1.0.1.post2` CPU build
- NumPy `1.16.4`

The repository's `pyproject.toml` intentionally remained unchanged.

The upstream `setup.py` declares `python_requires='==2.7'` and
`requirements.txt` pins the following legacy stack:

```text
numpy==1.16.4
matplotlib==2.2.4
torch==1.0.1
sklearn==0.20.3
pyproj==2.2.2
pandas==0.24.2
geopandas==0.6.1
shapely==1.6.4.post2
scipy==1.2.1
```

This is incompatible with the benchmark's Python `>=3.12` environment. The
SE-KGE dependencies must therefore stay in a separate legacy environment or
container; they must not be added to the main `pyproject.toml`.

## 3. Running the original implementation

The upstream README instructs users to download the GeoQA/DBGeo archive and
extract it into `graphqa/dbgeo/`. The full experiment is then started with:

```bash
cd graphqa
bash dbgeo_geoqa_full.sh
```

From this repository, the repeatable wrapper is:

```bash
bash scripts/algorithms/run_se_kge.sh /path/to/se-kge
```

The wrapper records the upstream commit, Python version, command output, and
exit status in `out/algorithms/se-kge/run.log`. It does not install packages,
download data, or modify the upstream checkout.

### Result of the checked attempt

Reproduction status: **validated at 3,000 iterations; full upstream run in
progress**.

The DBGeo archive was extracted into `graphqa/dbgeo/` and the wrapper was
executed with the official `dbgeo_geoqa_full.sh` configuration. At iteration
3,000 the log reported `ema_loss=0.353618` and produced these validation
metrics:

| Query family | AUC | APR |
| --- | ---: | ---: |
| General macro average | 0.781644 | 78.354961 |
| Geographic macro average | 0.808247 | 81.023577 |

The process continued beyond 3,000 iterations after the supplied checkpoint
was copied. These are validation metrics, not final test-set scores.

The checkpoint used for the embedding export is:

```text
/home/pawel/se-kge-checkpoints/backup/dbgeo-0-projbbox-theory-concat-64-16-5400000.000000-50.000000-sigmoid-geometric-T-F-fromid2geo-0-0.0--1-512-T-T-0.50-64-2048-0.005000-0.010000-bilinear_blockdiag-min_simple-F-concat_norm_postm-leakyrelu-sigmoid-1-F-T-7.pth
```

## 4. Entity embeddings

The inspected implementation does not expose a standalone
`entity -> vector` export command, so this repository now provides a small
legacy-environment exporter at
`scripts/algorithms/export_se_kge_embeddings.py`.

- During `load_graph`, it creates a separate `torch.nn.Embedding` matrix for
  each entity type, initialized with a normal distribution.
- The graph is represented by `graph_data.pkl`, loaded as
  `(rels, adj_lists, node_maps, rid2inverse)`.
- `node_maps` maps global entity identifiers to per-type local indices.
- Training also consumes pickled train/validation/test triples and query files,
  plus geographic metadata such as `id2geo.pkl` for location-aware modes.
- The supplied checkpoint is an `OrderedDict` with 1,056 parameters and
  separate `enc.feat_enc.feat-<type>.weight` matrices.
- The matrices have dimension 64 and contain one unused leading row; the
  remaining rows map through `graph_data.pkl`'s per-type `node_maps`.
- The exporter joins those rows to the original DBGeo identifiers from
  `entity2id.txt`.
- The 3,000-iteration checkpoint exports 25,980 entity vectors across seven
  types: Agent, Event, MeanOfTransportation, Place, Thing, TopicalConcept, and
  Work.

## 5. Integration with this benchmark

### KGBench `dmg777k`

The new `lemb_bench.export_kgbench` command exports indexed KGBench triples to
a human-readable CSV:

```bash
uv run python -m lemb_bench.export_kgbench \
  --dataset dmg777k \
  --output data/dmg777k/triples.csv
```

This is a useful common starting point, but it is not directly consumable by
SE-KGE. A complete adapter would still need to:

1. choose and encode entity types and relation templates;
2. build `graph_data.pkl` with adjacency lists and inverse relations;
3. produce the required pickled train/validation/test triples and query files;
4. preserve stable entity identifiers through the per-type `node_maps`; and
5. provide geographic metadata in the format expected by the selected
   location-aware mode.

KGBench's generic RDF-like triples do not by themselves guarantee the
geographic annotations required by SE-KGE. Geographic coverage must be
measured and a mapping strategy documented before training.

### GEval / DBpedia

The same compatibility gap applies to DBpedia/GEval. DBpedia TTL data would
need conversion into SE-KGE's typed pickled graph representation, including
the expected query splits and geographic metadata. Entity identifiers can be
preserved as strings in an adapter, but the upstream model internally uses
integer global IDs and per-type local IDs, so the mapping must be saved with
the output embeddings.

The generated vectors now include the original DBGeo entity IDs, so they are
structurally suitable for a GEval adapter. Direct GEval evaluation has not
yet been run; the remaining work is to verify identifier overlap and align the
exported vectors with the GEval label files.

## 6. Local validation

- The wrapper passed shell syntax validation and was executed against the
  cloned upstream checkout.
- The wrapper produced `out/algorithms/se-kge/run.log`; it created the missing
  upstream output directory and reached training.
- The exporter CLI help and a CSV smoke test passed.
- A real export on the small KGBench `aifb` dataset passed and wrote 29,043
  triples. This validates the loader/mapping path without adding data to the
  repository.
- A full `dmg777k` export passed and wrote 777,124 triples to
  `data/dmg777k/triples.csv`.
- The checkpoint structure and per-type embedding matrices were inspected, and
  the exporter wrote 25,980 rows to
  `/home/pawel/se-kge-checkpoints/embeddings-3000.tsv`.

## 7. Conclusion

- Reproduction status: **validated at 3,000 iterations; full run in progress**.
- Integration difficulty: **high**.
- Main blockers: the legacy runtime is isolated but fragile, the full upstream
  training run is still in progress, and KGBench/GEval require a typed
  graph/query adapter rather than the simple triple CSV.
- Completed in this repository: repeatable runner, KGBench triple exporter,
  SE-KGE checkpoint embedding exporter, compatibility analysis, and measured
  3,000-iteration reproduction results.
- Next implementation steps: record final test metrics after the full run,
  build the typed graph/query adapter for KGBench, and evaluate the exported
  vectors against GEval after confirming identifier coverage.
