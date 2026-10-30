# -*- coding: utf-8 -*-
"""Небольшой слой доступа к файлам: обычные пути и GVfs admin:// URI."""
from .imports import *  # noqa: F401,F403
from urllib.parse import quote, unquote
import stat as _stat

ADMIN = 'admin://'
ATTRS = ','.join((
    'standard::name',
    'standard::type',
    'standard::size',
    'standard::is-symlink',
    'unix::mode',
    'time::modified',
    'standard::content-type',
    'access::can-read',
    'access::can-write',
    'access::can-execute',
))
NOFOLLOW = Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS
FOLLOW = Gio.FileQueryInfoFlags.NONE


def is_admin(path):
    return isinstance(path, str) and path.startswith(ADMIN)


def gfile(path):
    return Gio.File.new_for_uri(path) if is_admin(path) else Gio.File.new_for_path(path)


def display(path):
    if not is_admin(path):
        return path
    try:
        p = Gio.File.new_for_uri(path).get_path()
        if p:
            return p
        rest = (Gio.File.new_for_uri(path).get_uri() or path)[len(ADMIN):]
        if rest.startswith('/'):
            return unquote(rest)
        return unquote('/' + rest.split('/', 1)[1]) if '/' in rest else unquote(rest)
    except Exception:
        return path[len(ADMIN):] or '/'


def uri(path):
    return path if is_admin(path) else Gio.File.new_for_path(path).get_uri()


def admin_uri(path):
    p = os.path.abspath(os.path.expanduser(display(path) if is_admin(path) else path))
    return ADMIN + quote(p, safe='/')


def join(parent, name):
    if is_admin(parent):
        return gfile(parent).get_child(name).get_uri()
    return os.path.join(parent, name)


def basename(path):
    if is_admin(path):
        try:
            return gfile(path).get_basename() or display(path).rstrip('/').rsplit('/', 1)[-1] or '/'
        except Exception:
            return display(path).rstrip('/').rsplit('/', 1)[-1] or '/'
    return os.path.basename(path)


def dirname(path):
    if is_admin(path):
        f = gfile(path)
        p = f.get_parent()
        return p.get_uri() if p is not None else None
    return os.path.dirname(path)


def norm(path):
    return display(path) if is_admin(path) else os.path.normpath(path)


def exists(path):
    try:
        return gfile(path).query_exists(None)
    except GLib.Error:
        return False


def lexists(path):
    return exists(path)


def _info(path, follow=True):
    flags = FOLLOW if follow else NOFOLLOW
    return gfile(path).query_info(ATTRS, flags, None)


class Stat:
    __slots__ = ('st_mode', 'st_size', 'st_mtime', 'is_dir', 'is_link',
                 'can_read', 'can_write', 'can_exec')

    def __init__(self, mode=0, size=0, mtime=0, is_dir=False, is_link=False,
                 can_read=False, can_write=False, can_exec=False):
        self.st_mode, self.st_size, self.st_mtime = mode, size, mtime
        self.is_dir, self.is_link = is_dir, is_link
        self.can_read, self.can_write, self.can_exec = can_read, can_write, can_exec


def stat(path):
    if not is_admin(path):
        return os.stat(path)
    i = _info(path, follow=True)
    typ = i.get_file_type()
    link = False
    try:
        link = i.get_is_symlink() or _info(path, follow=False).get_file_type() == Gio.FileType.SYMBOLIC_LINK
    except GLib.Error:
        pass
    return Stat(i.get_attribute_uint32('unix::mode'), i.get_size(),
                int(i.get_attribute_uint64('time::modified')), typ == Gio.FileType.DIRECTORY,
                link, i.get_attribute_boolean('access::can-read'),
                i.get_attribute_boolean('access::can-write'),
                i.get_attribute_boolean('access::can-execute'))


def is_dir(path):
    try:
        if is_admin(path):
            return _info(path, follow=True).get_file_type() == Gio.FileType.DIRECTORY
        return os.path.isdir(path)
    except (OSError, GLib.Error):
        return False


def is_file(path):
    try:
        if is_admin(path):
            return _info(path, follow=True).get_file_type() == Gio.FileType.REGULAR
        return os.path.isfile(path)
    except (OSError, GLib.Error):
        return False


def is_link(path):
    try:
        if is_admin(path):
            return _info(path, follow=False).get_file_type() == Gio.FileType.SYMBOLIC_LINK
        return os.path.islink(path)
    except (OSError, GLib.Error):
        return False


def can_read(path):
    if is_admin(path):
        try:
            return _info(path, follow=True).get_attribute_boolean('access::can-read')
        except GLib.Error:
            return False
    return os.access(path, os.R_OK)


def can_write(path):
    if is_admin(path):
        try:
            return _info(path, follow=True).get_attribute_boolean('access::can-write')
        except GLib.Error:
            return False
    return os.access(path, os.W_OK)


