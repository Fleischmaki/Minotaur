#!/bin/bash

set -e


DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers
for tool in base cpa-base cpa esbmc-base esbmc cbmc seahorn ultimate 2ls mopsa symbiotic;
    do echo "[*] Build minotaur-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --network=host --rm -t minotaur-$tool .; echo "[*] Done!";
done; 
echo "[*] Build minotaur-gen Docker image..."; cd "$DOCKERDIR/.."; docker build --network=host --rm -t minotaur-gen .; echo "[*] Done!";
