#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
    echo "Usage: $0 /path/to/HAML [dataset] [main.py arguments...]" >&2
    echo "Environment: HAML_PYTHON (default: python), HAML_GPU (default: cpu), HAML_LOG_DIR" >&2
}

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 2
fi

HAML_ROOT="$1"
shift
DATA_NAME="${1:-mht}"
if [[ $# -gt 0 ]]; then
    shift
fi

if [[ ! -d "$HAML_ROOT" ]]; then
    echo "error: HAML directory does not exist: $HAML_ROOT" >&2
    exit 2
fi

HAML_ROOT="$(cd "$HAML_ROOT" && pwd)"
PYTHON_BIN="${HAML_PYTHON:-python}"
GPU="${HAML_GPU:-cpu}"
LOG_DIR="${HAML_LOG_DIR:-$ROOT/out/algorithms/haml}"
LOG_FILE="$LOG_DIR/${DATA_NAME}.log"
DGLBACKEND="${DGLBACKEND:-pytorch}"

mkdir -p "$LOG_DIR"

required_files=(main.py subgraph.py trainer.py kge_model.py rgcn_model.py post_trainer.py)
for required in "${required_files[@]}"; do
    if [[ ! -f "$HAML_ROOT/$required" ]]; then
        echo "error: HAML checkout is missing $required: $HAML_ROOT/$required" >&2
        echo "The public upstream checkout does not contain all runtime modules; see docs/algorithms/haml.md." >&2
        exit 2
    fi
done

run() {
    cd "$HAML_ROOT"

    echo "HAML directory: $HAML_ROOT"
    echo "Dataset: $DATA_NAME"
    echo "DGL backend: $DGLBACKEND"
    echo "Repository commit:"
    git rev-parse HEAD

    echo "Python version:"
    "$PYTHON_BIN" --version

    echo "Python executable:"
    "$PYTHON_BIN" -c 'import sys; print(sys.executable)'

    echo "Installed packages:"
    "$PYTHON_BIN" -m pip freeze

    echo "Command:"
    printf '%q ' "$PYTHON_BIN" main.py --data_name "$DATA_NAME" --gpu "$GPU" "$@"
    echo

    DGLBACKEND="$DGLBACKEND" "$PYTHON_BIN" main.py --data_name "$DATA_NAME" --gpu "$GPU" "$@"
}

set +e
run "$@" 2>&1 | tee "$LOG_FILE"
status=${PIPESTATUS[0]}
set -e

echo "Exit status: $status" | tee -a "$LOG_FILE"
exit "$status"
