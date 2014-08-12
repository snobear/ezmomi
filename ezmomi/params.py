'''
Command line option definitions
'''


def add_params(subparsers):
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
        '--template',
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
        '--dhcp',
        action="store_true",
        required=False,
        help='Use DHCP instead of static IPs',
    )
    clone_parser.add_argument(
        '--waitforip',
        action="store_true",
        required=False,
        default=False,
        help='Wait for the system to obtain and IP address',
    )
    clone_parser.add_argument(
        '--cpus',
        type=int,
        help='Number of CPUs'
    )
    clone_parser.add_argument(
        '--mem',
        type=int,
        help='Memory in GB'
    )
    clone_parser.add_argument(
        '--folder',
        type=str,
        required=False,
        default='/',
        help='Destination folder for the new VM'
    )
    clone_parser.add_argument(
        '--count',
        type=int,
        help='Number of VMs to launch [dhcp only]'
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
        '--name',
        required=True,
        help='VM name (case-sensitive)'
    )
