# Args:
UDIR1="/home/maze/tools/U${TC1}-linux"
UDIR2="/home/maze/tools/U${TC2}-linux"

($UDIR1/Ultimate -tc $UDIR1/config/${TC1}Reach.xml -s $UDIR1/config/svcomp-Reach-64bit-${TC1}_$CONF1.epf -i $FILE 2>&1 > stdout1 || true) && 
grep -q "$REGEX1" stdout1 &&
($UDIR2/Ultimate -tc $UDIR2/config/${TC2}Reach.xml -s $UDIR2/config/svcomp-Reach-64bit-${TC2}_$CONF2.epf -i $FILE 2>&1 > stdout2 || true) &&  
grep -q "$REGEX2" stdout2