#!/bin/bash

# Arg1: File containing targets
# Arg2: Timeout (in minutes)

WORKDIR=/home/usea/workspace

OUTDIR=$WORKDIR/outputs
mkdir -p $OUTDIR


for maze in $(cat $1)
do
    name=$(basename $maze)
    OUTFILE=$OUTDIR/res$name
    # Create dummy file to indicate running start
    touch $WORKDIR/.start$name
    timeout --foreground -k 2s $2s  sea $3 --inline --track=mem -m=64 -unroll-threshold=1025 ${@:4} $maze &> $OUTFILE
    touch $WORKDIR/.end$name
done