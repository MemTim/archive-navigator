#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Экспорт живого интерфейса sevenzip-gtk в редактируемые SVG.

Скрипт поднимает приложение во временном профиле (свой каталог настроек и
демонстрационные файлы), обходит все окна, страницы настроек и меню и сохраняет
каждое состояние в ``docs/design/``.  Это не скриншоты: конвертер
``tools/gsk2svg.py`` превращает дерево отрисовки GTK (GSK) в настоящие
векторные фигуры, градиенты и значки, а текст остаётся текстом.

Запуск (нужен X-сервер; на headless-машине используется xvfb)::

    tools/export-design.sh

или вручную::

    xvfb-run -a -s '-screen 0 1400x1000x24' \\
        env GDK_BACKEND=x11 GSK_RENDERER=cairo dbus-run-session -- \\
        python3 tools/export_design.py

Повторный запуск полностью перезаписывает ``docs/design/``.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import tempfile
import time
import traceback
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))

OUT = ROOT / 'docs' / 'design'
DEMO = pathlib.Path('/tmp/sevenzip-gtk-design/demo')

# Отдельный профиль: настройки пользователя не читаются и не меняются.
_BASE = pathlib.Path(tempfile.mkdtemp(prefix='sz-design-'))
CONF_DIR = _BASE / 'config'
LOG_DIR = _BASE / 'log'
CONF_DIR.mkdir(parents=True, exist_ok=True)
os.environ['SZ_USER_CONFIG_DIR'] = str(CONF_DIR)
os.environ['SZ_LOG_DIR'] = str(LOG_DIR)
os.environ['LANG'] = 'ru_RU.UTF-8'
os.environ['LANGUAGE'] = 'ru'

import gi  # noqa: E402

gi.require_version('Gtk', '4.0')

from gi.repository import GLib, Gtk  # noqa: E402

from gsk2svg import GskToSvg  # noqa: E402

import szgtk.app as appmod  # noqa: E402
from szgtk.i18n import _  # noqa: E402
from szgtk.imports import APP_ID as REAL_APP_ID, APP_NAME, VERSION  # noqa: E402
from szgtk.settings import SettingsDialog  # noqa: E402
from szgtk.theme import apply_theme  # noqa: E402


# ───────────────────────────── демонстрационные данные ─────────────────────────────
DEMO_FILES = {
    'Договор.txt': 'Договор поставки\n\nг. Москва, 2026 г.\n' * 40,
    'Отчёт 2026.pdf': '%PDF-1.4\n% демонстрационный файл\n',
    'Заметки.md': '# Заметки\n\n- проверить макет\n- собрать архив\n' * 20,
    'Скрипт.sh': '#!/bin/sh\necho "Привет"\n',
    'фото.png': 'PNG',
    'песня.mp3': 'MP3',
    'клип.mp4': 'MP4',
}
DEMO_DIRS = ('Документы', 'Фотографии', 'Музыка')


