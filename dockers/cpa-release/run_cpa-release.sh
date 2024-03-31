#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant



WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res$3

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
# Tell CPA how long it has (to select heuristics, etc.), but use timeout to ensure termination
timeout --foreground $2s -k 2s /home/maze/tools/cpa/scripts/cpa.sh -spec sv-comp-reachability -preprocess -$4 -timelimit $2 $1 &> $OUTFILE 
touch $WORKDIR/.end$3