import paramiko
import os
import time
import commands
import re
import json
import sys
import signal

import getnodes
import checkfiles

checks = checkfiles.checks
nodes = []
services = {}
permissions = {}
cwd = os.getcwd()
cloud_info_dir = cwd + "/cloudinfo/"
conf_dir = cwd + "/conf/"


def signal_handler(sig, frame):
    print('You pressed Ctrl+C! Exiting...')
    sys.exit(0)


def execute_command(ssh, command):
    try:
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
        time.sleep(.1)
        result = stdout.read()
        time.sleep(.1)
    except:
        print("Failed to execute command : %s" % command)
        result = ("Failed Execution")
    return result


# Check auth_strategy==keystone in .conf files
def auth_strategy(ssh, service):
    c1 = 1
    c2 = 1
    if service == "nova_compute" or service == "nova_api":
        folder = "nova"
    elif service == "keystone":
        folder = "keystone"
    elif service == "neutron_api":
        folder = "neutron"
    elif service == "cinder_api":
        folder = "cinder"
    file = folder + '.conf'

    if service == "nova_compute":
        path = '''/var/lib/config-data/puppet-generated/nova_libvirt/etc/''' + folder + '''/''' + file
        p1 = '''sudo cat ''' + path + ''' | grep auth_strategy'''
    else:
        path = '''/var/lib/config-data/puppet-generated/''' + folder + '''/etc/''' + folder + '''/''' + file
        p1 = '''sudo cat ''' + path + ''' | grep auth_strategy'''
    out = execute_command(ssh, p1)
    out = out.splitlines()

    for line in out:
        if line.startswith('auth_strategy'):
            if line == "auth_strategy=keystone" or line == "auth_strategy = keystone":
                print('''\nService: %s, Expected_Authentication_Method: keystone, Status: Success\n''' %(service))
            else:
                print('''\nService: %s, Expected_Authentication_Method: keystone, Status: Failed''' %(service))
                print('''Restoring Authentication Method to keystone...''')
                replace = '''sudo sed -i 's/^auth_strategy.*/auth_strategy=keystone/' ''' + path
                stdin, stdout, stderr = ssh.exec_command(replace)
                c1 = stdout.channel.recv_exit_status()
                if c1 == 0:
                    print('''Authentication method restored Successfully > Service: %s, Authentication_Method: keystone''' %(service))
                    print('''Restarting %s service for changes to take effect...''' %(service))
                    restart = '''sudo docker restart ''' + service
                    stdin, stdout, stderr = ssh.exec_command(restart)
                    c2 = stdout.channel.recv_exit_status()
                    if c2 == 0:
                        print('''Restart Successfull...\n''')
                    else:
                        print('''Failed to restart...''')
                else:
                    print('''Failed to restore Authentication Method! Try Manually...''')


# Restore the file permissions
def restore_owners(ssh, list):

    for element in list:
        c1 = 1
        container = element["container"]
        owners = element["owners"]
        file = element["file"]
        cmd = element["cmd"]
        owners = ':'.join(owners.split())
        if container == "nova_compute" or container == "nova_api":
            folder = "nova"
        elif container == "keystone":
            folder = "keystone"
        elif container == "neutron_api":
            folder = "neutron"
        elif container == "cinder_api":
            folder = "cinder"

        if "puppet" in cmd:
            if container == "nova_compute":
                path = '''/var/lib/config-data/puppet-generated/nova_libvirt/etc/''' + folder + '''/''' + file
                p1 = '''sudo chown ''' + owners + ''' ''' + path
            else:
                path = '''/var/lib/config-data/puppet-generated/''' + folder + '''/etc/''' + folder + '''/''' + file
                p1 = '''sudo chown ''' + owners + ''' '''
        else:
            p1 = '''sudo docker exec --user 0 ''' + container + ''' bash -c "sudo chown ''' + owners + ''' /etc/''' + folder + '''/''' + file + '''"'''

        stdin, stdout, stderr = ssh.exec_command(p1, get_pty=True)
        c1 = stdout.channel.recv_exit_status()
        if c1 == 0:
            print("\nFile owners restored Successfully > Service: %s, File: %s, Owners: %s\n" %(container, file, owners))
            list.remove(element)
        else:
            print("\nFailed to restore file permissions. Try Manually > Service: %s, File: %s, Permissions: %s\n" %(container, file, owners))


