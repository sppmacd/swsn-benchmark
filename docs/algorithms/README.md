# Algorithm reproduction

This directory records reproduction attempts and integration checks for
location-aware embedding methods. A method is marked as reproduced only when
the original implementation has been run successfully on its original data.

| Method | Test owner | Official implementation | Original run | Embedding export | KGBench/GEval integration | Integration difficulty |
| --- | --- | --- | --- | --- | --- | --- |
| SE-KGE | swsn-benchmark team | [gengchenmai/se-kge](https://github.com/gengchenmai/se-kge) | Blocked before training: legacy environment and DBGeo data required | Not demonstrated; the code trains per-type `torch.nn.Embedding` modules inside a query model | Not compatible directly; an adapter for graph/query files and geographic metadata is required | High |

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
