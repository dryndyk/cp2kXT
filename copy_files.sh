#!/usr/bin/bash

cp  dftbXT/build/prog/dftb+/include/*.mod                         dftbXT_libs/
cp  dftbXT/build/prog/dftb+/libdftbplus.a                         dftbXT_libs/
cp  dftbXT/build/external/xmlf90/include/*.mod                    dftbXT_libs/
cp  dftbXT/build/external/mpifx/origin/lib/include/*.mod          dftbXT_libs/
cp  dftbXT/build/external/mpifx/origin/lib/libmpifx.a             dftbXT_libs/
cp  dftbXT/build/external/scalapackfx/origin/lib/include/*.mod    dftbXT_libs/
cp  dftbXT/build/external/scalapackfx/origin/lib/libscalapackfx.a dftbXT_libs/
cp  dftbXT/build/external/mudpack/libmudpack.a                    dftbXT_libs/
cp  dftbXT/build/external/sparskit/libsparskit.a                  dftbXT_libs/
