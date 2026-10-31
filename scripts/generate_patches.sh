#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
patch_dir="${1:-$root/patches}"

shopt -s nullglob
submodules=("$root"/submodules/*/)
shopt -u nullglob

if [ "${#submodules[@]}" -eq 0 ]; then
    echo "error: no submodules found under $root/submodules" >&2
    exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

generated=0

for submodule in "${submodules[@]}"; do
    name="$(basename "$submodule")"

    if ! git -C "$submodule" rev-parse --git-dir >/dev/null 2>&1; then
        echo "skipped $name (not a git checkout)" >&2
        continue
    fi

    index="$tmp_dir/index-$name"
    patch="$tmp_dir/$name.patch"

    GIT_INDEX_FILE="$index" git -C "$submodule" read-tree HEAD
    GIT_INDEX_FILE="$index" git -C "$submodule" add -A
    GIT_INDEX_FILE="$index" git -C "$submodule" diff --cached --binary HEAD > "$patch"

    if [ -s "$patch" ]; then
        generated=$((generated + 1))
    else
        rm -f "$patch"
    fi
done

if [ "$generated" -eq 0 ]; then
    echo "error: all submodules match their HEAD; nothing to generate" >&2
    exit 1
fi

mkdir -p "$patch_dir"
find "$patch_dir" -maxdepth 1 -name '*.patch' -type f -delete
mv "$tmp_dir"/*.patch "$patch_dir/"
echo "generated $generated patch file(s) in $patch_dir"
