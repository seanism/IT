# Kandji Secrets Inventory Scripts
These Scripts allow for enumeration of all Kandji assets secrets such as filevault, bypass codes and unlock pins

## Usage
1. Ensure your environment is at python3 version 3.10 or greater:
   1. Verify python version `python3 --version`
   1. If you do not have python3.10, it's recommended that you use [pyenv](https://github.com/pyenv/pyenv) to manage python versions on your system. 
1. Ensure you have pipenv installed - `pip3 install pipenv`
1. Ensure you have the dependencies for the tooling installed - `pipenv sync`
1. With your Kandji API Token in hand, create a file in the same direstory as this README, called `.env`.
   1. Inside of `.env`, add a line like `KANDJI_API_TOKEN=` and then paste your api token at the end of that line.
   1. Should look like `KANDJI_API_TOKEN=thisismysupersecrettoken`
1. Activate your virtual environment with `pipenv shell`
1. `python3 kandji_devices_report --platform=Mac --last-check-in=26w` will dump all devices that last checked in longer than 26 weeks ago from the moment you run the command.
4. Using the file produced from the devices report (named something like `mac_report_20230330.csv`, but with the date you run it), run `python3 kandji_device_secrets.py --input mac_report_20230330.csv`
1. All relevant secrets will be dumped to a file called `kandji_device_secrets.csv`
1. kandji_device_secrets.csv file will contain device_id, serial_number, device_name, model, filevault_key, bypass_code, unlock_pin for all machines older than the `--last-check-in` date in Kandji.
1. **NOTE: DO NOT KEEP THESE DEVICE SECRETS ON YOUR COMPUTER. ONCE YOU'VE GOTTEN THEM, PUT THEM SOMEWHERE SAFE AND THEN DELETE THE LOCAL FILE.**
