# Evaluating methods for location-aware entity embeddings

GeoRDF2Vec is an extension of RDF2Vec that accounts for geographical distances between objects in embeddings. This is a modification of RDF2Vec that applies weights depending on these distances. Our project goal is to evaluate different methods for computing such embeddings, and evaluate them on KGBench or GEval, like the [GeoRDF2Vec paper](https://arxiv.org/abs/2504.17099).

Detailed notes on the benchmarks: [KGBench](docs/eda/kgbench.md), [GEval](docs/eda/geval.md).

## Data

We do not store any datasets in this repository.

| Dataset | How to get it | License |
|---|---|---|
| KGBench dmg777k | downloaded automatically by [kgbench-loader](https://github.com/pbloem/kgbench-loader) | CC-BY (see also [docs](docs/eda/kgbench.md)) |
| DBpedia 2016-04 (for GEval) | `scripts/dbpedia_download.sh` (archived copy, SHA-1 verified) | CC BY-SA 3.0, GNU FDL |

## Run

- `git submodule update --init --recursive` to download submodules
- `uv sync` to install dependencies.

### EDA reports

#### KGBench

Summary of each KGBench dataset (size, classes, splits, sample triples):

`uv run python -m lemb_bench.eda_kgbench -o out`

#### GEval

- Download DBpedia dump (only once, ~12GB): `scripts/dbpedia_download.sh path/to/dbpedia/dump`
- Generate EDA report (graph statistics, geographic coverage, label distributions): `uv run python -m lemb_bench.eda_geval -d path/to/dbpedia/dump -o out`

### Algorithm reproduction

We investigate whether selected location-aware embedding methods can be
reproduced and integrated with KGBench and GEval. The experiments focus on
reproducing the original implementations, identifying dependency and data
compatibility issues, extracting entity embeddings, and assessing compatibility
with our benchmark datasets.

Implementation reviews and reproduction results are documented in
[`docs/algorithms`](docs/algorithms/README.md).

#### SE-KGE implementation

Official repository: [gengchenmai/se-kge](https://github.com/gengchenmai/se-kge)

The implementation requires a separate legacy environment because it pins
Python 2.7-era dependencies. It also requires the original DBGeo/GeoQA files
under `graphqa/dbgeo/`. After preparing the upstream checkout, run:

```bash
bash scripts/algorithms/run_se_kge.sh /path/to/se-kge
```

The wrapper does not install dependencies or download data. It records output
in `out/algorithms/se-kge/run.log`. See the
[SE-KGE reproduction notes](docs/algorithms/se-kge.md) for the tested commit,
observed blockers, and the KGBench/GEval integration assessment.

To create the adapter-independent KGBench triple export used during
compatibility analysis, run:

```bash
uv run python -m lemb_bench.export_kgbench \
  --dataset dmg777k \
  --output data/dmg777k/triples.csv
```

This CSV is an intermediate interchange format; it does not by itself create
the pickled graph, query splits, or geographic metadata required by SE-KGE.

For the first SE-KGE compatibility test on `dmg777k`, generate the typed graph
and one-edge query files with:

```bash
uv run python scripts/algorithms/adapt_kgbench_to_se_kge.py \
  --dataset dmg777k \
  --output-dir out/algorithms/se-kge/dmg777k-adapter \
  --type-mode rdf \
  --seed 777
```

This is a loader smoke-test adapter: its deterministic 90/5/5 edge split is
not the official KGBench node-classification split, and it does not invent
geographic metadata or final-evaluation negative samples.

To create a separate geographic smoke-test directory, add `--with-geo` and
use `out/algorithms/se-kge/dmg777k-adapter-geo` as the output path. This
extracts WGS84 WKT centroids into `id2geo.pkl`; it does not transform the
remaining RD geometries or create benchmark-valid negatives.

#### HAML implementation

Official repository: [LawrenceXieZ/HAML](https://github.com/LawrenceXieZ/HAML)

HAML requires a separate Python 3.7 environment and an external checkout. The
public checkout is incomplete: several runtime modules are absent from the
source tree, so use a prepared checkout as described in the
[HAML reproduction notes](docs/algorithms/haml.md). The runner defaults to CPU
and records its log in `out/algorithms/haml/`:

```bash
bash scripts/algorithms/run_haml.sh /path/to/HAML aifb_smoke4 \
  --name aifb_smoke4 --gpu cpu \
  --state_dir ./state_smoke4 --log_dir ./log_smoke4 --tb_log_dir ./tb_smoke4 \
  --num_train_subgraph 2 --num_valid_subgraph 1 \
  --num_sample_for_estimate_size 1 --rw_0 20 --rw_1 5 --rw_2 3 \
  --num_sample_cand 2 --metatrain_num_neg 2 \
  --metatrain_num_epoch 1 --metatrain_bs 1 \
  --metatrain_check_per_step 1 --indtest_eval_bs 4 \
  --emb_dim 16 --num_layers 1 --num_bases 2 --kge TransE
```

To create a leakage-safe HAML-format smoke dataset from KGBench, use:

```bash
python scripts/algorithms/adapt_kgbench_to_haml.py \
  --dataset aifb \
  --output-dir /path/to/HAML/data/aifb_smoke4
```

The adapter's split is synthetic and must not be reported as an official
KGBench result. HAML embedding export is available after training:

```bash
python scripts/algorithms/export_haml_embeddings.py \
  --haml-root /path/to/HAML \
  --data-pkl /path/to/HAML/data/aifb_smoke4.pkl \
  --checkpoint /path/to/HAML/state_smoke4/aifb_smoke4/aifb_smoke4.best \
  --entity-map /path/to/HAML/data/aifb_smoke4/entity_mapping.tsv \
  --output /path/to/HAML/embeddings.tsv \
  --emb-dim 16 --num-layers 1 --num-bases 2 --gpu cpu
```
