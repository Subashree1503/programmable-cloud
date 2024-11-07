#!/usr/bin/env python3

import os
import time
from pprint import pprint
import googleapiclient.discovery
import google.auth

# Manually set the project ID
project = 'directed-galaxy-437903-g9'
credentials, _ = google.auth.default()
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
ZONE = 'us-west1-b'
INSTANCE_NAME = 'flask-tutorial-instance'
DISK_NAME = 'flask-tutorial-instance'  # Replace with actual disk name

# Startup script for Flask application
STARTUP_SCRIPT = """#!/bin/bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git
git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial
cd flask-tutorial
sudo python3 setup.py install
sudo pip3 install -e .
export FLASK_APP=flaskr
flask init-db
nohup flask run -h 0.0.0.0 -p 5000 &
"""

def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print("Operation finished.")
            return result
        time.sleep(10)

def list_instances(compute, project, zone):
    """Lists all instances in the specified zone."""
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items'] if 'items' in result else None

def create_snapshot(compute, project, zone, instance_name, disk_name):
    """Creates a snapshot of the disk from an instance."""
    snapshot_body = {
        'name': f'base-snapshot-{instance_name}',
        'description': 'Snapshot of the Flask app instance'
    }

    print(f"Creating snapshot for instance {instance_name}...")

    operation = compute.disks().createSnapshot(
        project=project,
        zone=zone,
        disk=disk_name,
        body=snapshot_body
    ).execute()

    wait_for_operation(compute, project, zone, operation['name'])
    print(f"Snapshot created: base-snapshot-{instance_name}")

def create_instance_from_snapshot(compute, project, zone, instance_name, snapshot_name):
    """Creates a new instance from the given snapshot."""
    config = {
        'name': instance_name,
        'machineType': f'zones/{zone}/machineTypes/f1-micro',
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceSnapshot': f'global/snapshots/{snapshot_name}',
            }
        }],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [{
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT'
            }]
        }],
        'tags': {
            'items': ['allow-5000']
        },
        'metadata': {
            'items': [{
                'key': 'startup-script',
                'value': STARTUP_SCRIPT
            }]
        }
    }

    start_time = time.time()
    operation = compute.instances().insert(project=project, zone=zone, body=config).execute()
    wait_for_operation(compute, project, zone, operation['name'])
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Instance {instance_name} created in {elapsed_time:.2f} seconds")
    return elapsed_time

def create_multiple_instances_from_snapshot(compute, project, zone, snapshot_name):
    instance_times = []
    for i in range(1, 4):
        instance_name = f'flask-clone-{i}'
        elapsed_time = create_instance_from_snapshot(compute, project, zone, instance_name, snapshot_name)
        instance_times.append((instance_name, elapsed_time))
    
    with open('TIMING.md', 'w') as f:
        for instance_name, elapsed_time in instance_times:
            f.write(f"{instance_name}: {elapsed_time:.2f} seconds\n")
    print("TIMING.md created and times recorded.")

def main():
    # Validate project ID
    if not project:
        raise ValueError("Project ID is not set. Please provide a valid Google Cloud project ID.")

    # List running instances
    print("Your running instances are:")
    for instance in list_instances(service, project, ZONE):
        print(instance['name'])
    
    # Create a snapshot from the existing instance
    create_snapshot(service, project, ZONE, INSTANCE_NAME, DISK_NAME)

    # Create three instances from the snapshot and measure time
    create_multiple_instances_from_snapshot(service, project, ZONE, f'base-snapshot-{INSTANCE_NAME}')

if __name__ == '__main__':
    main()
