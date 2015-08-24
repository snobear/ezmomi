#!/usr/bin/env python

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from netaddr import IPNetwork, IPAddress
import atexit
import logging
import os
import sys
import time
import yaml


class EZMomi(object):
    def __init__(self, **kwargs):
        """
        Load the configuration and connect to the vSphere server
        """

        self.si = None
        self.content = None
        self.config = self.get_config(kwargs)
        self._minimum_column_spacing = 4
        levels = {0: logging.NOTSET, 1: logging.CRITICAL, 2: logging.ERROR,
                  3: logging.WARNING, 4: logging.INFO, 5: logging.DEBUG}
        logging.basicConfig(format='[%(levelname)s] %(name)s: %(message)s',
                            level=levels[self.config['verbose']])
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(levels[self.config['verbose']])
        if self.config['verbose'] == 0:
            logging.disable(logging.CRITICAL)

    def get_config(self, kwargs):
        """
        Get the YAML file and CLI specified configuration. CLI
        arguments override any existing definitions.

        :param kwargs: A dictionary of keyword arguments from the YAML file and
            CLI
        :return config: Dictionary of parsed config values
        """

        default_cfg_dir = "%s/.config/ezmomi" % os.path.expanduser("~")
        default_config_file = "%s/config.yml" % default_cfg_dir

        # use path from env var if it's set and valid
        if os.environ.get('EZMOMI_CONFIG'):
            if os.path.isfile(os.environ['EZMOMI_CONFIG']):
                config_file = os.environ['EZMOMI_CONFIG']
            else:
                self._logger.warning("%s does not exist. Set the EZMOMI_CONFIG"
                                     " environment variable to your config"
                                     " file's path." %
                                     os.environ.get('EZMOMI_CONFIG'))
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
                self._logger.debug("Error copying example config file from %s"
                                   "to %s" % (ezmomi_ex_config,
                                              default_cfg_dir))
                sys.exit(1)

            self._logger.info("Could not find config.yml, copied an example to"
                              " %s/config.yml.example. Please rename this to"
                              " config.yml and configure." % default_cfg_dir)
            sys.exit(0)
        try:
            config = yaml.load(file(config_file))
        except IOError:
            self._logger.warning("Unable to open config file. The default path"
                                 " for the ezmomi config file is"
                                 " ~/.config/ezmomi/config.yml. You can also "
                                 " specify the config file path by setting the"
                                 " EZMOMI_CONFIG environment variable.")
            sys.exit(1)
        except Exception:
            self._logger.warning("Unable to read config file. YAML syntax"
                                 " issue, perhaps?")
            sys.exit(1)

        # Check all required values were supplied either via command line
        # or config. override defaults from config.yml with any supplied
        # command line arguments
        for key, value in kwargs.items():
            if value is not None:
                config[key] = value

        return config

    def connect(self, server, username, password, port):
        """
        Connect to a vCenter server
        """

        try:
            self.si = SmartConnect(host=server, user=username,
                                   pwd=password, port=port)
        except Exception as e:
            self._logger.warning("Unable to connect to vSphere server.")
            sys.exit(1)

        # add a clean up routine
        atexit.register(Disconnect, self.si)

        self.content = self.si.RetrieveContent()

    def list_objects(self, vimtype):
        """
        List available vSphere objects

        :param vimtype: Type of vSphere vim object
        :return: List of list of vSphere vim objects
        """

        vim_obj = "vim.%s" % vimtype

        try:
            container = self.content.viewManager.CreateContainerView(
                self.content.rootFolder, [eval(vim_obj)], True)
        except AttributeError:
            self._logger.warning("%s is not a Managed Object Type. See the"
                                 " vSphere API docs for possible options." %
                                 vimtype)
            sys.exit(1)

        rows = []
        for c in container.view:
            if vimtype == "VirtualMachine":
                rows.append([c._moId, c.name, c.runtime.powerState])
            else:
                rows.append([c._moId, c.name])

        return rows

    def _get_network_settings(self, ips, networks):
        ip_settings = []

        for _, ip_string in enumerate(ips):
            # convert ip from string to the 'IPAddress' type
            ip = IPAddress(ip_string)

            # determine network this IP is in
            for network in networks:
                if ip in IPNetwork(network):
                    networks[network]['ip'] = ip
                    ipnet = IPNetwork(network)
                    networks[network]['subnet_mask'] = str(
                        ipnet.netmask
                    )
                    ip_settings.append(networks[network])

            # throw an error if we couldn't find a network for this ip
            if not any(d['ip'] == ip for d in ip_settings):
                self._logger.error("I don't know what network %s is"
                                   " in. You can supply settings"
                                   " for this network in config.yml."
                                   % ip_string)
                sys.exit(1)

        return ip_settings

    def _build_relospec(self, datastore, resource_pool):
        """
        Relocation spec
        """

        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = resource_pool

        return relospec

    def _build_vm_config_spec(self, cpus, memory, devices):
        """
        VM config spec
        """

        vmconf = vim.vm.ConfigSpec()
        vmconf.numCPUs = cpus
        vmconf.memoryMB = memory
        vmconf.cpuHotAddEnabled = True
        vmconf.memoryHotAddEnabled = True
        vmconf.deviceChange = devices

        return vmconf

    def _build_global_ip_settings(self, domain):
        """
        DNS settings
        """

        globalip = vim.vm.customization.GlobalIPSettings()
        globalip.dnsServerList = self.config['dns_servers']
        globalip.dnsSuffixList = domain

        return globalip

    def _build_customspec(self, adaptermaps, globalip, ident):
        customspec = vim.vm.customization.Specification()
        customspec.nicSettingMap = adaptermaps
        customspec.globalIPSettings = globalip
        customspec.identity = ident

        return customspec

    def _build_hostname_settings(self, domain, hostname):
        """
        Hostname settings
        """

        ident = vim.vm.customization.LinuxPrep()
        ident.domain = domain
        ident.hostName = vim.vm.customization.FixedName()
        ident.hostName.name = hostname

        return ident

    def _build_spec(self, relospec, vmconf, customspec, to_template):
        """
        The final spec for the clone operation
        """

        spec = vim.vm.CloneSpec()
        spec.location = relospec
        spec.config = vmconf
        spec.customization = customspec
        spec.powerOn = True
        spec.template = to_template

        return spec

    def _build_nic(self, ip_settings, key):
        # VM device
        nic = vim.vm.device.VirtualDeviceSpec()
        # or edit if a device exists
        nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        nic.device = vim.vm.device.VirtualVmxnet3()
        nic.device.wakeOnLanEnabled = True
        nic.device.addressType = 'assigned'
        nic.device.key = 4000  # Seems correct for a vmxnet3 device
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

        return nic

    def _build_guest_map(self, ip_settings, key, domain):
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
            guest_map.adapter.dnsDomain = domain
        except:
            pass

        return guest_map

    def create_network_devices_for_ips(self, ip_settings, domain):
        devices = []
        adaptermaps = []

        for key, _ in enumerate(ip_settings):
            devices.append(_build_nic(ip_settings, key))
            adaptermaps.append(self._build_guest_map(ip_settings,
                                                     key, domain))

            return devices, adaptermaps

    def clone(self, ips, template_name, domain, hostname,
              cpus, memory, to_template, networks=None):
        """
        Clone a virtual machine template to a new virtual machine or
        template
        """

        # Get network settings for each IP
        ip_settings = self._get_network_settings(ips, networks)

        # Network to place new VM in
        self.get_obj([vim.Network], ip_settings[0]['network'])
        datacenter = self.get_obj([vim.Datacenter],
                                  ip_settings[0]['datacenter'])

        cluster = self.get_obj([vim.ClusterComputeResource],
                               ip_settings[0]['cluster'])
        datastore = self.get_obj([vim.Datastore], ip_settings[0]['datastore'])
        template_vm = self.get_vm_failfast(template_name, 'Template VM')

        devices = []

        # Don't clone nic devices from template
        for device in template_vm.config.hardware.device:
            if hasattr(device, 'addressType'):
                # this is a VirtualEthernetCard, so we'll delete it,
                nic = vim.vm.device.VirtualDeviceSpec()
                nic.operation = \
                    vim.vm.device.VirtualDeviceSpec.Operation.remove
                nic.device = device
                devices.append(nic)

        # Create a Network device for each static IP
        network_devices = self.create_network_devices_for_ips(ip_settings,
                                                              domain)
        devices += network_devices[0]
        adaptermaps = network_devices[1]

        relospec = self._build_relospec(self, datastore,
                                        cluster.resourcePool)
        vmconf = self._build_vm_config_spec(cpus, memory, devices)
        globalip = self._build_global_ip_settings(domain)
        ident = self._build_hostname_settings(domain, hostname)
        customspec = self._build_customspec(adaptermaps, globalip,
                                            ident)
        spec = self._build_spec(relospec, vmconf, customspec,
                                to_template)

        return self.WaitForTasks([template_vm.Clone(folder=datacenter.vmFolder,
                                                    name=hostname,
                                                    spec=spec)])

    def destroy(self, vm_name):
        """
        Destroy a virtual machine
        """

        vm = self.get_vm_failfast(vm_name)

        # Need to shutdown the VM before destroying it
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            self.WaitForTasks([vm.PowerOff()])

        return self.WaitForTasks([vm.Destroy()])

    def status(self, vm_name):
        """
        Print the power status of a virtual machine
        """

        vm = self.get_vm_failfast(vm_name)

        return [vm.name, vm.runtime.powerState]

    def shutdown(self, vm_name):
        """
        Shutdown a virtual machine with fallback to power off if guest tools
        aren't installed
        """

        vm = self.get_vm_failfast(vm_name)

        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
            self._logger.info("%s already poweredOff" % vm.name)
        else:
            if guest_tools_running(vm):
                timeout_minutes = 10
                self._logger.debug("Waiting for %s to shutdown (%d minutes"
                                   " before forced powerOff)" %
                                   (vm.name, timeout_minutes))
                vm.ShutdownGuest()
                if self.WaitForVirtualMachineShutdown(vm, timeout_minutes*60):
                    self._logger.info("Shutdown complete")
                    self._logger.info("%s poweredOff" % vm.name)
                else:
                    self._logger.debug("%s has not shutdown after %d minutes."
                                       " Will powerOff" % (vm.name,
                                                           timeout_minutes))
                    self.power_off()
            else:
                self._logger.info("GuestTools not running or not installed."
                                  " Will powerOff")
                self.power_off()

    def create_snapshot(self, vm_name, name, memory=False,
                       quiesce=True):
        """
        Create a snapshot for a virtual machine
        """

        vm = self.get_vm_failfast(vm_name)

        return self.WaitForTasks([vm.CreateSnapshot(name, memory,
                                                    quiesce)])

    def get_all_snapshots(self, vm_name):
        """
        Get all snapshots for a virtual machine

        :param vm_name: The name of the virtual machine
        :returns: List of virtual machine snapshots
        """

        vm = self.get_vm_failfast(vm_name)

        try:
            vm_snapshot_info = vm.snapshot
            if vm_snapshot_info is not None:
                return vm_snapshot_info.rootSnapshotList
        except IndexError:
            return

        return

    def get_snapshot_by_name(self, vm, name):
        """
        Get a virtual machine snapshot by name

        :param vm: VirtualMachine object containing the named snapshot
        :param name: Name of the snapshot
        """

        return next(snapshot.snapshot for snapshot in
                    self.get_all_snapshots(vm) if
                    snapshot.name == name)

    def tabulate(self, data):
        """
        Prints tabulated input data specified by a list of lists

        :param data: A list of lists to tabulate
        """

        column_widths = []

        for row in data:
            for key, column in enumerate(row):
                column_len = len(column)
                try:
                    column_widths[key] = max(column_len,
                                             column_widths[key])
                except IndexError:
                    column_widths.append(column_len)

        for width, _ in enumerate(column_widths):
            column_widths[width] += self._minimum_column_spacing - 1

        format = "{0:<%d}" % column_widths[0]
        for width in range(1, len(column_widths)):
            format += " {%d:<%d}" % (width, column_widths[width])

        for row in data:
            print format.format(*row)

    def list_snapshots(self, vm_name):
        """
        List all snapshots for a virtual machine
        """

        snapshots = []
        root_snapshot_list = self.get_all_snapshots(vm_name)

        if root_snapshot_list:
            for snapshot in root_snapshot_list:
                snapshots.append([str(snapshot.vm), snapshot.name,
                                  str(snapshot.createTime)])

        return snapshots

    def remove_snapshot(self, vm_name, name, remove_children=False,
                       consolidate=True):
        """
        Remove snapshot for a virtual machine
        """

        snapshot = self.get_snapshot_by_name(vm_name,
                                             name)
        return self.WaitForTasks([snapshot.Remove(remove_children,
                                                  consolidate)])

    def revert_snapshot(self, vm_name, name, host=None,
                       suppress_power_on=False):
        """
        Revert a virtual machine to the specified snapshot
        """

        snapshot = self.get_snapshot_by_name(vm_name, name)
        if host:
            host_system = self.get_host_system_failfast(host)
            return self.WaitForTasks([snapshot.Revert(
                host=host_system,
                suppressPowerOn=suppress_power_on)])
        else:
            return self.WaitForTasks([
                snapshot.Revert(suppressPowerOn=suppress_power_on)])

    def power_off(self, vm_name):
        """
        Power off a virtual machine

        :return True: The virtual machine was powered off or is already powered
            off
        :return False: The virtual machine was not able to be powered off
        """

        vm = self.get_vm_failfast(vm_name)

        try:
            if (vm.runtime.powerState !=
                    vim.VirtualMachinePowerState.poweredOff):
                self.WaitForTasks([vm.PowerOff()])
            return True
        except Exception:
            return False

    def power_on(self, vm_name):
        """
        Power on a virtual machine

        :return True: The virtual machine was powered on or is already powered
            on
        :return False: The virtual machine was not able to be powered on
        """

        vm = self.get_vm_failfast(vm_name)

        try:
            if vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:
                self.WaitForTasks([vm.PowerOn()])
            return True
        except Exception:
            return False

    def send_mail(self, mailfrom, mailto, mailserver, subject, body):
        """
        Send a mail

        :param mailfrom: Address to send mail from
        :param mailto: Address to send mail to
        :param mailserver: SMTP mail server
        :param subject: Subject of the mail
        :param body: Body of the mail
        """

        import smtplib
        from email.mime.text import MIMEText

        mailfrom = mailfrom or os.getenv('USER')
        mailto = mailto or os.getenv('USER')
        mailserver = mailserver or 'localhost'

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['To'] = mailto
        msg['From'] = mailfrom

        s = smtplib.SMTP(mailserver)
        s.sendmail(mailfrom, [mailto], msg.as_string())
        s.quit()

    def get_obj(self, vimtype, name):
        """
        Get the vSphere object associated with a given name

        :param vimtype: Vim type object
        :param name: Name of the Vim type object
        :returns: vSphere object
        """

        obj = None
        container = self.content.viewManager.CreateContainerView(
            self.content.rootFolder, vimtype, True)
        for c in container.view:
            if c.name == name:
                obj = c
                break
        return obj

    def get_host_system(self, name):
        """
        Get a HostSystem object

        :param name: Name of the HostSystem
        :returns: HostSystem object
        """

        return self.get_obj([vim.HostSystem], name)

    def get_host_system_failfast(self, name):
        """
        Get a HostSystem object and fail fast if the object isn't a valid
        reference
        """

        hs = self.get_host_system(name)

        if None == hs:
            self._logger.debug("Error: HS '%s' does not exist" % (name))
            sys.exit(1)

        return hs

    def get_vm(self, name):
        """
        Get a VirtualMachine object

        :param name: Name of the virtual machine
        """

        return self.get_obj([vim.VirtualMachine], name)

    def get_vm_failfast(self, name, vm_term='VM'):
        """
        Get a VirtualMachine object and fail fast if the object
        isn't a valid reference

        :param name: Name of the virtual machine
        :param vm_term:
        """

        vm = self.get_vm(name)

        if None == vm:
            self._logger.debug("Error: %s '%s' does not exist" % (vm_term,
                                                                  name))
            sys.exit(1)

        return vm

    def WaitForTasks(self, tasks):
        """
        Wait for all tasks to finish before continuing

        :param tasks: List of tasks to wait for
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

    def WaitForVirtualMachineShutdown(self, vm, timeout, sleep_period=5):
        """
        Guest shutdown requests do not run a task we can wait for.
        So, we must poll and wait for status to be poweredOff.

        :param vm: Name of the virtual machine
        :param timeout: Timeout in seconds before the poll ends
        :param sleep_period: Period in seconds to sleep between each poll
        :return True: If shutdown
        :return False: If timeout expired and (probably) not shutdown
        """

        seconds_waited = 0

        while seconds_waited < timeout:
            seconds_waited += sleep_period
            time.sleep(sleep_period)

            vm = self.get_vm(vm.name)
            if (vm.runtime.powerState ==
                    vim.VirtualMachinePowerState.poweredOff):
                return True

        return False

def guest_tools_running(vm):
    """
    Test if guest tools are running for a VM. Helper to avoid
    potential typos on the string comparison

    :param vm: VirtualMachine object
    :return True: If guest tools are running
    :return False: If guest tools are not running
    """

    return 'guestToolsRunning' == vm.guest.toolsRunningStatus


