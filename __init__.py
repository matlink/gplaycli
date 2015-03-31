#! /usr/bin/python2
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
HERE = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(HERE, "googleplaydownloader", "version.txt"), "r") as f:
  __version__ = f.read().strip()

from .googleplaydownloader import main as start_gui

