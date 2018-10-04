try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

try:
    exec(open('ezmomi/version.py').read())
except:
    print "Unable to import ezmomi/version.py. Exiting."
    sys.exit(1)

setup(
    name='ezmomi',
    version=__version__,
    author='Jason Ashby',
    author_email='jashby2@gmail.com',
    packages=['ezmomi'],
    package_dir={'ezmomi': 'ezmomi'},
    package_data={'ezmomi': ['config/config.yml.example']},
    scripts=['bin/ezmomi'],
    url='https://github.com/snobear/ezmomi',
    license='LICENSE.txt',
    description='VMware vSphere Command line tool',
    long_description=open('README.txt').read(),
    install_requires=[
        "netaddr==0.7.19",
        "pyvmomi==6.7.0.2018.9",
        "PyYAML==3.13",
        "requests==2.19.1",
        "six==1.11.0",
        "wheel==0.31.1",
    ],
)
