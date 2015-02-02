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
        '--cpus',
        type=int,
        help='Number of CPUs'
    )
    clone_parser.add_argument(
        '--mem',
        type=float,
        help='Memory in GB'
    )
    clone_parser.add_argument(
        '--domain',
        type=str,
        help='Domain, e.g. "example.com"'
    )

    clone_parser.add_argument(
        '--datastore',
        type=str,
        help='Default datastore',
        default='none'
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
    destroy_parser.add_argument(
        '--silent',
        help='Silently destroy a VM (default is false and can be set to true)',
        action='store_true'
    )
    
    # status
    status_parser = subparsers.add_parser(
        'status',
        help="Get a Virtual Machine's power status"
    )
    status_parser.add_argument(
        '--name',
        required=True,
        help='VM name (case-sensitive)'
    )
