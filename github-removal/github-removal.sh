#!/bin/bash
# Purpose: Removes list of users from Github organization using a CSV file
# Created by @seanism 2022-01-03
#
# Ensure you are an org admin
# Create a personal access token in Github with the permissions admin:org
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
# This script reads from a CSV file ($INPUT) which should list each user you want to remove
# ------------------------------------------
INPUT=data.csv
OLDIFS=$IFS
COUNTER=0

# Defined variables
gituser=""
token=""
###################
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }

NOW=$(date +"%c")
echo "Script runtime: $NOW" >> github.log

accept="Accept: application/vnd.github.v3+json"
token="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"
while read username
do
	echo "Checking $username..."
	url="https://api.github.com/orgs/diem/members/${username}"
	curl -X DELETE $url -u "$gituser:$token" -H "Accept: application/vnd.github.v3+json" &> /dev/null
	if [ 200 -eq $? ]; then
		echo "  Removed: $username" >> github.log
		let COUNTER++
	else
		echo "  $username isn't a member"
		url_collab="https://api.github.com/orgs/diem/outside_collaborators/${username}"
		curl -X DELETE $url_collab -u "$gituser:$token" -H "Accept: application/vnd.github.v3+json"
		if [ 204 -eq $? ]; then
			echo "  Removed outside collaborator: $username" >> github.log
			let COUNTER++
		else
			echo "  $username isn't an outside collaborator"
		fi
	fi
echo ""
done < $INPUT
IFS=$OLDIFS
echo "Total Removed: $COUNTER"
echo "Total Removed: $COUNTER" >> github.log
echo "------------------------" >> github.log
