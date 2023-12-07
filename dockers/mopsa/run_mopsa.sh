#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant

sudo chown -R maze:maze $1

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

# Create dummy file to indicate running start
touch $WORKDIR/.start
timeout --foreground $2s /home/maze/tools/mopsa-analyzer/bin/mopsa -c-check-unsigned-implicit-cast-overflow false -no-color -config c/$3.json -additional-stubs c/mopsa/svcomp.c -ccopt -fbracket-depth=2048 $1 >  $OUTDIR/res 
touch $WORKDIR/.end
