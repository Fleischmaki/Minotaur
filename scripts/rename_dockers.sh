#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base cbmc cpa  seahorn gen ultimate-release cpa-release mopsa ultimate 2ls symbiotic esbmc;
    do echo "[*] Build minotaur-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker image tag maze-$tool minotaur-$tool; docker rmi maze-$tool; echo "[*] Done!";
done; 
