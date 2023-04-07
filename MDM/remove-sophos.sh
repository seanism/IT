#!/bin/bash
#####
# https://github.com/truework/internal-it-tools/kandji/sophos/remove.sh
#####
## postinstall
# Remove Sophos Endpoint v2.1.1
# Created By Mann Consulting - 2015
# Last Update:
#Exit Codes:
# 0 = Sucessful
# 1 = Installer Failed too many times, or a generic failure not defined by the script
# 2 = Variable 4 Not Set
### Variables & Arguments ###
if [[ $6 == "" ]]; then
        echo "WARN: Variable 6 (Sophos Installer Log Path) not set! Using default of /tmp/SophosAVInstallerLog.log"
        SAVInstallLog="/tmp/SophosAVInstallerLog.log"
    else
        SAVInstallLog="$5"
fi
### Functions ###
function fRemoveSophos { #Look for existing Sophos installs and remove them if needed
  # Sophos 8
  if [ -d "/Library/Sophos Anti-Virus/Remove Sophos Anti-Virus.pkg" ]; then
  	echo "Removing old Sophos 8 installation..."
      defaults write /Library/Preferences/com.sophos.sav TamperProtectionEnabled -bool false
  	installer -pkg "/Library/Sophos Anti-Virus/Remove Sophos Anti-Virus.pkg" -target /
  fi
  # Sophos 9 if uninstaller is available in opm-sa
  if [ -e "/Library/Application Support/Sophos/opm-sa/Installer.app/Contents/MacOS/InstallationDeployer" ]; then
      echo "Removing old Sophos 9 installation..."
  	defaults write /Library/Preferences/com.sophos.sav TamperProtectionEnabled -bool false
    rm "/Library/Sophos Anti-Virus/SophosSecure.keychain"
  	"/Library/Application Support/Sophos/opm-sa/Installer.app/Contents/MacOS/InstallationDeployer" --force_remove
  fi
  # Sophos 9 if uninstaller is available in saas
  if [ -e "/Library/Application Support/Sophos/saas/Installer.app/Contents/MacOS/tools/InstallationDeployer" ]; then
      echo "Removing old Sophos 9 installation..."
  	defaults write /Library/Preferences/com.sophos.sav TamperProtectionEnabled -bool false
    rm "/Library/Sophos Anti-Virus/SophosSecure.keychain"
  	"/Library/Application Support/Sophos/saas/Installer.app/Contents/MacOS/tools/InstallationDeployer" --force_remove
  fi
  # Garbage Collection - the installer often leaves this behind.
  if [ -d "/Applications/Sophos Anti-Virus.localized" ]; then
  	rm -R "/Applications/Sophos Anti-Virus.localized"
  fi
  exit
}
#### OK, Let's go!
fRemoveSophos
# If we're down here, then the installer failed too often. Log and exit.
echo "FATAL: The Sophos installer has failed too many times."
echo "Detailed logs are on the client at /var/log/installer.log. Last detailed logs below:"
cat "$SAVInstallLog"
echo "-------
"
echo "The install has failed. Exiting."
exit 1
