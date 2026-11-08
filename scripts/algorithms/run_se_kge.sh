#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEKGE_DIR="${1:?Usage: $0 /path/to/se-kge}"

if [[ ! -d "$SEKGE_DIR" ]]; then
    echo "error: SE-KGE directory does not exist: $SEKGE_DIR" >&2
    exit 2
fi

SEKGE_DIR="$(cd "$SEKGE_DIR" && pwd)"
LOG_DIR="$ROOT/out/algorithms/se-kge"
LOG_FILE="$LOG_DIR/run.log"

mkdir -p "$LOG_DIR"

run() {
    echo "Repository commit:"
    git -C "$SEKGE_DIR" rev-parse HEAD

    echo "Python version:"
    python --version

    echo "SE-KGE directory: $SEKGE_DIR"
    echo "Expected data directory: $SEKGE_DIR/graphqa/dbgeo"

    if [[ ! -f "$SEKGE_DIR/graphqa/dbgeo_geoqa_full.sh" ]]; then
        echo "error: dbgeo_geoqa_full.sh was not found in the supplied repository" >&2
        return 2
    fi

    if [[ ! -d "$SEKGE_DIR/graphqa/dbgeo" ]]; then
        echo "error: DBGeo data directory is missing: $SEKGE_DIR/graphqa/dbgeo" >&2
        echo "Download and extract the original DBGeo archive there before retrying." >&2
        return 2
    fi

    # The upstream shell script assumes that this output directory already
    # exists; create it here so a fresh checkout can start the experiment.
    mkdir -p "$SEKGE_DIR/graphqa/model_dir/dbgeo_test"

    cd "$SEKGE_DIR/graphqa"
    echo "Starting SE-KGE experiment..."
    bash dbgeo_geoqa_full.sh
}

set +e
run 2>&1 | tee "$LOG_FILE"
status=${PIPESTATUS[0]}
set -e

echo "Exit status: $status" | tee -a "$LOG_FILE"
exit "$status"
