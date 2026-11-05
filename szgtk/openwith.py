# -*- coding: utf-8 -*-
"""Пользовательские команды для «Открыть с помощью…».

Команды хранятся в конфиге, показываются в списке диалога и могут быть
назначены программой по умолчанию для типа файла или расширения.
"""
from .imports import *  # noqa: F401,F403

CUSTOM_KEY = 'open_with_custom'
DEFAULTS_KEY = 'open_with_defaults'


def command_name(command):
    """Короткое имя для команды: имя исполняемого файла."""
    try:
        argv = shlex.split(command)
    except ValueError:
        return command
    if not argv:
        return command
    return os.path.basename(argv[0]) or command


def custom_commands(conf):
    """Нормализованный список пользовательских команд."""
    raw = conf.get(CUSTOM_KEY) or []
    if not isinstance(raw, list):
        return []
    out, seen = [], set()
    for item in raw:
        if isinstance(item, str):
            name, command = '', item
        elif isinstance(item, dict):
            name = str(item.get('name') or '').strip()
            command = str(item.get('command') or '').strip()
        else:
            continue
        if not command or command in seen:
            continue
        seen.add(command)
        out.append({'name': name or command_name(command),
                    'command': command})
    return out


def add_custom(conf, name, command):
    """Добавить команду (или обновить её название) и сохранить в конфиг."""
    command = command.strip()
    if not command:
        return False
    items = custom_commands(conf)
    for item in items:
        if item['command'] == command:
            item['name'] = name.strip() or command_name(command)
            break
    else:
        items.append({'name': name.strip() or command_name(command),
                      'command': command})
    conf[CUSTOM_KEY] = items
    return True


def remove_custom(conf, command):
    """Удалить команду и все назначенные ею значения по умолчанию."""
    conf[CUSTOM_KEY] = [item for item in custom_commands(conf)
                        if item['command'] != command]
    defaults = dict(conf.get(DEFAULTS_KEY) or {})
    for key, value in list(defaults.items()):
        if value == command:
            defaults.pop(key, None)
    conf[DEFAULTS_KEY] = defaults


def default_command(conf, path, ctype=None):
    """Команда по умолчанию для файла: тип, расширение, затем «любой файл»."""
    defaults = conf.get(DEFAULTS_KEY) or {}
    if not isinstance(defaults, dict):
        return ''
    if ctype and defaults.get(ctype):
        return str(defaults[ctype])
    ext = os.path.splitext(path)[1].lower()
    if ext and defaults.get(ext):
        return str(defaults[ext])
    return str(defaults.get('*') or '')


def set_default_command(conf, command, path=None, ctype=None):
    """Запомнить команду как программу по умолчанию для этого типа файла."""
    defaults = dict(conf.get(DEFAULTS_KEY) or {})
    if ctype:
        defaults[ctype] = command
    if path:
        ext = os.path.splitext(path)[1].lower()
        if ext:
            defaults[ext] = command
    conf[DEFAULTS_KEY] = defaults


def clear_default(conf, path=None, ctype=None):
    """Снять пользовательское значение по умолчанию для типа/расширения."""
    defaults = dict(conf.get(DEFAULTS_KEY) or {})
    if ctype:
        defaults.pop(ctype, None)
    if path:
        ext = os.path.splitext(path)[1].lower()
        if ext:
            defaults.pop(ext, None)
    conf[DEFAULTS_KEY] = defaults


def command_argv(command, path):
    """Аргументы запуска: %f/%F заменяются путём, иначе путь идёт в конец."""
    parts = shlex.split(command)
    if not parts:
        raise ValueError('empty command')
    argv, replaced = [], False
    for part in parts:
        if '%f' in part or '%F' in part:
            argv.append(part.replace('%f', path).replace('%F', path))
            replaced = True
        else:
            argv.append(part)
    if not replaced:
        argv.append(path)
    return argv


def spawn(command, path):
    """Запустить команду для файла, не дожидаясь её завершения."""
    argv = command_argv(command, path)
    subprocess.Popen(argv, start_new_session=True)
    return argv
