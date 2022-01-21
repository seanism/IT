#!/bin/bash
# This script performs various offboarding tasks when a user leaves the company.
# For the standard offboard it will pull their manager from Google Workspace.

# Created by Sean Young (@seanism) 2021

gam="$HOME/bin/gam/gam"

# Define your company name for OOO
$company="Diem"

echo ""
# Enter user to deprovision
read  -p "Enter the email address you wish to deprovision: " username

# Confirm Okta deactivation
read -r -p "Have you deactivated the employee in Okta [y/n]: " response
if [[ $response =~ [nN] ]]
  then
    read -p "Please deactivate the user within Okta then return to this script.  Once completed press return to continue."
fi

echo ""
# Verifying account is not suspended
echo "-> Unsuspending user account"
$gam update user $username suspended off

echo ""

# Employee offboard standard setup
read -r -p "Did you want to do the standard offboard? (forward email & transfer files to manager) [y/n]: " response
if [[ $response =~ [yY] ]]
  then
		manageremail=$($gam info user $username | grep 'value: ' | tail -1 | sed 's/value: //')
    cal_response="y"
    emailforward="y"
    emailforwardaddress=$manageremail
    drivetransfer=$manageremail
    ooo="n"
	else
    # Should user's calendar be wiped? If so, it will be wiped later
    read -p "Do you want to wipe $username's calendar? [y/n]: " cal_response

    # Email forwarding?
    read -p "Did you want their email forwarded? [y/n]: " emailforward
    if [[ $emailforward =~ [yY] ]]
    then
      read -p "What account (email address) should email be forwarded to? " emailforwardaddress
    fi

    # Transfer docs to another employee
    read -p "Email address to receive Google Drive files: " drivetransfer

    # Set OOO
    read -p "Should there be an out of office set? [y/n]: " ooo
fi



# Starting deprovision
echo ""
echo "============================================"
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
all_devices=($($gam print devices query "email:$username" | grep -v name | awk -F"," '{print $1}'))
unset IFS
	for deviceid in ${all_devices[@]}
		do
			$gam update mobile $mobileid action account_wipe && echo "Removing $mobileid from $username"
	done | tee -a /Users/Shared/$username.log

# Changing user's password to random
echo "-> Changing "$username"'s' password to something random"
$gam update user $username password random | tee -a /Users/Shared/$username.log

# Removing all App-Specific account passwords, deleting MFA Recovery Codes,
# deleting all OAuth tokens
echo "-> Checking and Removing all of "$username"'s Application Specific Passwords, 2SV Recovery Codes, and all OAuth tokens"
$gam user $username deprovision | tee -a /Users/Shared/$username.log

# Removing user from all Groups
$gam user $username delete group

# Removing recovery email and phone
echo "-> Removing recovery email and phone"
$gam update user $username recoveryemail "" recoveryphone ""

# Forcing change password on next sign-in and then disabling immediately.
# Speculation that this will sign user out within 5 minutes and not allow
# user to send messages without reauthentication
echo "-> Setting force change password on next logon and then disabling immediately to expire current session"
$gam update user $username changepassword on | tee -a /Users/Shared/$username.log
sleep 2
$gam update user $username changepassword off | tee -a /Users/Shared/$username.log

# Generating new set of MFA recovery codes for the user. Only used if Admin needed to log in as the user once suspended
echo "-> Generating new 2FA Recovery Codes for $username"
# Supressing the screen output
{
$gam user $username update backupcodes | tee -a /Users/Shared/$username.log
} &> /dev/null

## Forwarding email
if [[ $emailforward =~ [yY] ]]
then
		echo "Forwarding "$username"'s email"
		$gam user $username add forwardingaddress $emailforwardaddress | tee -a /Users/Shared/$username.log
    $gam user $username forward on $emailforwardaddress markread
else
		echo "Not forwarding email" | tee -a /Users/Shared/$username.log
fi

## Out of office
if [[ $ooo =~ [yY] ]]
then
		echo "The message will say: Thank you for contacting me. I am no longer working at $company. Please direct any future correspondence to <<EMPLOYEE>>."
		echo "What email should be listed in the above message? "
		read ooo_employee
		echo "Setting "$username"'s OOO"
		$gam user $username  vacation on subject "No longer at Quizlet" message "Thank you for contacting me. I am no longer working at $company. Please direct any future correspondence to "$ooo_employee". Thank you."| tee -a /Users/Shared/$username.log
else
		echo "Not setting OOO" | tee -a /Users/Shared/$username.log
fi

echo "-> Transfering Google Drive to $drivetransfer"
$gam create datatransfer $username gdrive $drivetransfer privacy_level shared,private
echo "Drive transfer initiated" | tee -a /Users/Shared/$username.log

# Removing all of user's calendar events if previously selected
if [[ $cal_response =~ [yY] ]]
then
    echo "Waiting 10 seconds for suspension to be removed..."
    sleep 10
		echo "Deleting all of "$username"'s calendar events"
		$gam calendar $username wipe | tee -a /Users/Shared/$username.log
else
		echo "Not wiping calendar" | tee -a /Users/Shared/$username.log
fi

month=$(LANG=en_us_88591; date "+%B");

# Moving user to offboarding OU
echo "-> Moving $username to the Offboarding OU"
$gam update user $username org /Offboarding/$month

# hiding user from directory
echo "-> Hiding $username from the GAL"
$gam update user $username gal off


echo "============================================"
echo "Offboard complete for $username"
echo "============================================"
