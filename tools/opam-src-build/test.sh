#!/bin/bash
set -eux
cd "$(dirname "$0")"

export OPAM_PKG_PATH="$(pwd)/test/pkg/"

rm -rf ./test/build
export BUILDDIR="$(pwd)/test/build"
mkdir "$BUILDDIR"

# export "$SRCDIR"
export DESTDIR="$(pwd)/test/dist"

# XXX hacky
export PATH="/home/tim/dev/0install/zi-ocaml/opam.0compile/opam-linux-x86_64/bin/:$PATH"

./opam-build yojson
