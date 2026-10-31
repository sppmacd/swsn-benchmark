#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
patch_dir="${1:-$root/patches}"

if [ ! -d "$patch_dir" ]; then
    echo "error: patch directory $patch_dir does not exist" >&2
    exit 1
fi

patch_dir="$(cd "$patch_dir" && pwd)"

shopt -s nullglob
patches=("$patch_dir"/*.patch)
shopt -u nullglob

if [ "${#patches[@]}" -eq 0 ]; then
    echo "error: no patches found in $patch_dir" >&2
    exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for patch in "${patches[@]}"; do
    name="$(basename "$patch" .patch)"
    submodule="$root/submodules/$name"

    if ! git -C "$submodule" rev-parse --git-dir >/dev/null 2>&1; then
        echo "error: $submodule is not a git checkout" >&2
        exit 1
    fi

    GIT_INDEX_FILE="$tmp_dir/patch-$name" git -C "$submodule" read-tree HEAD
    if ! GIT_INDEX_FILE="$tmp_dir/patch-$name" git -C "$submodule" apply --cached --check "$patch"; then
        echo "error: $patch does not apply to the HEAD of $submodule" >&2
        exit 1
    fi
    GIT_INDEX_FILE="$tmp_dir/patch-$name" git -C "$submodule" apply --cached "$patch"
    desired="$(GIT_INDEX_FILE="$tmp_dir/patch-$name" git -C "$submodule" write-tree)"

    GIT_INDEX_FILE="$tmp_dir/work-$name" git -C "$submodule" add -A
    actual="$(GIT_INDEX_FILE="$tmp_dir/work-$name" git -C "$submodule" write-tree)"

    if [ "$actual" = "$desired" ]; then
        echo "unchanged $name"
        continue
    fi

    if [ -n "$(git -C "$submodule" status --porcelain)" ]; then
        git -C "$submodule" stash push --include-untracked --quiet --message "apply_patches: $name"
    fi

    git -C "$submodule" reset --hard --quiet HEAD
    git -C "$submodule" clean -fd --quiet
    git -C "$submodule" apply "$patch"
    echo "applied $name"
done
