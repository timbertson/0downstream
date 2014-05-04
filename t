#!/bin/bash
set -eu
feed="0downstream-local.xml"
gup -u "$feed"
set -x
0install run --command=test "$feed" "$@"
