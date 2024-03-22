#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: ID

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res$3

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
timeout --foreground $2s cbmc  --error-label "__VERIFIER_ERROR()" ${@:4}  $1 &> $OUTFILE
touch $WORKDIR/.end$3