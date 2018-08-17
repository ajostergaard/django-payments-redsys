#!/usr/bin/env python
from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

PACKAGES = [
    'payments_redsys',
]

REQUIREMENTS = [
    'Django>=1.11',
    'django-payments>=0.12.3',
]

setup(
    name='django-payments-redsys',
    author='AJ Ostergaard',
    author_email='aj.ostergaard@gmail.com',
    description='A django-payments backend for the Redsys payment gateway',
    long_description=long_description,
    long_description_content_type='text/markdown',
    version='0.3',
    url='https://github.com/ajostergaard/django-payments-redsys',
    packages=PACKAGES,
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules'],
    install_requires=REQUIREMENTS,
    zip_safe=False)
