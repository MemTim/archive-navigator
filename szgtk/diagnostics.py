# -*- coding: utf-8 -*-
"""Журнал работы и перехват аварийных завершений.

Пишет в ``$XDG_STATE_HOME/sevenzip-gtk/sevenzip-gtk.log`` (обычно
``~/.local/state/sevenzip-gtk/sevenzip-gtk.log``):

* ``faulthandler`` — трассировка всех потоков при SIGSEGV/SIGABRT/SIGBUS/SIGFPE;
* необработанные исключения главного потока и фоновых потоков;
* сообщения GLib/GTK уровня WARNING и выше;
* события жизненного цикла: старт, окна, фоновые задания, команды 7-Zip.

Каждая строка сразу сбрасывается на диск, поэтому журнал переживает
аварийное завершение процесса. Файл ограничен по размеру и при
переполнении сдвигается в ``sevenzip-gtk.log.1``.
"""
from __future__ import annotations

import ctypes
import faulthandler
import os
import re
import sys
import tempfile
import threading
import time
import traceback

_LOCK = threading.Lock()
_LOCAL = threading.local()
_PATH = None
_STREAM = None
_FAULT_STREAM = None
_ORIG_HOOKS = {}
_MAX_BYTES = 2 * 1024 * 1024


# ───────────────────────────── путь и запись ─────────────────────────────
def _state_dir():
    base = os.environ.get('SZ_LOG_DIR')
    if not base:
        root = (os.environ.get('XDG_STATE_HOME')
                or os.path.join(os.path.expanduser('~'), '.local', 'state'))
        base = os.path.join(root, 'sevenzip-gtk')
    try:
        os.makedirs(base, exist_ok=True)
        probe = os.path.join(base, '.writable')
        with open(probe, 'a'):
            pass
        os.unlink(probe)
    except OSError:
        base = tempfile.mkdtemp(prefix='sz-log-')
    return base


def log_path():
    """Путь к файлу журнала (или None, если он ещё не открыт)."""
    return _PATH


def _rotate(path):
    try:
        if os.path.getsize(path) > _MAX_BYTES:
            os.replace(path, path + '.1')
    except OSError:
        pass


def _open_streams():
    global _PATH, _STREAM, _FAULT_STREAM
    _PATH = os.path.join(_state_dir(), 'sevenzip-gtk.log')
    _rotate(_PATH)
    try:
        _STREAM = open(_PATH, 'a', encoding='utf-8', errors='replace', buffering=1)
    except OSError:
        _STREAM = None
    # отдельный дескриптор: faulthandler пишет в него напрямую, минуя буферы
    try:
        _FAULT_STREAM = open(_PATH, 'a', encoding='utf-8', errors='replace')
    except OSError:
        _FAULT_STREAM = None


def log(msg, *args):
    """Добавить строку в журнал. Никогда не бросает исключений."""
    if _STREAM is None or getattr(_LOCAL, 'busy', False):
        return
    if args:
        try:
            msg = msg % args
        except Exception:
            msg = '%s %r' % (msg, args)
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    line = '%s [%d] %s\n' % (stamp, os.getpid(), msg)
    _LOCAL.busy = True
    try:
        with _LOCK:
            _STREAM.write(line)
            _STREAM.flush()
    except Exception:
        pass
    finally:
        _LOCAL.busy = False


def log_stack(prefix, limit=14):
    """Записать префикс и текущий стек вызовов."""
    if _STREAM is None:
        return
    try:
        frames = traceback.format_stack(limit=limit)
        text = ''.join(frames[:-1]) if frames else ''
    except Exception:
        text = ''
    log('%s\n%s', prefix, text.rstrip('\n'))


# ───────────────────────────── перехватчики ─────────────────────────────
def _excepthook(exc_type, exc, tb):
    log('НЕОБРАБОТАННОЕ ИСКЛЮЧЕНИЕ (главный поток):\n%s',
        ''.join(traceback.format_exception(exc_type, exc, tb)).rstrip('\n'))
    hook = _ORIG_HOOKS.get('sys')
    if hook is not None:
        hook(exc_type, exc, tb)


def _thread_excepthook(args):
    if args.exc_type is SystemExit:
        return
    name = getattr(args.thread, 'name', '?') if args.thread is not None else '?'
    log('ИСКЛЮЧЕНИЕ В ПОТОКЕ %s:\n%s', name,
        ''.join(traceback.format_exception(args.exc_type, args.exc_value,
                                           args.exc_traceback)).rstrip('\n'))
    hook = _ORIG_HOOKS.get('threading')
    if hook is not None:
        hook(args)


_LEVEL_NAMES = {4: 'ERROR', 8: 'CRITICAL', 16: 'WARNING'}


