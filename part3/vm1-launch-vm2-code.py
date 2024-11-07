#!/usr/bin/env python3

import googleapiclient.discovery
import google.auth
import google.oauth2.service_account as service_account
import time
import logging

# Set up logging
logging.basicConfig(filename='/srv/vm1-launch-vm2.log', 
                    level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s:%(message)s')

logging.info("Starting vm1-launch-vm2-code.py")

# Path to the credentials file downloaded by the startup script
credentials_path = '/srv/service-credentials.json'

# Authenticate using the service credentials
try:
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    project = 'directed-galaxy-437903-g9'
    zone = 'us-west1-b'
    logging.info("Authenticated using service credentials.")
except Exception as e:
    logging.error(f"Failed to authenticate with service credentials: {e}")
    raise

# Create Compute Engine client
try:
    service = googleapiclient.discovery.build('compute', 'v1', credentials=credentials)
    logging.info("Successfully built Compute Engine client.")
except Exception as e:
    logging.error(f"Failed to build Compute Engine client: {e}")
    raise

def wait_for_operation(compute, project, zone, operation):
    logging.info(f"Waiting for operation {operation} to finish...")
    while True:
        try:
            result = compute.zoneOperations().get(project=project, zone=zone, operation=operation).execute()
            if result['status'] == 'DONE':
                logging.info(f"Operation {operation} finished.")
                return result
        except Exception as e:
            logging.error(f"Error while waiting for operation: {e}")
        time.sleep(5)

# Function to create VM-2 which will host the Flask app
def create_vm2(compute, project, zone, instance_name):
    # VM-2 startup script (to run the Flask app)
    vm2_startup_script = """#!/bin/bash
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

    # Configuration for VM-2
    vm2_config = {
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
            'items': [{
                'key': 'startup-script',
                'value': vm2_startup_script
            }]
        },
        'tags': {
            'items': ['allow-5000']
        }
    }

    try:
        logging.info(f"Creating VM-2 instance: {instance_name}")
        operation = compute.instances().insert(project=project, zone=zone, body=vm2_config).execute()
        logging.info(f"VM-2 instance creation initiated.")
        wait_for_operation(compute, project, zone, operation['name'])
    except Exception as e:
        logging.error(f"Failed to create VM-2 instance: {e}")
        raise

if __name__ == '__main__':
    try:
        logging.info("Starting the process to create VM-2.")
        create_vm2(service, project, zone, 'vm2-instance')
    except Exception as e:
        logging.error(f"Error occurred in vm1-launch-vm2-code.py: {e}")
        raise
