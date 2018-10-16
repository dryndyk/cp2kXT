#!/usr/bin/bash

cp  dftbXT/_build/prog/dftb+/*.mod dftbXT_libs/
mv  dftbXT_libs/environment.mod dftbXT_libs/environment_1.mod
cp  dftbXT/_build/prog/dftb+/*.o dftbXT_libs/
rm  dftbXT_libs/dftbplus.o
cp  dftbXT/_build/external/fsockets/libfsockets.a dftbXT_libs/
cp  dftbXT/_build/external/mpifx/libmpifx.a dftbXT_libs/
cp  dftbXT/_build/external/mpifx/libmpifx_module.mod dftbXT_libs/
cp  dftbXT/_build/external/mudpack/libmudpack.a dftbXT_libs/
cp  dftbXT/_build/external/scalapackfx/libscalapackfx.a dftbXT_libs/
cp  dftbXT/_build/external/sparskit/libzsparskit.a dftbXT_libs/
cp  dftbXT/_build/external/tranas/libtranas.a dftbXT_libs/
cp  dftbXT/_build/external/xmlf90/libxmlf90.a dftbXT_libs/
