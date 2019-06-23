#!/usr/bin/bash

cp  dftbXT/_build/prog/dftb+/*.mod dftbXT_libs/
cp  dftbXT/_build/prog/dftb+/*.o dftbXT_libs/
rm  dftbXT_libs/dftbplus.o
cp  dftbXT/_build/external/mpifx/libmpifx.a dftbXT_libs/
cp  dftbXT/_build/external/mpifx/libmpifx_module.mod dftbXT_libs/
cp  dftbXT/_build/external/poisson/libpoisson.a dftbXT_libs/
cp  dftbXT/_build/external/poisson/libmudpack.a dftbXT_libs/
cp  dftbXT/_build/external/scalapackfx/libscalapackfx.a dftbXT_libs/
cp  dftbXT/_build/external/sparskit/libzsparskit.a dftbXT_libs/
cp  dftbXT/_build/external/tranas/libtranas.a dftbXT_libs/
cp  dftbXT/_build/external/xmlf90/libxmlf90.a dftbXT_libs/
cp  dftbXT/_build/external/dftd3/libdftd3.a dftbXT_libs/
