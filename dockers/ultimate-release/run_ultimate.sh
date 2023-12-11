#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant 

sudo chown -R maze:maze $1
sudo chown -R maze:maze /home/maze/tools/$3

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res

mkdir -p $OUTDIR

export PATH=$PATH:/home/maze/tools/$3

# Create dummy file to indicate running start
touch $WORKDIR/.start
timeout $2s /home/maze/tools/$3/Ultimate.py --spec unreach.prp --witness-dir $OUTDIR --architecture 64bit --file $1 &> $OUTFILE
touch $WORKDIR/.end

# Cleanup outputs
mv Ultimate.log outputs/Ultimate.log
mv UltimateCounterExample.errorpath outputs/UltimateCounterExample.errorpath