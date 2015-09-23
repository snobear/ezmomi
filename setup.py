try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='ezmomi',
    version='0.4.1',
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
        "PyYAML==3.11",
        "argparse==1.2.1",
        "netaddr==0.7.11",
        "pyvmomi==5.5.0",
        "wsgiref==0.1.2",
    ],
)
