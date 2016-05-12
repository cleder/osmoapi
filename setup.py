# -*- coding: utf-8 -*-
import sys

from setuptools import find_packages
from setuptools import setup
from setuptools.command.test import test as TestCommand

version = '0.1'


class PyTest(TestCommand):

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='osmoapi',
    version=version,
    description="OpenStreetMap OAuth API",
    long_description=open("README.rst").read(),
    classifiers=[
        "Topic :: Scientific/Engineering :: GIS",
        "Programming Language :: Python",
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
    ],
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='osm OpenStreetMap api oauth',
    author='Christian Ledermann',
    author_email='christian.ledermann@gmail.com',
    url='https://github.com/cleder/osmoapi',
    license='LGPL',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
        'pygeoif',
        'requests_oauthlib',
    ],
    entry_points="""
      # -*- Entry points: -*-
      """,
    tests_require=['pytest'],
    cmdclass={'test': PyTest}, )
