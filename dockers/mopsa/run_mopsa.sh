#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant

# 

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res$3

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
timeout --foreground $2s /home/maze/tools/mopsa-analyzer/bin/mopsa -c-check-unsigned-implicit-cast-overflow false -no-color -config c/$4.json -additional-stubs c/mopsa/svcomp.c -ccopt -fbracket-depth=2048 $1 >  $OUTFILE 
touch $WORKDIR/.end$3
