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

- [SE-KGE — reproduction and benchmark integration](docs/algorithms/se-kge.md)
- [HAML — reproduction and benchmark integration](docs/algorithms/haml.md)
