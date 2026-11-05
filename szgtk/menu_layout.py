# -*- coding: utf-8 -*-
"""Порядок и видимость пунктов контекстного меню."""
from .i18n import N_
from .openwith import custom_commands

# (id, подпись для настроек, раздел по умолчанию)
MENU_ITEMS = [
    ('open', N_('Open'), 0),
    ('run', N_('Run'), 1),
    ('open-with', N_('Open with…'), 1),
    ('convert', N_('Convert…'), 2),
    ('convert-to', N_('Convert to'), 2),
    ('add', N_('Add to archive…'), 3),
    ('add-7z', N_('Add to .7z'), 3),
    ('add-zip', N_('Add to .zip'), 3),
    ('extract', N_('Extract files…'), 4),
    ('extract-here', N_('Extract here'), 4),
    ('extract-dir', N_('Extract to folder'), 4),
    ('test', N_('Test archive'), 4),
    ('open-inside', N_('Open inside'), 5),
    ('add-files', N_('Add files…'), 5),
    ('rename', N_('Rename'), 6),
    ('copy-selection', N_('Copy'), 6),
    ('cut-selection', N_('Cut'), 6),
    ('paste', N_('Paste'), 6),
    ('copy', N_('Copy to…'), 6),
    ('move', N_('Move to…'), 6),
    ('delete', N_('Delete'), 6),
    ('checksum', N_('Checksum'), 6),
    ('properties', N_('Properties'), 6),
    ('new-folder', N_('Create folder'), 7),
    ('select-all', N_('Select all'), 7),
    ('refresh', N_('Refresh'), 7),
    ('open-as-root', N_('Open as root'), 8),
]

# Ситуации, в которых может показываться пункт меню.
CONTEXTS = [
    ('empty', N_('Empty area')),
    ('folder', N_('Folder')),
    ('archive', N_('Archive')),
    ('audio', N_('Audio file')),
    ('video', N_('Video file')),
    ('image', N_('Image')),
    ('file', N_('Other file')),
    ('multi', N_('Multiple items')),
    ('inside', N_('Inside an archive')),
]
CONTEXT_LABELS = {context_id: label for context_id, label in CONTEXTS}
ALL_CONTEXTS = tuple(context_id for context_id, _label in CONTEXTS)

# Ситуации, в которых пункт появляется сам по себе — до того, как пользователь
# что-то отметил в «Условиях отображения». Совпадают с условиями, по которым
# пункт добавляется в контекстное меню.
_SELECTION = frozenset({'folder', 'archive', 'audio', 'video', 'image', 'file',
                        'multi'})
_SELECTION_OR_INSIDE = _SELECTION | {'inside'}
_FILE_LIKE = frozenset({'archive', 'audio', 'video', 'image', 'file', 'multi'})
_ALL = frozenset(ALL_CONTEXTS)

DEFAULT_CONTEXTS = {
    'open': _SELECTION_OR_INSIDE,
    'run': _FILE_LIKE,
    'open-with': _FILE_LIKE,
    'convert': _FILE_LIKE,
    'convert-to': _FILE_LIKE,
    'add': _SELECTION,
    'add-7z': _SELECTION,
    'add-zip': _SELECTION,
    'extract': frozenset({'archive', 'multi', 'inside'}),
    'extract-here': frozenset({'archive', 'multi'}),
    'extract-dir': frozenset({'archive', 'multi'}),
    'test': frozenset({'archive', 'multi', 'inside'}),
    'open-inside': frozenset({'audio', 'video', 'image', 'file', 'multi'}),
    'add-files': frozenset({'inside'}),
    'rename': _SELECTION_OR_INSIDE,
    'copy-selection': _SELECTION_OR_INSIDE,
    'cut-selection': _SELECTION_OR_INSIDE,
    'paste': _ALL,
    'copy': _SELECTION_OR_INSIDE,
    'move': _SELECTION_OR_INSIDE,
    'delete': _SELECTION_OR_INSIDE,
    'checksum': _SELECTION,
    'properties': _SELECTION_OR_INSIDE,
    'new-folder': _ALL,
    'select-all': _ALL,
    'refresh': _ALL,
    'open-as-root': _SELECTION | {'empty'},
}

LABELS = {item_id: label for item_id, label, _section in MENU_ITEMS}
SECTIONS = {item_id: section for item_id, _label, section in MENU_ITEMS}
DEFAULT_LAYOUT = [(item_id, section) for item_id, _label, section in MENU_ITEMS]

CUSTOM_PREFIX = 'cmd:'
CUSTOM_SECTION = max(SECTIONS.values(), default=0) + 1
_CUSTOM_CONTEXTS = _SELECTION | {'empty'}


