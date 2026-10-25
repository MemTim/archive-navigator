# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .display import format_date
from .fileicons import icon_for_file

# ───────────────────────────── утилиты ─────────────────────────────
Item = collections.namedtuple('Item', 'name is_dir full size')

ARCH_EXTS = {
    '7z', 'zip', 'rar', 'tar', 'gz', 'tgz', 'bz2', 'tbz', 'tbz2', 'xz', 'txz',
    'lzma', 'cab', 'iso', 'wim', 'swm', 'esd', 'arj', 'z', 'cpio', 'rpm', 'deb',
    'lzh', 'lha', 'squashfs', 'dmg', 'vhd', 'vhdx', '001', 'udf', 'img', 'chm',
    'msi', 'xar', 'ar', 'a',
}
TAR_COMPOUND = re.compile(r'\.(tar\.(gz|bz2|xz|lzma|z)|tgz|tbz|tbz2|txz)$', re.I)


def is_archive_name(name):
    ext = os.path.splitext(name)[1][1:].lower()
    return ext in ARCH_EXTS


def archive_stem(name):
    """x.tar.gz -> x, x.7z -> x"""
    m = TAR_COMPOUND.search(name)
    return name[:m.start()] if m else os.path.splitext(name)[0]


def fmt_num(n):
    return '{:,}'.format(int(n)).replace(',', ' ')


def human(n):
    n = float(n)
    for u in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if n < 1024 or u == 'TiB':
            return '%d B' % n if u == 'B' else '%.1f %s' % (n, u)
        n /= 1024.0


def fmt_time(ts):
    return format_date(ts)


def parse_time(s):
    try:
        return int(time.mktime(time.strptime(s[:19], '%Y-%m-%d %H:%M:%S')))
    except (ValueError, OverflowError):
        return 0

def unique_path(path):
    if not os.path.lexists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = '%s (%d)%s' % (base, i, ext)
        if not os.path.lexists(cand):
            return cand
        i += 1


_icon_cache = {}


def icon_for(name, is_dir, path=None):
    if not is_dir and path and os.path.splitext(name)[1].lower() in ('.desktop', '.exe'):
        ic = icon_for_file(path, name)
        if ic is not None:
            return ic
    key = '/dir' if is_dir else (os.path.splitext(name)[1].lower() or name)
    ic = _icon_cache.get(key)
    if ic is None:
        if is_dir:
            ic = Gio.ThemedIcon.new('folder')
        else:
            ctype = Gio.content_type_guess(name, None)[0]
            ic = Gio.content_type_get_icon(ctype)
        _icon_cache[key] = ic
    return ic


_special_icons = {}


def special_dir_icons():
    """Путь -> значок для домашней папки и стандартных каталогов (Документы, Загрузки, …)."""
    if not _special_icons:
        D = GLib.UserDirectory
        for d, name in ((D.DIRECTORY_DESKTOP, 'user-desktop'), (D.DIRECTORY_DOCUMENTS, 'folder-documents'),
                        (D.DIRECTORY_DOWNLOAD, 'folder-download'), (D.DIRECTORY_MUSIC, 'folder-music'),
                        (D.DIRECTORY_PICTURES, 'folder-pictures'), (D.DIRECTORY_PUBLIC_SHARE, 'folder-publicshare'),
                        (D.DIRECTORY_TEMPLATES, 'folder-templates'), (D.DIRECTORY_VIDEOS, 'folder-videos')):
            p = GLib.get_user_special_dir(d)
            if p:
                _special_icons[os.path.normpath(p)] = Gio.ThemedIcon.new_from_names([name, 'folder'])
        _special_icons[os.path.normpath(os.path.expanduser('~'))] = Gio.ThemedIcon.new_from_names(['user-home', 'folder'])
    return _special_icons


def dir_icon(path):
    return special_dir_icons().get(os.path.normpath(path)) or icon_for('', True)


