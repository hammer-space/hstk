from setuptools import setup, find_packages
from os import path

from io import open

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Internal build
release_file = None
tmp_release_file = 'RELEASE'
for i in range(10):
   if path.exists(tmp_release_file):
        release_file = tmp_release_file
        pkg_name = 'hs'
        break
   tmp_release_file = '../' + tmp_release_file
# External build
if release_file is None and path.isfile('VERSION'):
    release_file = 'VERSION'
    pkg_name = 'hstk'

with open(path.join(here, release_file)) as f:
    version=f.readline()
    version = version.strip()

requirements = open(path.join(here, 'requirements.txt')).readlines()

setup(
    name=pkg_name,
    version=version,
    python_requires='>=3.6.0',
    description='Hammerspace CLI tool and python toolkit (hstk)',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Hammerspace Inc',
    author_email='support@hammerspace.com',
    packages=find_packages(),
    install_requires=requirements,
    license='Apache License 2.0',
    url="https://github.com/hammer-space/hstk",
    entry_points={
        'console_scripts': [
            'hs=hstk.hscli:cli'
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Information Technology',
        'Topic :: Office/Business',
        'Topic :: System :: Archiving',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: System :: Archiving :: Compression',
        'Topic :: System :: Archiving :: Mirroring',
        'Topic :: System :: Filesystems',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    keywords=["hammerspace", "hammerscript", 'metadata', 'global filesystem', 'archive', 'object', 's3', 'nfs', 'nfs4', 'nfs4.2', 'smb' ],
)
