#!/usr/bin/env python
from __future__ import print_function
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import atexit
import os
import sys
# import random
# import errno
# from pprint import pprint, pformat
# import time
from netaddr import IPNetwork, IPAddress
import yaml
from shutil import copy


class EZMomi(object):
    def __init__(self, **kwargs):
        # load up our configs and connect to the vSphere server
        self.config = self.get_configs(kwargs)
        self.connect()

    @staticmethod
    def find_config_name():
        cfg_dir = os.path.join(
            os.path.abspath(os.path.expanduser("~")),
            '.config',
            'ezmomi'
        )
        default_cfg_file = os.path.join(cfg_dir, "config.yml")
        cfg_file = os.environ.get('EZMOMI_CONFIG', default_cfg_file)
        return cfg_file

    @staticmethod
    def gen_default_example_config_name():
        # copy example config
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "config/config.yml.example"
        )

    @staticmethod
    def gen_cfg_example(config_file, file_template=None):

        cfg_dir = os.path.dirname(config_file)
        if not os.path.exists(cfg_dir):
            os.makedirs(cfg_dir)

        if not file_template:
            file_template = EZMomi.gen_default_example_config_name()

        msg = " ".join([
            "Cannot find file_template config file at",
            file_template
        ])
        # if src is missing, exceptions from copy should be grokkable
        assert os.path.isfile(file_template), msg
        target = '.'.join([config_file, 'example'])
        copy(file_template, target)
        return target

    def get_configs(self, kwargs):
        config_file = self.find_config_name()

        if not os.path.isfile(config_file):
            if not 'EZMOMI_CONFIG' in os.environ:
                example = EZMomi.gen_cfg_example(config_file)
                msg = " ".join([
                    "I could not find configuration file, so I copied an "
                    "example to your home directory at:",
                    example + ".",
                    "Please rename this to config.yml and add your vSphere",
                    "environment's settings.",
                ])
                print(msg)
                sys.exit(0)

            # env var is set but no file exists
            msg = " ".join([
                "{config_file} does not exist.".format(**locals()),
                "Set the EZMOMI_CONFIG environment",
                "variable to your config file's path.",
            ])
            print(msg)
            sys.exit(1)

        # noinspection PyPackageRequirements
        try:
            config = yaml.load(file(config_file))
        except IOError:
            msg = " ".join([
                'Unable to open config file. The default path for the ezmomi',
                'config file is {config_file}.'.format(**locals()),
                'You can also specify the config file path by setting the',
                'EZMOMI_CONFIG environment variable.'
            ])
            print(msg)
            sys.exit(1)
        except Exception:
            print('Unable to read config file. YAML syntax issue, perhaps?')
            sys.exit(1)

        # Check all required values were supplied either via command line
        # or config. override defaults from config.yml with any supplied
        # command line arguments
        notset = list()
        for key, value in kwargs.items():
            if value:
                config[key] = value
            elif (value is None) and (key not in config):
                # compile list of parameters that were not set
                notset.append(key)

        if notset:
            print("Required parameters not set: {notset}".format(**locals()))
            sys.exit(1)

        return config

    '''
     Connect to vCenter server
    '''
    def connect(self):
        # connect to vCenter server
        try:
            self.si = SmartConnect(host=self.config['server'],
                                   user=self.config['username'],
                                   pwd=self.config['password'],
                                   port=int(self.config['port']),
                                   )
        except Exception as e:
            print('Unable to connect to vsphere server.')
            print(repr(e))
            sys.exit(1)

        # add a clean up routine
        atexit.register(Disconnect, self.si)

        self.content = self.si.RetrieveContent()

    '''
     Command Section: list
     List available VMware objects
    '''
    def list_objects(self):
        vimtype = self.config['type']
        vim_obj = ".".join(["vim", vimtype])

        try:
            container = self.content.viewManager.CreateContainerView(
                self.content.rootFolder, [eval(vim_obj)], True)
        except AttributeError:
            msg = " ".join([
                vimtype,
                "is not a Managed Object Type.",
                "See the vSphere API docs for possible options.",
            ])
            print(msg)
            sys.exit(1)

        # print header line
        print("{vimtype} list".format(**locals()))
        print("{0:<20} {1:<20}".format('MOID', 'Name'))

        for c in container.view:
            print("{0:<20} {1:<20}".format(c._moId, c.name))

    def build_clonespec_with_more_data(self, adaptermaps, devices, relospec):
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
        return clonespec

    def clone(self):
        self.config['hostname'] = self.config['hostname'].lower()
        self.config['mem'] = self.config['mem'] * 1024  # convert GB to MB
        msg = " ".join([
            "Cloning",
            self.config.get('template'),
            "to new host",
            self.config.get('hostname'),
            "...",
        ])
        print(msg)
        # initialize a list to hold our network settings
        if not 'networks' in self.config:
            return self.clone_as_template()

        ip_settings = list()

        # Get network settings for each IP
        for key, ip_string in enumerate(self.config['ips']):

            # convert ip from string to the 'IPAddress' type
            ip = IPAddress(ip_string)

            # determine network this IP is in
            for network in self.config['networks']:
                if ip in IPNetwork(network):
                    self.config['networks'][network]['ip'] = ip
                    ipnet = IPNetwork(network)
                    self.config['networks'][network]['subnet_mask'] = str(
                        ipnet.netmask
                    )
                    ip_settings.append(self.config['networks'][network])

            # throw an error if we couldn't find a network for this ip
            if not any(d['ip'] == ip for d in ip_settings):
                msg = " ".join([
                    "I don't know what network", ip_string, "is in.",
                    "You can supply settings for this network in config.yml.",
                ])
                print(msg)
                sys.exit(1)

        # network to place new VM in
        self.get_obj(
            [vim.Network],
            ip_settings[0]['network']
        )
        datacenter = self.get_obj(
            [vim.Datacenter],
            ip_settings[0]['datacenter']
        )

        # get the folder where VMs are kept for this datacenter
        destfolder = datacenter.vmFolder

        cluster = self.get_obj(
            [vim.ClusterComputeResource],
            ip_settings[0]['cluster']
        )
        # use same root resource pool that my desired cluster uses
        resource_pool = None
        if cluster:
            resource_pool = cluster.resourcePool
        datastore = self.get_obj(
            [vim.Datastore],
            ip_settings[0]['datastore']
        )
        template_vm = self.get_obj(
            [vim.VirtualMachine],
            self.config['template']
        )

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
            # or edit if a device exists
            nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            nic.device = vim.vm.device.VirtualVmxnet3()
            nic.device.wakeOnLanEnabled = True
            nic.device.addressType = 'assigned'
            # 4000 seems to be the value to use for a vmxnet3 device
            nic.device.key = 4000
            nic.device.deviceInfo = vim.Description()
            nic.device.deviceInfo.label = ' '.join([
                'Network Adapter',
                str(key+1),
            ])
            nic.device.deviceInfo.summary = ip_settings[key]['network']
            nic.device.backing = (
                vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            )
            nic.device.backing.network = (
                self.get_obj([vim.Network], ip_settings[key]['network'])
            )
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

        clonespec = self.build_clonespec_with_more_data(
            adaptermaps,
            devices,
            relospec
        )

        # fire the clone task
        tasks = [template_vm.Clone(folder=destfolder,
                                   name=self.config['hostname'],
                                   spec=clonespec
                                   )]
        self.WaitForTasks(tasks)
        self.send_email()


    def build_clonespec(
            self,
            datastore,
            pool,
            host,
            poweron=True,
            is_template=False):
        # Relocation spec
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = pool
        relospec.host = host
        # Clone spec
        clonespec = vim.vm.CloneSpec()
        clonespec.location = relospec
        clonespec.powerOn = poweron
        clonespec.template = is_template
        return clonespec

    def clone_as_template(self):
        self.config['hostname'] = self.config['hostname'].lower()
        self.config['mem'] *= 1024  # convert GB to MB
        ## we can choose target host randomly:
        # host = random.choice(self.config.get('hosts'))
        ## or not randomly
        host = self.config.get('hosts')[0]

        trg_host = self.get_obj([vim.HostSystem], host)
        dk = 'datacenter'
        dcname = self.config.get(dk)
        datacenter = self.get_obj([vim.Datacenter], dcname)

        # get the folder where VMs are kept for this datacenter
        destfolder = datacenter.vmFolder

        # use same root resource pool that my desired cluster uses
        resource_pool = None
        cluster = self.get_obj([vim.ClusterComputeResource], host)
        if cluster:
            resource_pool = cluster.resourcePool

        if not resource_pool:
            ## "clusterless" host: use its resource pool
            hosts = datacenter.hostFolder.childEntity
            for h in hosts:
                if h.name == host:
                    resource_pool = h.resourcePool
                    break
        assert not resource_pool is None

        datastore = self.get_obj([vim.Datastore], self.config.get('datastore'))
        template = self.get_obj([vim.VirtualMachine], self.config['template'])
        clonespec = self.build_clonespec(datastore, resource_pool, trg_host)

        # fire the clone task
        tasks = [
            template.Clone(
                folder=destfolder,
                name=self.config['hostname'],
                spec=clonespec
            )
        ]
        result = self.WaitForTasks(tasks)
        self.send_email()
        return result

    def destroy(self):
        tasks = list()
        print("Finding VM named {name}...".format(**self.config))
        vm = self.get_obj([vim.VirtualMachine], self.config['name'])

        # need to shut the VM down before destorying it
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            tasks.append(vm.PowerOff())

        tasks.append(vm.Destroy())
        print("Destroying {name}...".format(**self.config))
        self.WaitForTasks(tasks)

    '''
     Helper methods
    '''
    def send_email(self):
        import smtplib
        from email.mime.text import MIMEText

        # get user who ran this script
        alerts_conf = dict()
        rcpt = [os.environ.get('USER')]
        mailfrom = self.config.get('mailfrom')
        email_body = 'Your VM is ready!'

        if 'notifications' in self.config:
            alerts_conf = self.config['notifications']

        if 'recipients' in alerts_conf:
            rcpt = alerts_conf.get('recipients')
            assert isinstance(rcpt, (list, tuple))

        msg = MIMEText(email_body)
        msg['Subject'] = '{hostname} - VM deploy complete'.format(**self.config)
        msg['From'] = mailfrom
        msg['To'] = ', '.join(rcpt)

        s = smtplib.SMTP('localhost')
        s.sendmail(mailfrom, rcpt, msg.as_string())
        s.quit()

    '''
     Get the vsphere object associated with a given text name
    '''
    def get_obj(self, vimtype, name):
        obj = None
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vimtype, True)
        for c in container.view:
            if c.name == name:
                obj = c
                break
        return obj

    def WaitForTasks(self, tasks):
        """
        Given the service instance si and tasks, it returns after all the
        tasks are complete
        """

        pc = self.si.content.propertyCollector

        taskList = [str(task) for task in tasks]

        # Create filter
        objSpecs = [vmodl.query.PropertyCollector.ObjectSpec(
            obj=task) for task in tasks]
        propSpec = vmodl.query.PropertyCollector.PropertySpec(
            type=vim.Task, pathSet=[], all=True)
        filterSpec = vmodl.query.PropertyCollector.FilterSpec()
        filterSpec.objectSet = objSpecs
        filterSpec.propSet = [propSpec]
        filter = pc.CreateFilter(filterSpec, True)

        try:
            version, state = None, None

            # Loop looking for updates till the state moves to a
            # completed state.
            while len(taskList):
                update = pc.WaitForUpdates(version)
                for filterSet in update.filterSet:
                    for objSet in filterSet.objectSet:
                        task = objSet.obj
                        for change in objSet.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in taskList:
                                continue

                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                taskList.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if filter:
                filter.Destroy()
