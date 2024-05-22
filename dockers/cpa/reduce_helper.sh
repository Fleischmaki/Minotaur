grep -qPz "long scast_helper\(unsigned long i, unsigned char width\){([^}]*\n[^}]*)*return" $FILE && 
(/home/maze/tools/cpa/scripts/cpa.sh -64 -spec sv-comp-reachability -preprocess -$CONF1 $FILE 2>&1 > stdout1 || true) && 
grep -q "$REGEX1" stdout1 &&
(/home/maze/tools/cpa/scripts/cpa.sh -64 -spec sv-comp-reachability -preprocess -$CONF2 $FILE 2>&1 > stdout2 || true) && 
grep -q "$REGEX2" stdout2