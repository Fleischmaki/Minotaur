#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base esbmc-base cbmc cpa seahorn gen mopsa ultimate 2ls symbiotic esbmc;
    do echo "[*] Build minotaur-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --rm -t minotaur-$tool .; echo "[*] Done!";
done; 
