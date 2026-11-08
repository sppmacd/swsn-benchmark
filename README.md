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

#### SE-KGE

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
