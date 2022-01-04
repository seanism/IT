#!/bin/bash
# Purpose: Removes list of users from Github organization using a CSV file
# Created by @seanism 2022-01-03
#
# Ensure you are an org admin
# Create a personal access token in Github with the permissions admin:org
# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
# This file reads from a CSV file with NO header that lists all the users you want to remove
# ------------------------------------------
INPUT=data.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }

NOW=$(date +"%c")
echo "Script runtime: $NOW" >> github.log

accept="Accept: application/vnd.github.v3+json"
gituser=""
token=""
while read username
do
	url="https://api.github.com/orgs/diem/members/${username}"
	curl -X DELETE $url -u "$gituser:$token" -H "Accept: application/vnd.github.v3+json" &> /dev/null
	if [ 200 -eq $? ]; then
		echo "Removed: $username" >> github.log
	else
		echo "$username wasn't a member."
	fi

done < $INPUT
IFS=$OLDIFS
echo "------------------------" >> github.log
