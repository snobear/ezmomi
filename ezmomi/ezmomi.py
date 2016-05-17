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
import ssl


class EZMomi(object):
    def __init__(self, **kwargs):
        """load up our configs and connect to the vSphere server"""
        self.config = self.get_configs(kwargs)
        self.debug = self.config['debug']
        self.connect()
        self._column_spacing = 4

    def print_debug(self, title, obj):
        try:
            msg = vars(obj)
        except:
            msg = obj

        print "DEBUG: %s\n%s" % (title, pformat(msg))

    def get_configs(self, kwargs):
        default_cfg_dir = "%s/.config/ezmomi" % os.path.expanduser("~")
        default_config_file = "%s/config.yml" % default_cfg_dir

        # use path from env var if it's set and valid
        if 'EZMOMI_CONFIG' in os.environ:
            if os.path.isfile(os.environ['EZMOMI_CONFIG']):
                config_file = os.environ['EZMOMI_CONFIG']
            else:
                print "%s does not exist.  Set the EZMOMI_CONFIG environment" \
                      "variable to your config file's path."
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
            ezmomi_ex_config = ("%s/config/config.yml.example"
                                % ezmomi_module_dir)
            try:
                copy(ezmomi_ex_config, default_cfg_dir)
            except:
                print ("Error copying example config file from %s to %s"
                       % (ezmomi_ex_config, default_cfg_dir))
                sys.exit(1)

            print "Could not find a config.yml file, so I copied an example "\
                  "to your home directory at %s/config.yml.example.  Please "\
                  "rename this to config.yml and add your vSphere "          \
                  "environment's settings." % default_cfg_dir
            sys.exit(0)
        try:
            config = yaml.load(file(config_file))
        except IOError:
            print "Unable to open config file. The default ezmomi config "\
                  "filepath is ~/.config/ezmomi/config.yml. You can also "\
                  "specify the config file path by setting the EZMOMI_CONFIG "\
                  "environment variable."
            sys.exit(1)
        except Exception:
            print 'Unable to read config file.  YAML syntax issue, perhaps?'
            sys.exit(1)

        # Check all required values were supplied either via command line
        # or config. override defaults from config.yml with any supplied
        # command line arguments
        notset = list()
        for key, value in kwargs.items():
            if value is not None:
                config[key] = value
            elif (value is None) and (key not in config):
                # compile list of parameters that were not set
                notset.append(key)

        if notset:
            print "Required parameters not set: %s\n" % notset
            sys.exit(1)

        return config

    def connect(self):
        """Connect to vCenter server"""
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
            self.si = SmartConnect(
                        host=self.config['server'],
                        user=self.config['username'],
                        pwd=self.config['password'],
                        port=int(self.config['port']),
                        sslContext=context,
                        certFile=None,
                        keyFile=None,
                        )
        except Exception as e:
            print 'Unable to connect to vsphere server.'
            print e
            sys.exit(1)

        # add a clean up routine
        atexit.register(Disconnect, self.si)

        self.content = self.si.RetrieveContent()

    def list_objects(self):
        """
        Command Section: list
        List available VMware objects
        """
        vimtype = self.config['type']
        vim_obj = "vim.%s" % vimtype

        try:
            container = self.content.viewManager.CreateContainerView(
                self.content.rootFolder, [eval(vim_obj)], True)
        except AttributeError:
            print "%s is not a Managed Object Type.  See the vSphere API " \
                  "docs for possible options." % vimtype
            sys.exit(1)

        # print header line
        print "%s list" % vimtype

        if vimtype == "VirtualMachine":
            rows = [['MOID', 'Name', 'Status']]
        else:
            rows = [['MOID', 'Name']]

        for c in container.view:
            if vimtype == "VirtualMachine":
                rows.append([c._moId, c.name, c.runtime.powerState])
            else:
                rows.append([c._moId, c.name])

        self.tabulate(rows)

    def clone(self):
        """
        Command Section: clone
        Clone a VM from a template
        """
        self.config['hostname'] = self.config['hostname'].lower()
        self.config['mem'] = int(self.config['mem'] * 1024)  # convert GB to MB

        print "Cloning %s to new host %s with %sMB RAM..." % (
            self.config['template'],
            self.config['hostname'],
            self.config['mem']
        )

        # initialize a list to hold our network settings
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
                print "I don't know what network %s is in.  You can supply " \
                      "settings for this network in config.yml." % ip_string
                sys.exit(1)

        # network to place new VM in
        self.get_obj([vim.Network], ip_settings[0]['network'])
        datacenter = self.get_obj([vim.Datacenter],
                                  ip_settings[0]['datacenter']
                                  )

        # get the folder where VMs are kept for this datacenter
        destfolder = datacenter.vmFolder

        cluster = self.get_obj([vim.ClusterComputeResource],
                               ip_settings[0]['cluster']
                               )

        resource_pool_str = self.config['resource_pool']
        # resource_pool setting in config file takes priority over the
        # default 'Resources' pool
        if resource_pool_str == 'Resources' \
                and ('resource_pool' in ip_settings[key]):
            resource_pool_str = ip_settings[key]['resource_pool']

        resource_pool = self.get_resource_pool(cluster, resource_pool_str)

        host_system = self.config['host']
        if host_system != "":
            host_system = self.get_obj([vim.HostSystem],
                                       self.config['host']
                                       )

        if self.debug:
            self.print_debug(
                "Destination cluster",
                cluster
            )
            self.print_debug(
                "Resource pool",
                resource_pool
            )

        if resource_pool is None:
            # use default resource pool of target cluster
            resource_pool = cluster.resourcePool

        datastore = None
        if 'datastore' in ip_settings[0]:
            datastore = self.get_obj(
                [vim.Datastore],
                ip_settings[0]['datastore'])
            if datastore is None:
                print "Error: Unable to find Datastore '%s'" \
                    % ip_settings[0]['datastore']
                sys.exit(1)

        template_vm = self.get_vm_failfast(
            self.config['template'],
            False,
            'Template VM'
            )

        # Relocation spec
        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        if host_system:
            relospec.host = host_system

        if resource_pool:
            relospec.pool = resource_pool

        # Networking self.config for VM and guest OS
        devices = []
        adaptermaps = []

        # add existing NIC devices from template to our list of NICs
        # to be created
        try:
            for device in template_vm.config.hardware.device:

                if hasattr(device, 'addressType'):
                    # this is a VirtualEthernetCard, so we'll delete it
                    nic = vim.vm.device.VirtualDeviceSpec()
                    nic.operation = \
                        vim.vm.device.VirtualDeviceSpec.Operation.remove
                    nic.device = device
                    devices.append(nic)
        except:
            # not the most graceful handling, but unable to reproduce
            # user's issues in #57 at this time.
            pass

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
            nic.device.deviceInfo.label = 'Network Adapter %s' % (key + 1)
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

            # these may not be set for certain IPs
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

        if self.debug:
            self.print_debug("CloneSpec", clonespec)

        # fire the clone task
        tasks = [template_vm.Clone(folder=destfolder,
                                   name=self.config['hostname'],
                                   spec=clonespec
                                   )]
        result = self.WaitForTasks(tasks)

        if self.config['post_clone_cmd']:
            try:
                # helper env variables
                os.environ['EZMOMI_CLONE_HOSTNAME'] = self.config['hostname']
                print "Running --post-clone-cmd %s" % \
                    self.config['post_clone_cmd']
                os.system(self.config['post_clone_cmd'])

            except Exception as e:
                print "Error running post-clone command. Exception: %s" % e
                pass

        # send notification email
        if self.config['mail']:
            self.send_email()

    def destroy(self):
        tasks = list()

        destroyed = 'no'

        if self.config['silent']:
            destroyed = 'yes'
        else:
            destroyed = raw_input(
                "Do you really want to destroy %s ? [yes/no] "
                % self.config['name'])

        if destroyed == 'yes':
            vm = self.get_vm_failfast(self.config['name'], True)
            # need to shut the VM down before destroying it
            if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                tasks.append(vm.PowerOff())

            tasks.append(vm.Destroy())
            print "Destroying %s..." % self.config['name']
            result = self.WaitForTasks(tasks)

    def status(self):
        """Check power status"""
        vm = self.get_vm_failfast(self.config['name'])
        self.tabulate([[vm.name, vm.runtime.powerState]])

    def shutdown(self):
        """
        Shutdown guest
        fallback to power off if guest tools aren't installed
        """
        vm = self.get_vm_failfast(self.config['name'])

        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
            print "%s already poweredOff" % vm.name
        else:
            if self.guestToolsRunning(vm):
                timeout_minutes = 10
                print "waiting for %s to shutdown " \
                      "(%s minutes before forced powerOff)" % (
                          vm.name,
                          str(timeout_minutes)
                          )
                vm.ShutdownGuest()
                if self.WaitForVirtualMachineShutdown(vm, timeout_minutes*60):
                    print "shutdown complete"
                    print "%s poweredOff" % vm.name
                else:
                    print "%s has not shutdown after %s minutes:" \
                          "will powerOff" % (vm.name, str(timeout_minutes))
                    self.powerOff()

            else:
                print "GuestTools not running or not installed: will powerOff"
                self.powerOff()

    def createSnapshot(self):
        tasks = []

        vm = self.get_vm_failfast(self.config['vm'])
        tasks.append(vm.CreateSnapshot(self.config['name'],
                                       memory=self.config['memory'],
                                       quiesce=self.config['quiesce']))
        result = self.WaitForTasks(tasks)
        print "Created snapshot for %s" % vm.name

    def get_all_snapshots(self, vm_name):
        vm = self.get_vm_failfast(vm_name)

        try:
            vm_snapshot_info = vm.snapshot
        except IndexError:
            return

        return vm_snapshot_info.rootSnapshotList

    def get_snapshot_by_name(self, vm, name):
        return next(snapshot.snapshot for snapshot in
                    self.get_all_snapshots(vm) if
                    snapshot.name == name)

    def tabulate(self, data):
        column_widths = []

        for row in data:
            for column in range(0, len(row)):
                column_len = len(row[column])
                try:
                    column_widths[column] = max(column_len,
                                                column_widths[column])
                except IndexError:
                    column_widths.append(column_len)

        for column in range(0, len(column_widths)):
            column_widths[column] += self._column_spacing - 1

        format = "{0:<%d}" % column_widths[0]
        for width in range(1, len(column_widths)):
            format += " {%d:<%d}" % (width, column_widths[width])

        for row in data:
            print format.format(*row)

    def listSnapshots(self):
        root_snapshot_list = self.get_all_snapshots(self.config['vm'])

        if root_snapshot_list:
            snapshots = []
            for snapshot in root_snapshot_list:
                snapshots.append([str(snapshot.vm), snapshot.name,
                                  str(snapshot.createTime)])

            data = [['VM', 'Snapshot', 'Create Time']] + snapshots
            self.tabulate(data)
        else:
            print "No snapshots for %s" % self.config['vm']

    def removeSnapshot(self):
        tasks = []

        snapshot = self.get_snapshot_by_name(self.config['vm'],
                                             self.config['name'])
        tasks.append(snapshot.Remove(self.config['remove_children'],
                                     self.config['consolidate']))
        result = self.WaitForTasks(tasks)
        print("Removed snapshot %s for virtual machine %s" %
              (self.config['name'], self.config['vm']))

    def revertSnapshot(self):
        tasks = []

        snapshot = self.get_snapshot_by_name(self.config['vm'],
                                             self.config['name'])
        host_system = self.get_host_system_failfast(self.config['host'])
        tasks.append(
            snapshot.Revert(host=host_system,
                            suppressPowerOn=self.config['suppress_power_on'])
            )
        result = self.WaitForTasks(tasks)
        print("Reverted snapshot %s for virtual machine %s" %
              (self.config['name'], self.config['vm']))

    def powerOff(self):
        vm = self.get_vm_failfast(self.config['name'])

        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
            print "%s already poweredOff" % vm.name
        else:
            tasks = list()
            tasks.append(vm.PowerOff())
            result = self.WaitForTasks(tasks)
            print "%s poweredOff" % vm.name

    def powerOn(self):
        vm = self.get_vm_failfast(self.config['name'])

        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            print "%s already poweredOn" % vm.name
        else:
            tasks = list()
            tasks.append(vm.PowerOn())
            result = self.WaitForTasks(tasks)
            print "%s poweredOn" % vm.name

    '''
     Helper methods
    '''
    def send_email(self):
        import smtplib
        from email.mime.text import MIMEText

        if 'mailfrom' in self.config:
            mailfrom = self.config['mailfrom']
        else:
            mailfrom = os.getenv('USER')  # user who ran this script

        if 'mailto' in self.config:
            mailto = self.config['mailto']
        else:
            mailto = os.getenv('USER')

        if 'mailserver' in self.config:
            mailserver = self.config['mailserver']
        else:
            mailserver = 'localhost'

        email_body = 'Your VM is ready!'
        msg = MIMEText(email_body)
        msg['Subject'] = '%s - VM deploy complete' % self.config['hostname']
        msg['To'] = mailto
        msg['From'] = mailfrom

        s = smtplib.SMTP(mailserver)
        s.sendmail(mailfrom, [mailto], msg.as_string())
        s.quit()

    def get_resource_pool(self, cluster, pool_name):
        """
        Find a resource pool given a pool name for desired cluster
        """
        pool_obj = None

        # get a list of all resource pools in this cluster
        cluster_pools_list = cluster.resourcePool.resourcePool

        # get list of all resource pools with a given text name
        pool_selections = self.get_obj(
            [vim.ResourcePool],
            pool_name,
            return_all=True
            )

        # get the first pool that exists in a given cluster
        if pool_selections:
            for p in pool_selections:
                if p in cluster_pools_list:
                    pool_obj = p
                    break

        return pool_obj

    def get_obj(self, vimtype, name, return_all=False):
        """Get the vsphere object associated with a given text name or MOID"""
        obj = list()
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vimtype, True)

        for c in container.view:
            if name in [c.name, c._GetMoId()]:
                if return_all is False:
                    return c
                    break
                else:
                    obj.append(c)

        if len(obj) > 0:
            return obj
        else:
            # for backwards-compat
            return None

    def get_host_system(self, name):
        return self.get_obj([vim.HostSystem], name)

    def get_host_system_failfast(
            self,
            name,
            verbose=False,
            host_system_term='HS'
            ):
        """
        Get a HostSystem object
        fail fast if the object isn't a valid reference
        """
        if verbose:
            print "Finding HostSystem named %s..." % name

        hs = self.get_host_system(name)

        if hs is None:
            print "Error: %s '%s' does not exist" % (host_system_term, name)
            sys.exit(1)

        if verbose:
            print "Found HostSystem: {0} Name: {1}" % (hs, hs.name)

        return hs

    def get_vm(self, name):
        """Get a VirtualMachine object"""
        return self.get_obj([vim.VirtualMachine], name)

    def get_vm_failfast(self, name, verbose=False, vm_term='VM'):
        """
        Get a VirtualMachine object
        fail fast if the object isn't a valid reference
        """
        if verbose:
            print "Finding VirtualMachine named %s..." % name

        vm = self.get_vm(name)

        if vm is None:
            print "Error: %s '%s' does not exist" % (vm_term, name)
            sys.exit(1)

        if verbose:
            print "Found VirtualMachine: %s Name: %s" % (vm, vm.name)

        return vm

    def guestToolsRunning(self, vm):
        """simple helper to avoid potential typos on the string comparison"""
        return 'guestToolsRunning' == vm.guest.toolsRunningStatus

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

    def WaitForVirtualMachineShutdown(
            self,
            vm_to_poll,
            timeout_seconds,
            sleep_period=5
            ):
        """
        Guest shutdown requests do not run a task we can wait for.
        So, we must poll and wait for status to be poweredOff.

        Returns True if shutdown, False if poll expired.
        """
        seconds_waited = 0  # wait counter
        while seconds_waited < timeout_seconds:
            # sleep first, since nothing shuts down instantly
            seconds_waited += sleep_period
            time.sleep(sleep_period)

            vm = self.get_vm(vm_to_poll.name)
            if vm.runtime.powerState == \
                    vim.VirtualMachinePowerState.poweredOff:
                return True

        return False
