import paramiko
import os
import time
import commands
import re

# returns ssh object for a node
def connect(ip):
    try:
        pwd = None
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=ip, username="heat-admin", password=pwd)
    except:
        print("Failed to connect through SSH on node: {}".format(ip))
        ssh = "Failed Execution"
    return ssh

# returns a list of container services currently running on a node
def get_services(ip):
    try:
        ssh = connect(ip)
        if ssh != "Failed Execution":
            stdin, stdout, stderr = ssh.exec_command('''sudo docker ps --format "{{.Names}}"''' , get_pty=True)
            time.sleep(.01)
            data = stdout.read()
            result = data.split("\r\n")
            while("" in result):
                result.remove("")
            ssh.close()
        else:
            result = "Failed Execution"
    except:
        print("Failed to get container-services info for node: {}".format(ip))
        result = "Failed Execution"
    return result

# returns a list of nodes and their credentials
def get_nodes():
    nodes = []
    node = {}
    # Get OpenStack Servers List
    output = commands.getoutput('openstack server list')
    # Extract IDs
    ids = re.findall("(\w{8}\-\w{4}\-\w{4}\-\w{4}\-\w{12})", output)
    # Extract Names
    names = re.findall("\w{8}\-\w{4}\-\w{4}\-\w{4}\-\w{12}\s\|\s([^\s]+)", output)
    # Extract IP Adresses
    ips = re.findall("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", output)
    # Extract Flavors
    flavors = re.findall("overcloud\-full\s\|\s([^\s]+)", output)
    #print(str(range(flavors)))

    for i in range(len(ids)):
        node["id"] = ids[i]
        node["name"] = names[i]
        node["ip"] = ips[i]
        node["flavor"] = flavors[i]
        nodes.append(node)
        node = {}
    return nodes


def main():
    nodes = get_nodes()
    print(nodes)

if __name__ == "__main__":
    main()