def can_exec(path):
    if is_admin(path):
        try:
            return _info(path, follow=True).get_attribute_boolean('access::can-execute')
        except GLib.Error:
            return False
    return os.access(path, os.X_OK)


def is_program(path):
    """Исполняемый файл, который можно запустить напрямую (ELF или скрипт с shebang)."""
    if is_admin(path) or is_dir(path) or not can_exec(path):
        return False
    name = os.path.basename(path)
    if '.so' in name:                       # разделяемые библиотеки не запускаем
        return False
    try:
        with open(path, 'rb') as f:
            head = f.read(4)
    except OSError:
        return False
    return head[:4] == b'\x7fELF' or head[:2] == b'#!'


class Entry:
    __slots__ = ('name', 'path', 'is_dir', 'is_link', 'size', 'mtime', 'mode',
                 'can_read', 'can_write')

    def __init__(self, name, path, is_dir, is_link, size, mtime, mode, can_read, can_write):
        self.name, self.path, self.is_dir, self.is_link = name, path, is_dir, is_link
        self.size, self.mtime, self.mode = size, mtime, mode
        self.can_read, self.can_write = can_read, can_write


def listdir(path):
    out = []
    if is_admin(path):
        try:
            en = gfile(path).enumerate_children(ATTRS, NOFOLLOW, None)
        except GLib.Error as e:
            raise OSError(e.message)
        try:
            while True:
                i = en.next_file(None)
                if i is None:
                    break
                name = i.get_name()
                child = gfile(path).get_child(name).get_uri()
                typ = i.get_file_type()
                link = typ == Gio.FileType.SYMBOLIC_LINK or i.get_is_symlink()
                src = i
                if link:
                    try:
                        src = _info(child, follow=True)
                        typ = src.get_file_type()
                    except GLib.Error:
                        pass
                isdir = typ == Gio.FileType.DIRECTORY
                out.append(Entry(name, child, isdir, link,
                                 src.get_size() if not isdir else -1,
                                 int(src.get_attribute_uint64('time::modified')),
                                 src.get_attribute_uint32('unix::mode'),
                                 src.get_attribute_boolean('access::can-read'),
                                 src.get_attribute_boolean('access::can-write')))
        finally:
            en.close(None)
        return out
    with os.scandir(path) as it:
        for de in it:
            try:
                st = de.stat()
            except OSError:
                try:
                    st = de.stat(follow_symlinks=False)
                except OSError:
                    continue
            isdir = _stat.S_ISDIR(st.st_mode)
            out.append(Entry(de.name, de.path, isdir, de.is_symlink(),
                             -1 if isdir else st.st_size, int(st.st_mtime), st.st_mode,
                             os.access(de.path, os.R_OK), os.access(de.path, os.W_OK)))
    return out


def mkdir(path):
    try:
        gfile(path).make_directory(None)
        return True
    except GLib.Error:
        return False


def mkdirs(path):
    try:
        gfile(path).make_directory_with_parents(None)
        return True
    except GLib.Error:
        return exists(path) and is_dir(path)


def touch(path):
    try:
        stream = gfile(path).create(Gio.FileCreateFlags.NONE, None)
        stream.close(None)
        return True
    except GLib.Error:
        return False


def _delete_tree(path):
    if is_dir(path) and not is_link(path):
        for e in listdir(path):
            _delete_tree(e.path)
    gfile(path).delete(None)


def remove(path):
    if not is_admin(path):
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return
    _delete_tree(path)


def trash(path):
    if not is_admin(path):
        Gio.File.new_for_path(path).trash(None)
        return
    try:
        gfile(path).trash(None)
    except GLib.Error:
        _delete_tree(path)


def trash_with_path(path):
    """Переместить в корзину и вернуть путь файла в корзине (если удалось узнать)."""
    if is_admin(path):
        trash(path)
        return None
    data_dir = GLib.get_user_data_dir()
    info_dir = os.path.join(data_dir, 'Trash', 'info')
    files_dir = os.path.join(data_dir, 'Trash', 'files')
    try:
        before = set(os.listdir(info_dir))
    except OSError:
        before = set()
    Gio.File.new_for_path(path).trash(None)
    try:
        after = set(os.listdir(info_dir))
    except OSError:
        return None
    new = after - before
    if not new:
        return None
    target = os.path.abspath(display(path))
    for name in new:
        if not name.endswith('.trashinfo'):
            continue
        try:
            with open(os.path.join(info_dir, name), encoding='utf-8', errors='replace') as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        for line in lines:
            if line.startswith('Path='):
                try:
                    original = unquote(line[5:])
                except Exception:
                    original = line[5:]
                if os.path.abspath(original) == target:
                    return os.path.join(files_dir, name[:-len('.trashinfo')])
    name = next((n for n in new if n.endswith('.trashinfo')), None)
    return os.path.join(files_dir, name[:-len('.trashinfo')]) if name else None


def rename(path, new_name):
    if not is_admin(path):
        new = os.path.join(os.path.dirname(path), new_name)
        os.rename(path, new)
        return new
    return gfile(path).set_display_name(new_name, None).get_uri()


