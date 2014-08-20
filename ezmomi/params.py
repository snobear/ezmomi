'''
Command line option definitions
'''

import sys
import os
import yaml

def get_configs():
    default_cfg_dir = "%s/.config/ezmomi" % os.path.expanduser("~")
    default_config_file = "%s/config.yml" % default_cfg_dir

    # use path from env var if it's set and valid
    if 'EZMOMI_CONFIG' in os.environ:
        if os.path.isfile(os.environ['EZMOMI_CONFIG']):
            config_file = os.environ['EZMOMI_CONFIG']
        else:
            print "%s does not exist.  Set the EZMOMI_CONFIG environment" \
                  "variable to your config file's path."
            sys.exit(1)

    # or use the default config file path if it exists
    elif os.path.isfile(default_config_file):
        config_file = default_config_file
    # else create the default config path and copy the example config there
    else:
        from shutil import copy
        if not os.path.exists(default_cfg_dir):
            os.makedirs(default_cfg_dir)
        config_file = default_config_file

        # copy example config
        ezmomi_module_dir = os.path.dirname(os.path.abspath(__file__))
        ezmomi_ex_config = ("%s/config/config.yml.example"
                            % ezmomi_module_dir)
        try:
            copy(ezmomi_ex_config, default_cfg_dir)
        except:
            print ("Error copying example config file from %s to %s"
                   % (ezmomi_ex_config, default_cfg_dir))
            sys.exit(1)

        print "I could not find a config.yml file, so I copied an example "  \
              "to your home directory at %s/config.yml.example.  Please "    \
              "rename this to config.yml and add your vSphere "              \
              "environment's settings." % default_cfg_dir
        sys.exit(0)
    try:
        config = yaml.load(file(config_file))
    except IOError:
        print 'Unable to open config file.  The default path for the ezmomi' \
              ' config file is ~/.config/ezmomi/config.yml. You can also '   \
              'specify the config file path by setting the EZMOMI_CONFIG '   \
              'environment variable.'
        sys.exit(1)
    except Exception:
        print 'Unable to read config file.  YAML syntax issue, perhaps?'
        sys.exit(1)

    return config

def get_default(config, param):
    if param in config:
        return config[param]

def add_params(subparsers):
    # default configs
    config = get_configs()
    # list
    list_parser = subparsers.add_parser(
        'list',
        help='List VMware objects on your VMware server'
    )
    list_parser.add_argument(
        '--type',
        help='Object type, e.g. Network, VirtualMachine.',
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
        default=get_default(config, 'server'),
    )
    clone_parser.add_argument(
        '--port',
        type=str,
        help='vCenter server port',
        default=get_default(config, 'port'),
    )
    clone_parser.add_argument(
        '--username',
        type=str,
        help='vCenter username',
        default=get_default(config, 'username'),
    )
    clone_parser.add_argument(
        '--password',
        type=str,
        help='vCenter password',
        default=get_default(config, 'password'),
    )
    clone_parser.add_argument(
        '--template',
        type=str,
        help='VM template name to clone from',
        default=get_default(config, 'template'),
    )
    clone_parser.add_argument(
        '--hostname',
        type=str,
        help='New host name',
        default=get_default(config, 'hostname'),
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
        help='Number of CPUs',
        default=get_default(config, 'cpus'),
    )
    clone_parser.add_argument(
        '--mem',
        type=int,
        help='Memory in GB',
        default=get_default(config, 'mem'),
    )
    clone_parser.add_argument(
        '--domain',
        type=str,
        help='Domain, e.g. "example.com"',
        default=get_default(config, 'domain'),
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