def command_id(command):
    """Идентификатор своего пункта меню для команды."""
    return CUSTOM_PREFIX + command


def is_custom(item_id):
    return isinstance(item_id, str) and item_id.startswith(CUSTOM_PREFIX)


def custom_items(conf):
    """Пары (id пункта, подпись) для своих команд из конфига."""
    return [(command_id(item['command']), item['name'])
            for item in custom_commands(conf)]


def item_label(conf, item_id):
    """Подпись пункта меню: встроенного или своего."""
    if is_custom(item_id):
        for cid, name in custom_items(conf):
            if cid == item_id:
                return name
        return item_id[len(CUSTOM_PREFIX):]
    return LABELS.get(item_id, item_id)


def default_contexts(item_id):
    """Ситуации показа пункта по умолчанию (без пользовательских правок)."""
    if is_custom(item_id):
        return set(_CUSTOM_CONTEXTS)
    return set(DEFAULT_CONTEXTS.get(item_id, _ALL))


def normalize(layout):
    """Сделать разделы непрерывными, сохранив порядок их первого появления."""
    order = []
    for _item_id, section in layout:
        if section not in order:
            order.append(section)
    groups = {section: [] for section in order}
    for item_id, section in layout:
        groups[section].append((item_id, section))
    result = []
    for section in order:
        result.extend(groups[section])
    return result


def group_selected(layout, item_ids):
    """Собрать выбранные пункты в отдельную группу (секцию)."""
    selected = set(item_ids)
    ordered_ids = [item_id for item_id, _section in layout]
    selected_order = [item_id for item_id in ordered_ids if item_id in selected]
    if len(selected_order) < 2:
        return layout
    first = next(i for i, item_id in enumerate(ordered_ids) if item_id in selected)
    before = [(item_id, section) for item_id, section in layout[:first]
              if item_id not in selected]
    after = [(item_id, section) for item_id, section in layout[first:]
             if item_id not in selected]
    ordered = before + [(item_id, None) for item_id in selected_order] + after
    original = {item_id: section for item_id, section in layout}
    next_section = max((section for _item_id, section in layout), default=0) + 1
    group_section = next_section
    next_section += 1
    result = []
    previous_original = None
    current_section = None
    for item_id, _section in ordered:
        if item_id in selected:
            section = group_section
            previous_original = None
        else:
            orig = original[item_id]
            if previous_original is None or orig != previous_original:
                current_section = next_section
                next_section += 1
            section = current_section
            previous_original = orig
        result.append((item_id, section))
    return normalize(result)


def load(conf):
    """Загрузить раскладку из конфигурации, дополнив её новыми пунктами."""
    raw = conf.get('menu_layout') or []
    custom = custom_items(conf)
    known = {item_id for item_id, _label, _section in MENU_ITEMS}
    known.update(item_id for item_id, _name in custom)
    layout, seen = [], set()
    for entry in raw:
        if not isinstance(entry, (list, tuple)) or not entry:
            continue
        item_id = entry[0]
        if item_id not in known or item_id in seen:
            continue
        section = entry[1] if len(entry) > 1 else SECTIONS.get(item_id, CUSTOM_SECTION)
        try:
            section = int(section)
        except (TypeError, ValueError):
            section = SECTIONS.get(item_id, CUSTOM_SECTION)
        layout.append((item_id, section))
        seen.add(item_id)
    for item_id, section in DEFAULT_LAYOUT:
        if item_id not in seen:
            layout.append((item_id, section))
    for item_id, _name in custom:
        if item_id not in seen:
            layout.append((item_id, CUSTOM_SECTION))
            seen.add(item_id)
    return normalize(layout)


def hidden(conf):
    """Множество скрытых пунктов; неизвестные id отбрасываются."""
    known = {item_id for item_id, _label, _section in MENU_ITEMS}
    known.update(item_id for item_id, _name in custom_items(conf))
    return {item_id for item_id in (conf.get('menu_hidden') or []) if item_id in known}


def contexts(conf):
    """Разрешённые ситуации для пунктов: id -> множество ситуаций."""
    known_items = {item_id for item_id, _label, _section in MENU_ITEMS}
    known_items.update(item_id for item_id, _name in custom_items(conf))
    known_contexts = set(ALL_CONTEXTS)
    result = {}
    raw = conf.get('menu_contexts') or {}
    if not isinstance(raw, dict):
        return result
    for item_id, values in raw.items():
        if item_id not in known_items or not isinstance(values, (list, tuple, set)):
            continue
        allowed = {value for value in values if value in known_contexts}
        # Все ситуации — то же самое, что отсутствие ограничения.
        if allowed != known_contexts:
            result[item_id] = allowed
    return result
