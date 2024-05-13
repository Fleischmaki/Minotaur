(/home/maze/tools/esbmc/build/src/esbmc/esbmc $CONF1 -fbracket-depth=2048 $FILE &> stdout1 || true) && 
grep -q "$REGEX1" stdout1 &&
(/home/maze/tools/esbmc/build/src/esbmc/esbmc $CONF2 -fbracket-depth=2048 $FILE &> stdout2 || true) && 
grep -q "$REGEX2" stdout2