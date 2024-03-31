#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant 


sudo chown -R maze:maze /home/maze/tools/$4

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res$3

mkdir -p $OUTDIR

export PATH=$PATH:/home/maze/tools/$4

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
timeout --foreground -k 2s $2s  /home/maze/tools/$4/Ultimate.py --spec unreach.prp --witness-dir $OUTDIR --architecture 64bit --file $1 &> $OUTFILE
touch $WORKDIR/.end$3
