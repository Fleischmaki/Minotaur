#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base cbmc cpa  seahorn gen ultimate-release cpa-release mopsa ultimate 2ls symbiotic esbmc;
    do echo "[*] Build minotaur-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --rm -t minotaur$tool .; echo "[*] Done!";
done; 
echo "[*] Build minotaur$tool Docker image..."; cd "$DOCKERDIR/base"; docker build --rm -t minotaur-$tool .; echo "[*] Done!";
