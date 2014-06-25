ezmomi
======

A simple command line interface for common VMware vSphere tasks.

EZmomi uses [pyvmomi](https://github.com/vmware/pyvmomi) (VMware vSphere API Python Bindings).


#### Example Usage


Clone a template with two static IPs:

```
./ezmomi.py clone --hostname foo01 --cpus 2 --mem 4 --ips 172.10.16.203 172.10.16.204
```

`ips` takes any number of ips.

Get info about available resources, e.g.:

```
./ezmomi.py list --type Network
./ezmomi.py list --type Datastore
./ezmomi.py list --type VirtualMachine
```

See [Managed Object Types](http://pubs.vmware.com/vsphere-50/index.jsp#com.vmware.wssdk.apiref.doc_50/mo-types-landing.html) in the vSphere API docs for a list of types to look up.

#### Help

Each command section has its own help:

```
./ezmomi.py --help
./ezmomi.py clone --help
./ezmomi.py list --help
```

#### Install/Setup

I'm working on making this available via pip, but currently you can just clone via github:

```
git clone git@github.com:snobear/ezmomi.git
virtualenv --no-site-packages ezmomi
cd ezmomi && source bin/activate
pip install -r requirements.txt
mv config.yml.example config.yml
```

Then define your credentials, networks, and VMware objects in config.yml and you're all set.

#### Contributing
Pull requests, bug reports, and feature requests are extremely welcome.
