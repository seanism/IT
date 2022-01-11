#!/bin/sh

# Sets computer name to XX-First-LAST with the XX being the country code
# Assumes username is firstName lastName
# created by Sean Young 2021-10-20

# Gets the country code
location_raw=$(whois $(curl ifconfig.me) | grep -iE ^country: | awk '{print toupper($2)}')

location_short="${location_raw:0:2}"
if [ "$location_short" == "GB" ]; then
	location="UK"
else
	location=$location_short
fi

# Gets current logged in user
getUser=$(ls -l /dev/console | awk '{ print $3 }')

# Gets first and last name
firstName=$(finger -s $getUser | head -2 | tail -n 1 | awk '{print tolower($2)}')
lastName=$(finger -s $getUser | head -2 | tail -n 1 | awk '{print toupper($3)}')

deviceName="$location-$firstName-$lastName"

# Sets computer name in JAMF
/usr/local/bin/jamf setcomputername -name "$deviceName"
if [ $? -eq 0 ]; then
    echo "JAMF computername updated!"
else
    echo "JAMF computername failed."
fi
# Sets computer name for bonjour aware services on the local network
scutil --set LocalHostName "$deviceName"

# Sets the hostname that is associated with hostname(1) and gethostname(3)
scutil --set HostName "$deviceName"

# Sets the user friendly computer name
scutil --set ComputerName "$deviceName"
if [ $? -eq 0 ]; then
    echo "Computer name updated!"
else
    echo "Computer name failed."
fi

/usr/local/bin/jamf recon
