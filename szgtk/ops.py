# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from . import vfs
from . import diagnostics

# ───────────────────────────── вспомогательные функции операций ─────────────────────────────
HASHES = ['CRC32', 'CRC64', 'XXH64', 'MD5', 'SHA1', 'SHA256', 'SHA384', 'SHA512', 'SHA3-256',
          'BLAKE2sp', '*']


def names_for(items):
    out = []
    for i in items:
        out.append(i.full)
        if i.is_dir:
            out.append(i.full + '/*')
    return out


def default_stem(paths):
    if len(paths) == 1:
        n = vfs.basename(paths[0].rstrip('/'))
        return os.path.splitext(n)[0] if vfs.is_file(paths[0]) and os.path.splitext(n)[0] else n
    return vfs.basename(vfs.dirname(paths[0])) or 'archive'


def prepare_add(paths, subdir, pathmode):
    """→ (names, cwd, tmp_to_cleanup). Для вставки в подпапку архива строится дерево симлинков."""
    paths = [os.path.abspath(p) for p in paths]
    if pathmode != 'relative':
        return paths, None, None
    parents = {os.path.dirname(p) for p in paths}
    if not subdir and len(parents) == 1:
        return [os.path.basename(p) for p in paths], parents.pop(), None
    tmp = tempfile.mkdtemp(prefix='7zgtk-add-')
    base = os.path.join(tmp, subdir) if subdir else tmp
    os.makedirs(base, exist_ok=True)
    for p in paths:
        try:
            os.symlink(p, os.path.join(base, os.path.basename(p)))
        except OSError:
            pass
    names = [subdir.split('/')[0]] if subdir else [os.path.basename(p) for p in paths]
    return names, tmp, tmp


def add_thread_limit(level, fmt='7z'):
    """Сколько потоков 7z можно дать, чтобы не улететь в OOM.

    Уровни 7-9 требуют сотни мегабайт на поток; на машине, где уже занята
    память, 7-Zip может выйти за пределы и попасть под OOM-killer вместе
    со всем cgroup приложения. Возвращает None, если ограничение не нужно
    (памяти достаточно) — тогда 7-Zip сам выберет число потоков.
    """
    if fmt != '7z':
        return None
    try:
        level = int(level)
    except (TypeError, ValueError):
        return None
    per_thread = {5: 60, 6: 60, 7: 80, 8: 110, 9: 160}.get(level)
    if per_thread is None:
        return None
    cpu = os.cpu_count() or 1
    if cpu <= 2:
        return None
    avail = diagnostics.available_mb()
    if not avail:
        return None
    limit = max(1, min(cpu, int(avail * 0.4) // per_thread))
    if limit >= cpu:
        return None
    diagnostics.log('мало памяти (%d МБ): потоков 7z %d из %d, уровень %d',
                    avail, limit, cpu, level)
    return limit


def count_conflicts(entries, names, dest, pathmode):
    bases = None if names is None else [n for n in names if not n.endswith('/*')]
    n = 0
    for e in entries:
        if e.is_dir:
            continue
        if bases is not None and not any(e.path == b or e.path.startswith(b + '/') for b in bases):
            continue
        rel = os.path.basename(e.path) if pathmode == 'none' else e.path
        if os.path.lexists(os.path.join(dest, rel)):
            n += 1
    return n


def widget_xy(widget, target, x=0.0, y=0.0):
    """Координаты точки виджета в системе координат target (или None)."""
    try:
        r = widget.translate_coordinates(target, x, y)
    except Exception:
        return None
    return (r[-2], r[-1]) if r else None


def groups_from_model(model):
    """Gio.MenuModel -> список групп (между группами рисуется разделитель)."""
    groups, cur = [], []
    if model is None:
        return groups
    for i in range(model.get_n_items()):
        sec = model.get_item_link(i, 'section')
        if sec is not None:
            if cur:
                groups.append(cur)
                cur = []
            groups.extend(groups_from_model(sec))
            continue
        lab = model.get_item_attribute_value(i, 'label', None)
        act = model.get_item_attribute_value(i, 'action', None)
        tgt = model.get_item_attribute_value(i, 'target', None)
        cur.append(dict(label=(lab.get_string() if lab else '').replace('__', '_'),
                        action=act.get_string() if act else None, target=tgt,
                        submenu=model.get_item_link(i, 'submenu')))
    if cur:
        groups.append(cur)
    return groups
