#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)
# Arg3: Variant 
# Arg4: Config

sudo chown -R maze:maze $1

WORKDIR=/home/maze/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/$3

mkdir -p $OUTDIR
UDIR="/home/maze/tools/U${4}-linux"
sudo chown -R maze:maze $UDIR


export PATH=$PATH:$UDIR 

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
timeout --foreground $2s $UDIR/Ultimate -tc $UDIR/config/${4}Reach.xml -s $UDIR/config/svcomp-Reach-64bit-${4}_$5.epf -i $1 &> $OUTFILE
touch $WORKDIR/.end$3

# Cleanup outputs
mv Ultimate.log outputs/Ultimate.log
mv UltimateCounterExample.errorpath outputs/UltimateCounterExample.errorpath