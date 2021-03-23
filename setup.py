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
    }
)
