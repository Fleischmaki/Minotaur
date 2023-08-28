#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant


WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
let TIMEOUT=60*$2 
timeout $2m /home/maze/tools/symbiotic/scripts/symbiotic --explicit-symbolic --undefined-are-pure --exit-on-error $1 &> $OUTDIR/res 
touch $WORKDIR/.end