def build_demo():
    if DEMO.exists():
        shutil.rmtree(DEMO, ignore_errors=True)
    DEMO.mkdir(parents=True)
    for name in DEMO_DIRS:
        (DEMO / name).mkdir()
    for name, body in DEMO_FILES.items():
        (DEMO / name).write_text(body, encoding='utf-8')
    # Настоящий архив — чтобы пункты «Распаковать» и свойства архива были живыми.
    with zipfile.ZipFile(DEMO / 'архив.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('README.txt', 'Демонстрационный архив\n')
        z.writestr('Документы/Договор.txt', 'Договор\n')
        z.writestr('Документы/Заметки.md', '# Заметки\n')

    conf = {
        'scheme': 'midnight', 'language': 'ru', 'design': 'classic',
        'last_dir': str(DEMO), 'restore_last_dir': True,
        'view_mode': 'tiles', 'show_thumbs': False, 'tile_icon_size': 64,
        'two_panels': False, 'width': 1100, 'height': 700,
        'favorites': {
            '0': {'path': str(DEMO), 'name': 'Демо-папка'},
            '1': {'path': str(DEMO / 'Документы'), 'name': 'Документы'},
            '2': {'path': str(DEMO / 'Фотографии'), 'name': 'Фотографии'},
        },
    }
    (CONF_DIR / 'config.json').write_text(
        json.dumps(conf, ensure_ascii=False, indent=1), encoding='utf-8')


# ───────────────────────────── экспорт одного виджета ─────────────────────────────
class Exporter:
    def __init__(self):
        self.entries = []       # (relpath, title, category, width, height)
        self.failures = []
        self.unknown = {}
        self.notes = []

    @staticmethod
    def pump(seconds=0.35):
        ctx = GLib.MainContext.default()
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ctx.iteration(False)
            time.sleep(0.01)

    def take(self, widget, relpath, title, category):
        """Сохранить виджет как SVG и запомнить его для оглавления."""
        try:
            self.pump(0.3)
            w = int(widget.get_width())
            h = int(widget.get_height())
            if w < 2 or h < 2:
                nw = widget.measure(Gtk.Orientation.HORIZONTAL, -1)[1]
                nh = widget.measure(Gtk.Orientation.VERTICAL, -1)[1]
                w, h = max(w, int(nw)), max(h, int(nh))
            if w < 2 or h < 2:
                raise RuntimeError('виджет ещё не размечен (%dx%d)' % (w, h))
            paintable = Gtk.WidgetPaintable.new(widget)
            snap = Gtk.Snapshot.new()
            paintable.snapshot(snap, w, h)
            node = snap.to_node()
            conv = GskToSvg()
            svg = conv.render(node, w, h)
            for key, count in conv.unknown.items():
                self.unknown[key] = self.unknown.get(key, 0) + count
            path = OUT / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding='utf-8')
            self.entries.append((relpath, title, category, w, h))
            print('  ✓ %-46s %4d×%-4d %6.1f КБ' %
                  (relpath, w, h, path.stat().st_size / 1024.0))
            return True
        except Exception as exc:  # noqa: BLE001 — один экран не должен валить экспорт
            self.failures.append((relpath, '%s: %s' % (type(exc).__name__, exc)))
            print('  ✗ %-46s %s: %s' % (relpath, type(exc).__name__, exc))
            traceback.print_exc()
            return False


# ───────────────────────────── главное окно ─────────────────────────────
def set_view(win, mode):
    win.conf['view_mode'] = mode
    for p in (win.p1, win.p2):
        p.apply_view()
    win.update_zoom_slider()
    Exporter.pump(0.6)


def export_main(ex, win):
    print('\nГлавное окно')
    win.p1.navigate_fs(str(DEMO))
    ex.pump(1.0)
    ex.take(win, 'main/main-tiles.svg', 'Главное окно — плитки', 'Главное окно')

    set_view(win, 'list')
    ex.take(win, 'main/main-details.svg', 'Главное окно — подробный список', 'Главное окно')

    win.searchbar.set_search_mode(True)
    win.search_entry.set_text('Договор')
    ex.pump(0.6)
    ex.take(win, 'main/main-search.svg', 'Главное окно — поиск', 'Главное окно')
    win.search_entry.set_text('')
    win.searchbar.set_search_mode(False)
    ex.pump(0.4)

    set_view(win, 'tiles')
    win.lookup_action('two-panels').activate(None)
    ex.pump(0.8)
    win.p1.navigate_fs(str(DEMO / 'Документы'))
    win.p2.navigate_fs(str(DEMO))
    ex.pump(0.8)
    ex.take(win, 'main/main-two-panels.svg', 'Главное окно — две панели', 'Главное окно')
    win.lookup_action('two-panels').activate(None)
    win.p1.navigate_fs(str(DEMO))
    ex.pump(0.6)


