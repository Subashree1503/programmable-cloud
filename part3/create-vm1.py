#!/usr/bin/env python3

import googleapiclient.discovery
import google.auth
import google.oauth2.service_account as service_account
import time

# Use Google Service Account credentials for authentication
credentials = service_account.Credentials.from_service_account_file('/home/sudi2972/lab5new-programmable-cloud-Subashree1503/part3/service-credentials.json')
project = 'directed-galaxy-437903-g9'
zone = 'us-west1-b'

# Create a Compute Engine client
service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)

def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(project=project, zone=zone, operation=operation).execute()
        if result['status'] == 'DONE':
            print("Operation finished.")
            return result
        time.sleep(5)

# Function to create VM-1 that will create VM-2
def create_vm1(compute, project, zone, instance_name):
    # This startup script will run on VM-1 and will create VM-2
    vm1_startup_script = """#!/bin/bash
    mkdir -p /srv
    cd /srv
    curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/vm2-startup-script -H "Metadata-Flavor: Google" > vm2-startup-script.sh
    curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/service-credentials -H "Metadata-Flavor: Google" > service-credentials.json
    curl http://metadata.google.internal/computeMetadata/v1/instance/attributes/vm1-launch-vm2-code -H "Metadata-Flavor: Google" > vm1-launch-vm2-code.py

    # Install necessary libraries
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
    pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

    # Run the Python script to launch VM-2
    python3 ./vm1-launch-vm2-code.py
    """


    # Create VM-1 configuration
    vm1_config = {
        'name': instance_name,
        'machineType': f'zones/{zone}/machineTypes/f1-micro',
        'disks': [{
            'boot': True,
            'autoDelete': True,
            'initializeParams': {
                'sourceImage': 'projects/debian-cloud/global/images/family/debian-11',
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
            'items': [
                {
                    'key': 'startup-script',
                    'value': vm1_startup_script
                },
                {
                    'key': 'vm2-startup-script',
                    'value': """#!/bin/bash
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
                },
                {
                    'key': 'service-credentials',
                    'value': open('/home/sudi2972/lab5new-programmable-cloud-Subashree1503/part3/service-credentials.json').read()
                },
                {
                    'key': 'vm1-launch-vm2-code',
                    'value': open('/home/sudi2972/lab5new-programmable-cloud-Subashree1503/part3/vm1-launch-vm2-code.py').read()
                }
            ]
        },
        'tags': {
            'items': ['allow-5000']
        }
    }

    print(f"Creating VM-1 instance: {instance_name}")
    operation = compute.instances().insert(project=project, zone=zone, body=vm1_config).execute()

    wait_for_operation(compute, project, zone, operation['name'])

if __name__ == '__main__':
    create_vm1(service, project, zone, 'vm1-instance')
