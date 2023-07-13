#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)

WORKDIR=/home/usea/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
timeout $2m sea $3 $1 > $OUTFILE
touch $WORKDIR/.end