#!/bin/bash

# Arg1: File containing targets
# Arg2: Timeout (in minutes)


WORKDIR=/home/maze/workspace

OUTDIR=$WORKDIR/outputs
mkdir -p $OUTDIR

for maze in $(cat $1)
do
    name=$(basename $maze)
    OUTFILE=$OUTDIR/res$name
    # Create dummy file to indicate running start
    touch $WORKDIR/.start$name
    timeout -k 2s $2s  cbmc  --error-label "__VERIFIER_ERROR()" ${@:3} $maze &> $OUTFILE
    touch $WORKDIR/.end$name
done