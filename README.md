# Evaluating methods for location-aware entity embeddings

GeoRDF2Vec is an extension of RDF2Vec that accounts for geographical distances between objects in embeddings. This is a modification of RDF2Vec that applies weights depending on these distances. Our project goal is to evaluate different methods for computing such embeddings, and evaluate them on KGBench or GEval, like the GeoRDF2Vec paper.

## Run

First, `uv sync` to install dependencies.

Then `uv run python -m lemb_bench.eda_kgbench -o out` (this takes several minutes)
