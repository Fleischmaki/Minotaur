#!/bin/bash

while getopts a:w:h:o:r:n:c:g:s:e:b:m:t: option
do
    case "${option}"
    in
    a) ALGORITHM=${OPTARG};;
    w) WIDTH=${OPTARG};;
    h) HEIGHT=${OPTARG};;
    o) OUTPUT_DIR=${OPTARG};;
    r) SEED=${OPTARG};;
    n) NUMB=${OPTARG};;
    c) CYCLE=${OPTARG};;
    g) GEN=${OPTARG};;
    s) SMT_PATH=${OPTARG};;
    e) EXIT=${OPTARG};;
    b) BUGTYPE=${OPTARG};;
    m) T_NUMB=${OPTARG};;
    t) T_TYPE=${OPTARG};;
    esac
done

if [ -z ${ALGORITHM+x} ]; then
    echo "No algorithm selected. Exiting..."
    exit 1
fi

if [[ -z ${WIDTH+x} || -z ${HEIGHT+x} ]]; then
    echo "Size of maze was not specified. Exiting..."
    exit 1
fi

case "${WIDTH#[-+]}" in
    *[!0-9]* | '')
        echo "Invalid size input: width should be a positive integer"
        exit 1;;
esac

case "${HEIGHT#[-+]}" in
    *[!0-9]* | '')
        echo "Invalid size input: height should be a positive integer"
        exit 1;;
esac

(($WIDTH < 3)) && { echo "Invalid size input: width should be greater than 2"; exit 1; }
(($HEIGHT < 3)) && { echo "Invalid size input: height should be greater than 2"; exit 1; }

if [ -z ${OUTPUT_DIR+x} ]; then
    echo "Output directory not specified. Exiting..."
    exit 1
fi

if [ -z ${NUMB+x} ]; then
    echo "NOTE: The number of mazes to generate was not specified. Default value of 1 will be used."
    NUMB=1
fi

case "${NUMB#[-+]}" in
    *[!0-9]* | '')
        echo "Invalid input: number of mazes to generate should be a positive integer"
        exit 1;;
esac

(($NUMB < 1)) && { echo "Invalid input: number of mazes should be greater than 0"; exit 1; }

if [ -z ${SEED+x} ]; then
    echo "NOTE: The seed was not specified. Default value of 1 will be used."
    SEED=1
fi

if [ -z ${CYCLE+x} ]; then
    echo "NOTE: The percentage of cycles was not specified. Default value of 100 will be used."
    CYCLE="100"
fi

if [ -z ${BUGTYPE} ]; then
    echo "NOTE: The bugtype was not specified. Default function abort() will be used."
    BUGTYPE="abort"
fi

if [ -z ${EXIT+x} ]; then
    EXIT="default"
fi

if [ -z ${GEN+x} ]; then
    echo "NOTE: The program generator was not specified. Default generator will be used."
    GEN="default_gen"
fi

if [ -z ${T_NUMB} ]; then
    echo "NOTE: The number of transformed mazes was not specified. No transformations will be performed"
    T_NUMBFORMS=0
fi

if [ -z ${T_TYPE} ]; then
    echo "NOTE: No transformations where specified. No transformations will be performed"
    T_TYPE = "id"
fi

echo "Generating mazes..."
echo "##############################################"
echo "Algorithm: "$ALGORITHM
echo "Size: "$WIDTH" by "$HEIGHT
echo "Maze exit: "$EXIT
echo "Pseudo-random seed: "$SEED
echo "Remaining cycles: "$CYCLE"%"
echo "Number of mazes: "$NUMB
echo "Types of transformations used: "$T_TYPE
echo "Number of transformations per maze: "$T_NUMB
echo "Bugtype: "$BUGTYPE
echo "Generator used: "$GEN
echo "Output directory: "$OUTPUT_DIR
echo "##############################################"

mkdir -p $OUTPUT_DIR/src $OUTPUT_DIR/bin $OUTPUT_DIR/png $OUTPUT_DIR/txt $OUTPUT_DIR/sln
MAZEGEN_DIR=$(readlink -f $(dirname "$0")/..)/maze-gen

for (( INDEX=1; INDEX<=$NUMB; INDEX++ ))
do
    NAME=$ALGORITHM"_"$WIDTH"x"$HEIGHT"_"$SEED"_"$INDEX"_"$T_TYPE
    python3 $MAZEGEN_DIR/array_gen.py $ALGORITHM $WIDTH $HEIGHT $SEED $EXIT $INDEX $T_TYPE $T_NUMB 
    if [ $? -eq 1 ]; then
        echo "Select one of the following algorithms: Backtracking, Kruskal, Prims, Wilsons, Sidewinder"
        exit 1
    fi
    if [[ "$GEN" == *"CVE"* ]]; then
        SMT_NAME=$(basename $SMT_PATH .smt2)
        NAME_EXT="_"$CYCLE"percent_"$SMT_NAME"_gen_"$BUGTYPE
        echo $NAME $WIDTH $HEIGHT $CYCLE $SEED $BUGTYPE $T_INDEX $GEN $SMT_PATH
        python3 $MAZEGEN_DIR/array_to_code.py $NAME $WIDTH $HEIGHT $CYCLE $SEED $BUGTYPE $T_TYPE $T_NUMB $GEN $SMT_PATH 
    else
        NAME_EXT="_"$CYCLE"percent_"$GEN"_"$BUGTYPE
        echo $NAME $WIDTH $HEIGHT $CYCLE $SEED $BUGTYPE $T_ $T_INDEX $GEN $SMT_PATH
        python3 $MAZEGEN_DIR/array_to_code.py $NAME $WIDTH $HEIGHT $CYCLE $SEED $BUGTYPE $T_TYPE $T_NUMB $GEN 
    fi
    for (( T_INDEX=0; T_INDEX<=$T_NUMB; T_INDEX++ ))
    do
        NAME_P=$NAME"_"$T_INDEX$NAME_EXT;
        gcc -O3 -w -o $NAME_P".bin" $NAME_P".c"
        mv $NAME"_"$T_INDEX".png" $OUTPUT_DIR/png
        mv $NAME"_"$T_INDEX".txt" $OUTPUT_DIR/txt
        mv $NAME_P".c" $OUTPUT_DIR/src
        mv $NAME_P".bin" $OUTPUT_DIR/bin
    done
    mv $NAME"_solution.txt" $OUTPUT_DIR/sln
done

echo "Done!"