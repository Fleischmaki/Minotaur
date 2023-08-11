#!/bin/bash

set -e

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

## Build base image
echo "[*] Build maze-base Docker image..."
cd $DOCKERDIR/base 
docker build -t maze-base .
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

## Build symbiotic image
echo "[*] Build maze-symbiotic Docker image..."
cd $DOCKERDIR/symbiotic
docker build --rm -t maze-symbiotic .
echo "[*] Done!"