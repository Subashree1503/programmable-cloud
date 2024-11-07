#!/usr/bin/env python3

import argparse
import os
import time
from pprint import pprint

import googleapiclient.discovery
import google.auth
import google.oauth2.service_account as service_account

# Use Google Service Account credentials
credentials = service_account.Credentials.from_service_account_file(filename='lab5new-programmable-cloud-Subashree1503/part3/service-credentials.json')
project = 'directed-galaxy-437903-g9'
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

# Function to wait for operation completion
def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(project=project, zone=zone, operation=operation).execute()
        if result['status'] == 'DONE':
            print("Operation finished.")
            return result
        time.sleep(5)

# Function to create a new VM (VM-2)
def create_vm(compute, project, zone, instance_name):
    """Creates a new VM instance with Flask app setup"""
    
    # This is the startup script that installs Flask and runs a simple app
    startup_script = """#!/bin/bash
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip git
    git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial
    cd flask-tutorial
    sudo python3 setup.py install
    sudo pip3 install -e .
    
    # Set up the Flask app
    export FLASK_APP=flaskr
    flask init-db
    
    # Start Flask app on port 5000
    nohup flask run -h 0.0.0.0 -p 5000 &
    """


    config = {
        'name': instance_name,
        'machineType': f'zones/{zone}/machineTypes/f1-micro',
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceImage': 'projects/debian-cloud/global/images/family/debian-11',  # Updated to Debian 11
            }
        }],
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [{
                'type': 'ONE_TO_ONE_NAT',
                'name': 'External NAT'
            }]
        }],
        'metadata': {
            'items': [{
                'key': 'startup-script',
                'value': startup_script
            }]
        },
        'tags': {
            'items': ['allow-5000']  # Allows Flask app to be accessible on port 5000
        }
    }

    # Start creating the instance
    print(f"Creating VM instance {instance_name}...")
    operation = compute.instances().insert(project=project, zone=zone, body=config).execute()

    # Wait for the operation to complete
    wait_for_operation(compute, project, zone, operation['name'])

# Function to list running instances with error handling and debugging
def list_instances(compute, project, zone):
    try:
        result = compute.instances().list(project=project, zone=zone).execute()
        pprint(result)  # Debugging: print the raw response to inspect it
        if 'items' in result:
            return result['items']
        else:
            print("No instances found in this zone.")
            return None
    except Exception as e:
        print(f"Error while listing instances: {e}")
        return None

# Main script execution
if __name__ == '__main__':
    # List existing instances
    print("Your running instances are:")
    instances = list_instances(service, project, 'us-west1-b')
    if instances:  # Only iterate if instances are found
        for instance in instances:
            print(instance['name'])
    else:
        print("No instances to display.")
    
    # Create a new VM-2
    create_vm(service, project, 'us-west1-b', 'vm2-flask-instance')