def export_other_designs(ex, app):
    """Ещё два макета главного окна: двухпанельный и с боковой панелью."""
    for design, slug, title in (
            ('dual', 'dual', 'Главное окно — двухпанельный дизайн'),
            ('nav', 'nav', 'Главное окно — навигация с боковой панелью')):
        print('\nДизайн «%s»' % title)
        try:
            app.conf['design'] = design
            app.rebuild()
            ex.pump(2.0)
            win = app.win
            win.p1.navigate_fs(str(DEMO))
            ex.pump(1.2)
            if design == 'dual':
                win.p2.navigate_fs(str(DEMO / 'Фотографии'))
                ex.pump(0.8)
            ex.take(win, 'main/main-%s.svg' % slug, title, 'Главное окно')
            if design == 'nav' and getattr(win, 'sidebar', None) is not None:
                side = win.sidebar
                side._group_menu(side.groups[1], side)
                ex.pump(0.6)
                if side._group_popup is not None:
                    ex.take(side._group_popup, 'menus/sidebar-group-menu.svg',
                            'Меню группы боковой панели', 'Меню')
                    side._group_popup.popdown()
                    ex.pump(0.25)
        except Exception as exc:  # noqa: BLE001
            ex.failures.append(('main/main-%s.svg' % slug,
                                '%s: %s' % (type(exc).__name__, exc)))
            print('  ✗ дизайн %s: %s' % (design, exc))
            traceback.print_exc()


# ───────────────────────────── меню ─────────────────────────────
def _menu_row(win, label, level=0):
    """Найти строку открытого меню по подписи; вернуть (button, entry)."""
    if len(win.menus.levels) <= level:
        return None, None
    for b, e in win.menus.levels[level]['rows']:
        if e.get('submenu') is not None and e.get('label') == label:
            return b, e
    return None, None


def open_sub(win, label, level=0):
    b, e = _menu_row(win, label, level)
    if e is not None:
        before = len(win.menus.levels)
        win.menus._open_sub(e, b, level)
        Exporter.pump(0.35)
        return len(win.menus.levels) > before
    return False


MENUBAR = [('file', 'Файл'), ('edit', 'Правка'), ('view', 'Просмотр'),
           ('favorites', 'Избранное'), ('tools', 'Сервис'), ('help', 'Справка')]


def export_menus(ex, win):
    print('\nМеню')
    subs = {
        'file': [(_('Checksum'), 'checksum')],
        'view': [(_('Columns'), 'columns'), (_('Sort by'), 'sort')],
        'favorites': [(_('Add folder to Favorites as'), 'add-as'),
                      (_('Remove from Favorites'), 'remove'),
                      (_('Rename favorite'), 'rename')],
    }
    for i, (slug, title) in enumerate(MENUBAR):
        win.menubar.open_index(i)
        ex.pump(0.35)
        ex.take(win, 'menus/menubar-%s.svg' % slug,
                'Меню «%s»' % title, 'Меню')
        for label, sub_slug in subs.get(slug, ()):
            if open_sub(win, label):
                ex.take(win, 'menus/menubar-%s-%s.svg' % (slug, sub_slug),
                        'Меню «%s» → «%s»' % (title, label), 'Меню')
                win.menus._remove_levels(1)
    win.menus.close()
    ex.pump(0.3)

    # ── контекстное меню панели ──
    p = win.p1
    p.select_all()
    ex.pump(0.5)
    win.open_context_menu(p, p.grid, 330, 250)
    ex.pump(0.45)
    ex.take(win, 'menus/context-selection.svg',
            'Контекстное меню — несколько файлов', 'Меню')
    for label, slug in ((_('Convert to'), 'convert-to'), (_('Checksum'), 'checksum'),
                        (_('Create document'), 'new-document')):
        if open_sub(win, label):
            ex.take(win, 'menus/context-%s.svg' % slug,
                    'Контекстное меню → «%s»' % label, 'Меню')
            win.menus._remove_levels(1)
    win.menus.close()
    p.unselect_all()
    ex.pump(0.3)

    # ── прочие меню ──
    win.open_panel_menu(p, p.btn_panels)
    ex.pump(0.4)
    ex.take(win, 'menus/panel-menu.svg', 'Меню панели', 'Меню')
    win.menus.close()

    win.open_columns_menu(p.btn_panels)
    ex.pump(0.4)
    ex.take(win, 'menus/columns-menu.svg', 'Меню колонок', 'Меню')
    win.menus.close()

    p.navigate_fs(str(DEMO / 'Документы'))
    ex.pump(0.7)
    p.navigate_fs(str(DEMO))
    ex.pump(0.7)
    win.open_history_menu(p)
    ex.pump(0.4)
    ex.take(win, 'menus/history-menu.svg', 'История папок', 'Меню')
    win.menus.close()

    pop = win.open_top_panels_menu(p.btn_panels)
    ex.pump(0.6)
    ex.take(pop, 'menus/top-panels-popover.svg', 'Поповер «Панели»', 'Меню')
    pop.popdown()
    ex.pump(0.3)


