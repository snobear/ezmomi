#!/usr/bin/env python
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import atexit
import os
import sys
from pprint import pprint, pformat
import time
from netaddr import IPNetwork, IPAddress
import argparse
from copy import deepcopy
import yaml
import logging
from netaddr import IPNetwork, IPAddress

'''
Logging
'''
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


'''
 Send an email
'''
def send_email(config, ip_settings):
    import smtplib
    from email.mime.text import MIMEText

    # get user who ran this script
    me = os.getenv('USER')

    email_body = 'Your VM is ready!'
    msg = MIMEText(email_body)
    msg['Subject'] = '%s - VM deploy complete' % config['hostname']
    msg['From'] = config['mailfrom'] 
    msg['To'] = me

    s = smtplib.SMTP('localhost')
    s.sendmail(config['mailfrom'] , [me], msg.as_string())
    s.quit()

'''
 Waits and provides updates on a vSphere task
'''
def WaitTask(task, actionName='job', hideResult=False):
    #print 'Waiting for %s to complete.' % actionName
    
    while task.info.state == vim.TaskInfo.State.running:
       time.sleep(2)
    
    if task.info.state == vim.TaskInfo.State.success:
       if task.info.result is not None and not hideResult:
          out = '%s completed successfully, result: %s' % (actionName, task.info.result)
       else:
          out = '%s completed successfully.' % actionName
    else:
       out = '%s did not complete successfully: %s' % (actionName, task.info.error)
       print out
       raise task.info.error # should be a Fault... check XXX
    
    # may not always be applicable, but can't hurt.
    return task.info.result

'''
 Get the vsphere object associated with a given text name
'''
def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj

'''
 Connect to vCenter server and return content object
'''
def connect(config):
    # connect to vCenter server
    try:
        si = SmartConnect(host=config['server'], user=config['username'], pwd=config['password'], port=int(config['port']))
    except:
        logging.exception('Unable to connect to vsphere server.')
        sys.exit()
    
    # add a clean up routine
    atexit.register(Disconnect, si)
    
    content = si.RetrieveContent()

    return content


