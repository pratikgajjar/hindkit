#!/usr/bin/env AFDKOPython
# encoding: UTF-8
from __future__ import division, absolute_import, print_function, unicode_literals

import os, sys, functools

def relative_to_interpreter(path):
    return os.path.join(os.path.dirname(sys.executable), path)

def relative_to_package(path):
    return os.path.join(__path__[0], path)

def relative_to_cwd(path):
    return os.path.join(os.getcwdu(), path)

def memoize(obj):
    memoized = {}
    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        k = str(args) + str(kwargs)
        if k not in memoized:
            memoized[k] = obj(*args, **kwargs)
        return memoized[k]
    return memoizer

sys.path.insert(0, relative_to_interpreter('../SharedData/FDKScripts'))
# __path__.append(relative_to_interpreter('../SharedData/FDKScripts'))
import agd

import hindkit.patches
import defcon as defcon_patched
defcon_patched.Glyph.insertAnchor = patches.insertAnchor

from hindkit import constants, objects, tools
