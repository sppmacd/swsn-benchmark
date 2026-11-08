# HAML — reproduction and benchmark integration

## 1. Algorithm and implementation

- Paper: [Hierarchical Adaptive Meta-Learning for Geographic Knowledge Graph Representation Learning](https://onlinelibrary.wiley.com/doi/10.1111/tgis.70245)
- Implementation: [LawrenceXieZ/HAML](https://github.com/LawrenceXieZ/HAML)
- License: **Not stated in the checked-out repository**; verify the authors'
  distribution terms before redistribution.
- Tested upstream commit: `168127d` (`dataset`)

HAML is a graph-conditioned geographic knowledge-graph representation model.
It samples local subgraphs, initializes relation-dependent edge features, and
uses an RGCN plus a KGE scoring model. It is not a plain entity lookup table:
the entity representations are produced by `EntInit` and `RGCN` for a supplied
support graph. The implementation supports link-prediction-style evaluation
and the checkpoint contains `ent_init`, `rgcn`, and `kge_model` state
dictionaries.

HAML uses geographic structure indirectly through the input graph and its
region-guided subgraph sampling. The inspected code has no coordinate encoder,
distance loss, or GeoSPARQL parser. Coordinates therefore cannot be passed as
an independent feature without extending the model or materializing them as
graph relations/entities.

## 2. Source audit and upstream blockers

The public checkout was inspected rather than relying on its README. The
following facts were confirmed from `main.py`, `pre_process.py`, the tracked
Python bytecode, and the reconstructed runtime modules:

- The README's `--kge haml-model` example is invalid. `main.py` accepts only
  `TransE`, `DistMult`, `ComplEx`, `RotatE`, and `ConvE`.
- `main.py` defaults to `--gpu cuda:0`; CPU execution requires
  `--gpu cpu`.
- Input files are `data/<dataset>/train.txt`, `valid.txt`, and `test.txt`.
  Each line is three tab-separated labels: head, relation, tail.
- If the pickle is absent, `pre_process.data2pkl` reads all three files, then
  calls `reidx(train + valid + test)`. Consequently its `train_graph.train`
  includes validation and test edges. This is a data-leakage bug.
- The same function comments out creation of `ind_test_graph`, while
  `Trainer` expects that key during final inductive evaluation. A clean run
  therefore reaches a missing-data failure unless the pickle is prepared with
  the expected structure.
- Subgraph LMDB sizing is underestimated for small sampling settings and can
  fail with `lmdb.MapFullError` during generation. The HAML fork uses a larger
  map-size multiplier.
- The GitHub checkout has the source files for `main.py`, `pre_process.py`,
  `datasets.py`, `ent_init_model.py`, `meta_trainer.py`, `utils.py`, and
  related bytecode, but it does not contain the runtime sources for
  `subgraph.py`, `trainer.py`, `kge_model.py`, `rgcn_model.py`, and
  `post_trainer.py`. The HAML fork reconstructs these modules from the tracked
  CPython 3.7 bytecode and applies the missing evaluation and parser fixes. A
  fresh upstream clone is therefore **not runnable as-is**.

Because of the missing source files, a clean upstream checkout is not runnable
as-is. The reconstructed sources and fixes are now maintained in this
benchmark's HAML submodule at commit `a8e5efa` on the fork's `main` branch.

## 3. Tested environment

The smoke test ran in WSL2/Ubuntu in an isolated Conda environment:

```text
Python 3.7.16
PyTorch 1.13.1 (CPU)
DGL 0.9.1
LMDB 1.4.1
NumPy 1.21.6
pandas 1.3.5
SciPy 1.7.3
TensorBoard 2.11.2
```

The following setup is the tested dependency boundary; HAML dependencies are
not added to the benchmark `pyproject.toml`:

```bash
conda create -n haml python=3.7.16 -y
conda activate haml
conda install -y pytorch==1.13.1 cpuonly -c pytorch
conda install -y mkl=2020.2 intel-openmp=2023.0
pip install dgl==0.9.1 lmdb==1.4.1 numpy==1.21.6 pandas==1.3.5 \
    scipy==1.7.3 tqdm tensorboard==2.11.2
```

`lmdb==1.4.1` is important for Python 3.7. The newer LMDB wheel tested first
failed to import because it used a Python C-API unavailable in that runtime.
The MKL/OpenMP pins were needed to avoid a PyTorch `iJIT_NotifyEvent` import
error in the WSL environment.

## 4. Running HAML

The repository runner accepts an external HAML checkout, a dataset name, and
additional `main.py` arguments. It records the upstream commit, Python
version, installed packages, command, output, and exit status in
`out/algorithms/haml/`:

```bash
bash scripts/algorithms/run_haml.sh /path/to/HAML aifb_smoke4 \
  --name aifb_smoke4 \
  --state_dir ./state_smoke4 \
  --log_dir ./log_smoke4 \
  --tb_log_dir ./tb_smoke4 \
  --num_train_subgraph 2 \
  --num_valid_subgraph 1 \
  --num_sample_for_estimate_size 1 \
  --rw_0 20 --rw_1 5 --rw_2 3 \
  --num_sample_cand 2 \
  --metatrain_num_neg 2 \
  --metatrain_num_epoch 1 \
  --metatrain_bs 1 \
  --metatrain_check_per_step 1 \
  --emb_dim 16 \
  --num_layers 1 --num_bases 2 \
  --indtest_eval_bs 4 \
  --kge TransE
```

The runner defaults to CPU through `HAML_GPU=cpu`; set `HAML_GPU=cuda:0` only
when the external environment has a compatible CUDA stack. It returns the
training process' exit code.

## 5. Reproduction result

A bounded smoke test was executed through `submodules/HAML` at commit
`a8e5efa`, using a deterministic AIFB link-prediction split generated by the
adapter below. It used two training subgraphs, one validation subgraph, one
meta-training epoch, batch size one, embedding size 16, one RGCN layer, two
bases, `TransE`, and CPU execution.

The run completed successfully and produced a checkpoint:

```text
submodules/HAML/state_submodule_smoke/aifb_submodule_smoke/aifb_submodule_smoke.best
```

Observed final inductive smoke metrics were:

```text
MRR       0.1205
Hits@1    0.0532
Hits@5    0.1286
Hits@10   0.1822
```

These are smoke-test link-prediction values, not official AIFB or KGBench
benchmark results. The original `mht` files are present in the HAML submodule,
but a full `mht` training run was not attempted.

## 6. Entity embedding export

The repository provides `scripts/algorithms/export_haml_embeddings.py`. It
loads `ent_init` and `rgcn` from the checkpoint, reconstructs the training
graph from `train_graph.train`, and computes the node representations under
`torch.no_grad()`. It writes a TSV with:

```text
entity_id    entity    dim_0 ... dim_(d-1)
```

This is a graph-conditioned export. It is not a global entity parameter copied
from the checkpoint, because HAML computes entity states dynamically for the
support graph.

The checked export command was:

```bash
python scripts/algorithms/export_haml_embeddings.py \
  --haml-root /path/to/swsn-benchmark/submodules/HAML \
  --data-pkl /path/to/swsn-benchmark/submodules/HAML/data/aifb_submodule_smoke.pkl \
  --checkpoint /path/to/swsn-benchmark/submodules/HAML/state_submodule_smoke/aifb_submodule_smoke/aifb_submodule_smoke.best \
  --entity-map /path/to/swsn-benchmark/submodules/HAML/data/aifb_submodule_smoke/entity_mapping.tsv \
  --output /path/to/swsn-benchmark/submodules/HAML/state_submodule_smoke/aifb_submodule_smoke/embeddings.tsv \
  --emb-dim 16 --num-layers 1 --num-bases 2 --gpu cpu
```

It exported 8,285 entity vectors of dimension 16. A TSV validation pass found
8,285 data rows, 16 dimensions, and zero NaN/Inf rows. The original KGBench
integer IDs are preserved in `entity_mapping.tsv` and the embedding TSV uses
the HAML entity index together with the corresponding label.

## 7. KGBench adapter

`adapt_kgbench_to_haml.py` converts a KGBench graph into the HAML directory
layout and writes the pickle expected by `main.py`:

```bash
python scripts/algorithms/adapt_kgbench_to_haml.py \
  --dataset aifb \
  --output-dir /path/to/HAML/data/aifb_smoke4
```

The checked AIFB conversion produced 8,285 entities, 45 relations, and
29,043 unique triples, split into 26,139/1,452/1,452 train/validation/test
edges. The split is synthetic and intended for link-prediction smoke testing;
KGBench's official AIFB task is node classification.

The adapter writes:

- HAML `train.txt`, `valid.txt`, and `test.txt` files;
- a leakage-safe pickle where `train_graph.train` contains only training
  edges, while `ind_test_graph` contains the held-out split;
- `entity_mapping.tsv`, `relation_mapping.tsv`, and `manifest.json`.

Labels are made single-line and long literals are replaced by deterministic
SHA-256 placeholders in the text representation; empty labels use an explicit
`<empty>` token because HAML strips trailing whitespace while parsing. The
original KGBench data
and integer identifiers remain the source of truth through the mapping files.
The corrected mapping writer uses proper TSV quoting.

The upstream `pre_process.data2pkl` was run on a copy of the generated AIFB
text files. It parsed 29,043/1,452/1,452 train/validation/test triples, but its
result had `train_graph.train` containing all 29,043 triples and no
`ind_test_graph`, confirming the leakage and missing-key issues described
above. The benchmark adapter avoids both issues by writing the pickle directly.

The `dmg777k` conversion command is:

```bash
python scripts/algorithms/adapt_kgbench_to_haml.py \
  --dataset dmg777k \
  --output-dir out/algorithms/haml/dmg777k
```

The conversion was executed successfully. It produced 341,270 entities, 60
relations, and 777,124 unique triples, split into 699,412/38,856/38,856
train/validation/test edges. The output files are ignored by Git because they
are generated data. This remains a conversion/format smoke test: full HAML
training on `dmg777k` was not run because the graph is much larger than the
bounded CPU experiment, and no official KGBench link-prediction split has been
defined here.

## 8. GEval/DBpedia and comparison scope

HAML can consume a DBpedia-derived triple graph after the same identifier and
split conversion, but it does not consume GEval labels or coordinates directly.
For a fair comparison with GeoRDF2Vec and SE-KGE, the benchmark still needs:

1. a common entity universe and identifier policy;
2. a documented train/validation/test policy without HAML's `data2pkl` leak;
3. a decision about whether geographic relations are included as ordinary KG
   edges or represented by a new spatial feature module;
4. a consistent way to export graph-conditioned vectors for every benchmark
   entity; and
5. task-specific evaluation code using the same labels and metrics.

## 9. Status

- Original clean upstream checkout: **Blocked** by missing runtime source
  modules and an incomplete preprocessing/evaluation path.
- HAML fork submodule on CPU: **Smoke-tested successfully at `a8e5efa`**.
- Entity embedding export: **Implemented and validated on the smoke
  checkpoint**.
- AIFB adapter: **Implemented and validated**.
- `dmg777k` conversion: **Implemented and validated; full training not
  tested**.
- Official HAML-versus-GeoRDF2Vec/SE-KGE benchmark: **Not tested**.
