ezmomi
======

A simple command line interface for common VMware vSphere tasks such as:

* deploying VMs from a template
* ...more to come!


EZmomi uses [pyvmomi](https://github.com/vmware/pyvmomi) (VMware vSphere API Python Bindings).
 

#### Example Usage


Deploy a new VM with two static IPs:


```
./ezmomi.py --hostname foo01 --cpus 2 --mem 4 --ips 172.10.16.203 172.10.16.204
```

`ips` takes any number of ips.

#### Install/Setup

Right now it requires setting up the virtualenv, but eventually it'll be a python module on pypi that you can install via pip.

```
git clone git@github.com:snobear/ezmomi.git
virtualenv ezmomi
cd ezmomi
pip install -r requirements.txt
mv config.yml.example config.yml
```

Then define your networks and VMware objects in config.yml and you're all set.

#### Contributing
Don't hesitate to file any bugs or feature requests, and of course pull requests are more than welcome.



