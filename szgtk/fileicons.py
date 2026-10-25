# -*- coding: utf-8 -*-
"""Иконки файлов .desktop и .exe.

.desktop — берём значение Icon= (имя темы или путь к картинке).
.exe     — разбираем PE-ресурсы RT_GROUP_ICON/RT_ICON и собираем ICO,
           который умеет читать GdkPixbuf. Внешние утилиты не нужны.
"""
from .imports import *  # noqa: F401,F403
import hashlib
import mmap
import struct

_DESKTOP_CACHE = {}
_EXE_CACHE = {}
_CACHE_VER = 1
_ICON_FILE_EXTS = ('.png', '.svg', '.svgz', '.xpm', '.ico')


def icon_for_file(path, name=None):
    """GIcon для .desktop/.exe или None, если файл не особый/не удалось."""
    if not path:
        return None
    ext = os.path.splitext(name or path)[1].lower()
    if ext == '.desktop':
        return _desktop_icon(path)
    if ext == '.exe':
        return _exe_icon(path)
    return None


def _file_key(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    return (os.path.abspath(path), st.st_mtime_ns, st.st_size)


# ───────────────────────────── .desktop ─────────────────────────────
def _desktop_icon(path):
    key = _file_key(path)
    if key is None:
        return None
    if key in _DESKTOP_CACHE:
        return _DESKTOP_CACHE[key]
    value = _desktop_icon_value(path)
    ic = _resolve_icon_value(path, value) if value else None
    _DESKTOP_CACHE[key] = ic
    return ic


def _desktop_icon_value(path):
    """Достаём Icon= из секции [Desktop Entry], не доверяя синтаксису файла."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            data = f.read(1024 * 1024)
    except OSError:
        return ''
    section = ''
    for line in data.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('[') and s.endswith(']'):
            section = s[1:-1].strip()
            continue
        if section != 'Desktop Entry':
            continue
        key, sep, value = s.partition('=')
        if not sep or key.strip() != 'Icon':
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        # В .desktop-файлах строки допускают \s, \n, \t, \\.
        value = (value.replace('\\s', ' ').replace('\\t', '\t')
                 .replace('\\n', '\n').replace('\\\\', '\\'))
        return value
    return ''


def _resolve_icon_value(desktop_path, value):
    if not value:
        return None
    value = os.path.expanduser(value)
    base = os.path.dirname(os.path.abspath(desktop_path))
    candidates = []
    if os.path.isabs(value):
        candidates.append(value)
    elif os.sep in value or (os.altsep and os.altsep in value):
        candidates.append(os.path.join(base, value))
    elif os.path.splitext(value)[1].lower() in _ICON_FILE_EXTS:
        # Некоторые файлы ссылаются на картинку рядом с .desktop.
        candidates.append(os.path.join(base, value))
    for cand in candidates:
        try:
            if os.path.isfile(cand) and os.access(cand, os.R_OK) and os.path.getsize(cand) <= 20 * 1024 * 1024:
                return Gio.FileIcon.new(Gio.File.new_for_path(cand))
        except OSError:
            continue
    if candidates:
        # Это был путь, но файла нет — не подменяем его темой.
        return None
    return _themed_icon(value)


def _themed_icon(name):
    try:
        display = Gdk.Display.get_default()
        if display is None:
            return None
        theme = Gtk.IconTheme.get_for_display(display)
        if theme is not None and theme.has_icon(name):
            return Gio.ThemedIcon.new(name)
    except Exception:
        pass
    return None


# ───────────────────────────── .exe (PE) ─────────────────────────────
def _exe_icon(path):
    key = _file_key(path)
    if key is None:
        return None
    if key in _EXE_CACHE:
        return _EXE_CACHE[key]
    cache_dir, cache_path = _ico_cache_paths(key)
    if cache_path and os.path.isfile(cache_path) and os.path.getsize(cache_path) > 0:
        ic = Gio.FileIcon.new(Gio.File.new_for_path(cache_path))
        _EXE_CACHE[key] = ic
        return ic
    ico = _extract_ico(path)
    if not ico or not _ico_ok(ico):
        _EXE_CACHE[key] = None
        return None
    if cache_path and _write_cache(cache_dir, cache_path, ico):
        ic = Gio.FileIcon.new(Gio.File.new_for_path(cache_path))
    else:
        ic = None
    _EXE_CACHE[key] = ic
    return ic


def _ico_cache_paths(key):
    base = GLib.get_user_cache_dir() or tempfile.gettempdir()
    cache_dir = os.path.join(base, 'sevenzip-gtk', 'exe-icons')
    digest = hashlib.sha1(('v%d|%s|%d|%d' % (_CACHE_VER, key[0], key[1], key[2]))
                          .encode('utf-8', 'replace')).hexdigest()
    return cache_dir, os.path.join(cache_dir, digest + '.ico')


def _write_cache(cache_dir, cache_path, data):
    tmp = None
    try:
        os.makedirs(cache_dir, mode=0o700, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.tmp-', suffix='.ico', dir=cache_dir)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.chmod(tmp, 0o600)
        os.replace(tmp, cache_path)
        tmp = None
        return True
    except OSError:
        return False
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _ico_ok(data):
    if GdkPixbuf is None:
        return True
    try:
        stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(data))
        pb = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
        return pb is not None and pb.get_width() > 0 and pb.get_height() > 0
    except Exception:
        return False


def _u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def _u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def _rva_to_off(sections, rva):
    for va, vsize, rawsize, rawptr in sections:
        span = max(vsize, rawsize)
        if va <= rva < va + span:
            delta = rva - va
            if delta < rawsize:
                return rawptr + delta
    return None


def _parse_group(data):
    if len(data) < 6:
        return []
    _reserved, typ, count = struct.unpack_from('<HHH', data, 0)
    if typ != 1 or count <= 0 or count > 256:
        return []
    out = []
    for i in range(count):
        off = 6 + i * 14
        if off + 14 > len(data):
            break
        w, h, _colors, _res, planes, bpp, size, rid = struct.unpack_from(
            '<BBBBHHIH', data, off)
        out.append({'w': w or 256, 'h': h or 256, 'planes': planes,
                    'bpp': bpp, 'size': size, 'rid': rid})
    return out


def _extract_ico(path):
    """Собираем ICO из первого подходящего RT_GROUP_ICON PE-файла."""
    try:
        with open(path, 'rb') as f:
            if os.fstat(f.fileno()).st_size < 0x40:
                return None
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                return _extract_ico_mm(mm)
            finally:
                mm.close()
    except (OSError, ValueError, struct.error):
        return None


def _extract_ico_mm(mm):
    if mm[:2] != b'MZ':
        return None
    pe = _u32(mm, 0x3c)
    if pe + 24 > len(mm) or mm[pe:pe + 4] != b'PE\0\0':
        return None
    coff = pe + 4
    nsec = _u16(mm, coff + 2)
    optsize = _u16(mm, coff + 16)
    opt = coff + 20
    if opt + optsize > len(mm):
        return None
    magic = _u16(mm, opt)
    if magic == 0x10b:
        dd = opt + 96
    elif magic == 0x20b:
        dd = opt + 112
    else:
        return None
    if dd + 16 > len(mm):
        return None
    res_rva = _u32(mm, dd + 16)
    res_size = _u32(mm, dd + 20)
    if not res_rva or not res_size:
        return None
    sec = opt + optsize
    sections = []
    for i in range(nsec):
        so = sec + i * 40
        if so + 40 > len(mm):
            return None
        vsize = _u32(mm, so + 8)
        va = _u32(mm, so + 12)
        rawsize = _u32(mm, so + 16)
        rawptr = _u32(mm, so + 20)
        sections.append((va, vsize, rawsize, rawptr))

    icons, groups = {}, []
    _seen_dirs = set()

    def walk(rva, path):
        if len(path) > 8:
            return
        off = _rva_to_off(sections, rva)
        if off is None:
            return
        if off in _seen_dirs:
            return
        _seen_dirs.add(off)
        if off is None or off + 16 > len(mm):
            return
        n_named = _u16(mm, off + 12)
        n_id = _u16(mm, off + 14)
        total = n_named + n_id
        if total > 4096:
            return
        for i in range(total):
            eo = off + 16 + i * 8
            if eo + 8 > len(mm):
                return
            name = _u32(mm, eo)
            data = _u32(mm, eo + 4)
            ident = None if name & 0x80000000 else name
            if data & 0x80000000:
                # Смещения в ресурсном дереве считаются от его начала.
                walk(res_rva + (data & 0x7fffffff), path + [ident])
                continue
            de = _rva_to_off(sections, res_rva + data)
            if de is None or de + 16 > len(mm):
                continue
            data_rva = _u32(mm, de)
            data_size = _u32(mm, de + 4)
            doff = _rva_to_off(sections, data_rva)
            if doff is None or data_size <= 0 or data_size > 16 * 1024 * 1024:
                continue
            if doff + data_size > len(mm):
                continue
            p = path + [ident]
            if len(p) >= 2:
                typ, rid = p[0], p[1]
                if typ == 3 and rid is not None:
                    icons.setdefault(rid, mm[doff:doff + data_size])
                elif typ == 14:
                    # Имя группы в PE часто строковое (не числовой id).
                    groups.append(mm[doff:doff + data_size])

    walk(res_rva, [])
    best = None
    for g in groups:
        entries = [e for e in _parse_group(g) if e['rid'] in icons]
        if not entries:
            continue
        score = max(e['w'] * e['h'] for e in entries)
        if best is None or score > best[0]:
            best = (score, entries)
    if best is None:
        return None
    entries = best[1]
    e = max(entries, key=lambda x: (x['w'] * x['h'], x['bpp']))
    data = icons[e['rid']]
    bw = 0 if e['w'] >= 256 else e['w']
    bh = 0 if e['h'] >= 256 else e['h']
    hdr = struct.pack('<HHH', 0, 1, 1)
    ent = struct.pack('<BBBBHHII', bw, bh, 0, 0, e['planes'] or 1,
                      e['bpp'] or 32, len(data), 6 + 16)
    return hdr + ent + data
