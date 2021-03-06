#!/usr/bin/env python

"""The setup script."""
from setuptools import find_packages, setup

with open('requirements.txt') as f:
    INSTALL_REQUIREs = f.read().strip().split('\n')
with open('README.md', encoding='utf8') as f:
    LONG_DESCRIPTION = f.read()
CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Scientific/Engineering',
]

setup(
    name='cesm-catalog',
    description='cesm-catalog: a wrapper layer for intake-esm and tools to generate catalogs of CESM output.',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    python_requires='>=3.6',
    maintainer='NCAR XDev Team',
    maintainer_email='xdev@ucar.edu',
    classifiers=CLASSIFIERS,
    url='https://cesm-catalog.readthedocs.io',
    project_urls={
        'Documentation': 'https://cesm-catalog.readthedocs.io',
        'Source': 'https://github.com/NCAR/cesm-catalog',
        'Tracker': 'https://github.com/NCAR/cesm-catalog/issues',
    },
    packages=find_packages(exclude=('tests',)),
    include_package_data=True,
    install_requires=INSTALL_REQUIREs,
    license='Apache 2.0',
    zip_safe=False,
    entry_points={},
    keywords='intake, intake-esm, catalog, cesm, The Community Earth System Model',
    use_scm_version={'version_scheme': 'post-release', 'local_scheme': 'dirty-tag'},
    setup_requires=['setuptools_scm', 'setuptools>=30.3.0'],
)
