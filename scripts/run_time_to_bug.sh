#!/bin/bash

set -e

MINOTAUR_DIR=$(readlink -f $(dirname "$0")/..)

for bug in  cpa1 cpa2 cpa3 cpa4 \
            esbmc1 esbmc2 esbmc3 esbmc4 \
            mopsa1 \
            ultimate1 ultimate2 ultimate3 ultimate4;
    do python3 $MINOTAUR_DIR --e time_to_bug_$bug $1/$bug &;
done