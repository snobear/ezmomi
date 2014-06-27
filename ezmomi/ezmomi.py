#!/usr/bin/env python
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import atexit
import os
import sys
import errno
from pprint import pprint, pformat
import time
from netaddr import IPNetwork, IPAddress
import yaml
from netaddr import IPNetwork, IPAddress

class EZMomi(object):
    def __init__(self, **kwargs):
        # load up our configs and connect to the vSphere server
        self.config = self.get_configs(kwargs)
        self.connect()

    def get_configs(self, kwargs):
        default_cfg_dir = "%s/.config/ezmomi" % os.path.expanduser("~")
        default_config_file = "%s/config.yml" % default_cfg_dir
        
        # use path from env var if it's set and valid
        if 'EZMOMI_CONFIG' in os.environ:
            if os.path.isfile(os.environ['EZMOMI_CONFIG']):
                config_file = os.environ['EZMOMI_CONFIG']
            else:
                print "%s does not exist.  Set the EZMOMI_CONFIG environment variable to your config file's path."
                sys.exit(1)

        # or use the default config file path if it exists
        elif os.path.isfile(default_config_file):
            config_file = default_config_file
        # else create the default config path and copy the example config there
        else:
            from shutil import copy
            if not os.path.exists(default_cfg_dir):
                os.makedirs(default_cfg_dir)
            config_file = default_config_file
            
            # copy example config
            ezmomi_module_dir = os.path.dirname(os.path.abspath(__file__))
            ezmomi_ex_config = "%s/config/config.yml.example" % ezmomi_module_dir
            try:
                copy(ezmomi_ex_config, default_cfg_dir)
            except:
                print "Error copying example config file from %s to %s" % (ezmomi_ex_config, default_cfg_dir)
                sys.exit(1)
            
            print "I could not find a config.yml file, so I copied an example to your home directory at %s/config.yml.example.  Please rename this to config.yml and add your vSphere environment's settings." % default_cfg_dir
            sys.exit(0)
        try:
            config = yaml.load(file(config_file))
        except IOError:
            print 'Unable to open config file.  The default path for the ezmomi config file is ~/.config/ezmomi/config.yml. You can also specify the config file path by setting the EZMOMI_CONFIG environment variable.'
            sys.exit(1)
        except Exception:
            print 'Unable to read config file.  YAML syntax issue, perhaps?'
            sys.exit(1)

        # Check all required values were supplied either via command line or config
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
            print "Required parameters not set: %s\n" % notset
            sys.exit(1)
    
        return config

    '''
     Connect to vCenter server
    '''
    def connect(self):
        # connect to vCenter server
        try:
            si = SmartConnect(host = self.config['server'],
                              user = self.config['username'],
                              pwd  = self.config['password'],
                              port = int(self.config['port']),
                              )
        except:
            print 'Unable to connect to vsphere server.'
            sys.exit()

        # add a clean up routine
        atexit.register(Disconnect, si)

        self.content = si.RetrieveContent()

    '''
     Command Section: list
     List available VMware objects
    '''
    def list_objects(self):
        vimtype = self.config['type']
        vim_obj = "vim.%s" % vimtype
        
        try:
            container = self.content.viewManager.CreateContainerView(self.content.rootFolder, [eval(vim_obj)], True)
        except AttributeError:
            print "%s is not a Managed Object Type.  See the vSphere API docs for possible options." % vimtype
            sys.exit()
            
        # print header line
        print "%s list" % vimtype
        print "{0:<20} {1:<20}".format('MOID','Name')

        for c in container.view:
            print "{0:<20} {1:<20}".format(c._moId, c.name)

    def clone(self):
        self.config['hostname'] = self.config['hostname'].lower()
        self.config['mem'] = self.config['mem'] * 1024  # convert GB to MB

        print "Cloning %s to new host %s..." % (self.config['template'], self.config['hostname'])

        # initialize a list to hold our network settings
        ip_settings = list()
    
        # Get network settings for each IP
        for key, ip_string in enumerate(kwargs['ips']):
            
            # convert ip from string to the 'IPAddress' type
            ip = IPAddress(ip_string)
        
            # determine network this IP is in
            for network in self.config['networks']:
                #pprint(network['cluster'])
                if ip in IPNetwork(network):
                    self.config['networks'][network]['ip'] = ip
                    ipnet = IPNetwork(network)
                    self.config['networks'][network]['subnet_mask'] = str(ipnet.netmask)
                    ip_settings.append(self.config['networks'][network])
       
            # throw an error if we couldn't find a network for this ip
            if not any(d['ip'] == ip for d in ip_settings):
                print "I don't know what network %s is in.  You can supply settings for this network in self.config.yml." % ip_string
                sys.exit(1)
    
        # network to place new VM in
        self.get_obj( [vim.Network], ip_settings[0]['network'])
        datacenter = self.get_obj( [vim.Datacenter], ip_settings[0]['datacenter'])
        
        # get the folder where VMs are kept for this datacenter
        destfolder = datacenter.vmFolder
        
        cluster = self.get_obj( [vim.ClusterComputeResource], ip_settings[0]['cluster'])
        resource_pool = cluster.resourcePool # use same root resource pool that my desired cluster uses
        datastore = self.get_obj( [vim.Datastore], ip_settings[0]['datastore'])
        template_vm = self.get_obj( [vim.VirtualMachine], self.config['template'])
    
        # Relocation spec
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = resource_pool
    
        '''
         Networking self.config for VM and guest OS
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
            nic.device.backing.network = self.get_obj( [vim.Network], ip_settings[key]['network'])
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
                guest_map.adapter.dnsDomain = self.config['domain']
            except:
                pass

            adaptermaps.append(guest_map)

        # VM config spec
        vmconf = vim.vm.ConfigSpec()
        vmconf.numCPUs = self.config['cpus']
        vmconf.memoryMB = self.config['mem']
        vmconf.cpuHotAddEnabled = True
        vmconf.memoryHotAddEnabled = True
        vmconf.deviceChange = devices

        # DNS settings
        globalip = vim.vm.customization.GlobalIPSettings()
        globalip.dnsServerList = self.config['dns_servers']
        globalip.dnsSuffixList = self.config['domain']

        # Hostname settings
        ident = vim.vm.customization.LinuxPrep()
        ident.domain = self.config['domain']
        ident.hostName = vim.vm.customization.FixedName()
        ident.hostName.name = self.config['hostname']

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
        task = template_vm.Clone(folder=destfolder, name=self.config['hostname'], spec=clonespec)
        result = self.WaitTask(task, 'VM clone task')

        self.send_email()
         
    def destroy(self):
        print "Finding VM named %s..." % self.config['name']
        vm = self.get_obj([vim.VirtualMachine], self.config['name'])
        
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            print "Powering off %s..." % self.config['name']
            task = vm.PowerOff()
            result = self.WaitTask(task, 'VM power off')
        
        print "Destroying %s..." % self.config['name']
        task = vm.Destroy()
        result = self.WaitTask(task, 'VM destroy task')

    '''
     Helper methods
    '''
    def send_email(self):
        import smtplib
        from email.mime.text import MIMEText
    
        # get user who ran this script
        me = os.getenv('USER')
    
        email_body = 'Your VM is ready!'
        msg = MIMEText(email_body)
        msg['Subject'] = '%s - VM deploy complete' % self.config['hostname']
        msg['From'] = self.config['mailfrom'] 
        msg['To'] = me
    
        s = smtplib.SMTP('localhost')
        s.sendmail(self.config['mailfrom'] , [me], msg.as_string())
        s.quit()

    '''
     Get the vsphere object associated with a given text name
    '''
    def get_obj(self, vimtype, name):
        obj = None
        container = self.content.viewManager.CreateContainerView(self.content.rootFolder, vimtype, True)
        for c in container.view:
            if c.name == name:
                obj = c
                break
        return obj

    '''
     Waits and provides updates on a vSphere task
    '''
    def WaitTask(self, task, actionName='job', hideResult=False):
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
           raise task.info.error
        
        return task.info.result
