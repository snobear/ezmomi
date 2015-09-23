'''
 Command line definitions for ezmomi
'''
import argparse
from params import add_params
from ezmomi import EZMomi

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
    elif kwargs['mode'] == 'listSnapshots':
        ez.listSnapshots()
    elif kwargs['mode'] == 'createSnapshot':
        ez.createSnapshot()
    elif kwargs['mode'] == 'removeSnapshot':
        ez.removeSnapshot()
    elif kwargs['mode'] == 'revertSnapshot':
        ez.revertSnapshot()
    elif kwargs['mode'] == 'status':
        ez.status()
    elif kwargs['mode'] == 'shutdown':
        ez.shutdown()
    elif kwargs['mode'] == 'powerOff':
        ez.powerOff()
    elif kwargs['mode'] == 'powerOn':
        ez.powerOn()
