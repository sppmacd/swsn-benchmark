# KGBench

KGBench[^kgbench] is a set of knowledge graphs with nodes labeled by classes. It is useful for benchmarking classification accuracy.

Main paper: _kgbench: A Collection of Knowledge Graph Datasets for Evaluating Relational and Multimodal Machine Learning_ https://openreview.net/forum?id=yeK_9wxRDbA

The `kgbench-loader` pip package[^kgbenchloader] provides automatic loaders, so no data loading code is required from our side.

## Available datasets

The loader implements the following datasets:[^kgbenchloader]

| name       | description                                                                                                        | license                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------ | ------------------------ |
| `aifb`     | "the AIFB research institute in terms of its staff, research group, and publications"                              | ?                        |
| `am`       | Amsterdam Museum dataset                                                                                           | CC-BY                    |
| `amplus`   | Extended version of the AM data                                                                                    | CC-BY                    |
| `bgs`      | (TODO)                                                                                                             | ?                        |
| `dblp`     | Subset of the DBLP database[^dblp] (computer science bibliography), enriched with author information from Wikidata | CC0                      |
| `dmgfull`  | Monuments in the Netherlands                                                                                       | CC-BY                    |
| `dmg777k`  | Subset of dmgfull                                                                                                  | CC-BY                    |
| `mdgender` | (TODO)                                                                                                             | CC0+no rights for images |
| `mdgenre`  | Movie data extracted from Wikidata                                                                                 | CC0+no rights for images |
| `mutag`    | (TODO)                                                                                                             | ?                        |

Each datasets has a separate set of classes.

The GeoRDF2Vec[^geordf2vec] uses `dmg777k` for geographic embedding evaluation and this one looks most promising for us. `bgs` looks related to some stones/rocks and seems to have some geographic data too - but (TODO) check if we have any positions/coordinates for algorithms to take advantage of?

## Gotchas

- No class names seem to be available in general, only class IDs.
- The datasets are in general very sparsely classified (most datasets have less than 10% of IRI nodes annotated).
- Some datasets ("legacy" ones) don't store distinction between literal & IRI ("normal node") in the entity itself - we infer this from entity name (we check if it looks like an URI)
- 

## References

- [^dblp]: https://dblp.org/
- [^geordf2vec]: https://arxiv.org/pdf/2504.17099v1
- [^kgbench]: https://openreview.net/pdf?id=yeK_9wxRDbA
- [^kgbenchloader]: https://github.com/pbloem/kgbench-loader