def _copy_file(src, dst):
    flags = Gio.FileCopyFlags.OVERWRITE
    if is_link(src):
        flags |= Gio.FileCopyFlags.NOFOLLOW_SYMLINKS
    gfile(src).copy(gfile(dst), flags, None, None)


def copy(src, dst):
    if is_dir(src) and not is_link(src):
        mkdirs(dst)
        for e in listdir(src):
            copy(e.path, join(dst, e.name))
    else:
        _copy_file(src, dst)


def size_of(path):
    """Суммарный размер файла или дерева (символические ссылки не разворачиваются)."""
    try:
        if is_dir(path) and not is_link(path):
            return sum(size_of(e.path) for e in listdir(path))
        return _file_size(path)
    except (OSError, GLib.Error):
        return 0


def _set_progress(ctx):
    job, total = ctx['job'], ctx['total']
    if job is None or not total:
        return
    job.bytes_done = ctx['done']
    job.bytes_total = total
    job.fraction = min(1.0, ctx['done'] / total)
    if ctx['name']:
        job.text = ctx['name']


def _cancelled(ctx):
    job = ctx['job']
    return job is not None and job.cancelled


def _file_size(path):
    try:
        if is_link(path):
            # сама ссылка, а не её цель — ровно столько и «копируется»
            return max(0, _info(path, follow=False).get_size())
        return max(0, stat(path).st_size)
    except (OSError, GLib.Error):
        return 0


def _copy_one(src, dst, ctx):
    if _cancelled(ctx):
        return
    job = ctx['job']
    sfile, dfile = gfile(src), gfile(dst)
    if is_link(src):
        # символическую ссылку копируем как ссылку, а не как содержимое
        sfile.copy(dfile, Gio.FileCopyFlags.OVERWRITE | Gio.FileCopyFlags.NOFOLLOW_SYMLINKS,
                   None, None)
        # size_of() считает размер по цели ссылки — учитываем его же
        ctx['done'] += _file_size(src)
        _set_progress(ctx)
        return
    # Потоковое копирование блоками: даёт настоящий прогресс и позволяет
    # прервать копирование в любой момент (в отличие от g_file_copy, чей
    # колбэк прогресса работает только при запущенном главном цикле).
    src_stream = sfile.read(None)
    out = dfile.replace(None, False, Gio.FileCreateFlags.REPLACE_DESTINATION, None)
    chunk = 4 * 1024 * 1024
    try:
        while True:
            if _cancelled(ctx):
                return
            data = src_stream.read_bytes(chunk, None)
            n = data.get_size()
            if n == 0:
                break
            out.write_bytes(data, None)
            ctx['done'] += n
            _set_progress(ctx)
    finally:
        for stream in (out, src_stream):
            try:
                stream.close(None)
            except Exception:
                pass
    if not _cancelled(ctx):
        try:
            sfile.copy_attributes(dfile, Gio.FileCopyFlags.OVERWRITE, None)
        except GLib.Error:
            pass


def _copy_node(src, dst, ctx):
    if _cancelled(ctx):
        return
    if is_dir(src) and not is_link(src):
        mkdirs(dst)
        for e in listdir(src):
            if _cancelled(ctx):
                return
            _copy_node(e.path, join(dst, e.name), ctx)
    else:
        _copy_one(src, dst, ctx)


def copy_with_progress(src, dst, job=None, total=0, done=0, name=None):
    """Копировать файл/дерево, обновляя прогресс в job и слушая отмену.

    Возвращает новое значение «скопировано байт» — его нужно передать в
    следующий вызов, чтобы прогресс по нескольким элементам был сквозным.
    При отмене (job.cancelled) копирование прекращается.
    """
    ctx = {'job': job, 'total': total, 'done': done, 'name': name}
    _copy_node(src, dst, ctx)
    return ctx['done']


def move(src, dst):
    try:
        gfile(src).move(gfile(dst), Gio.FileCopyFlags.OVERWRITE, None, None)
    except GLib.Error:
        copy(src, dst)
        remove(src)


def unique(path):
    if not exists(path):
        return path
    base = display(path) if is_admin(path) else path
    root, ext = os.path.splitext(base)
    i = 1
    while True:
        cand = '%s (%d)%s' % (root, i, ext)
        uri_cand = ADMIN + quote(cand, safe='/') if is_admin(path) else cand
        if not exists(uri_cand):
            return uri_cand
        i += 1


def copy_to_temp(path):
    """Скопировать файл admin:// во временный каталог. -> (tmpdir, local_path)."""
    tmp = tempfile.mkdtemp(prefix='7zgtk-')
    name = basename(path) or 'file'
    dst = os.path.join(tmp, name)
    try:
        _copy_file(path, Gio.File.new_for_path(dst))
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return tmp, dst


def copy_from_temp(local, path):
    _copy_file(Gio.File.new_for_path(local), path)