# ───────────────────────────── настройки ─────────────────────────────
SETTINGS_PAGES = [
    ('general', 'Общие'), ('favorites', 'Избранное'), ('appearance', 'Оформление'),
    ('display', 'Отображение'), ('language', 'Язык'), ('hotkeys', 'Горячие клавиши'),
]


def export_settings(ex, win):
    print('\nНастройки')
    for i, (slug, title) in enumerate(SETTINGS_PAGES):
        d = SettingsDialog(win, win.conf, lambda *a: None, page=i)
        d.present()
        ex.pump(0.7)
        ex.take(d, 'settings/settings-%d-%s.svg' % (i + 1, slug),
                'Настройки — %s' % title, 'Настройки')
        d.destroy()
        ex.pump(0.25)


def _find_popover(widget):
    """Найти всплывающую панель, привязанную к виджету (Gtk.Popover)."""
    child = widget.get_first_child()
    while child is not None:
        if isinstance(child, Gtk.Popover):
            return child
        found = _find_popover(child)
        if found is not None:
            return found
        child = child.get_next_sibling()
    return None


def export_settings_popovers(ex, win):
    """Меню внутри страниц настроек: порядок записей избранного."""
    print('\nМеню настроек')
    d = SettingsDialog(win, win.conf, lambda *a: None, page=1)
    d.present()
    ex.pump(0.8)
    if d.fav_rows:
        btn = d.fav_rows[0]['sort']
        d._fav_sort_menu(btn, 0)
        ex.pump(0.5)
        pop = _find_popover(btn)
        if pop is not None:
            ex.take(pop, 'menus/favorites-order.svg',
                    'Избранное — порядок записи', 'Меню')
            pop.popdown()
            ex.pump(0.25)
    d.destroy()
    ex.pump(0.25)


# ───────────────────────────── диалоги ─────────────────────────────
def _present(ex, dialog, relpath, title, category='Диалоги', delay=0.7):
    dialog.present()
    ex.pump(delay)
    ex.take(dialog, relpath, title, category)
    dialog.destroy()
    ex.pump(0.25)