'''
 Connect to vCenter server and deploy a VM from template
'''
def clone(config):
    config['hostname'] = config['hostname'].lower()
    config['cpus'] = config['cpus']
    config['mem'] = config['mem'] * 1024  # convert GB to MB

    # initialize a list to hold our network settings
    ip_settings = list()

    # Get network settings for each IP
    for key, ip_string in enumerate(kwargs['ips']):
        
        # convert ip from string to the 'IPAddress' type
        ip = IPAddress(ip_string)
    
        # determine network this IP is in
        for network in config['networks']:
            #pprint(network['cluster'])
            if ip in IPNetwork(network):
                config['networks'][network]['ip'] = ip
                ipnet = IPNetwork(network)
                config['networks'][network]['subnet_mask'] = str(ipnet.netmask)
                ip_settings.append(config['networks'][network])
   
        # throw an error if we couldn't find a network for this ip
        if not any(d['ip'] == ip for d in ip_settings):
            logging.error("I don't know what network %s is in.  You can supply settings for this network via command line or in config.yml." % ip_string)
            sys.exit(1)

    # network to place new VM in
    get_obj(content, [vim.Network], ip_settings[0]['network'])
    datacenter = get_obj(content, [vim.Datacenter], ip_settings[0]['datacenter'])
    # get the folder where VMs are kept for this datacenter
    destfolder = datacenter.vmFolder
    
    cluster = get_obj(content, [vim.ClusterComputeResource], ip_settings[0]['cluster'])
    resource_pool = cluster.resourcePool # use same root resource pool that my desired cluster uses
    datastore = get_obj(content, [vim.Datastore], ip_settings[0]['datastore'])
    template_vm = get_obj(content, [vim.VirtualMachine], config['template'])

    # Relocation spec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    '''
     Networking config for VM and guest OS
    '''
    devices = [] 
    adaptermaps = []

    # create a Network device for each static IP
    for key, ip in enumerate(ip_settings):
        # VM device
        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.add  # or edit if a device exists
        nic.device = vim.vm.device.VirtualVmxnet3()
        nic.device.wakeOnLanEnabled = True
        nic.device.addressType = 'assigned'
        nic.device.key = 4000  # 4000 seems to be the value to use for a vmxnet3 device
        nic.device.deviceInfo = vim.Description()
        nic.device.deviceInfo.label = 'Network Adapter %s' % (key + 1)
        nic.device.deviceInfo.summary = ip_settings[key]['network']
        nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic.device.backing.network = get_obj(content, [vim.Network], ip_settings[key]['network'])
        nic.device.backing.deviceName = ip_settings[key]['network']
        nic.device.backing.useAutoDetect = False
        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True
        devices.append(nic)

        # guest NIC settings, i.e. 'adapter map'
        guest_map = vim.vm.customization.AdapterMapping()
        guest_map.adapter = vim.vm.customization.IPSettings()
        guest_map.adapter.ip = vim.vm.customization.FixedIp()
        guest_map.adapter.ip.ipAddress = str(ip_settings[key]['ip'])
        guest_map.adapter.subnetMask = str(ip_settings[key]['subnet_mask'])
        
        # these may not be set for certain IPs, e.g. storage IPs
        try:
            guest_map.adapter.gateway = ip_settings[key]['gateway']
        except:
            pass

        try:
            guest_map.adapter.dnsDomain = config['domain']
        except:
            pass
            
        adaptermaps.append(guest_map)

    # VM config spec
    vmconf = vim.vm.ConfigSpec()
    vmconf.numCPUs = config['cpus']
    vmconf.memoryMB = config['mem']
    vmconf.cpuHotAddEnabled = True
    vmconf.memoryHotAddEnabled = True
    vmconf.deviceChange = devices

    # DNS settings
    globalip = vim.vm.customization.GlobalIPSettings()
    globalip.dnsServerList = config['dns_servers']
    globalip.dnsSuffixList = config['domain']
    
    # Hostname settings
    ident = vim.vm.customization.LinuxPrep()
    ident.domain = config['domain']
    ident.hostName = vim.vm.customization.FixedName()
    ident.hostName.name = config['hostname']
    
    customspec = vim.vm.customization.Specification()
    customspec.nicSettingMap = adaptermaps
    customspec.globalIPSettings = globalip
    customspec.identity = ident

    # Clone spec
    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.config = vmconf
    clonespec.customization = customspec
    clonespec.powerOn = True
    clonespec.template = False

    # fire the clone task
    
    task = template_vm.Clone(folder=destfolder, name=config['hostname'].title(), spec=clonespec)
    result = WaitTask(task, 'VM clone task')
    
    # send me an email when the task is complete
    send_email(config, ip_settings)

def get_configs(kwargs):
    # load config file
    try:
        config_path = '%s/config.yml' % os.path.dirname(os.path.realpath(__file__))
        config = yaml.load(file(config_path))
    except IOError:
        logging.exception('Unable to open config file.')
        sys.exit(1)
    except Exception:
        logging.exception('Unable to read config file.')
        sys.exit(1)

    # Check all required values were supplied either via command line or config
    #
    # override defaults from config.yml with any supplied command line arguments
    notset = list()
    for key, value in kwargs.items():
        if value:
            config[key] = value
        elif (value is None) and (key not in config):
            # compile list of parameters that were not set
            notset.append(key)

    if notset:
        parser.print_help()
        print
        logging.error("Required parameters not set: %s\n" % notset)
        sys.exit(1)

    return config

def listing(config):




def main(**kwargs):
    # Do action
    if kwargs['list']:
        config = get_configs(kwargs)

        print 'list'
    # clone template to a new VM with our specified settings
    else:
        connect(kwargs)
        clone(config)

'''
 Main program
'''
if __name__ == '__main__':
    # Define command line arguments
    parser = argparse.ArgumentParser(description='Deploy a new VM in vSphere')
    parser.add_argument('--server', type=str, help='vCenter server',)
    parser.add_argument('--port', type=str, help='vCenter server port',)
    parser.add_argument('--username', type=str, help='vCenter username',)
    parser.add_argument('--password', type=str, help='vCenter password',)
    parser.add_argument('--list', type=str, help='List my vSphere objects',)
    parser.add_argument('--template', type=str, help='VM template name to clone from')
    parser.add_argument('--hostname', type=str, help='New host name',)
    parser.add_argument('--ips', type=str, help='Static IPs of new host, separated by a space.  List primary IP first.', nargs='+')
    parser.add_argument('--cpus', type=int, help='Number of CPUs')
    parser.add_argument('--mem', type=int, help='Memory in GB')
    parser.add_argument('--domain', type=str, help='Domain, e.g. "example.com"',)

    # Parse arguments and hand off to main()
    args = parser.parse_args()
    main(**vars(args))