def esc_label(s):
    return s.replace('_', '__')


def parse_accel(s):
    """'<Alt>Up' -> (keyval, int(mods)) | None"""
    if not s:
        return None
    try:
        res = Gtk.accelerator_parse(s)
    except Exception:
        return None
    ok, keyval, mods = res if len(res) == 3 else (True, res[0], res[1])
    return (keyval, int(mods)) if ok and keyval else None


# Физические клавиши латинской раскладки и соответствующие им клавиши русской
# раскладки (ЙЦУКЕН). Нужны, чтобы сочетания вроде Ctrl+C работали при русской
# раскладке: GTK сравнивает сочетания по keyval, а не по физической клавише.
LATIN_TO_CYRILLIC = {
    Gdk.KEY_q: Gdk.KEY_Cyrillic_shorti, Gdk.KEY_w: Gdk.KEY_Cyrillic_tse,
    Gdk.KEY_e: Gdk.KEY_Cyrillic_u, Gdk.KEY_r: Gdk.KEY_Cyrillic_ka,
    Gdk.KEY_t: Gdk.KEY_Cyrillic_ie, Gdk.KEY_y: Gdk.KEY_Cyrillic_en,
    Gdk.KEY_u: Gdk.KEY_Cyrillic_ghe, Gdk.KEY_i: Gdk.KEY_Cyrillic_sha,
    Gdk.KEY_o: Gdk.KEY_Cyrillic_shcha, Gdk.KEY_p: Gdk.KEY_Cyrillic_ze,
    Gdk.KEY_bracketleft: Gdk.KEY_Cyrillic_ha, Gdk.KEY_bracketright: Gdk.KEY_Cyrillic_hardsign,
    Gdk.KEY_a: Gdk.KEY_Cyrillic_ef, Gdk.KEY_s: Gdk.KEY_Cyrillic_yeru,
    Gdk.KEY_d: Gdk.KEY_Cyrillic_ve, Gdk.KEY_f: Gdk.KEY_Cyrillic_a,
    Gdk.KEY_g: Gdk.KEY_Cyrillic_pe, Gdk.KEY_h: Gdk.KEY_Cyrillic_er,
    Gdk.KEY_j: Gdk.KEY_Cyrillic_o, Gdk.KEY_k: Gdk.KEY_Cyrillic_el,
    Gdk.KEY_l: Gdk.KEY_Cyrillic_de, Gdk.KEY_semicolon: Gdk.KEY_Cyrillic_zhe,
    Gdk.KEY_apostrophe: Gdk.KEY_Cyrillic_e,
    Gdk.KEY_z: Gdk.KEY_Cyrillic_ya, Gdk.KEY_x: Gdk.KEY_Cyrillic_che,
    Gdk.KEY_c: Gdk.KEY_Cyrillic_es, Gdk.KEY_v: Gdk.KEY_Cyrillic_em,
    Gdk.KEY_b: Gdk.KEY_Cyrillic_i, Gdk.KEY_n: Gdk.KEY_Cyrillic_te,
    Gdk.KEY_m: Gdk.KEY_Cyrillic_softsign, Gdk.KEY_comma: Gdk.KEY_Cyrillic_be,
    Gdk.KEY_period: Gdk.KEY_Cyrillic_yu, Gdk.KEY_grave: Gdk.KEY_Cyrillic_io,
}
CYRILLIC_TO_LATIN = {cyr: lat for lat, cyr in LATIN_TO_CYRILLIC.items()}


def cyrillic_keyval(keyval):
    """Латинская клавиша -> клавиша русской раскладки (или None)."""
    return LATIN_TO_CYRILLIC.get(Gdk.keyval_to_lower(keyval))


def latin_keyval(keyval):
    """Клавиша русской раскладки -> латинская клавиша (или None)."""
    return CYRILLIC_TO_LATIN.get(Gdk.keyval_to_lower(keyval))