def export_dialogs(ex, win, sz):
    print('\nДиалоги')
    from szgtk.archive_dialogs import AddDialog, ExtractDialog, SplitDialog
    from szgtk.benchmark import BenchmarkDialog
    from szgtk.convert import ConverterDialog
    from szgtk.dialogs import (ConfirmDialog, HistoryDialog, OpenWithDialog,
                               PasswordDialog, ProgressDialog, PromptDialog,
                               text_dialog)
    from szgtk.properties import PropertiesDialog
    from szgtk.settings import KeyCaptureDialog
    from szgtk.backend import Job

    add = AddDialog(win, str(DEMO / 'Архив.7z'), lambda *a: None)
    _present(ex, add, 'dialogs/add-archive.svg', 'Добавить в архив')

    extract = ExtractDialog(win, _('Extract'), str(DEMO / 'Извлечь'),
                            lambda *a: None)
    _present(ex, extract, 'dialogs/extract.svg', 'Извлечь файлы')

    split = SplitDialog(win, str(DEMO / 'Отчёт 2026.pdf'), lambda *a: None)
    _present(ex, split, 'dialogs/split.svg', 'Разбить файл')

    bench = BenchmarkDialog(win, sz)
    _present(ex, bench, 'dialogs/benchmark.svg', 'Тест производительности')

    conv = ConverterDialog(win, [str(DEMO / 'фото.png'), str(DEMO / 'песня.mp3'),
                                 str(DEMO / 'клип.mp4')])
    _present(ex, conv, 'dialogs/converter.svg', 'Конвертер')

    props = PropertiesDialog(win, paths=[str(DEMO / 'Договор.txt')])
    props.present()
    ex.pump(0.9)
    ex.take(props, 'dialogs/properties-file-main.svg',
            'Свойства файла — Основное', 'Диалоги')
    for idx, slug, title in ((1, 'permissions', 'Права'),
                             (2, 'metadata', 'Метаданные')):
        if idx < len(props.tab_buttons):
            props.tab_buttons[idx].set_active(True)
            ex.pump(0.5)
            ex.take(props, 'dialogs/properties-file-%s.svg' % slug,
                    'Свойства файла — %s' % title, 'Диалоги')
    props.destroy()
    ex.pump(0.25)

    props_a = PropertiesDialog(win, paths=[str(DEMO / 'архив.zip')])
    _present(ex, props_a, 'dialogs/properties-archive.svg',
             'Свойства архива', delay=1.0)

    props_d = PropertiesDialog(win, paths=[str(DEMO / 'Документы')])
    _present(ex, props_d, 'dialogs/properties-folder.svg', 'Свойства папки')

    job = Job()
    job.text = 'Копирование «Документы»'
    job.subtitle = 'Копирование в «Фотографии»'
    job.fraction = 0.42
    job.bytes_done = 48 * 1024 * 1024
    job.bytes_total = 114 * 1024 * 1024
    job.files_done = 12
    job.files_total = 28
    job.files_label = 'Договор.txt'
    job.pausable = True
    job.icon = 'folder-copy-symbolic'
    job.action = 'copy'
    prog = ProgressDialog(win, _('Copy'), job)
    prog.present()
    ex.pump(1.0)
    ex.take(prog, 'dialogs/progress-copy.svg', 'Прогресс — копирование', 'Диалоги')
    prog.destroy()
    ex.pump(0.25)

    pw = PasswordDialog(win, 'архив.zip', lambda *a: None)
    _present(ex, pw, 'dialogs/password.svg', 'Ввод пароля')

    prompt = PromptDialog(win, _('Rename'), _('New name:'), 'Договор.txt',
                          _('Rename'), lambda *a: None)
    _present(ex, prompt, 'dialogs/prompt-rename.svg', 'Переименование')

    confirm = ConfirmDialog(win, _('Confirm'), 'Удалить 3 объекта?',
                            _('Delete'), lambda *a: None,
                            detail='Файлы будут перемещены в корзину.')
    _present(ex, confirm, 'dialogs/confirm-delete.svg', 'Подтверждение удаления')

    hist = HistoryDialog(win, [str(DEMO / n) for n in DEMO_DIRS] + [str(DEMO)],
                         lambda *a: None)
    _present(ex, hist, 'dialogs/history.svg', 'История папок')

    ow = OpenWithDialog(win, str(DEMO / 'фото.png'))
    # Список всех установленных программ не нужен для макета: в окно видно
    # около десяти строк, а сотня скрытых иконок раздувает SVG на мегабайты.
    ow.apps = ow.apps[:12]
    ow._reload()
    _present(ex, ow, 'dialogs/open-with.svg', 'Открыть с помощью…', delay=1.2)

    kc = KeyCaptureDialog(win, _('Rename'), 'global', lambda *a: None)
    _present(ex, kc, 'dialogs/key-capture.svg', 'Запись сочетания клавиш')

    txt = text_dialog(win, _('Checksum') + ' SHA-256',
                      'a1b2c3d4e5f6…  Договор.txt\n'
                      '9f8e7d6c5b4a…  Отчёт 2026.pdf\n\n'
                      'Проверено файлов: 2\nОшибок: 0\n', 560, 300)
    ex.pump(0.6)
    ex.take(txt, 'dialogs/text-checksum.svg', 'Результат проверки контрольных сумм',
            'Диалоги')
    txt.destroy()
    ex.pump(0.25)

    about = Gtk.AboutDialog(transient_for=win, modal=True)
    about.set_program_name(APP_NAME)
    about.set_version(VERSION)
    about.set_logo_icon_name(REAL_APP_ID)
    about.set_comments(_('Two-panel GTK4 file manager and archiver') + '\n7-Zip 26.00')
    about.set_website('https://github.com/MemTim/archive-navigator')
    about.set_website_label(_('Project page on GitHub'))
    about.set_license_type(Gtk.License.CUSTOM)
    about.set_license('PolyForm Noncommercial License 1.0.0\n'
                      'https://polyformproject.org/licenses/noncommercial/1.0.0')
    _present(ex, about, 'dialogs/about.svg', 'О программе')

    # Системный AlertDialog: GTK рисует его отдельным окном MessageDialog.
    alert = Gtk.AlertDialog()
    alert.set_message('Удалить 3 объекта?')
    alert.set_detail('Файлы будут перемещены в корзину. Это действие нельзя отменить.')
    alert.set_buttons([_('Cancel'), _('Delete')])
    alert.set_cancel_button(0)
    alert.set_default_button(1)
    alert.show(win)
    ex.pump(0.9)
    for w in Gtk.Window.list_toplevels():
        if type(w).__name__ == 'MessageDialog':
            ex.take(w, 'dialogs/alert.svg', 'Системное предупреждение', 'Диалоги')
            w.destroy()
            break
    ex.pump(0.25)


