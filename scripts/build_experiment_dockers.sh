#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

for tool in base gen \
    cpa-base cpa-bug1 cpa-fixed1 cpa-bug2 cpa-fixed2 cpa-bug3 cpa-fixed3 \
    ultimate-bug1 ultimate-bug2 ultimate-fixed1 ultimate-fixed2 \
    esbmc-base esbmc-bug1 esbmc-fixed1 esbmc-bug2 esbmc-fixed2 esbmc-bug3 esbmc-fixed3 esbmc-bug4 esbmc-fixed4;
    do echo "[*] Build minotaur-$tool Docker image..."; cd "$DOCKERDIR/$tool"; docker build --rm -t minotaur-$tool .; echo "[*] Done!";
done; 
