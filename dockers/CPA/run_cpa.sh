#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: ID

sudo chown -R maze:maze /home/maze/maze.c

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
let TIMEOUT=60*$2
/home/maze/tools/cpa/scripts/cpa.sh -preprocess -svcompNotl -timelimit $TIMEOUT $1 &> $OUTDIR/res
touch $WORKDIR/.end

mv output outputs/output