# ───────────────────────────── оглавление ─────────────────────────────
CATEGORY_ORDER = ['Главное окно', 'Меню', 'Настройки', 'Диалоги']
CARD_W, CARD_H, GAP, PAD = 380, 300, 22, 40
HEADER, TITLE_H, COLS = 120, 56, 3


def write_index(ex, failures):
    print('\nОглавление')
    rows = (len(ex.entries) + COLS - 1) // COLS
    width = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP
    height = HEADER + rows * (CARD_H + TITLE_H + GAP) + PAD
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'width="%d" height="%d" viewBox="0 0 %d %d">' % (width, height, width, height),
        '<defs><style>'
        'text{font-family:"Adwaita Sans","Noto Sans",sans-serif}'
        '.h{font-size:30px;font-weight:700;fill:#f0edfa}'
        '.s{font-size:15px;fill:#9a93b5}'
        '.c{font-size:17px;font-weight:600;fill:#d8d2ee}'
        '.n{font-size:12px;fill:#7f7899}'
        '.b{fill:#1c1830;stroke:#3a3358;stroke-width:1}'
        '</style></defs>',
        '<rect width="%d" height="%d" fill="#121020"/>' % (width, height),
    ]
    parts.append('<text class="h" x="%d" y="58">sevenzip-gtk — экспорт интерфейса</text>' % PAD)
    parts.append('<text class="s" x="%d" y="88">Векторные макеты окон, страниц настроек и меню. '
                 'Правка SVG не меняет приложение.</text>' % PAD)
    sections = {}
    for e in ex.entries:
        sections.setdefault(e[2], []).append(e)

    n = 0
    for cat in CATEGORY_ORDER:
        items = sections.get(cat)
        if not items:
            continue
        for rel, title, _cat, w, h in items:
            row, col = divmod(n, COLS)
            x = PAD + col * (CARD_W + GAP)
            y = HEADER + row * (CARD_H + TITLE_H + GAP)
            scale = min((CARD_W - 12) / max(w, 1), (CARD_H - 12) / max(h, 1), 1.0)
            tw, th = w * scale, h * scale
            ox = x + (CARD_W - tw) / 2.0
            oy = y + (CARD_H - th) / 2.0
            parts.append('<a xlink:href="%s">' % rel)
            parts.append('<rect class="b" x="%d" y="%d" width="%d" height="%d" rx="12"/>'
                         % (x, y, CARD_W, CARD_H))
            parts.append('<image x="%s" y="%s" width="%s" height="%s" '
                         'preserveAspectRatio="xMidYMid meet" xlink:href="%s"/>'
                         % ('%.1f' % ox, '%.1f' % oy, '%.1f' % tw, '%.1f' % th, rel))
            parts.append('<rect x="%d" y="%d" width="%d" height="1" fill="#3a3358"/>'
                         % (x, y + CARD_H, CARD_W))
            parts.append('<text class="c" x="%d" y="%d">%s</text>'
                         % (x + 4, y + CARD_H + 26, _xml(title)))
            parts.append('<text class="n" x="%d" y="%d">%s · %s · %d×%d</text>'
                         % (x + 4, y + CARD_H + 46, _xml(_cat), _xml(rel), w, h))
            parts.append('</a>')
            n += 1

    if failures:
        y = HEADER + rows * (CARD_H + TITLE_H + GAP)
        parts.append('<text class="n" x="%d" y="%d">Не удалось экспортировать: %s</text>'
                     % (PAD, y, _xml(', '.join(r for r, _e in failures))))
    parts.append('</svg>')
    (OUT / 'index.svg').write_text('\n'.join(parts), encoding='utf-8')
    print('  ✓ index.svg (%d экранов, %.1f КБ)' %
          (len(ex.entries), (OUT / 'index.svg').stat().st_size / 1024.0))


