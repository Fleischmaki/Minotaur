#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)

sudo chown -R maze:maze /home/maze/maze.c
sudo chown -R maze:maze /home/maze/tools/UA

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

export PATH=$PATH:/home/maze/tools/UA

# Create dummy file to indicate running start
touch $WORKDIR/.start
timeout $2m /home/maze/tools/UA/Ultimate.py --spec unreach.prp --witness-dir $OUTDIR --architecture 64bit --file $1 &> $OUTFILE
touch $WORKDIR/.end

# Cleanup outputs
mv Ultimate.log outputs/Ultimate.log
mv UltimateCounterExample.errorpath outputs/UltimateCounterExample.errorpath