'''
 Command line definitions for ezmomi
'''
import argparse
from params import add_params
from ezmomi import EZMomi


# DEV
import sys
from pprint import pprint
#ENDDEV

def cli():
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description='Perform common vSphere API tasks'
    )
    subparsers = parser.add_subparsers(help='Command', dest='mode')

    # set up each command section
    add_params(subparsers)

    # parse arguments
    args = parser.parse_args()
    
    # required arguments
    
    pprint(args)
    notset = list()

    if not args.hostname:
        parser.error('hostname not set')
    
    sys.exit()
    # initialize ezmomi instance
    ez = EZMomi(**vars(args))

    kwargs = vars(args)

    # choose your adventure
    if kwargs['mode'] == 'list':
        ez.list_objects()
    elif kwargs['mode'] == 'clone':
        ez.clone()
    elif kwargs['mode'] == 'destroy':
        ez.destroy()
