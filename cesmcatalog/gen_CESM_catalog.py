#!/usr/bin/env python
"""
  Goal: a script that gets pointed to a CESM case directory and generates
        an intake-esm catalog of output in the short-term archive directory

  Current state: a script that gets pointed to a CESM case directory and prints
                 some environment variables that will be necessary for above

  NOTE: this script needs to be run in the CESM postprocessing python environment,
        which is still based on python 2.7. Follow instructions at

        https://github.com/NCAR/CESM_postprocessing/wiki/cheyenne-and-DAV-quick-start-guide
"""

import argparse
import fnmatch
import logging
import os
import subprocess
import sys

################################################################################


def _parse_args():
    """ Wrapper for argparse, returns dictionary of arguments """

    parser = argparse.ArgumentParser(
        description='Generate intake-esm catalog for a CESM case',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '-c',
        '--caseroot',
        action='store',
        dest='caseroot',
        required=True,
        help='CESM case root to generate intake-esm catalog for',
    )

    parser.add_argument(
        '--cimeroot',
        action='store',
        dest='cimeroot',
        required=False,
        help='CIMEROOT variable from case root (will be determined via xmlquery if not provided)',
    )

    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        dest='debug',
        help='Add additional output for debugging',
    )

    return parser.parse_args()


################################################################################


def _find_data(caseroot, cimeroot):
    logger = logging.getLogger(__name__)

    # 1. change directory to caseroot (if it exists)
    try:
        os.chdir(caseroot)
    except:
        # TODO: set up logger instead of print statements
        logger.error('{} does not exist'.format(caseroot))
        sys.exit(1)

    # 2. Collect info on where time slice output is
    if not os.path.isfile('./xmlquery'):
        # TODO: set up logger instead of print statements
        logger.error('Can not find xmlquery in {}'.format(caseroot))
        sys.exit(1)

    # 3. Load CIME libraries for access to case information
    if cimeroot is None:
        cimeroot = subprocess.check_output('./xmlquery --value CIMEROOT', shell=True)
    sys.path.append(os.path.join(cimeroot, 'scripts', 'Tools'))

    import standard_script_setup  # noqa: F401 (used to get path to CIME.case in path)
    from CIME.case import Case

    run_config = dict()
    with Case(caseroot, read_only=True) as case:
        for var in ['CASE', 'GET_REFCASE', 'RUN_REFCASE', 'RUN_REFDATE', 'RUN_STARTDATE']:
            run_config[var] = case.get_value(var)

        if case.get_value('DOUT_S') == 'TRUE':
            DOUT_S_ROOT = case.get_value('DOUT_S_ROOT')
        else:
            DOUT_S_ROOT = None

    # 4. If time series preprocess was used, pull out necessary config data
    # TODO: how do we determine if we actually generated timeseries?
    if os.path.isdir('postprocess'):
        os.chdir('postprocess')
        TIMESERIES_OUTPUT_ROOTDIR = subprocess.check_output(
            './pp_config --value --get TIMESERIES_OUTPUT_ROOTDIR', shell=True
        ).rstrip()
    else:
        TIMESERIES_OUTPUT_ROOTDIR = None

    return run_config, DOUT_S_ROOT, TIMESERIES_OUTPUT_ROOTDIR


################################################################################


def _gen_timeslice_catalog(caseroot, archive_root, run_config):
    # TODO: figure out how to generate catalog from time slice
    logger = logging.getLogger(__name__)
    logger.info('Will catalog files in {}'.format(archive_root))


################################################################################


