#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base  cbmc cpa  seahorn gen ultimate-release cpa-release mopsa ultimate 2ls symbiotic esbmc;
    do echo "[*] Build maze-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --no-cache --rm -t maze-$tool .; echo "[*] Done!";
done; 