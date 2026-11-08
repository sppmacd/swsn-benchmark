# GeoRDF2Vec

Note: only tried to run data prep scripts. Training - starts and writes weighted graph; generating random walks takes lot of time.

## What's in the repo

- Data processsing pipeline (kgbench/geval)
- `geo_rdf2vec.py` - trains model on a given KG and saves as .model file
- kgbench (dmg777k) xgboost classification eval script
- Some experiments with hyperparameter optimization
- Implementation and data loader for GeoTransE, the algorithm they compare to in the paper. Did not try to run it.

## Input/output data format

Input: A triples CSV or any rdflib-compatible KG. Both dmg777k (kgbench) and DBPedia (GEval) supported with a single format.

Example CSV file ("full_triple_set.csv"):

```
subject,predicate,object
http://bag.basisregistraties.overheid.nl/bag/id/geometry/0003549B7CE875B77925FFA6CC2C2861,http://www.opengis.net/ont/geosparql#asWKT,"POLYGON ((4.667227191836703 51.81920171648348, 4.667236120685068 51.819203883584755, 4.6672263678506125 51.81920790458488, 4.667215533196375 51.81921064256385, 4.667204024085515 51.81921201912295, 4.667192305891625 51.8192119562197, 4.667180842410027 51.81921047467658, 4.6671700681438875 51.819207613114045, 4.667166621983456 51.81920634255311, 4.667156165455297 51.819200840285575, 4.667147349428573 51.81919433236882, 4.667140403217145 51.81918699099386, 4.667135780138812 51.819179493088576, 4.667129317016587 51.819177323131235, 4.667130389037754 51.81917558591724, 4.667152519231947 51.81913942566619, 4.667155115181994 51.81913944159352, 4.667171227731092 51.81912317217984, 4.6671213056248275 51.81910588638567, 4.66711781270861 51.81910936152579, 4.667104906737694 51.819105570038566, 4.6672250864548825 51.818990174460154, 4.667266511602796 51.819007309211784, 4.667283154068365 51.819014170743344, 4.667307706464115 51.81902433467257, 4.6673250116089795 51.81903147891019, 4.667381551819727 51.81905485454895, 4.667227191836703 51.81920171648348), (4.667299578607784 51.819087384901664, 4.667249504965178 51.81906687131927, 4.667231847882202 51.8190835896879, 4.667281925982875 51.81910382465799, 4.667299578607784 51.819087384901664))"
http://bag.basisregistraties.overheid.nl/bag/id/geometry/0003549B7CE875B77925FFA6CC2C2861,http://www.w3.org/1999/02/22-rdf-syntax-ns#type,http://www.opengis.net/ont/geosparql#Geometry
http://bag.basisregistraties.overheid.nl/bag/id/geometry/0007B6B76243781C77D67D7D535024FF,http://www.opengis.net/ont/geosparql#asWKT,"POLYGON ((5.60646698164352 53.28817643955265, 5.606439267253656 53.28823750112665, 5.6062357112245325 53.288205246608605, 5.606235278651657 53.288202749452516, 5.606196994707091 53.28819650254103, 5.606191923286311 53.28820767167587, 5.605683337943017 53.28812476428544, 5.605760639323662 53.287951115229895, 5.606275023503642 53.288033571432045, 5.606228177063838 53.28813913668662, 5.606256000755324 53.28814366848807, 5.606256697824638 53.28814215766658, 5.60646698164352 53.28817643955265))"
http://bag.basisregistraties.overheid.nl/bag/id/geometry/0007B6B76243781C77D67D7D535024FF,http://www.w3.org/1999/02/22-rdf-syntax-ns#type,http://www.opengis.net/ont/geosparql#Geometry
http://bag.basisregistraties.overheid.nl/bag/id/geometry/000B23D2133D5AE6A0CA771ECB2368B9,http://www.opengis.net/ont/geosparql#asWKT,"POLYGON ((6.7140030623806455 52.758601460629194, 6.713975225446867 52.75845416329967, 6.713983031514269 52.75845362694113, 6.713970826135439 52.75838909533757, 6.71415787087038 52.75837608214358, 6.71417723756294 52.75847847165101, 6.714193425658023 52.75847733856224, 6.714214102235433 52.758586777916214, 6.7140030623806455 52.758601460629194))"
```

Output: A `.model` file with per-node embeddings. I didn't find anything which would get us ready vectors for geval but that's just data conversion.

## Gotchas

- `pandas<2.3.0` required because of some `str`/`object` dtype changes causing preprocessing to fail
- They DON'T use kgbench-loader, instead (if you use their data preprocessing pipeline) you have to download all the files from https://github.com/pbloem/kgbench-data/tree/main/datasets/dmg777k
- I didn't find anything which would get us ready vectors for geval.
- Very computationally heavy: Uses LOTS of RAM (Sam Altman would be proud), set n_cpus to 120, etc. presumably run on some more powerful computer than a standard one, and the unmodified version may take lot of time (hours/days?).

## How would I use it

- Ignore their data preprocessing. We do our own anyway to be compatible with other algorithm implementations.
- Also ignore their evaluation scripts, but we can get inspired by them for evaluations (that is, do xgboost too?)
- I'd say - geo_rdf2vec.py then custom .model loader based on their eval scripts.
