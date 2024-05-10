(/home/maze/tools/2ls/src/2ls/2ls --inline $CONF1 $FILE 2>&1 > stdout1 || true) && 
grep -q "$REGEX1" stdout1 &&
(cbmc $FILE 2>&1 > stdout2 || true) && 
grep -q "$REGEX2" stdout2