"""Command line option definitions"""


def arg_setup():
    from .version import __version__
    import argparse

    main_parser = argparse.ArgumentParser(
        description="Perform common vSphere API tasks"
    )

    subparsers = main_parser.add_subparsers(help="Command", dest="mode")

    main_parser.add_argument(
        "--version",
        action="version",
        version="ezmomi version %s" % __version__
    )

    # specify any arguments that are common to all subcommands
    common_parser = argparse.ArgumentParser(
        add_help=False,
        description="Shared/common arguments for all subcommands"
    )
    common_parser.add_argument(
        "--debug",
        action='store_true',
        help="Print debug messages"
    )

    # list
    list_parser = subparsers.add_parser(
        "list",
        parents=[common_parser],
        help="List VMware objects on your VMware server"
    )

    list_parser.add_argument(
        "--type",
        required=True,
        help="Object type, e.g. Network, VirtualMachine."
    )

    list_snapshot_parser = subparsers.add_parser(
        "listSnapshots",
        help="List snapshots for a VM"
    )
    list_snapshot_parser.add_argument(
        "--vm",
        required=True,
        help="VM name (case-sensitive)"
    )

    create_snapshot_parser = subparsers.add_parser(
        "createSnapshot",
        parents=[common_parser],
        help="Create snapshot for a VM"
    )
    create_snapshot_parser.add_argument(
        "--vm",
        required=True,
        help="VM name (case-sensitive)"
    )
    create_snapshot_parser.add_argument(
        "--name",
        required=True,
        help="Snapshot name (case-sensitive)"
    )
    create_snapshot_parser.add_argument(
        "--memory",
        required=False,
        action="store_true",
        default=False,
        help=("When set, a dump of the internal state of the virtual "
              "machine (basically a memory dump) is included in the "
              "snapshot. When unset, the power state of the snapshot "
              "is set to powered off.")
    )
    create_snapshot_parser.add_argument(
        "--quiesce",
        required=False,
        action="store_true",
        default=True,
        help=("When set and the virtual machine is powered on when the "
              "snapshot is taken, VMware Tools is used to quiesce "
              "the file system in the virtual machine.")
    )

    remove_snapshot_parser = subparsers.add_parser(
        "removeSnapshot",
        parents=[common_parser],
        help="Remove snapshot for a VM"
    )
    remove_snapshot_parser.add_argument(
        "--vm",
        required=True,
        help="VM name (case-sensitive)"
    )
    remove_snapshot_parser.add_argument(
        "--name",
        required=True,
        help="Snapshot name (case-sensitive)"
    )
    remove_snapshot_parser.add_argument(
        "--remove-children",
        required=False,
        action="store_true",
        default=False,
        help="Flag to specify removal of the entire snapshot subtree"
    )
    remove_snapshot_parser.add_argument(
        "--consolidate",
        required=False,
        action="store_true",
        default=True,
        help="If true, the virtual disk associated with this snapshot "
             "will be merged with other disk if possible"
    )

    revert_snapshot_parser = subparsers.add_parser(
        "revertSnapshot",
        parents=[common_parser],
        help="Revert snapshot for a VM"
    )
    revert_snapshot_parser.add_argument(
        "--vm",
        required=True,
        help="VM name (case-sensitive)"
    )
    revert_snapshot_parser.add_argument(
        "--name",
        required=True,
        help="Snapshot name (case-sensitive)"
    )
    revert_snapshot_parser.add_argument(
        "--host",
        required=False,
        type=str,
        help="Choice of host for the virtual machine, in case this operation "
             "causes the virtual machine to power on."
    )
    revert_snapshot_parser.add_argument(
        "--suppress-power-on",
        required=False,
        action="store_true",
        default=False,
        help=("When set, the virtual machine will not be powered on regardless"
              "of the power state when the snapshot was created")
    )

    # clone
    clone_parser = subparsers.add_parser(
        "clone",
        parents=[common_parser],
        help="Clone a VM template to a new VM"
    )
    clone_parser.add_argument(
        "--template",
        type=str,
        help="VM template name to clone from"
    )
    clone_parser.add_argument(
        "--host",
        required=False,
        type=str,
        default="",
        help="Choice of host for the virtual machine to run on."
             "if not specified, the host system is auto-selected by vsphere."
    )
    clone_parser.add_argument(
        "--hostname",
        required=True,
        type=str,
        help="New host name",
    )
    clone_parser.add_argument(
        "--ips",
        type=str,
        help="Static IPs of new host, separated by a space. "
             "List primary IP first.",
        nargs="+",
    )
    clone_parser.add_argument(
        "--cpus",
        type=int,
        help="Number of CPUs"
    )
    clone_parser.add_argument(
        "--mem",
        type=float,
        help="Memory in GB"
    )
    clone_parser.add_argument(
        "--domain",
        type=str,
        help="Domain, e.g. example.com"
    )
    clone_parser.add_argument(
        "--resource-pool",
        type=str,
        default="Resources",
        help="Resource Pool, e.g. 'Linux Servers'"
    )
    clone_parser.add_argument(
        "--post-clone-cmd",
        type=str,
        help="Command to run after clone. This is run from the same shell "
             "that ezmomi is called from. Useful in running extra "
             "provisioning steps."
    )

    # destroy
    destroy_parser = subparsers.add_parser(
        "destroy",
        parents=[common_parser],
        help="Destroy/delete a Virtual Machine"
    )
    destroy_parser.add_argument(
        "--name",
        required=True,
        help="VM name (case-sensitive)"
    )
    destroy_parser.add_argument(
        "--silent",
        help="Silently destroy a VM (default is false and can be set to true)",
        default=False,
        action="store_true"
    )

    # status
    status_parser = subparsers.add_parser(
        "status",
        parents=[common_parser],
        help="Get a Virtual Machine's power status"
    )
    status_parser.add_argument(
        "--name",
        required=True,
        help="VM name (case-sensitive)"
    )

    # shutdown
    shutdown_parser = subparsers.add_parser(
        "shutdown",
        parents=[common_parser],
        help="Shutdown a Virtual Machine "
             "(will fall back to powerOff if guest tools are not running)"
    )
    shutdown_parser.add_argument(
        "--name",
        required=True,
        help="VM name (case-sensitive)"
    )

    # powerOff
    powerOff_parser = subparsers.add_parser(
        "powerOff",
        parents=[common_parser],
        help="Power Off a Virtual Machine (not a clean shutdown)"
    )
    powerOff_parser.add_argument(
        "--name",
        required=True,
        help="VM name (case-sensitive)"
    )

    # powerOn
    powerOn_parser = subparsers.add_parser(
        "powerOn",
        parents=[common_parser],
        help="Power On a Virtual Machine"
    )
    powerOn_parser.add_argument(
        "--name",
        required=True,
        help="VM name (case-sensitive)"
    )

    return main_parser.parse_args()
