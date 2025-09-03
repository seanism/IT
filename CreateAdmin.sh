#!/bin/bash

# CreateAdmin v5
# Enables remote management for the local admin account

# Create local admin
read -r -p 'What is the local admin password? ' -s PASSWORD

PSUM=$(echo -n ${PASSWORD} | shasum)

if [[ "${PSUM}" != "<<SHASUM HASH OF PW>>" ]]; then
    echo "Incorrect Password.  Exiting."
    exit 1
fi

if [[ $(dscl . list /Users) =~ "qit" ]]; then 
    echo "Local admin already exists.  Skipping creation"
else 
	echo "Creating local admin account"
	. /etc/rc.common
	dscl . create /Users/it
	dscl . create /Users/qit RealName "IT"
	dscl . create /Users/qit picture "<<PATHTOIMAGE>>"
	dscl . passwd /Users/qit ${PASSWORD}
	dscl . create /Users/qit UniqueID 450
	dscl . create /Users/qit PrimaryGroupID 20
	dscl . create /Users/qit UserShell /bin/bash
	dscl . create /Users/qit NFSHomeDirectory /Users/it
	dscl . append /Groups/admin GroupMembership it
	cp -R /System/Library/User\ Template/English.lproj /Users/it
	chown -R it:staff /Users/it
	echo "Done creating the local admin account"
fi

# enable ARD
echo "Enabling ARD"
/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -activate -configure -allowAccessFor -specifiedUser
/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -configure -users it -access -on -privs -all -restart -agent -menu
echo "Done"
