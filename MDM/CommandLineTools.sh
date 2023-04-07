#!/bin/bash
LOG_FILE=/var/tmp/jamf.log
exec >  >(tee -a $LOG_FILE)
exec 2> >(tee -a $LOG_FILE >&2)

CURRENT_USER=$(/usr/bin/python -c 'from SystemConfiguration import SCDynamicStoreCopyConsoleUser; import sys; username = (SCDynamicStoreCopyConsoleUser(None, None, None) or [None])[0]; username = [username,""][username in [u"loginwindow", None, u""]]; sys.stdout.write(username + "\n");')
echo -e "--- Commandline Tools ---\n" | tee $LOG_FILE

os=$(sw_vers -productVersion | awk -F. '{print $1 "." $2}')

# string comparison
if [[ "$os" == 10.15 ]]; then
	echo "macOS Catalina detected"
    if softwareupdate --history | grep --silent "Command Line Tools.*"; then
		echo 'Command-line tools already installed.'
	else
		echo ""
		echo '##### Installing Command-line tools...'
    	in_progress=/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
    	touch ${in_progress}
    	product=$(softwareupdate -l | grep -B 1 -E 'Command Line Tools' | awk -F'*' '/^ *\\*/ {print $2}' | sed -e 's/^ *Label: //' -e 's/^ *//' | sort -V | tail -n1)
    	softwareupdate --verbose --install "${product}" || echo 'Installation failed.' 1>&2 && rm ${in_progress} && echo 'Command-line tools installed.'
	fi    
    
    
elif [[ "$os" == 10.14 ]]; then
	echo "macOS Mojave"
    if softwareupdate --history | grep --silent "Command Line Tools.*${os}"; then
		echo 'Command-line tools already installed.'
	else
		echo ""
		echo '##### Installing Command-line tools...'
    	in_progress=/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
    	touch ${in_progress}
    	product=$(softwareupdate --list | awk "/\* Command Line.*${os}/ { sub(/^   \* /, \"\"); print }")
    	softwareupdate --verbose --install "${product}" || echo 'Installation failed.' 1>&2 && rm ${in_progress} && echo 'Command-line tools installed.'
	fi
else
	echo "MacOS 10.13 or earlier.  You should upgrade."
    if softwareupdate --history | grep --silent "Command Line Tools.*${os}"; then
		echo 'Command-line tools already installed.'
	else
		echo ""
		echo '##### Installing Command-line tools...'
    	in_progress=/tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
    	touch ${in_progress}
    	product=$(softwareupdate --list | awk "/\* Command Line.*${os}/ { sub(/^   \* /, \"\"); print }")
    	softwareupdate --verbose --install "${product}" || echo 'Installation failed.' 1>&2 && rm ${in_progress} && echo 'Command-line tools installed.'
	fi
fi
