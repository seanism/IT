#!/bin/bash
# Runs the drive transfer locally instead of using the bulk transfer feature
# Usage: ./drive-transfer.sh from@truework.com getFiles@truework.com

# Put in the path to GAM below.  Use which gam to show the path in Terminal
GAM="/Users/syoung/bin/gamadv-xtd3/gam"

if [[ -n "$1" ]] || [[-n "$2" ]]; then
    offboarded="$1"
    receiver="$2"
    echo ""
    echo "--------------------"
    echo "Transfering files from $offboarded to $receiver..."
    echo ""
    $GAM user $offboarded transfer drive $receiver
    echo "--------------------"
else
    echo "Please run script with the from and to emails"
    echo ""
    echo "Eg ./drive-transfer.sh from@truework.com getFiles@truework.com"
fi
