# *** required arguments = [subscription_id] ***

import sys, random, string

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

# Get the credentials
credential = DefaultAzureCredential()
subscription_id = sys.argv[1]

# Create the clients
resource_client = ResourceManagementClient(credential, subscription_id)
network_client = NetworkManagementClient(credential, subscription_id)
compute_client = ComputeManagementClient(credential, subscription_id)

# 1.) Create the resource group
print("Creating the resource group...")

RESOURCE_GROUP_NAME = "py-vm-rg-1"
LOCATION = "centralus"

rg = resource_client.resource_groups.create_or_update(
    RESOURCE_GROUP_NAME,
    { "location": LOCATION },
)

print(f"Resource group {RESOURCE_GROUP_NAME} created in {LOCATION}\n")

# 2.) Create the network security group
print("Creating the network security group...")

NSG_NAME = "py-vm-nsg-1"

poller = network_client.network_security_groups.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    NSG_NAME,
    {
        "location": LOCATION,
        "security_rules": [
            {
                "name": "allow-ssh",
                "source_address_prefix": "*",
                "source_port_range": "*",
                "destination_address_prefix": "*",
                "destination_port_range": "22",
                "protocol": "tcp",
                "access": "Allow",
                "priority": 100,
                "direction": "Inbound",
            },
        ],
    },
)

nsg = poller.result()

print(f"Network security group {NSG_NAME} created in {LOCATION}\n")

# 3.) Create the vnet
print("Creating the virtual network...")

VNET_NAME = "py-vm-vnet-1"

poller = network_client.virtual_networks.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VNET_NAME,
    {
        "location": LOCATION,
        "address_space": { "address_prefixes": ["10.0.0.0/16"] },
    },
)
vnet = poller.result()

print(f"Virtual network {VNET_NAME} created in {LOCATION}\n")

# 4.) Create the subnet
print("Creating the subnet...")

SUBNET_NAME = "subnet-1"

poller = network_client.subnets.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VNET_NAME,
    SUBNET_NAME,
    { 
        "address_prefix": "10.0.1.0/24",
        "network_security_group": { "id": nsg.id },
    },
)
subnet = poller.result()

print(f"Subnet {SUBNET_NAME} created in {LOCATION}\n")

# 5.) Create the public IP address
print("Creating the public IP...")

IP_NAME = "py-vm-ip-1"

poller = network_client.public_ip_addresses.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    IP_NAME,
    {
        "location": LOCATION,
        "sku": { "name": "Standard" },
        "public_ip_allocation_method": "Static",
        "public_ip_address_version": "IPv4",
    },
)

public_ip = poller.result()

print(f"Public IP {IP_NAME} created in {LOCATION} | ADDRESS: {public_ip.ip_address}\n")

# 6.) Create the nic
print("Creating the NIC...")

NIC_NAME = "py-vm-nic-1"
IP_CONFIG_NAME = "py-vm-ip-config-1"

poller = network_client.network_interfaces.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    NIC_NAME,
    {
        "location": LOCATION,
        "ip_configurations": [
            {
                "name": IP_CONFIG_NAME,
                "subnet": { "id": subnet.id },
                "public_ip_address": { "id": public_ip.id },
            },
        ],
    },
)

nic = poller.result()

print(f"Network interface {NIC_NAME} created in {LOCATION}\n")

# 7.) Create the VM
print("Creating the VM...")

VM_NAME = "py-vm-1"
USERNAME = "azureuser"
PASSWORD = "Ch@ng3Me=" + (lambda length=4: ''.join(random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(length)))()

poller = compute_client.virtual_machines.begin_create_or_update(
    RESOURCE_GROUP_NAME,
    VM_NAME,
    {
        "location": LOCATION,
        "storage_profile": {
            "image_reference": {
                "publisher": "Canonical",
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest"
            },
        },
        "hardware_profile": { "vm_size": "Standard_B2s" },
        "os_profile": {
            "computer_name": VM_NAME,
            "admin_username": USERNAME,
            "admin_password": PASSWORD,
        },
        "network_profile": {
            "network_interfaces": [
                {
                    "id": nic.id,
                },
            ],
        },
    },
)

vm = poller.result()

print(f"VM {VM_NAME} created in {LOCATION} | USER: {USERNAME} | PASSWORD: {PASSWORD}\n")

print("VM created successfully!")
