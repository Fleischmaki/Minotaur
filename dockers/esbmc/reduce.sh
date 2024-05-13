if [ $# -ne 5 ] ; then
    echo "Wrong number of parameters";
    exit 0
fi

export FILE=$1
export CONF1="$2"
export REGEX1="$3"
export CONF2="$4"
export REGEX2="$5"


cvise $(dirname "$0")/reduce_helper.sh $FILE | tee output

if $(grep -q "cannot run because the interestingness test does not return" output); then
    echo -e "\n=> The interestingness failed, probably the regexps are not matching?\nPlease note that if you want to try creduce_compare_util.sh, you will need to export variables:\n  export FILE=$FILE CONF1=\"$CONF1\" REGEX1=\"$REGEX1\" CONF2=\"$CONF2\" REGEX2=\"$REGEX2\" ";
fi;