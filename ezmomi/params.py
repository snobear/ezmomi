"""
Command line option definitions
"""


def add_params(parser):
    """
    Add parameters to the main argument parser
    """

    parser.add_argument(
        '--mailfrom',
        type=str,
        required=False,
        help='Address to send mail from'
    )
    parser.add_argument(
        '--mailserver',
        type=str,
        required=False,
        help='Outgoing SMTP server used to send mail'
    )
    parser.add_argument(
        '--mailto',
        type=str,
        required=False,
        help='Address to send mail to'
    )

    parser.add_argument('-v', '--verbose', help="Show messages at the"
                        " specified log level according to the number of"
                        " v\'s: INFO, DEBUG. DEBUG shows most function"
                        " entry and exit", action='count', default=0)


def add_subparser_params(subparsers):
    """
    Add subparsers and their parameters to the main argument parser

    :param subparsers: Subparser to add parsers to
    """

    # list
    list_parser = subparsers.add_parser(
        'list',
        help='List VMware objects on your VMware server'
    )

    list_parser.add_argument(
        '--type',
        required=True,
        help='Object type, e.g. Network, VirtualMachine.'
    )

    list_snapshot_parser = subparsers.add_parser(
        'list-snapshots',
        help='List snapshots for a VM'
    )
    list_snapshot_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )

    create_snapshot_parser = subparsers.add_parser(
        'create-snapshot',
        help='Create snapshot for a VM'
    )
    create_snapshot_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )
    create_snapshot_parser.add_argument(
        '--name',
        required=True,
        help='Snapshot name (case-sensitive)'
    )
    create_snapshot_parser.add_argument(
        '--memory',
        required=False,
        action='store_true',
        default=False,
        help=("When set, a dump of the internal state of the virtual "
              "machine (basically a memory dump) is included in the "
              "snapshot. When unset, the power state of the snapshot "
              "is set to powered off.")
    )
    create_snapshot_parser.add_argument(
        '--quiesce',
        required=False,
        action='store_true',
        default=True,
        help=("When set and the virtual machine is powered on when the "
              "snapshot is taken, VMware Tools is used to quiesce "
              "the file system in the virtual machine.")
    )

    remove_snapshot_parser = subparsers.add_parser(
        'remove-snapshot',
        help='Remove snapshot for a VM'
    )
    remove_snapshot_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )
    remove_snapshot_parser.add_argument(
        '--name',
        required=True,
        help='Snapshot name (case-sensitive)'
    )
    remove_snapshot_parser.add_argument(
        '--remove-children',
        required=False,
        action='store_true',
        default=False,
        help='Flag to specify removal of the entire snapshot subtree'
    )
    remove_snapshot_parser.add_argument(
        '--consolidate',
        required=False,
        action='store_true',
        default=True,
        help=("If true, the virtual disk associated with this snapshot will be"
              " merged with other disk if possible")
    )

    revert_snapshot_parser = subparsers.add_parser(
        'revert-snapshot',
        help='Revert snapshot for a VM'
    )
    revert_snapshot_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )
    revert_snapshot_parser.add_argument(
        '--name',
        required=True,
        help='Snapshot name (case-sensitive)'
    )
    revert_snapshot_parser.add_argument(
        '--host',
        required=False,
        type=str,
        help=("Choice of host for the virtual machine, in case this operation"
              " causes the virtual machine to power on.")
    )
    revert_snapshot_parser.add_argument(
        '--suppress-power-on',
        required=False,
        action='store_true',
        default=False,
        help=("When set, the virtual machine will not be powered on regardless"
              "of the power state when the snapshot was created")
    )

    # clone
    clone_parser = subparsers.add_parser(
        'clone',
        help='Clone a VM template to a new VM'
    )
    clone_parser.add_argument(
        '--server',
        type=str,
        help='vCenter server',
    )
    clone_parser.add_argument(
        '--port',
        type=str,
        help='vCenter server port',
    )
    clone_parser.add_argument(
        '--username',
        type=str,
        help='vCenter username',
    )
    clone_parser.add_argument(
        '--password',
        type=str,
        help='vCenter password',
    )
    clone_parser.add_argument(
        '--to-template',
        default=False,
        action='store_true',
        help=('Specifies whether or not the new virtual machine '
              'should be marked as a template')
    )
    clone_parser.add_argument(
        '--template-name',
        type=str,
        help='VM template name to clone from'
    )
    clone_parser.add_argument(
        '--hostname',
        required=True,
        type=str,
        help='New host name',
    )
    clone_parser.add_argument(
        '--ips',
        type=str,
        help='Static IPs of new host, separated by a space. '
             'List primary IP first.',
        nargs='+',
    )
    clone_parser.add_argument(
        '--cpus',
        type=int,
        help='Number of CPUs'
    )
    clone_parser.add_argument(
        '--mem',
        type=lambda x: int(x) * 1024,
        help='Memory in GB'
    )
    clone_parser.add_argument(
        '--domain',
        type=str,
        help='Domain, e.g. "example.com"'
    )

    # destroy
    destroy_parser = subparsers.add_parser(
        'destroy',
        help='Destroy/delete a Virtual Machine'
    )
    destroy_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )

    # status
    status_parser = subparsers.add_parser(
        'status',
        help="Get a Virtual Machine's power status"
    )
    status_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )

    # shutdown
    shutdown_parser = subparsers.add_parser(
        'shutdown',
        help=("Shutdown a Virtual Machine (will fall back to powerOff if guest"
              " tools are not running)")
    )
    shutdown_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )

    # power-off
    power_off_parser = subparsers.add_parser(
        'power-off',
        help="Power Off a Virtual Machine (not a clean shutdown)"
    )
    power_off_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )

    # power-on
    power_on_parser = subparsers.add_parser(
        'power-on',
        help="Power On a Virtual Machine"
    )
    power_on_parser.add_argument(
        '--vm',
        required=True,
        help='VM name (case-sensitive)'
    )
