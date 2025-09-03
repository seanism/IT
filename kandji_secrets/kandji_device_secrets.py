import argparse
import csv
from typing import Any
import requests
import os

from dotenv import load_dotenv

load_dotenv()

################################################################################################
# Created by Patrick Albert | patrickalbert@truework.com | Truework
################################################################################################
# Created on 03/28/2023
################################################################################################
# Software Information
################################################################################################
#
#   This script is used to generate a report based on the GET Devices Secrets API
#   endpoint from Kandji. 
#   The script requires a CSV file with the following headers:
#   device_id, serial_number, device_name, model 
#
#   The kandji_devices_report.py script will generate a CSV file with the required headers.
#
########################################################################################
######################### UPDATE VARIABLES BELOW #######################################
########################################################################################

# Replace with your own API token
api_token = os.getenv("KANDJI_API_TOKEN")
if not api_token:
    raise SystemExit("Please run export KANDJI_API_TOKEN=<API_TOKEN> before running this script")
# URL endpoint for the Kandji API
url_base = "https://truework.api.kandji.io/api/v1"

########################################################################################
######################### DO NOT MODIFY BELOW THIS LINE ################################
########################################################################################

def parse_csv_report(filename: str) -> list[dict[str, str | Any]]:
    with open(filename) as csv_file:
        csv_reader = csv.DictReader(csv_file)
        devices = [
            {
                'device_id': row['device_id'],
                'serial_number': row['serial_number'],
                'device_name': row['device_name'],
                'model': row['model'],
            }
            for row in csv_reader
        ]
    return devices

def fetch_device_secrets(devices):
    device_secrets = []
    for device in devices:
        filevault_key = ""
        bypass_code = ""
        unlock_pin = ""

        print(f"Retrieving secrets for device {device['device_id']}")

        # Make API call to retrieve FileVault key
        url = f"{url_base}/devices/{device['device_id']}/secrets/filevaultkey/"
        headers = {"Authorization": f"Bearer {api_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            filevault_key = response.text
            print(f"FileVault key retrieved for device {device['device_id']}")
        else:
            print(f"Error retrieving FileVault key for device {device['device_id']}: {response.text}")

        # Make API call to retrieve bypass code
        url = f"{url_base}/devices/{device['device_id']}/secrets/bypasscode/"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            bypass_code = response.text
            print(f"Bypass code retrieved for device {device['device_id']}")
        else:
            print(f"Error retrieving bypass code for device {device['device_id']}: {response.text}")

        # Make API call to retrieve unlock PIN
        url = f"{url_base}/devices/{device['device_id']}/secrets/unlockpin/"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            unlock_pin = response.text
            print(f"Unlock PIN retrieved for device {device['device_id']}")
        else:
            print(f"Error retrieving unlock PIN for device {device['device_id']}: {response.text}")
            
            # Write secrets to terminal
        device_secrets.append({
            'device_id': device['device_id'],
            'serial_number': device['serial_number'],
            'device_name': device['device_name'],
            'model': device['model'],
            'filevault_key': filevault_key,
            'bypass_code': bypass_code,
            'unlock_pin': unlock_pin
        })

        print(f"Secrets retrieved for device {device['device_id']}\n")
    return device_secrets

def write_output_file(data, filename: str) -> None:
    with open(filename, mode='w', newline='') as csv_file:
        fieldnames = ['device_id', 'serial_number', 'device_name', 'model', 'filevault_key', 'bypass_code', 'unlock_pin']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for device in data:
            writer.writerow(device)

def parse_args():
    parser = argparse.ArgumentParser(
        prog="kandji_secrets_dumper",
        description=(
            "This tool is used to dump the secrets from devices in kandji."
        ),
        allow_abbrev=False,
    )

    parser.add_argument(
        "--input",
        type=str,
        default="device_ids.csv",
        metavar="FILENAME",
        help="The filename containing your device report",
        required=False,
    )

    parser.add_argument(
        "--output",
        type=str,
        default="kandji_device_secrets.csv",
        metavar="FILENAME",
        help="Filename to dump secrets out to",
        required=False
    )

    return parser.parse_args()

def main():
    args = parse_args()
    print(f"Parsing csv report {args.input}")
    devices = parse_csv_report(args.input)
    print("Fetching secrets for devices in report")
    device_secrets = fetch_device_secrets(devices)
    print(f"Writing output file to kandji {args.output}")
    write_output_file(device_secrets, args.output)

if __name__ == "__main__":
    main()
