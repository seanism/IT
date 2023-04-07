#!/bin/sh

# Sets computer name to XX-First-LAST with the XX being the country code
# pulls their name from JAMF real name field.
# Define fields 4,5,6 under Options in JAMF

# Parameter 4: JAMF Username
# Parameter 5: JAMF Password
# Parameter 6: JAMF URL

# created by Sean Young 2021-10-20

# Variables
jssUser=$4
jssPass=$5
jssHost=$6

serial=$(ioreg -rd1 -c IOPlatformExpertDevice | awk -F'"' '/IOPlatformSerialNumber/{print $4}')

echo "\n"

response=$(/usr/bin/curl -H -s "Accept: text/xml" -sfku "${jssUser}:${jssPass}" "${jssHost}/JSSResource/computers/serialnumber/${serial}/subset/location")
if [ $? -eq 0 ]; then
    echo "-> Successfully connected to JAMF"
else
    echo "Error: failed to connect to JAMF"
    exit 1
fi

realName=$(echo $response | /usr/bin/awk -F'<real_name>|</real_name>' '{print $2}');

if [ "$realName" == "" ]; then
    echo "Error: Name field is blank"
    exit 1
fi

echo "-> Retrieved name $realName"

# Converts to camel case and lowercases first name and uppercases lastname.  Includes second last name with the $3 variable below (eg Jason De Lopez)
camelName=$(sed -r 's/\<./\U&/g'<<< $realName)
firstName=$(echo $realName | awk '{print tolower($1)}')
lastName=$(echo $realName | awk '{print toupper($2$3)}')
#name=$(sed "s/ //g" <<< $camelName)


# Gets the country code
locationRaw=$(whois $(curl -s ifconfig.me) | grep -iE ^country: | awk '{print toupper($2)}')

locationShort="${locationRaw:0:2}"
if [ "$locationShort" == "GB" ]; then
	location="UK"
else
	location=$locationShort
fi


deviceName="$location-$firstName-$lastName"
echo "-> Setting computer name to $deviceName"


# Sets computer name in JAMF
/usr/local/bin/jamf setcomputername -name "$deviceName" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "-> JAMF updated to $deviceName"
else
    echo "Error: JAMF computername failed."
fi
# Sets computer name for bonjour aware services on the local network
scutil --set LocalHostName "$deviceName"

# Sets the hostname that is associated with hostname(1) and gethostname(3)
scutil --set HostName "$deviceName"

# Sets the user friendly computer name
scutil --set ComputerName "$deviceName"
if [ $? -eq 0 ]; then
    echo "-> Computer name updated to $deviceName"
else
    echo "Error: Computer name failed."
fi

/usr/local/bin/jamf recon > /dev/null 2>&1
