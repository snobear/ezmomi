ezmomi
======

A simple command line interface for common VMware tasks such as:

* deploying VMs from a template
* ...more to come!


EZmomi uses pyvmomi and 
 

Example Usage
=============

Deploy a new VM with two static IPs:


```
./ezmomi.py --hostname foo01 --cpus 2 --mem 4 --ips 172.10.16.203 172.10.16.204
```

Install/Setup
=============
```
git clone git@github.com:snobear/ezmomi.git
virtualenv ezmomi
cd ezmomi
mv config.yml.example config.yml
```

Then define your networks and VMware objects in config.yml and you're all set.

Contributing
============
Don't hesitate to file any bugs or feature requests, and of course pull requests are more than welcome.  I'm also interested in packaging this up and adding to pypi if anyone wants to tackle that.




