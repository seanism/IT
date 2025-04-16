#!/bin/bash
# Runs the drive transfer locally instead of using the bulk transfer feature
# Usage: ./drive-transfer.sh from@truework.com getFiles@truework.com

# Put in the path to GAM below.  Use which gam to show the path in Terminal
GAM="/Users/syoung/bin/gamadv-xtd3/gam"

if [[ -z $1 && -z $2 ]]; then
    echo "Please run script with the from and to emails"
    echo ""
    echo "Eg ./mail-forward.sh from@truework.com getEmails@truework.com"
else
    offboarded="$1"
    receiver="$2"
    echo ""
    echo "--------------------"
    echo "Forwarding emails from $offboarded to $receiver..."
    echo ""
    $GAM user $offboarded add forwardingaddress $receiver
    $GAM user $offboarded forward on $receiver markread
    echo "--------------------"
fi
