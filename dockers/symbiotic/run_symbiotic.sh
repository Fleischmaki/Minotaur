#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant


WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/$3

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
timeout --foreground $2s /home/maze/tools/symbiotic/scripts/symbiotic --explicit-symbolic --exit-on-error $1 &> $OUTDIR/$3 
touch $WORKDIR/.end$3