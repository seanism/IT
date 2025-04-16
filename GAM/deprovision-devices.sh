#!/bin/bash
# This script performs various offboarding tasks when a user leaves the company.
# For the standard offboard it will pull their manager from Google Workspace.

# Created by Sean Young (@seanism) 2021

gam="$HOME/bin/gamadv-xtd3/gam"

# Define your company name for OOO and offboard OU path in Google
company="Truework"
offboardOU="/Offboards"

# You'll need an OU in Google Workspace under root called offboards

echo ""
# Enter user to deprovision
read  -p "Enter the email address you wish to deprovision: " username

echo ""
# Verifying account is not suspended
echo "-> Unsuspending user account"
$gam update user $username suspended off

echo ""
# Starting deprovision
echo ""
echo "============================================"
echo "Timestamp: `date +"%Y-%m-%d %T %p"`"
echo ""
echo "Deprovisioning " $username"..."

# Removing all mobile devices connected
echo "-> Gathering mobile devices for $username"
IFS=$'\n'
mobile_devices=($($gam print mobile query $username | grep -v resourceId | awk -F"," '{print $1}'))
unset IFS
	for mobileid in ${mobile_devices[@]}
		do
			$gam update mobile $mobileid action account_wipe && echo "Removing $mobileid from $username"
	done | tee -a /Users/Shared/$username.log


# Removing all devices connected
echo "-> Gathering all devices for $username"
IFS=$'\n'
all_devices=$($gam print devices query $username | grep -v name | awk -F"," '{print $1}')
unset IFS
	for deviceid in ${all_devices[@]}
		do
			$gam delete device id $deviceid && echo "Removing $deviceid from $username"
	done