def write_html(ex):
    """Та же галерея в HTML: браузеры надёжнее показывают внешние SVG."""
    by_cat = {}
    for entry in ex.entries:
        by_cat.setdefault(entry[2], []).append(entry)
    cards = []
    for cat in CATEGORY_ORDER:
        items = by_cat.get(cat)
        if not items:
            continue
        cards.append('<h2>%s</h2><div class="grid">' % _xml(cat))
        for rel, title, _cat, w, h in items:
            cards.append(
                '<a class="card" href="%s"><img loading="lazy" src="%s" alt="%s">'
                '<div class="t">%s</div><div class="n">%s · %d×%d</div></a>'
                % (_xml(rel), _xml(rel), _xml(title), _xml(title),
                   _xml(rel), w, h))
        cards.append('</div>')
    html = """<!doctype html>
<html lang="ru"><meta charset="utf-8">
<title>sevenzip-gtk — макеты интерфейса</title>
<style>
:root{color-scheme:dark}
body{margin:0;padding:34px 40px 60px;background:#121020;color:#f0edfa;
  font:15px/1.45 "Adwaita Sans","Noto Sans",sans-serif}
h1{margin:0 0 4px;font-size:30px}
.lead{color:#9a93b5;margin:0 0 30px;max-width:900px}
.danger{color:#e8c56a}
h2{margin:34px 0 14px;font-size:18px;color:#d8d2ee}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:22px}
.card{display:block;background:#1c1830;border:1px solid #3a3358;border-radius:12px;
  padding:14px;text-decoration:none;color:inherit}
.card:hover{border-color:#8b7dd8;background:#241f3d}
.card img{display:block;width:100%;height:230px;object-fit:contain;background:#0e0c1a;
  border-radius:7px}
.t{margin-top:10px;font-weight:600;font-size:16px}
.n{margin-top:2px;color:#7f7899;font-size:12px;word-break:break-all}
</style>
<h1>sevenzip-gtk — экспорт интерфейса</h1>
<p class="lead">Векторные макеты окон, страниц настроек и меню.
<span class="danger">Правка SVG не меняет приложение</span> — это снимки текущего
оформления для обсуждения и перерисовки. Перегенерация:
<code>tools/export-design.sh</code>.</p>
__CARDS__
</html>
""".replace('__CARDS__', '\n'.join(cards))
    (OUT / 'index.html').write_text(html, encoding='utf-8')
    print('  ✓ index.html')


