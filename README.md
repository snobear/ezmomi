ezmomi
======

A simple command line interface for common VMware vSphere tasks.

EZmomi uses [pyvmomi](https://github.com/vmware/pyvmomi) (VMware vSphere API Python Bindings).


### Install

```
pip install ezmomi
```

### Example Usage

##### Clone a template with two static IPs:

```
ezmomi clone --template centos65 --hostname test01 --cpus 2 --mem 4 --ips 172.10.16.203 172.10.16.204
```

`ips` takes any number of ips.  See `ezmomi clone --help` for a list of params.

##### Destroy a VM

```
ezmomi destroy --name test01
```

##### Listing your resources:

```
ezmomi list --type VirtualMachine
ezmomi list --type Network
ezmomi list --type Datastore
etc...
```

See [Managed Object Types](http://pubs.vmware.com/vsphere-50/index.jsp#com.vmware.wssdk.apiref.doc_50/mo-types-landing.html) in the vSphere API docs for a list of types to look up.

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
git clone git@github.com:snobear/ezmomi.git
virtualenv --no-site-packages ezmomi
cd ezmomi && source bin/activate
pip install -r requirements.txt
```

### Contributing
Pull requests, bug reports, and feature requests are extremely welcome.