def _gen_timeseries_catalog(caseroot, archive_root, run_config):
    import pandas as pd
    import xarray as xr

    # Set up logger
    # Define casename, file to create, and columns the catalog will contain
    logger = logging.getLogger(__name__)
    casename = run_config['CASE']
    out_file = 'cesm_catalog.csv.gz'
    col_order = [
        'case',
        'component',
        'stream',
        'variable',
        'long_name',
        'start_date',
        'end_date',
        'path',
        'parent_branch_year',
        'child_branch_year',
        'parent_case',
    ]
    long_name_dict = dict()

    # cd archive_root and make sure intake/ subdirectory exists (for output)
    os.chdir(archive_root)
    if not os.path.isdir('intake'):
        os.mkdir('intake')

    # want paths in catalog to be relative to location of catalog
    os.chdir('intake')
    logger.info('Will catalog files in {}'.format(archive_root))
    catalog = dict()
    for col_name in col_order:
        catalog[col_name] = []

    # Find each netcdf file in directory
    for root, dirs, files in os.walk('..'):
        for ncfile in fnmatch.filter(files, '{}*.nc'.format(casename)):
            # each file should be {casename}.{stream}.{variable}.{start_date}-{end_date}.nc
            # first we drop the leading {casename}.
            file_without_case = ncfile.replace(casename, '')[1:]
            # then we split on .
            file_info = file_without_case.split('.')
            # {stream} will have at least one . in it
            # figure out how many by location of date_range
            # (only part of filename that should contain a '-')
            for date_ind, info in enumerate(file_info):
                if len(info.split('-')) > 1:
                    break

            # Enough to determine stream, variable, start_date, and end_date
            catalog['stream'].append('.'.join(file_info[: date_ind - 1]))
            variable = file_info[date_ind - 1]
            catalog['variable'].append(variable)
            date_range = info.split('-')
            catalog['start_date'].append(date_range[0])
            catalog['end_date'].append(date_range[1])

            # path should be relative to intake/, so we keep root
            path = os.path.join(root, ncfile)
            catalog['path'].append(path)
            # component is the name of the subdirectory of archive_root
            component = path.split('/')[1]
            catalog['component'].append(component)
            if component not in long_name_dict:
                long_name_dict[component] = dict()
            if variable not in long_name_dict[component]:
                ds = xr.open_dataset(path, decode_cf=False, chunks={})
                long_name_dict[component][variable] = ds[variable].attrs['long_name']
            catalog['long_name'].append(long_name_dict[component][variable])

    # Columns that do not change by row
    entry_cnt = len(catalog['path'])
    catalog['case'] = entry_cnt * [casename]
    if run_config['GET_REFCASE'] == 'TRUE':
        catalog['parent_case'] = entry_cnt * [run_config['RUN_REFCASE']]
        catalog['parent_branch_year'] = entry_cnt * [run_config['RUN_REFDATE']]
        catalog['child_branch_year'] = entry_cnt * [run_config['RUN_STARTDATE']]
    else:
        catalog['parent_case'] = entry_cnt * ['-']
        catalog['parent_branch_year'] = entry_cnt * [-1]
        catalog['child_branch_year'] = entry_cnt * [-1]

    pd.DataFrame(catalog).to_csv(out_file, index=False, columns=col_order, compression='gzip')
    logger.info('Created {}'.format(os.path.join(os.getcwd(), out_file)))


################################################################################


def gen_catalog(caseroot, cimeroot):
    logger = logging.getLogger(__name__)

    # 1. Find where data is
    run_config, DOUT_S_ROOT, TIMESERIES_OUTPUT_ROOTDIR = _find_data(caseroot, cimeroot)
    if (DOUT_S_ROOT is None) and (TIMESERIES_OUTPUT_ROOTDIR is None):
        logger.error('Error: can not find any data for {}'.format(caseroot))
        sys.exit(1)

    if TIMESERIES_OUTPUT_ROOTDIR:
        _gen_timeseries_catalog(caseroot, TIMESERIES_OUTPUT_ROOTDIR, run_config)
    else:  # only generate time slice catalog if time series not available
        _gen_timeslice_catalog(caseroot, DOUT_S_ROOT, run_config)


################################################################################

if __name__ == '__main__':
    args = _parse_args()
    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(format='%(levelname)s (%(funcName)s): %(message)s', level=log_level)
    # strip trailing / from case root (if user provides it)
    while args.caseroot[-1] == '/':
        args.caseroot = args.caseroot[:-1]
    gen_catalog(args.caseroot, args.cimeroot)