def _xml(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def write_readme(ex):
    by_cat = {}
    for rel, title, cat, w, h in ex.entries:
        by_cat.setdefault(cat, []).append((rel, title))
    lines = [
        '# Макеты интерфейса (SVG)',
        '',
        'Каждое окно, страница настроек и меню приложения выгружены в отдельный',
        'редактируемый SVG. Начните с [`index.svg`](index.svg) — там все экраны',
        'сеткой, с ссылками на файлы. Для браузера есть та же галерея в',
        '[`index.html`](index.html).',
        '',
        'SVG содержат настоящие векторные фигуры, градиенты, значки и текст',
        '(не скриншоты). Исключение — миниатюры и растровые изображения: они',
        'встроены как PNG.',
        '',
        '> Правка этих файлов **не меняет приложение**. Это снимки текущего',
        '> оформления для обсуждения и перерисовки макета. После изменения кода',
        '> или темы файлы нужно сгенерировать заново.',
        '',
        '## Как перегенерировать',
        '',
        '```sh',
        'tools/export-design.sh',
        '```',
        '',
        'Скрипт запускает приложение во временном профиле (ваши настройки не',
        'затрагиваются), обходит окна и сохраняет SVG в `docs/design/`.',
        'Нужен X-сервер; на headless-машине используется `xvfb-run`. Для текста',
        'требуется `python3-fonttools` (fontTools).',
        '',
        'Для правки в Inkscape/Figma удобнее открывать отдельные файлы: текст',
        'остаётся текстом, палитра и размеры читаются напрямую.',
        '',
    ]
    for cat in CATEGORY_ORDER:
        items = by_cat.get(cat)
        if not items:
            continue
        lines += ['## %s' % cat, '']
        for rel, title in items:
            lines.append('- [%s](%s)' % (title, rel))
        lines.append('')
    if ex.failures:
        lines += ['## Не удалось экспортировать', '']
        for rel, err in ex.failures:
            lines.append('- `%s` — %s' % (rel, err))
        lines.append('')
    (OUT / 'README.md').write_text('\n'.join(lines), encoding='utf-8')


# ───────────────────────────── запуск ─────────────────────────────
def main():
    build_demo()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    appmod.APP_ID = 'io.sevenzipgtk.DesignExport'
    from szgtk.app import App

    app = App()
    app.register(None)
    app.activate()
    win = app.win
    ex = Exporter()
    ex.pump(2.2)
    win.p1.navigate_fs(str(DEMO))
    ex.pump(1.2)

    export_main(ex, win)
    export_menus(ex, win)
    export_settings(ex, win)
    export_settings_popovers(ex, win)
    export_dialogs(ex, win, app.sz)

    print('\nСветлая схема')
    win.conf['scheme'] = 'light'
    apply_theme(win.conf)
    ex.pump(1.0)
    ex.take(win, 'main/main-tiles-light.svg',
            'Главное окно — светлая схема', 'Главное окно')
    win.conf['scheme'] = 'midnight'
    apply_theme(win.conf)
    ex.pump(0.5)

    export_other_designs(ex, app)

    write_index(ex, ex.failures)
    write_html(ex)
    write_readme(ex)

    print('\nГотово: %d экранов' % len(ex.entries))
    if ex.unknown:
        print('Пропущенные/неподдержанные узлы GSK:')
        for k, v in sorted(ex.unknown.items()):
            print('  %s ×%d' % (k, v))
    if ex.failures:
        print('Ошибки:')
        for rel, err in ex.failures:
            print('  %s: %s' % (rel, err))
    app.quit()
    return 0 if not ex.failures else 1


if __name__ == '__main__':
    sys.exit(main())
