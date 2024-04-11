#!/bin/bash
# ARG 1: Outdir
# ARG 2: Outfile
ESBMC_DIR="/home/tools/esbmc/src"
mkdir -p "$1"
python3 -m gcovr -v -r $ESBMC_DIR/src/ --filter=$ESBMC_DIR/src/ --filter=$ESBMC_DIR/build/src --json "$1/$2".json $ESBMC_DIR/build/src/esbmc