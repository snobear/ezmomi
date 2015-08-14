"""
Command line definitions for ezmomi
"""

import argparse
from params import add_params, add_subparser_params
from ezmomi import EZMomi


def cli():
    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description='Perform common vSphere API tasks'
    )

    add_params(parser)

    subparsers = parser.add_subparsers(help='Command', dest='mode')

    # Set up each command section
    add_subparser_params(subparsers)

    # Parse arguments
    args = parser.parse_args()

    # Initialize ezmomi instance
    ezmomi = EZMomi(**vars(args))

    ezmomi.connect(ezmomi.config['server'], ezmomi.config['username'],
                   ezmomi.config['password'], ezmomi.config['port'])

    kwargs = vars(args)

    if kwargs['mode'] == 'list':
        list_objects(ezmomi)
    elif kwargs['mode'] == 'clone':
        clone(ezmomi)
    elif kwargs['mode'] == 'destroy':
        destroy(ezmomi)
    elif kwargs['mode'] == 'list-snapshots':
        list_snapshots(ezmomi)
    elif kwargs['mode'] == 'create-snapshot':
        create_snapshot(ezmomi)
    elif kwargs['mode'] == 'remove-snapshot':
        remove_snapshot(ezmomi)
    elif kwargs['mode'] == 'revert-snapshot':
        revert_snapshot(ezmomi)
    elif kwargs['mode'] == 'status':
        status(ezmomi)
    elif kwargs['mode'] == 'shutdown':
        shutdown(ezmomi)
    elif kwargs['mode'] == 'power-off':
        power_off(ezmomi)
    elif kwargs['mode'] == 'power-on':
        power_on(ezmomi)


def list_objects(ezmomi):
    vimtype = ezmomi.config['type']
    print "%s list" % vimtype
    rows = ([['MOID', 'Name', 'Status']] if vimtype == "VirtualMachine" else
            [['MOID', 'Name']])

    rows += ezmomi.list_objects(vimtype)

    ezmomi.tabulate(rows)


def clone(ezmomi):
    print "Cloning %s to new host %s with %sMB RAM..." % (
        ezmomi.config['template_name'],
        ezmomi.config['hostname'],
        ezmomi.config['mem']
    )

    ezmomi.clone(ezmomi.config['ips'], ezmomi.config['template_name'],
             ezmomi.config['domain'], ezmomi.config['hostname'],
             ezmomi.config['cpus'], ezmomi.config['mem'],
             ezmomi.config['to_template'], ezmomi.config.get('networks'))

    # Send notification mail
    if ezmomi.config['mailto']:
        subject = '%s - VM deploy complete' % ezmomi.config['hostname']
        body = 'Your VM is ready!'

        ezmomi.send_mail(ezmomi.config['mailfrom'], ezmomi.config['mailto'],
                     ezmomi.config['mailserver'], subject, body)


def destroy(ezmomi):
    print "Destroying %s..." % ezmomi.config['vm']
    ezmomi.destroy()


def list_snapshots(ezmomi):
    rows = [['VM', 'Snapshot', 'Create Time']]

    snapshots = ezmomi.list_snapshots(ezmomi.config['vm'])
    if snapshots:
        rows += snapshots
        ezmomi.tabulate(rows)
    else:
        print "No snapshots for %s" % ezmomi.config['vm']


def create_snapshot(ezmomi):
    ezmomi.create_snapshot(ezmomi.config['vm'], ezmomi.config['name'])

    print "Created snapshot for %s" % ezmomi.config['vm']


def remove_snapshot(ezmomi):
    ezmomi.remove_snapshot(ezmomi.config['vm'], ezmomi.config['name'],
                       ezmomi.config['remove_children'],
                       ezmomi.config['consolidate'])
    print("Removed snapshot %s for virtual machine %s" %
          (ezmomi.config['name'], ezmomi.config['vm']))


def revert_snapshot(ezmomi):
    ezmomi.revert_snapshot(ezmomi.config['vm'],
                       ezmomi.config['name'],
                       ezmomi.config.get('host'),
                       ezmomi.config.get('suppress_power_on'))
    print("Reverted snapshot %s for virtual machine %s" %
          (ezmomi.config['name'], ezmomi.config['vm']))


def status(ezmomi):
    rows = ezmomi.status(ezmomi.config['vm'])

    ezmomi.tabulate([rows])


def shutdown(ezmomi):
    ezmomi.shutdown(ezmomi.config['vm'])


def power_off(ezmomi):
    if ezmomi.power_off(ezmomi.config['vm']):
        print "%s poweredOff" % ezmomi.config['vm']
    else:
        print("%s encountered an unhandled exception when attempting to"
              " power_off" % ezmomi.config['vm'])


def power_on(ezmomi):
    if ezmomi.power_on(ezmomi.config['vm']):
        print "%s poweredOn" % ezmomi.config['vm']
    else:
        print("%s encountered an unhandled exception when attempting to"
              " power_on" % ezmomi.config['vm'])
