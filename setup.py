#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import shutil
import subprocess
import sys
from pathlib import Path

from packaging.version import Version
from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext as _build_ext


ROOT = Path(__file__).parent.resolve()
NUMPY_MIN_VERSION = "2.0"


def check_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise ImportError("PyMC requires NumPy >= {0}.".format(NUMPY_MIN_VERSION)) from exc

    if Version(numpy.__version__) < Version(NUMPY_MIN_VERSION):
        raise ImportError(
            "Your NumPy installation ({0}) is too old. PyMC requires NumPy >= {1}.".format(
                numpy.__version__, NUMPY_MIN_VERSION
            )
        )
    return numpy


def rel(*parts):
    return str(ROOT.joinpath(*parts))


F2PY_EXTENSIONS = [
    {
        "package": "pymc",
        "module": "flib",
        "sources": [
            rel("pymc", "flib.f"),
            "skip:",
            "ppnd7",
            ":",
            rel("pymc", "histogram.f"),
            rel("pymc", "flib_blas.f"),
            rel("pymc", "blas_wrap.f"),
            rel("pymc", "math.f"),
            rel("pymc", "gibbsit.f"),
            rel("cephes", "i0.c"),
            rel("cephes", "c2f.c"),
            rel("cephes", "chbevl.c"),
        ],
        "deps": ["lapack", "blas"],
        "include_paths": [rel("cephes")],
    },
    {
        "package": "pymc.gp",
        "module": "linalg_utils",
        "sources": [rel("pymc", "gp", "linalg_utils.f"), rel("pymc", "blas_wrap.f")],
        "deps": ["lapack", "blas"],
    },
    {
        "package": "pymc.gp",
        "module": "incomplete_chol",
        "sources": [rel("pymc", "gp", "incomplete_chol.f"), rel("pymc", "blas_wrap.f")],
        "deps": ["lapack", "blas"],
    },
    {
        "package": "pymc.gp.cov_funs",
        "module": "isotropic_cov_funs",
        "sources": [rel("pymc", "gp", "cov_funs", "isotropic_cov_funs.f"), rel("blas", "BLAS", "dscal.f")],
    },
    {
        "package": "pymc.gp.cov_funs",
        "module": "distances",
        "sources": [rel("pymc", "gp", "cov_funs", "distances.f")],
    },
]


class build_ext(_build_ext):
    def run(self):
        super().run()
        self.build_f2py_extensions()

    def build_f2py_extensions(self):
        for spec in F2PY_EXTENSIONS:
            self.build_f2py_extension(spec)

    def build_f2py_extension(self, spec):
        build_dir = Path(self.build_temp) / ("f2py_" + spec["module"])
        build_dir.mkdir(parents=True, exist_ok=True)

        command = [
            sys.executable,
            "-m",
            "numpy.f2py",
            "-c",
            "-m",
            spec["module"],
        ]
        for include_path in spec.get("include_paths", []):
            command.extend(["--include-paths", include_path])
        for dep in spec.get("deps", []):
            command.extend(["--dep", dep])
        command.extend(spec["sources"])

        subprocess.check_call(command, cwd=str(build_dir))

        built = list(build_dir.glob(spec["module"] + "*.so")) + list(build_dir.glob(spec["module"] + "*.pyd"))
        if not built:
            raise RuntimeError("f2py did not produce an extension for {0}".format(spec["module"]))

        package_dir = Path(self.build_lib).joinpath(*spec["package"].split("."))
        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(built[0]), str(package_dir / built[0].name))


numpy = check_numpy()

try:
    from Cython.Build import cythonize

    ext_modules = cythonize(
        [
            Extension("pymc.LazyFunction", [rel("pymc", "LazyFunction.pyx")], include_dirs=[numpy.get_include()]),
            Extension("pymc.Container_values", [rel("pymc", "Container_values.pyx")], include_dirs=[numpy.get_include()]),
        ],
        compiler_directives={"language_level": "3"},
        force=True,
    )
except ImportError:
    ext_modules = [
        Extension("pymc.LazyFunction", [rel("pymc", "LazyFunction.c")], include_dirs=[numpy.get_include()]),
        Extension("pymc.Container_values", [rel("pymc", "Container_values.c")], include_dirs=[numpy.get_include()]),
    ]


setup(
    name="PyMC",
    version="2.3.8",
    description="Markov Chain Monte Carlo sampling toolkit.",
    author="Christopher Fonnesbeck, Anand Patil and David Huard",
    author_email="fonnesbeck@gmail.com ",
    url="http://github.com/pymc-devs/pymc",
    license="Academic Free License",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Academic Free License (AFL)",
        "Programming Language :: Python",
        "Programming Language :: Fortran",
        "Topic :: Scientific/Engineering",
    ],
    install_requires=["numpy>=2,<3", "scipy"],
    packages=find_packages(),
    cmdclass={"build_ext": build_ext},
    ext_modules=ext_modules,
)
