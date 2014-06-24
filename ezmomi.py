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
from params import *

'''
Logging
'''
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


class EZMomi(object):
    def __init__(self, **kwargs):
        self.config = self.get_configs(kwargs)
        self.connect()
        self.list_objects(kwargs['type'])

    def get_configs(self, kwargs):
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
            logging.error("Required parameters not set: %s\n" % notset)
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
            logging.exception('Unable to connect to vsphere server.')
            sys.exit()

        # add a clean up routine
        atexit.register(Disconnect, si)

        self.content = si.RetrieveContent()

    '''
     Command Section: list
     List available VMware objects
    '''
    def list_objects(self, vimtype):
        vim_obj = "vim.%s" % vimtype
        
        try:
            container = self.content.viewManager.CreateContainerView(self.content.rootFolder, [eval(vim_obj)], True)
        except AttributeError:

        # print header line
        print "%s list" % vimtype
        print "{0:<20} {1:<20}".format('MOID','Name')

        for c in container.view:
            print "{0:<20} {1:<20}".format(c._moId, c.name)


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
 Main program
'''
if __name__ == '__main__':
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Perform common vSphere API tasks')
    subparsers = parser.add_subparsers(help='Section e.g. list, deploy', dest='mode')

    # set up parser for each command section
    add_params_for_list(subparsers)

    args = parser.parse_args()

    # initialize ezmomi instance with supplied arguments
    em = EZMomi(**vars(args))

