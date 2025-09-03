#!/bin/sh

loggedInUser=$( ls -l /dev/console | awk '{print $3}' )
if [[ "$loggedInUser" = "root" ]];
then
    echo "loggedInUser is root.  Exiting."
    exit 1
else
    HostName=$(/usr/sbin/scutil --get HostName)
    echo "Current Hostname is ${HostName}..."
    deviceName="mac-$loggedInUser-tw"

    if [ "${HostName}" != "${deviceName}" ]; then 
        echo "Current Hostname ${HostName} is not correct."
        # Sets computer name for bonjour aware services on the local network
        scutil --set LocalHostName "$deviceName"

        # Sets the hostname that is associated with hostname(1) and gethostname(3)
        scutil --set HostName "$deviceName"

        # Sets the user friendly computer name
        scutil --set ComputerName "$deviceName"
        
        #Check Host Name was setup
	    HostName=$(/usr/sbin/scutil --get HostName)
	
	    #Validates if the HostName changed
	    if [ "${HostName}" != "${deviceName}" ]; then 
		    echo "Set Hostname Failed..."
		    echo "Hostname is ${HostName}"
		    exit 1
	    else 
		    echo "Set Hostname Succeeded..."
		    echo "Hostname is now ${HostName}"
		    exit 0
	    fi
    else
        echo "Exiting.  Hostname is already correct."
        exit 0
    fi
fi