def _install_glib():
    """Писать в журнал сообщения GLib/GTK уровня WARNING и выше."""
    try:
        from gi.repository import GLib
    except Exception:
        return
    if not hasattr(GLib, 'log_set_writer_func'):
        return
    try:
        # в разных версиях PyGObject перечисление называется по-разному
        out = GLib.LogWriterOutput
        handled = int(getattr(out, 'HANDLED', 1))
        unhandled = int(getattr(out, 'UNHANDLED', 0))
    except Exception:
        return
    flags = GLib.LogLevelFlags
    keep = int(flags.LEVEL_ERROR | flags.LEVEL_CRITICAL | flags.LEVEL_WARNING)
    domains_skip = ('GdkPixbuf',)
    recent = {}
    window = 10.0

    def _text(value):
        if not value:
            return ''
        try:
            return ctypes.string_at(value).decode('utf-8', 'replace')
        except Exception:
            return ''

    def writer(level, fields, n_fields, user):
        # никогда не бросать исключений: GLib вызовет writer повторно и уйдёт
        # в бесконечную рекурсию
        if getattr(_LOCAL, 'busy', False):
            return unhandled
        _LOCAL.busy = True
        try:
            lvl = int(level)
            if not lvl & keep:
                return unhandled
            info = {}
            for f in fields[:n_fields]:
                key = f.key
                if isinstance(key, str):
                    info[key] = _text(f.value)
            domain = info.get('GLIB_DOMAIN', '')
            if domain in domains_skip:
                return unhandled
            message = info.get('MESSAGE', '').rstrip('\n')
            # одинаковые предупреждения (например, про размеры слайдера) не
            # должны заливать журнал — пишем не чаще раза в 10 секунд
            sig = re.sub(r'\d+', '#', domain + '|' + message)
            now = time.monotonic()
            entry = recent.get(sig)
            if entry is not None and now - entry[0] < window:
                entry[1] += 1
                return handled
            repeats = entry[1] if entry is not None else 0
            if len(recent) > 200:
                recent.clear()
            recent[sig] = [now, 0]
            name = _LEVEL_NAMES.get(lvl & 0xFF, str(lvl))
            where = ''
            if info.get('CODE_FILE'):
                where = ' (%s:%s %s)' % (info.get('CODE_FILE'), info.get('CODE_LINE', ''),
                                         info.get('CODE_FUNC', ''))
            if repeats:
                message += ' (повторов: %d)' % repeats
            _LOCAL.busy = False
            log('%s %s: %s%s', name, domain or 'GLib', message, where)
            return handled
        except Exception:
            return unhandled
        finally:
            _LOCAL.busy = False

    try:
        GLib.log_set_writer_func(writer, None)
    except Exception:
        pass


def install():
    """Включить журнал и перехватчики. Вызывается один раз при старте."""
    if _STREAM is not None:
        return _PATH
    _open_streams()
    if _STREAM is None:
        return None
    _ORIG_HOOKS['sys'] = sys.excepthook
    _ORIG_HOOKS['threading'] = getattr(threading, 'excepthook', None)
    sys.excepthook = _excepthook
    if hasattr(threading, 'excepthook'):
        threading.excepthook = _thread_excepthook
    if _FAULT_STREAM is not None:
        try:
            faulthandler.enable(file=_FAULT_STREAM, all_threads=True)
        except Exception:
            pass
    _install_glib()
    log('── запуск ── argv=%r pid=%d', sys.argv, os.getpid())
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gtk
        log('GTK %d.%d.%d', Gtk.get_major_version(), Gtk.get_minor_version(),
            Gtk.get_micro_version())
    except Exception:
        pass
    log('сессия: XDG_SESSION_TYPE=%s WAYLAND_DISPLAY=%s GDK_BACKEND=%s GSK_RENDERER=%s',
        os.environ.get('XDG_SESSION_TYPE'), os.environ.get('WAYLAND_DISPLAY'),
        os.environ.get('GDK_BACKEND'), os.environ.get('GSK_RENDERER'))
    log('память: %s', _meminfo())
    return _PATH


def _meminfo():
    vals = {}
    try:
        with open('/proc/meminfo', encoding='utf-8') as f:
            for line in f:
                k, _, v = line.partition(':')
                if k in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
                    vals[k] = int(v.split()[0]) // 1024
    except Exception:
        return '?'
    return 'MemTotal=%dMB MemAvailable=%dMB SwapTotal=%dMB SwapFree=%dMB' % (
        vals.get('MemTotal', -1), vals.get('MemAvailable', -1),
        vals.get('SwapTotal', -1), vals.get('SwapFree', -1))


def available_mb():
    """Сколько памяти реально доступно системе, МБ (или None)."""
    try:
        with open('/proc/meminfo', encoding='utf-8') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return None


def rss_mb():
    """Память текущего процесса (RSS), МБ."""
    try:
        with open('/proc/self/status', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return None


def note_exit(reason):
    """Записать причину выхода — помогает отличить штатное закрытие от аварии."""
    log('── выход: %s ──', reason)
