import csv

with open('device_ids.csv') as csv_file:
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

for device in devices:
    print(f"Device ID: {device['device_id']}")
    print(f"Serial Number: {device['serial_number']}")
    print(f"Device Name: {device['device_name']}")
    print(f"Model: {device['model']}")
    print()
