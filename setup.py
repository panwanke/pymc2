#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Do not add setuptools here; use setupegg.py instead. Nose still has problems running
# tests inside of egg packages, so it is useful to be able to install without eggs as needed.

from __future__ import print_function
from pkg_resources import parse_version

import os, sys

dist = sys.argv[1]

numpy_min_version = '1.8'

def get_numpy_status():
    """
    Returns a dictionary containing a boolean specifying whether NumPy
    is up-to-date, along with the version string (empty string if
    not installed).
    """
    numpy_status = {}
    try:
        import numpy
        numpy_version = numpy.__version__
        numpy_status['up_to_date'] = parse_version(
            numpy_version) >= parse_version(numpy_min_version)
        numpy_status['version'] = numpy_version
    except ImportError:
        numpy_status['up_to_date'] = False
        numpy_status['version'] = ""
    return numpy_status

def build_ext(config):
    # ==============================
    # = Compile Fortran extensions =
    # ==============================
    
    from numpy.distutils.system_info import get_info
    

    # If optimized lapack/ BLAS libraries are present, compile distributions that involve linear algebra against those.
    # Otherwise compile blas and lapack from netlib sources.
    lapack_info = get_info('lapack_opt',1)
    f_sources = ['pymc/flib.f','pymc/histogram.f', 'pymc/flib_blas.f', 'pymc/blas_wrap.f', 'pymc/math.f', 'pymc/gibbsit.f', 'cephes/i0.c',
                 'cephes/c2f.c','cephes/chbevl.c']
    if lapack_info:
        config.add_extension(name='flib',sources=f_sources, extra_info=lapack_info, f2py_options=['skip:', 'ppnd7', ':'])

    if not lapack_info or dist in ['bdist', 'sdist']:
        ##inc_dirs = ['blas/BLAS','lapack/double']
        print('No optimized BLAS or Lapack libraries found, building from source. This may take a while...')
        for fname in os.listdir('blas/BLAS'):
            # Make sure this is a Fortran file, and not one of those weird hidden files that
            # pop up sometimes in the tarballs
            if fname[-2:]=='.f' and fname[0].find('_')==-1:
                f_sources.append('blas/BLAS/'+fname)


        for fname in ['dpotrs','dpotrf','dpotf2','ilaenv','dlamch','ilaver','ieeeck','iparmq']:
            f_sources.append('lapack/double/'+fname+'.f')
        config.add_extension(name='flib',sources=f_sources)


    # ============================
    # = Compile Pyrex extensions =
    # ============================

    config.add_extension(name='LazyFunction',sources=['pymc/LazyFunction.c'])
    config.add_extension(name='Container_values', sources='pymc/Container_values.c')

    config_dict = config.todict()
    try:
        config_dict.pop('packages')
    except:
        pass


    # ===========================================
    # = Compile GP package's Fortran extensions =
    # ===========================================

    # Compile linear algebra utilities
    if lapack_info:
        config.add_extension(name='gp.linalg_utils',sources=['pymc/gp/linalg_utils.f','pymc/blas_wrap.f'], extra_info=lapack_info)
        config.add_extension(name='gp.incomplete_chol',sources=['pymc/gp/incomplete_chol.f'], extra_info=lapack_info)

    if not lapack_info or dist in ['bdist', 'sdist']:
        print('No optimized BLAS or Lapack libraries found, building from source. This may take a while...')
        f_sources = ['pymc/blas_wrap.f']
        for fname in os.listdir('blas/BLAS'):
            if fname[-2:]=='.f':
                f_sources.append('blas/BLAS/'+fname)

        for fname in ['dpotrs','dpotrf','dpotf2','ilaenv','dlamch','ilaver','ieeeck','iparmq']:
            f_sources.append('lapack/double/'+fname+'.f')

        config.add_extension(name='gp.linalg_utils',sources=['pymc/gp/linalg_utils.f'] + f_sources)
        config.add_extension(name='gp.incomplete_chol',sources=['pymc/gp/incomplete_chol.f'] + f_sources)


    # Compile covariance functions
    config.add_extension(name='gp.cov_funs.isotropic_cov_funs',\
    sources=['pymc/gp/cov_funs/isotropic_cov_funs.f','blas/BLAS/dscal.f'],\
    extra_info=lapack_info)

    config.add_extension(name='gp.cov_funs.distances',sources=['pymc/gp/cov_funs/distances.f'], extra_info=lapack_info)
    
    return config_dict

def setup_pymc():

    numpy_status = get_numpy_status()
    numpy_req_str = "PyMC requires NumPy >= {0}.\n".format(
        numpy_min_version)
        
    if numpy_status['up_to_date'] is False:
        if numpy_status['version']:
            raise ImportError("Your installation of NumPy"
                              "{0} is out-of-date.\n{1}"
                              .format(numpy_status['version'],
                                      numpy_req_str))
        else:
            raise ImportError("NumPy is not installed.\n{0}"
                              .format(numpy_req_str))
                              
    
    from numpy.distutils.misc_util import Configuration
    from numpy.distutils.core import setup
    
    config_dict = build_ext(Configuration('pymc',parent_package=None,top_path=None))
                              
    
    setup(  version="2.3.8",
            description="Markov Chain Monte Carlo sampling toolkit.",
            author="Christopher Fonnesbeck, Anand Patil and David Huard",
            author_email="fonnesbeck@gmail.com ",
            url="http://github.com/pymc-devs/pymc",
            license="Academic Free License",
            classifiers=[
                'Development Status :: 5 - Production/Stable',
                'Environment :: Console',
                'Operating System :: OS Independent',
                'Intended Audience :: Science/Research',
                'License :: OSI Approved :: Academic Free License (AFL)',
                'Programming Language :: Python',
                'Programming Language :: Fortran',
                'Topic :: Scientific/Engineering',
                 ],
            requires=['NumPy (>=1.8)',],
            long_description="""
            Bayesian estimation, particularly using Markov chain Monte Carlo (MCMC),
            is an increasingly relevant approach to statistical estimation. However,
            few statistical software packages implement MCMC samplers, and they are
            non-trivial to code by hand. ``pymc`` is a python package that implements the
            Metropolis-Hastings algorithm as a python class, and is extremely
            flexible and applicable to a large suite of problems. ``pymc`` includes
            methods for summarizing output, plotting, goodness-of-fit and convergence
            diagnostics.

            ``pymc`` only requires ``NumPy``. All other dependencies such as ``matplotlib``,
            ``SciPy``, ``pytables``, ``sqlite`` or ``mysql`` are optional.
            """,
            packages=["pymc", "pymc/database", "pymc/examples", "pymc/examples/gp", "pymc/tests", "pymc/gp", "pymc/gp/cov_funs"],
            **(config_dict))
            
if __name__ == '__main__':
    setup_pymc()
    
    

