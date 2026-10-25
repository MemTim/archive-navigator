# -*- coding: utf-8 -*-
"""Общие импорты, константы и пути приложения."""

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Pango
try:
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
except (ValueError, ImportError):
    GdkPixbuf = None
try:
    gi.require_version('Gsk', '4.0')
    gi.require_version('Graphene', '1.0')
    from gi.repository import Gsk, Graphene
except (ValueError, ImportError):
    Gsk = Graphene = None

import base64
import collections
import copy
import fnmatch
import json
import math
import os
import re
import shlex
import shutil
import stat
import string
import subprocess
import sys
import tempfile
import threading
import time

APP_ID = 'io.sevenzipgtk.App'
APP_NAME = 'Archive Navigator'
VERSION = '1.0'

IS_ROOT = os.geteuid() == 0
# экземпляр, запущенный через «Открыть от root», только читает настройки пользователя
CONFIG_READONLY = IS_ROOT and bool(os.environ.get('SZ_USER_CONFIG_DIR'))
CONF_DIR = os.environ.get('SZ_USER_CONFIG_DIR') or os.path.join(GLib.get_user_config_dir(), 'sevenzip-gtk')
CONF_FILE = os.path.join(CONF_DIR, 'config.json')

H, V = Gtk.Orientation.HORIZONTAL, Gtk.Orientation.VERTICAL

MODMASK = Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK
MODIFIER_KEYS = {Gdk.KEY_Shift_L, Gdk.KEY_Shift_R, Gdk.KEY_Control_L, Gdk.KEY_Control_R, Gdk.KEY_Alt_L,
                 Gdk.KEY_Alt_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R, Gdk.KEY_Super_L, Gdk.KEY_Super_R,
                 Gdk.KEY_ISO_Level3_Shift, Gdk.KEY_Caps_Lock, Gdk.KEY_Num_Lock, Gdk.KEY_Hyper_L, Gdk.KEY_Hyper_R}

# путь к исполняемому файлу-лаунчеру (нужен для перезапуска через pkexec)
APP_ENTRY = os.environ.get('SZ_APP_ENTRY') or os.path.abspath(sys.argv[0])


