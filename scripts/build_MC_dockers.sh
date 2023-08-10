#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

## Build base image
echo "[*] Build maze-base Docker image..."
cd $DOCKERDIR/base 
docker build --rm -t maze-base . # Make sure to always update apt-get
echo "[*] Done!"

#Build maze-gen image
echo "[*] Build maze-generation Docker image..."
cd $DOCKERDIR/gen 
docker build --rm -t maze-gen .  # Make sure to pull latest version
echo "[*] Done!"

## Build Ultimate base image
echo "[*] Build ultimate Docker image..."
cd $DOCKERDIR/ultimate 
docker build --rm -t maze-ultimate .
echo "[*] Done!"

# Build UA image
#echo "[*] Build maze-UA Docker image..."
#cd $DOCKERDIR/UA
#docker build --rm -t maze-ua .
#echo "[*] Done!"

# Build UT image
#echo "[*] Build maze-UT Docker image..."
#cd $DOCKERDIR/UT
#docker build --rm -t maze-ut .
#echo "[*] Done!"

# Build UGC image
#echo "[*] Build maze-UGC Docker image..."
#cd $DOCKERDIR/UGC
#docker build --rm -t maze-ugc .
#echo "[*] Done!"

# Build UK image
#echo "[*] Build maze-UK Docker image..."
#cd $DOCKERDIR/UK
#docker build --rm -t maze-uk .
#echo "[*] Done!"

## Build CPA image
echo "[*] Build maze-CPA Docker image..."
cd $DOCKERDIR/cpa
docker build --rm -t maze-cpa .
echo "[*] Done!"

## Build seahorn image
echo "[*] Build maze-seahorn Docker image..."
cd $DOCKERDIR/seahorn
docker build --rm -t maze-seahorn .
echo "[*] Done!"

## Build cbmc image
echo "[*] Build maze-cbmc Docker image..."
cd $DOCKERDIR/cbmc
docker build --rm -t maze-cbmc .
echo "[*] Done!"
