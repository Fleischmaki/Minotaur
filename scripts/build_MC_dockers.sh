#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

# Build base image
echo "[*] Build maze-base Docker image..."
cd $DOCKERDIR/base 
docker build -t maze-base .
echo "[*] Done!"

# Build UA image
echo "[*] Build maze-UA Docker image..."
cd $DOCKERDIR/UA
docker build -t maze-ua .
echo "[*] Done!"

# Build CPA image
echo "[*] Build maze-CPA Docker image..."
cd $DOCKERDIR/CPA
docker build -t maze-cpa .
echo "[*] Done!"

# Build seahorn image
echo "[*] Build maze-seahorn Docker image..."
cd $DOCKERDIR/seahorn
docker build -t maze-seahorn .
echo "[*] Done!"
