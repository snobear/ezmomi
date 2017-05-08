[![Build Status](https://travis-ci.org/snobear/ezmomi.svg?branch=master)](https://travis-ci.org/snobear/ezmomi)
ezmomi
======

A simple Linux command line interface for common VMware vSphere VM tasks.

EZmomi uses [pyvmomi](https://github.com/vmware/pyvmomi) (VMware vSphere API Python Bindings).


### Requirements

```
vSphere 6
Python 2.7
```

(If you are using vSphere 5, install the older ezmomi 0.x:  `pip install ezmomi==0.4.2`)

### Install

```
pip install ezmomi
```

### Example Usage

##### Clone a template with two static IPs:

```
ezmomi clone --template centos67 --hostname test01 --cpus 2 --mem 4 --ips 172.10.16.203 172.10.16.204
```

`ips` takes any number of ips.  See `ezmomi clone --help` for a list of params.

To optionally run a command/script after clone has started:

```
ezmomi clone --template centos6 --hostname test01 --cpus 2 --mem 4 --ips 172.10.16.203 172.10.16.204 --post-clone-cmd /usr/local/bin/additional-provisioning-steps.sh
```

This example would run /usr/local/bin/additional-provisioning-steps.sh on the same host ezmomi is run on. You can reference the `EZMOMI_CLONE_HOSTNAME` environment variable in your script to retrieve the `--hostname`.

##### Power Operations 

Guest shutdown

```
ezmomi shutdown --name test01
```

This command falls back to powerOff if VMware guest tools are not installed/available.

Power On/Off

```
ezmomi powerOn --name test01
ezmomi powerOff --name test01
```

##### Power Status

```
ezmomi status --name test01
# for much more information add --extra:
ezmomi status --name test01 --extra
```

##### Destroy a VM

```
ezmomi destroy --name test01
```

##### VM Snapshot operations

See help for more info on each operation:

```
ezmomi listSnapshots --help
ezmomi createSnapshot --help
ezmomi removeSnapshot --help
ezmomi revertSnapshot --help
```

##### Listing your resources:

```
ezmomi list --type VirtualMachine
ezmomi list --type Network
ezmomi list --type Datastore
etc...
```

##### Sync a VM's time with ESXi host

```
ezmomi syncTimeWithHost --name somevm01
```

See [Managed Object Types](http://pubs.vmware.com/vsphere-60/topic/com.vmware.wssdk.apiref.doc/mo-types-landing.html) in the vSphere API docs for a list of types to look up.

### Help

Each command section has its own help:

```
ezmomi --help
ezmomi clone --help
ezmomi list --help
etc...
```

### Install via github

```
git clone https://github.com/snobear/ezmomi.git
# using python2.7 virtualenv
virtualenv -p python2.7 --no-site-packages ezmomi
cd ezmomi && source bin/activate
pip install -r requirements.txt
export PYTHONPATH=$PWD:$PYTHONPATH
ezmomi --help
```

### Contributing
Pull requests, bug reports, and feature requests are extremely welcome.
