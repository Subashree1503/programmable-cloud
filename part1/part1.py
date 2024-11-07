#!/usr/bin/env python3

import argparse
import os
import time
from pprint import pprint
import googleapiclient.discovery
import google.auth

# Authenticate and build the compute engine client
credentials, _ = google.auth.default()
project = 'directed-galaxy-437903-g9'  # Replace with your project ID

service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

# Constants for the instance creation
INSTANCE_NAME = 'flask-tutorial-instance'
ZONE = 'us-west1-b'
MACHINE_TYPE = f'zones/{ZONE}/machineTypes/f1-micro'
SOURCE_IMAGE = 'projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts'
FIREWALL_RULE_NAME = 'allow-5000'

# Startup script for the Flask app setup
STARTUP_SCRIPT = """#!/bin/bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip git
git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial
cd flask-tutorial
sudo python3 setup.py install
sudo pip3 install -e .
export FLASK_APP=flaskr
flask init-db
nohup flask run -h 0.0.0.0 &
"""

def create_instance(compute, project, zone, instance_name):
    """Creates a VM instance."""
    config = {
        'name': instance_name,
        'machineType': MACHINE_TYPE,
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceImage': SOURCE_IMAGE,
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

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config
    ).execute()

def create_firewall_rule(compute, project):
    """Creates a firewall rule to allow traffic on port 5000."""
    firewall_body = {
        'name': FIREWALL_RULE_NAME,
        'allowed': [{
            'IPProtocol': 'tcp',
            'ports': ['5000']
        }],
        'direction': 'INGRESS',
        'sourceRanges': ['0.0.0.0/0'],
        'targetTags': ['allow-5000']
    }

    try:
        # Check if firewall rule already exists
        firewall = compute.firewalls().get(project=project, firewall=FIREWALL_RULE_NAME).execute()
        if firewall:
            print("Firewall rule already exists.")
    except googleapiclient.errors.HttpError as e:
        if e.resp.status == 404:
            print(f"Creating firewall rule {FIREWALL_RULE_NAME}...")
            return compute.firewalls().insert(project=project, body=firewall_body).execute()
        else:
            raise e

def get_instance_ip(compute, project, zone, instance_name):
    """Retrieves the external IP of the VM instance."""
    instance_info = compute.instances().get(project=project, zone=zone, instance=instance_name).execute()
    return instance_info['networkInterfaces'][0]['accessConfigs'][0]['natIP']

def main():
    # Create the firewall rule if it doesn't exist
    create_firewall_rule(service, project)

    # Create the VM instance
    print(f"Creating instance {INSTANCE_NAME} in {ZONE}...")
    create_instance(service, project, ZONE, INSTANCE_NAME)

    # Wait for the instance to initialize (you may need to adjust sleep time)
    print("Waiting for the instance to start...")
    time.sleep(60)  # Adjust the sleep time as needed

    # Retrieve and print the external IP of the VM instance
    external_ip = get_instance_ip(service, project, ZONE, INSTANCE_NAME)
    print(f"Your Flask application is running at http://{external_ip}:5000")

if __name__ == '__main__':
    main()