def accel_variants(acc):
    """Все варианты сочетания: исходный и эквивалент в русской раскладке."""
    p = parse_accel(acc)
    if not p:
        return [acc] if acc else []
    keyval, mods = p
    keyval = Gdk.keyval_to_lower(keyval)
    keys = [keyval]
    alt = LATIN_TO_CYRILLIC.get(keyval) or CYRILLIC_TO_LATIN.get(keyval)
    if alt is not None and alt not in keys:
        keys.append(alt)
    out = []
    for k in keys:
        name = Gtk.accelerator_name(k, Gdk.ModifierType(mods))
        if name and name not in out:
            out.append(name)
    return out or [acc]


# Сочетания редактирования текста, которые GTK не распознаёт при русской
# раскладке. Для них вручную вызываем действия внутреннего Gtk.Text.
_TEXT_ACTIONS = {
    Gdk.KEY_c: 'clipboard.copy',
    Gdk.KEY_x: 'clipboard.cut',
    Gdk.KEY_v: 'clipboard.paste',
    Gdk.KEY_a: 'selection.select-all',
    Gdk.KEY_z: 'text.undo',
    Gdk.KEY_y: 'text.redo',
}


def _text_target(root):
    """Найти текстовый виджет в фокусе (Entry/SpinButton/TextView)."""
    w = root.get_focus()
    while w is not None:
        if isinstance(w, Gtk.TextView):
            return w
        if isinstance(w, Gtk.Text):
            return w
        get_delegate = getattr(w, 'get_delegate', None)
        if get_delegate is not None:
            try:
                d = get_delegate()
            except Exception:
                d = None
            if d is not None:
                return d
        w = w.get_parent()
    return None


def has_text_target(root):
    return _text_target(root) is not None


def handle_text_shortcut(root, keyval, state):
    """Обработать Ctrl+C/X/V/A/Z/Y при русской раскладке. -> bool."""
    mods = state & MODMASK
    if not (mods & Gdk.ModifierType.CONTROL_MASK) or (mods & Gdk.ModifierType.ALT_MASK):
        return False
    latin = latin_keyval(keyval)
    if latin is None:
        return False
    shift = bool(mods & Gdk.ModifierType.SHIFT_MASK)
    if shift and latin == Gdk.KEY_z:
        action = 'text.redo'
    elif shift:
        return False
    else:
        action = _TEXT_ACTIONS.get(latin)
    if action is None:
        return False
    target = _text_target(root)
    if target is None:
        return False
    if isinstance(target, Gtk.TextView):
        buf = target.get_buffer()
        clip = target.get_clipboard()
        editable = target.get_editable()
        try:
            if action == 'clipboard.copy':
                buf.copy_clipboard(clip)
            elif action == 'clipboard.cut':
                if editable:
                    buf.cut_clipboard(clip, True)
            elif action == 'clipboard.paste':
                if editable:
                    buf.paste_clipboard(clip, None, True)
            elif action == 'text.undo':
                if editable:
                    buf.undo()
            elif action == 'text.redo':
                if editable:
                    buf.redo()
            elif action == 'selection.select-all':
                buf.select_range(buf.get_start_iter(), buf.get_end_iter())
        except Exception:
            return False
        return True
    if action == 'selection.select-all':
        try:
            target.select_region(0, -1)
        except Exception:
            return False
        return True
    try:
        return bool(target.activate_action(action, None))
    except Exception:
        return False


def accel_label(s):
    p = parse_accel(s)
    return Gtk.accelerator_get_label(p[0], Gdk.ModifierType(p[1])) if p else ''


def accel_pretty(s):
    lab = accel_label(s)
    for a, b in (('Up', '↑'), ('Down', '↓'), ('Left', '←'), ('Right', '→'), ('Return', 'Enter')):
        if lab == a or lab.endswith('+' + a):
            lab = lab[:len(lab) - len(a)] + b
    return lab
