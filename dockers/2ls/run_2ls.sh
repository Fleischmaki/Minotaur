#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: ID

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
timeout $2m /home/maze/tools/2ls/src/2ls/2ls $3 $1 &> $OUTDIR/res
touch $WORKDIR/.end