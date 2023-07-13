#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant

sudo chown -R maze:maze /home/maze/maze.c

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
let TIMEOUT=60*$2 
# Tell CPA how long it has (to select heuristics, etc.), but use timeout to ensure termination
timeout $2m /home/maze/tools/cpa/scripts/cpa.sh -spec sv-comp-reachability -preprocess -$3 -timelimit $TIMEOUT $1 &> $OUTDIR/res 
touch $WORKDIR/.end

mv output outputs/output