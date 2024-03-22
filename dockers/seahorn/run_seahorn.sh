#!/bin/bash

# Arg1: Target Source code
# Arg2: Timeout (in minutes)

WORKDIR=/home/usea/workspace

INDIR=$WORKDIR/inputs
OUTDIR=$WORKDIR/outputs
OUTFILE=$OUTDIR/res$3

mkdir -p $OUTDIR

# Remove explicit initialisations
# sed -i "s/init(.*);//g" $1 
# sed -i "s/ = __VERIFIER_nondet_.*()//g" $1

# Create dummy file to indicate running start
touch $WORKDIR/.start$3
timeout --foreground $2s sea $4 --inline --track=mem -m=64 -unroll-threshold=1025 ${@:5} $1 &> $OUTFILE
touch $WORKDIR/.end$3