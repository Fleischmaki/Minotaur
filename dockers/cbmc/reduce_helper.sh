#!/bin/bash
(/home/maze/tools/cbmc/build/bin/cbmc $CONF1 $FILE &> stdout1 || true) && 
grep -q "$REGEX1" stdout1 &&
(/home/maze/tools/cbmc/build/bin/cbmc $CONF2 $FILE &> stdout2 || true) && 
grep -q "$REGEX2" stdout2