#!/bin/bash
gam="$HOME/bin/gam/gam"

echo "Please make sure all the arguments are entered with no spaces and separated by commas"
echo "eg ./addGroups engineering@quizlet.com,sg-eng@quizlet.com"
echo ""
read  -p "Enter email that should be added to the groups: " username
oIFS="$IFS"; IFS=, ; set -- $1 ; IFS="$oIFS"
for i in "$@"; do
    $gam update group $i add member user $username
    #echo "Added $username to $i"
done
echo "Added to: $# group(s)!"