# Restore the file permissions
def restore_permissions(ssh, list):
    for element in list:
        c1 = 1
        container = element["container"]
        permissions = element["permissions"]
        file = element["file"]
        cmd = element["cmd"]
        if container == "nova_compute" or container == "nova_api":
            folder = "nova"
        elif container == "keystone":
            folder = "keystone"
        elif container == "neutron_api":
            folder = "neutron"
        elif container == "cinder_api":
            folder = "cinder"

        if "puppet" in cmd:
            if container == "nova_compute":
                p1 = '''sudo chmod ''' + permissions + ''' /var/lib/config-data/puppet-generated/nova_libvirt/etc/''' + folder + '''/''' + file
            else:
                p1 = '''sudo chmod ''' + permissions + ''' /var/lib/config-data/puppet-generated/''' + folder + '''/etc/''' + folder + '''/''' + file
        else:
            p1 = '''sudo docker exec --user 0 ''' + container + ''' bash -c "sudo chmod ''' + permissions + ''' /etc/''' + folder + '''/''' + file + '''"'''

        stdin, stdout, stderr = ssh.exec_command(p1, get_pty=True)
        c1 = stdout.channel.recv_exit_status()
        if c1 == 0:
            print("\nFile permissions restored Successfully > Service: %s, File: %s, Permissions: %s\n" %(container, file, permissions))
        else:
            print("\nFailed to restore file permissions. Try Manually > Service: %s, File: %s, Permissions: %s\n" %(container, file, permissions))


def compare_permissions(ssh, service, service_checks, service_permissions):
    global restore_permissions_dict
    change_owners = []
    change_permissions = []

    # Compare file permissions
    file_perm = service_permissions["permissions"]
    commands = service_checks["permission_checks"]
    for file in file_perm:
        change_file = {}
        for cmd in commands:
            if file in cmd:
                cmd_result = execute_command(ssh, cmd)
                cmd_result = cmd_result.rstrip("\r\n")
                if file_perm[file] == cmd_result:
                    print("\nService: %s, File: %s, Expected: %s, Recieved: %s, Status: Success\n" %(service,file,file_perm[file],cmd_result))
                else:
                    print("\nService: %s, File: %s, Expected: %s, Recieved: %s, Status: Failed" %(service,file,file_perm[file],cmd_result))
                    print("File added to restore_permissions_list to restore recommended permissions...\n")
                    change_file["container"] = service
                    change_file["file"] = file
                    change_file["permissions"] = file_perm[file]
                    change_file["cmd"] = cmd
                    change_permissions.append(change_file)
    restore_permissions(ssh, change_permissions)

    # Compare file owners
    file_owners = service_permissions["owners"]
    commands = service_checks["owner_checks"]
    for file in file_owners:
        change_file = {}
        for cmd in commands:
            if file in cmd:
                cmd_result = execute_command(ssh, cmd)
                cmd_result = cmd_result.rstrip("\r\n")
                if file_owners[file] in cmd_result:
                    print("\nService: %s, File: %s, Expected: %s, Recieved: %s, Status: Success\n" %(service,file,file_owners[file],cmd_result))
                else:
                    print("\nService: %s, File: %s, Expected: %s, Recieved: %s, Status: Failed" %(service,file,file_owners[file],cmd_result))
                    print("File added to restore_owners_list to restore recommended permissions...\n")
                    change_file["container"] = service
                    change_file["file"] = file
                    change_file["owners"] = file_owners[file]
                    change_file["cmd"] = cmd
                    change_owners.append(change_file)
    restore_owners(ssh, change_owners)

