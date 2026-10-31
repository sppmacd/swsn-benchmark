#!/bin/bash

# Taken from https://github.com/MartinBoeckling/GeoRDF2Vec/blob/main/data_preparation/dbpedia_download.sh
# Changes:
# - Fixed download URL (the original one is dead)
# - Added SHA-1 validation

# Download and decompress article categories
filename=(
    article_categories_en.ttl.bz2
    instance_types_en.ttl.bz2
    instance_types_transitive_en.ttl.bz2
    mappingbased_objects_en.ttl.bz2
    skos_categories_en.ttl.bz2
    geo_coordinates_mappingbased_en.ttl.bz2
)

# SHA-1's taken from GEval README, except geo_coordinates_mappingbased_en
# which was computed locally (it's not published anywhere)
declare -A sha1=(
    [article_categories_en.ttl]=b3d1e5c5ef25c85dd89995732a5957e21de29ead
    [instance_types_en.ttl]=29fec5589a51d175ef11adcb0f7e5f6821c7ed9c
    [instance_types_transitive_en.ttl]=3001cb5898fda21b590abab936c75cb04783c731
    [mappingbased_objects_en.ttl]=f2268b9d19bdbd7abfcad408e82805bd81f29610
    [skos_categories_en.ttl]=887e02a41e69476eabd0df285a7f76d9cd6bf433
    [geo_coordinates_mappingbased_en.ttl]=2cd4778d5b5c01b9521c1b9ed1b2ea237c098577
)

set -euo pipefail

base_path=${1:?usage: $0 <output-directory>}
mkdir -p "$base_path"

base_url='https://web.archive.org/web/2id_/https://downloads.dbpedia.org/2016-04/core'

for file in "${filename[@]}"; do
    output_path="${base_path}/${file}"
    ttl_path="${output_path%.bz2}"
    file_url="${base_url}/${file}"

    wget --tries=5 --waitretry=10 "$file_url" -O "$output_path"
    bzip2 -f -d "$output_path"

    actual=$(sha1sum "$ttl_path" | cut -d ' ' -f 1)
    expected=${sha1[$(basename "$ttl_path")]}

    if [ "$actual" != "$expected" ]; then
        echo "SHA-1 mismatch for $ttl_path" >&2
        echo "  expected: $expected" >&2
        echo "  actual:   $actual" >&2
        exit 1
    fi
done
