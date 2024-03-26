# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in bottle_filler/__init__.py
from bottle_filler import __version__ as version

setup(
	name='bottle_filler',
	version=version,
	description='Bottle Filler App',
	author='Glistercp',
	author_email='support@glistercp.com.ng',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
