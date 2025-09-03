#!/bin/bash
# This script performs various offboarding tasks when a user leaves the company.
# For the standard offboard it will pull their manager from Google Workspace.

# Created by Sean Young (@seanism) 2021

gam="$HOME/bin/gamadv-xtd3/gam"

# Define the offboardOU name, csv filename, and month format
#company=""
offboardOU="/Offboards"
csv="offboard.csv"
month=$(LANG=en_us_88591; date "+%B");

# CSV fields are Email, ForwardEmail, DriveEmail, OOOmessage

# Starting deprovision
echo ""
echo "============================================"
echo "Timestamp: `date +"%Y-%m-%d %T %p"`"
echo ""
echo "Ensuring the user is active and not suspended"
$gam csv $csv gam update user "~Email" suspended off | tee -a /Users/Shared/sept2024-offboard.log

# Changing user's password to random
echo "-> Changing password to something random"
$gam csv $csv gam update user "~Email" password random | tee -a /Users/Shared/sept2024-offboard.log

# deleting all OAuth tokens
echo "-> Checking and Removing all Application Specific Passwords, 2SV Recovery Codes, and all OAuth tokens"
$gam csv $csv gam user "~Email" deprovision | tee -a /Users/Shared/sept2024-offboard.log

# Removing user from all Groups
$gam csv $csv gam user "~Email" delete group | tee -a /Users/Shared/sept2024-offboard.log

# Removing recovery email and phone
echo "-> Removing recovery email and phone"
$gam csv $csv gam update user "~Email" recoveryemail "" recoveryphone "" | tee -a /Users/Shared/sept2024-offboard.log

echo "-> Setting force change password on next logon and then disabling immediately to expire current session"
$gam csv $csv gam update user "~Email" changepassword on | tee -a /Users/Shared/sept2024-offboard.log
sleep 2
$gam csv $csv gam update user "~Email" changepassword off | tee -a /Users/Shared/sept2024-offboard.log

# Mail forwarding
echo "Forwarding email"
$gam csv $csv gam user "~Email" add forwardingaddress "~forwardEmail" | tee -a /Users/Shared/sept2024-offboard.log
$gam csv $csv gam user "~Email" forward on "~forwardEmail" markread | tee -a /Users/Shared/sept2024-offboard.log

# Drive transferring
echo "-> Transfering Google Drive"
$gam csv $csv gam create datatransfer "~Email" gdrive "~driveEmail" privacy_level shared,private
echo "Drive transfer initiated" | tee -a /Users/Shared/sept2024-offboard.log

# Setting OOO
#echo "Setting OOO"
#$gam csv $csv gam user "~Email" vacation on subject "No longer at Truework" message "~OOOmessage" enddate 2025-12-31 | tee -a /Users/Shared/$username.log

# Calendar delegate
$gam csv $csv gam calendar "~Email" add owner "~driveEmail" | tee -a /Users/Shared/sept2024-offboard.log

# Moving user to offboarding OU
echo "-> Moving to the Offboarding OU"
$gam csv $csv gam update user "~Email" org $offboardOU/$month

# hiding user from directory
echo "-> Hiding from the GAL"
$gam csv $csv gam update user "~Email" gal off


echo "============================================"
echo "Offboard complete"
echo "============================================"
