#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base esbmc-base ultimate-release cpa-release ultimate-bug2  esbmc-bug1 esbmc-bug2 esbmc-bug3;
    do echo "[*] Build minotaur-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --rm -t minotaur-$tool .; echo "[*] Done!";
done; 
