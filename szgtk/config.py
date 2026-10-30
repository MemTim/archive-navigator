# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .display import DISP_DEFAULTS

# ───────────────────────────── конфигурация ─────────────────────────────
class Config(dict):
    DEFAULTS = {
        'favorites': {}, 'show_hidden': False, 'grid': False, 'single_click': False,
        'confirm_delete': True, 'use_trash': True, 'two_panels': False,
        'hide_menu_bar': False, 'hide_toolbar': False,
        'hide_sidebar': False, 'hide_panels_button': False,
        'editor': '', 'viewer': '', 'width': 1100, 'height': 700,
        'last_dir': '', 'add_format': '7z', 'add_level': 5,
        # оформление
        'design': 'classic', 'scheme': 'midnight', 'density': 'normal', 'show_hints': True,
        # язык / горячие клавиши
        'language': 'auto', 'accels': {},
        # прочее
        'restore_last_dir': True, 'extract_overwrite': 'ask', 'extract_pathmode': 'full',
        'columns_hidden': [],
        # вид: список / плитки, миниатюры, размеры значков
        'view_mode': 'list', 'show_thumbs': True, 'list_icon_size': 16, 'tile_icon_size': 64,
        # значки запрета доступа (lock / cross) и ссылок (link)
        'show_badges': True,
        # выбор файла набором букв
        'typeahead': True, 'typeahead_timeout': 1000,
        # контекстное меню: порядок, скрытые пункты и ситуации показа
        'menu_layout': [], 'menu_hidden': [], 'menu_contexts': {},
        # боковая панель: порядок, скрытые группы/пункты и ширина
        'sidebar_groups': ['places', 'favorites', 'devices'], 'sidebar_hidden': [],
        'sidebar_places': ['home', 'desktop', 'downloads', 'documents',
                           'pictures', 'music', 'videos'],
        'sidebar_hidden_places': [],
        'sidebar_width': 220,
        # последнее сетевое подключение (протокол и адрес для диалога)
        'network_last': {},
    }
    DEFAULTS.update(DISP_DEFAULTS)

    def __init__(self):
        super().__init__(copy.deepcopy(self.DEFAULTS))
        try:
            with open(CONF_FILE, encoding='utf-8') as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        if CONFIG_READONLY:
            return
        try:
            os.makedirs(CONF_DIR, exist_ok=True)
            with open(CONF_FILE, 'w', encoding='utf-8') as f:
                json.dump(self, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
