#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base 2ls cbmc cpa esbmc ultimate seahorn symbiotic gen;
    do echo "[*] Build maze-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --rm -t maze-$tool .; echo "[*] Done!";
done; 