# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from . import i18n

# ───────────── формат отображения размера и даты ─────────────
DISP_DEFAULTS = dict(size_mode='bytes', size_units='si', size_decimals=1, size_group='space',
                     size_bytes_unit=False, date_style='iso', time_style='hm',
                     date_custom='%d.%m.%Y %H:%M',
                     badge_nowrite='lock', badge_noread='cross', badge_link='link',
                     badge_plate='white')
DISP = dict(DISP_DEFAULTS)
SIZE_UNITS = {
    'si': dict(base=1000, en=['B', 'kB', 'MB', 'GB', 'TB', 'PB'], ru=['Б', 'КБ', 'МБ', 'ГБ', 'ТБ', 'ПБ']),
    'win': dict(base=1024, en=['B', 'KB', 'MB', 'GB', 'TB', 'PB'], ru=['Б', 'КБ', 'МБ', 'ГБ', 'ТБ', 'ПБ']),
    'iec': dict(base=1024, en=['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'], ru=['Б', 'КиБ', 'МиБ', 'ГиБ', 'ТиБ', 'ПиБ']),
}
SIZE_GROUP_CHARS = {'space': ' ', 'none': '', 'comma': ',', 'dot': '.'}
MON_ABBR = {'en': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'ru': ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']}
MON_FULL = {'en': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                   'September', 'October', 'November', 'December'],
            'ru': ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                   'сентября', 'октября', 'ноября', 'декабря']}
DAY_ABBR = {'en': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'ru': ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']}
DAY_FULL = {'en': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            'ru': ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']}
DATE_PATTERNS = {'iso': '%Y-%m-%d', 'dmy': '%d.%m.%Y', 'mdy': '%m/%d/%Y', 'dmony': '%d %b %Y', 'none': ''}
TIME_PATTERNS = {'none': '', 'hm': '%H:%M', 'hms': '%H:%M:%S', 'hm12': '%I:%M %p'}


def apply_display(conf):
    for k, v in DISP_DEFAULTS.items():
        DISP[k] = conf.get(k, v)


def _group_digits(int_str, sep):
    if not sep or len(int_str) <= 3:
        return int_str
    rev = int_str[::-1]
    return sep.join(rev[i:i + 3] for i in range(0, len(rev), 3))[::-1]


def _num(v, dec, group_sep, dec_sep):
    text = '%.*f' % (dec, v)
    int_part, dot, frac = text.partition('.')
    return _group_digits(int_part, group_sep) + (dec_sep + frac if frac else '')


def format_size(n, cfg=None, with_unit=False):
    """Размер файла по настройкам пользователя. with_unit — всегда показывать единицу (строка состояния)."""
    if n is None or n < 0:
        return ''
    c = cfg or DISP
    sep = SIZE_GROUP_CHARS.get(c['size_group'], ' ')
    dsep = ',' if i18n.LANG_RU else '.'
    u = SIZE_UNITS.get(c['size_units'], SIZE_UNITS['si'])
    names, base, mode = u['ru' if i18n.LANG_RU else 'en'], u['base'], c['size_mode']
    dec = max(0, min(3, int(c['size_decimals'])))
    if mode == 'bytes':
        text = _num(n, 0, sep, dsep)
        if with_unit:
            return text + ' ' + ('байт' if i18n.LANG_RU else 'bytes')
        return text + (' ' + names[0] if c['size_bytes_unit'] else '')
    if mode == 'adaptive':
        i, v = 0, float(n)
        while v >= base and i < len(names) - 1:
            v /= base
            i += 1
        if i and round(v, dec) >= base and i < len(names) - 1:
            v /= base
            i += 1
        if i == 0:
            return _num(n, 0, sep, dsep) + ' ' + names[0]
        return _num(v, dec, sep, dsep) + ' ' + names[i]
    i = {'kb': 1, 'mb': 2, 'gb': 3}.get(mode, 1)
    return _num(n / float(base ** i), dec, sep, dsep) + ' ' + names[i]


def _strftime(lt, pattern):
    lang = 'ru' if i18n.LANG_RU else 'en'
    pattern = pattern.replace('%%', '\0')
    for code, table, idx in (('%b', MON_ABBR, lt.tm_mon - 1), ('%B', MON_FULL, lt.tm_mon - 1),
                             ('%a', DAY_ABBR, lt.tm_wday), ('%A', DAY_FULL, lt.tm_wday)):
        pattern = pattern.replace(code, table[lang][idx])
    try:
        return time.strftime(pattern.replace('\0', '%%'), lt)
    except ValueError:
        return pattern.replace('\0', '%')


def format_date(ts, cfg=None):
    """Дата/время изменения по настройкам пользователя."""
    if not ts:
        return ''
    c = cfg or DISP
    try:
        lt = time.localtime(ts)
    except (ValueError, OverflowError, OSError):
        return ''
    if c['date_style'] == 'custom':
        return _strftime(lt, c['date_custom'])
    pattern = (DATE_PATTERNS.get(c['date_style'], '%Y-%m-%d') + ' ' +
               TIME_PATTERNS.get(c['time_style'], '%H:%M')).strip()
    return _strftime(lt, pattern)


def parse_size(text):
    m = re.fullmatch(r'\s*(\d+)\s*([bBkKmMgG]?)\s*', text or '')
    if not m:
        return 0
    mult = {'': 1, 'b': 1, 'k': 1024, 'm': 1024 ** 2, 'g': 1024 ** 3}[m.group(2).lower()]
    return int(m.group(1)) * mult


def pretty_size_token(s):
    """'64k' -> '64 KB', '1m' -> '1 MB', 'off' -> 'Non-solid'."""
    m = re.fullmatch(r'(\d+)([kmg])', s)
    if not m:
        return s
    return '%s %sB' % (m.group(1), m.group(2).upper())
