#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Archive Navigator — двухпанельный файловый менеджер и архиватор в стиле
«7-Zip File Manager» (Windows).
GTK4 (нативный Wayland), бэкенд — консольный 7z / 7zz.

Точка входа. Код приложения находится в пакете szgtk/.

Arch Linux:   sudo pacman -S gtk4 python-gobject 7zip
Запуск:       python sevenzip-gtk.py [папка | архив]
              sevenzip-gtk.py --add файл...        (диалог «Добавить в архив»)
              sevenzip-gtk.py --extract архив...   (диалог «Распаковать»)
              sevenzip-gtk.py --extract-here архив...
"""

import os
import sys

_here = os.path.dirname(os.path.realpath(__file__))
for _base in (_here,
              os.path.join(_here, '..', 'share', 'sevenzip-gtk'),
              os.path.expanduser('~/.local/share/sevenzip-gtk')):
    if os.path.isdir(os.path.join(_base, 'szgtk')):
        sys.path.insert(0, _base)
        break

os.environ.setdefault('SZ_APP_ENTRY', os.path.abspath(__file__))

from szgtk.app import main

if __name__ == '__main__':
    main()