def secure_control(node):
    global services, permissions, checks
    node_services = services[node['name']]
    ssh = getnodes.connect(node['ip'])
    for service in node_services:
        if service in checks:
            service_checks = checks[service]
            service_permissions = permissions[service]
            compare_permissions(ssh, service, service_checks, service_permissions)
            if service != 'keystone':
                auth_strategy(ssh, service)
    ssh.close()


def secure_compute(node):
    global services, permissions, checks
    node_services = services[node['name']]
    ssh = getnodes.connect(node['ip'])
    for service in node_services:
        if service in checks:
            service_checks = checks[service]
            service_permissions = permissions[service]
            compare_permissions(ssh, service, service_checks, service_permissions)
            if service != 'keystone':
                auth_strategy(ssh, service)
    # Check if ksm/ksmtuned service is running and disable
    ksm = "systemctl status ksmtuned"
    ksm = "systemctl status ksm"
    stdin, stdout, stderr = ssh.exec_command(ksm)
    ksmtuned_status = stdout.channel.recv_exit_status()
    stdin, stdout, stderr = ssh.exec_command(ksm)
    ksm_status = stdout.channel.recv_exit_status()
    if ksmtuned_status == 0 or ksm_status == 0:
        print("\nService: KSM, Expected: Disabled, Recieved: Enabled, Status: Failed\nDisabling KSM services...")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl stop ksmtuned")
        st0 = stdout.channel.recv_exit_status() # status of succes of command > success = 0
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl stop ksm")
        st1 = stdout.channel.recv_exit_status()
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl disable ksmtuned")
        stdin, stdout, stderr = ssh.exec_command("sudo systemctl disable ksmtuned")
        if st0 == st1 == 0:
            print("Successfully Disabled\n")
        else:
            print("Failed to Disable KSM services, Try Manually...")
    else:
        print("\nService: KSM, Expected: Disabled, Recieved: Disabled, Status: Success\n")

    ssh.close()


def start_secure():
    global nodes, services, permissions
    while(True):
        for node in nodes:
            if node['flavor'] == 'compute':
                print("\n:::::::::::Securing Compute Node: {}::::::::::\n".format(node['ip']))
                secure_compute(node)
            elif node['flavor'] == 'control':
                print("\n::::::::::Securing Control Node: {}::::::::::\n".format(node['ip']))
                secure_control(node)

        print("\nCheck cycle completed Successfully. Waiting for 10 sec...\n")
        time.sleep(10)

def main():
    global nodes, services, permissions, cloud_info_dir, conf_dir
    signal.signal(signal.SIGINT, signal_handler)

    # Get file permissions from file
    with open(conf_dir + 'permissions.json', 'r') as f:
        permissions = json.load(f)
        f.close()

    # Get nodes info and save in nodes.json file
    nodes = getnodes.get_nodes()
    with open(cloud_info_dir + 'nodes.json', 'w') as f:
        json.dump(nodes, f)
        f.close()
    with open(cloud_info_dir + 'nodes.json', 'r') as f:
        nodees = json.load(f)
        print("\n::::::::::Following server nodes exist currently in your Deployment::::::::::\n")
        for node in nodees:
            print(node)
        f.close()

    # Get services on each node and save in services.json file
    for node in nodes:
        services[node["name"]] = getnodes.get_services(node["ip"])
    with open(cloud_info_dir + 'services.json', 'w') as f:
        json.dump(services, f)
        f.close()
    with open(cloud_info_dir + 'services.json', 'r') as f:
        servicees = json.load(f)
        for node in servicees:
            print("\n::::::::::Following services are running on %s::::::::::\n" %node)
            print(servicees[node])
        f.close()

    start_secure()


if __name__ == "__main__":
    try:
        main()
    except:
        print('Exception in Secure.py')
        print('Cause of Exception: %s' %(sys.exc_info()[0]))
        print('Exception: %s' %(sys.exc_info()[1]))
        sys.exit(0)
    finally:
        print('Secure.py stopped...')
