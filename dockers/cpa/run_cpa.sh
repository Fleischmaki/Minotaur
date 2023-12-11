#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant

sudo chown -R maze:maze $1

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
# Tell CPA how long it has (to select heuristics, etc.), but use timeout to ensure termination
timeout $2s /home/maze/tools/cpa/scripts/cpa.sh -64 -spec sv-comp-reachability -preprocess -$3 -timelimit $2 $1 &> $OUTDIR/res 
touch $WORKDIR/.end