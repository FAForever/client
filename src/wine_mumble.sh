#!/bin/sh
#
# Place in the same folder as FAForever.exe.

if ! command -v > /dev/null 2>&1 mumble ; then
	exit 1
else
	mumble "$@" &
	exit 0
fi
