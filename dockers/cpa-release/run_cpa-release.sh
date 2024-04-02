#!/bin/bash

# Arg1: File containing targets
# Arg2: Timeout (in minutes)
# Arg3: Variant



WORKDIR=/home/maze/workspace

OUTDIR=$WORKDIR/outputs
mkdir -p $OUTDIR


for maze in $(cat $1)
do
    name=$(basename $maze)
    OUTFILE=$OUTDIR/res$name
    touch $WORKDIR/.start$name
    timeout --foreground -k 2s $2s  /home/maze/tools/cpa/scripts/cpa.sh -spec sv-comp-reachability -preprocess -$3 -timelimit $2 $maze &> $OUTFILE 
    touch $WORKDIR/.end$name
done