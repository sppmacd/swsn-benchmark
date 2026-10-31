# Evaluating methods for location-aware entity embeddings

GeoRDF2Vec is an extension of RDF2Vec that accounts for geographical distances between objects in embeddings. This is a modification of RDF2Vec that applies weights depending on these distances. Our project goal is to evaluate different methods for computing such embeddings, and evaluate them on KGBench or GEval, like the GeoRDF2Vec paper.

## Run

- `git submodule update --init --recursive` to download dependencies
- `scripts/apply_patches.sh` to patch dependencies to support new Python
- `uv sync` to install dependencies.

### EDA reports

#### KDBench

`uv run python -m lemb_bench.eda_kgbench -o out`

#### GEval

- Download DBPedia dump (only once, ~12GB): `scripts/dbpedia_download.sh path/to/dbpedia/dump`
- Generate EDA report: `uv run python -m lemb_bench.eda_geval -d path/to/dbpedia/dump -o out`
