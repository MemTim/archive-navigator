# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .display import DISP

# ───────────── значки: pixbuf нужного размера + бейджи (нет записи / нет чтения / ссылка) ─────────────
# Рисуется через GdkPixbuf: не зависит от рендерера GTK и версии GTK, масштабируется точно.
FLAG_NOWRITE, FLAG_NOREAD, FLAG_LINK = 1, 2, 4
BADGE_SVG = {
    'lock': """<svg width="16" height="20" viewBox="0 0 16 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M2 20H14C15.1 20 16 19.1 16 18V9C16 7.9 15.1 7 14 7H13V5C13 2.24 10.76 0 8 0C5.24 0 3 2.24 3 5V7H2C0.9 7 0 7.9 0 9V18C0 19.1 0.9 20 2 20ZM5 5C5 3.35 6.35 2 8 2C9.65 2 11 3.35 11 5V7H5V5ZM2 9H14V18H2V9Z" fill="#FF0000"/>
</svg>""",
    'link': """<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M11.5 8.5L19 1M19 6V1H14M19 12V17C19 17.5304 18.7893 18.0391 18.4142 18.4142C18.0391 18.7893 17.5304 19 17 19H3C2.46957 19 1.96086 18.7893 1.58579 18.4142C1.21071 18.0391 1 17.5304 1 17V3C1 2.46957 1.21071 1.96086 1.58579 1.58579C1.96086 1.21071 2.46957 1 3 1H8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke="#5F5F5F"/>
</svg>""",
    'cross': """<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M19 19L10 10M10 10L1 1M10 10L19 1M10 10L1 19" stroke-width="2" stroke-linecap="round" stroke="#FF5500"/>
</svg>""",
    'key': """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<circle cx="7.5" cy="12" r="4.6" stroke="#E01B24" stroke-width="2.4"/>
<path d="M12 12H22.5M18.5 12V16.5M21.5 12V15" stroke="#E01B24" stroke-width="2.4" stroke-linecap="round"/>
</svg>""",
}
# Значки берутся из szgtk/assets — их можно заменить, не меняя код.
_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')


def _load_badge_svg(name):
    try:
        with open(os.path.join(_ASSET_DIR, name + '.svg'), encoding='utf-8') as f:
            return f.read()
    except OSError:
        return None


for _badge_name in ('lock', 'cross', 'link'):
    _badge_svg = _load_badge_svg(_badge_name)
    if _badge_svg:
        BADGE_SVG[_badge_name] = _badge_svg

# Запасной вариант — растровые копии тех же значков (если в системе нет SVG-загрузчика gdk-pixbuf / librsvg)
BADGE_PNG = {
    'lock': (
        'iVBORw0KGgoAAAANSUhEUgAAAGcAAACACAYAAAAWAHfDAAAABmJLR0QA/wD/AP+gvaeTAAAFnElEQVR4nO2dXYiVRRyHnzmt'
        'Wn6EfZd2kQapaAUZXWUakgRieRHdWAQRhhF1EdRNRBdR1k1IF3ZTBBUoRdjHRVISmEGaWVFZRmVKLghFLJrrx+aviznKurtn'
        '2XfeOWf+Z/f/wFzsOTvn/GaefWfnnXfOeQNdhGA6sAS4AZgHzAeuAC4EpgFTgD7gSLPsA34B9gI7AuwvEHv8IpgreEbwheCU'
        'QDXKfsFrghWC80q3rSsRTBLcL/hccLqmkFblkOBFwezS7e0KBJMF65p/4e0QMlI5LnhVcE3p9ptFsEzwYwelDC0nBOsF55fu'
        'CzMIZgreLihlaPlVcdIxsREsbnZGaSFDy4DgWUGjdB8VQfBgcygpLWK08qHiFH3iIHhc7ZuF5S67BJeV7rOOIHjeQIdXLXvH'
        'vSDBowY6OrV8pbhCMf4QrFH3DGWtylZBT+m+zIpgkeDfNnXYKcEfiudIewS/CfraKOi50v2ZDcE0xTE7V+f0C94VPCxYKJjc'
        '4n1nCVYJXhYcyPj+/wlWdLof24LglUydclDwmGBmQoaGYLng40xZehVXwrsXxZPMgZodcVTwZKsjJCHTrYLvMgjakCNPEQRB'
        'sLNmB+wSzGlDth7FKX2dCcqA4Mbc2TqC4K6aYt7MdbSMknG14FiNjFvama9tCL6s0eiNgtChnLcpfSZ5WnB9J3JmQ3B7DTGb'
        '1OEFR8FKpV9lfauTWWvTHJJSGvqDYGqhzE8nZu5XwgyyCILpijOsqo08KVhUMHdDsD1R0EOlcldCcZkmpYEvGci+KHF421Y6'
        '+5gQvJHQuD7BRaWzQ3L+E+qG6z5KWyopftScQTBfaec/d5TOPiqCOYlD2vzS2Qcj2JHQhuwLormnrAsT6nwb4OfMOeqyOaFO'
        '9slMbjkpR8CnmTPkIOUf/LzcIXLLuS6hzq7MGWoT4t7qvorVrlXmLb655VySUOenzBlysa/i708i82WE3HJSrrH3Zs6Qiz8T'
        '6piWMyOhztHMGXJxJKFOSvtbkltO5SX+ACczZ8jFiYQ6U3IGmJjbTbsEl2MYl2MYl2MYl2MYl2MYl2MYl2MYl2MYl2MYl2OY'
        'Sh8EElwMXEXrz+pX3nMmWFy1TodI+ZjhAo38uIDDwOEAA2N9sVG3vDZl3AOsBpZSaMPfOELEC3kfAO8E+CblFaYKnhL8k7hh'
        'w8vYyicaZa/1sCNHMLdpNmWzhlOdk8C6AK8PfeKcCYHgFmAnLqaTTCZ+zdgLQ584e+QIZhE3W/hXXJXjkQAbz/wQAJq7RnZi'
        'd+Y0UTgFLAnRxdlh7QFcjAUmARvUPGiC4gO/A1cXjeUMZlWAjxrAMlyMNdZAHNbuLhzEGc5KwZQGcfrs2GIGMK9BnEI79pjd'
        'A1xesdJfwHttCDOeWUD17w29koT1oN3tSD+eEaxN6Oe1fj3HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7H'
        'MC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7H'
        'MC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMC7HMD3AcVrfWnIkFvgXf1fm'
        '0oQ6/UHx3jlzcqdxarO8ARwqncIZkd4G8FnpFM4weoF9DeD90kmcYWwJoAawp1kcG4jmDV0bIf7wRNk8ziA2Bfgazr2J62bg'
        '3mKRHIC/gcUBDsC5ci4AtgM3Fwo20RkA7gyw7cwDZ1cIAvQDq0m5DbxTl37gvsFiYMjyTYjnPEuIQ5zTGQ4CS0OVPhcsF+xO'
        'uNeYl7GVI4L1gumtHIRWTwySdBPxRq/LiHfinUW1tTgnzogPE08uvyeeW24NcGy0Sv8DSH4JXT148a4AAAAASUVORK5CYII='),
    'link': (
        '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'),
    'cross': (
        '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'
        'SUVORK5CYII='),
    'key': (
        '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'),
}
_SVG_OK = [True]
_PIX, _BADGE, _BADGE_TEX = {}, {}, {}
# Цвета для варианта «фон темы»: плашка — фон схемы, обводка и значок — основной цвет.
BADGE_THEME = {'bg': (8, 7, 31), 'accent': (69, 139, 223)}


def clear_icon_cache():
    _PIX.clear()
    _BADGE.clear()
    _BADGE_TEX.clear()


def _hex_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def set_badge_theme(bg, accent):
    """Задать цвета плашки для схемы оформления и сбросить кэш значков."""
    BADGE_THEME['bg'] = _hex_rgb(bg)
    BADGE_THEME['accent'] = _hex_rgb(accent)
    clear_icon_cache()


def _svg_pixbuf(svg_text, w, h):
    stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(svg_text.encode('utf-8')))
    return GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, w, h, True, None)


def _glyph_pixbuf(style, w, h):
    """Иконка бейджа: SVG (чёткая при любом размере), а без загрузчика SVG — встроенный PNG."""
    if _SVG_OK[0]:
        try:
            return _svg_pixbuf(BADGE_SVG[style], w, h)
        except Exception:
            _SVG_OK[0] = False
    stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(base64.b64decode(BADGE_PNG[style])))
    return GdkPixbuf.Pixbuf.new_from_stream_at_scale(stream, w, h, True, None)


def _plate_pixbuf(d, plate='white'):
    """Круглая плашка: белая с тёмной обводкой или в цветах темы."""
    if plate == 'theme':
        return _theme_plate_pixbuf(d)
    buf = bytearray(d * d * 4)
    r = d / 2.0
    c = r - 0.5
    bw = max(1.0, d * 0.045)
    for y in range(d):
        for x in range(d):
            dist = math.hypot(x - c, y - c)
            cov = max(0.0, min(1.0, r - dist))
            if cov <= 0.0:
                continue
            t = max(0.0, min(1.0, dist - (r - 0.5 - bw)))
            a = cov * (0.95 * (1.0 - t) + 0.34 * t)
            v = int(255 * (1.0 - t))
            i = (y * d + x) * 4
            buf[i] = buf[i + 1] = buf[i + 2] = v
            buf[i + 3] = int(255 * a)
    return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(buf)), GdkPixbuf.Colorspace.RGB, True, 8, d, d, d * 4)


def _theme_plate_pixbuf(d):
    """Плашка цвета фона темы с обводкой основным цветом."""
    bg, ring = BADGE_THEME['bg'], BADGE_THEME['accent']
    buf = bytearray(d * d * 4)
    r = d / 2.0
    c = r - 0.5
    bw = max(1.4, d * 0.09)
    for y in range(d):
        for x in range(d):
            dist = math.hypot(x - c, y - c)
            cov = max(0.0, min(1.0, r - dist))
            if cov <= 0.0:
                continue
            t = max(0.0, min(1.0, (dist - (r - bw)) / bw))
            t = t * t * (3.0 - 2.0 * t)
            i = (y * d + x) * 4
            for k in range(3):
                buf[i + k] = int(round(bg[k] * (1.0 - t) + ring[k] * t))
            buf[i + 3] = int(255 * cov)
    return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(buf)), GdkPixbuf.Colorspace.RGB, True, 8, d, d, d * 4)


def _tint_pixbuf(pb, rgb):
    """Перекрасить непрозрачные пиксели значка, сохранив сглаживание."""
    if pb is None:
        return None
    w, h = pb.get_width(), pb.get_height()
    n = pb.get_n_channels()
    stride = pb.get_rowstride()
    data = bytearray(pb.get_pixels())
    for y in range(h):
        row = y * stride
        for x in range(w):
            i = row + x * n
            if n == 4 and data[i + 3] == 0:
                continue
            data[i], data[i + 1], data[i + 2] = rgb
    return GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(bytes(data)), GdkPixbuf.Colorspace.RGB,
                                           n == 4, 8, w, h, stride)


def _badge_pixbuf(style, d):
    """Круглая плашка диаметра d с иконкой style внутри (None — рисовать нечем)."""
    plate_style = DISP.get('badge_plate', 'white')
    key = (style, d, plate_style)
    if key in _BADGE:
        return _BADGE[key]
    pb = None
    if GdkPixbuf is not None and style in BADGE_SVG:
        try:
            plate = _plate_pixbuf(d, plate_style)
            g = max(5, int(d * 0.66))
            glyph = _glyph_pixbuf(style, g, g)
            if plate_style == 'theme':
                glyph = _tint_pixbuf(glyph, BADGE_THEME['accent'])
            gw, gh = glyph.get_width(), glyph.get_height()
            x, y = (d - gw) // 2, (d - gh) // 2
            glyph.composite(plate, x, y, gw, gh, x, y, 1.0, 1.0, GdkPixbuf.InterpType.BILINEAR, 255)
            pb = plate
        except Exception:
            pb = None
    _BADGE[key] = pb
    return pb


def badge_texture(style, d):
    """Бейдж как Gdk.Texture (для плиток); None — рисовать нечем."""
    key = (style, d, DISP.get('badge_plate', 'white'))
    if key not in _BADGE_TEX:
        pb = _badge_pixbuf(style, d)
        _BADGE_TEX[key] = Gdk.Texture.new_for_pixbuf(pb) if pb is not None else None
    return _BADGE_TEX[key]


def _base_pixbuf(gicon, size):
    """Значок темы, отмасштабированный до size×size (None — если не удалось/символьный)."""
    if GdkPixbuf is None or gicon is None:
        return None
    try:
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        paint = theme.lookup_by_gicon(gicon, size, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags(0))
        if paint.is_symbolic():
            return None
        f = paint.get_file()
        path = f.get_path() if f is not None else None
        if not path:
            return None
        return GdkPixbuf.Pixbuf.new_from_file_at_size(path, size, size)
    except Exception:
        return None


def make_icon_pixbuf(gicon, size, flags=0):
    """Значок нужного размера с бейджами; None — пусть рисует сам GTK (по имени значка)."""
    if gicon is None or GdkPixbuf is None:
        return None
    key = (gicon.to_string(), size, flags, DISP['badge_nowrite'], DISP['badge_noread'],
           DISP['badge_link'], DISP.get('badge_plate', 'white'))
    if key in _PIX:
        return _PIX[key]
    pb = None
    base = _base_pixbuf(gicon, size)
    if base is not None:
        canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
        canvas.fill(0x00000000)
        bw, bh = base.get_width(), base.get_height()
        x, y = (size - bw) // 2, (size - bh) // 2
        base.composite(canvas, x, y, bw, bh, x, y, 1.0, 1.0, GdkPixbuf.InterpType.BILINEAR, 255)
        d = max(9, int(size * 0.46))
        for flag, which, cx, cy in ((FLAG_NOREAD, 'badge_noread', 0, size - d),
                                    (FLAG_NOWRITE, 'badge_nowrite', size - d, size - d),
                                    (FLAG_LINK, 'badge_link', size - d, 0)):
            if flags & flag and DISP[which] != 'none':
                badge = _badge_pixbuf(DISP[which], d)
                if badge is not None:
                    badge.composite(canvas, cx, cy, d, d, cx, cy, 1.0, 1.0, GdkPixbuf.InterpType.BILINEAR, 255)
        pb = canvas
    _PIX[key] = pb
    return pb


def square_pixbuf(pb, size):
    """Миниатюра по центру прозрачного квадрата size×size — плитки получаются ровными."""
    if GdkPixbuf is None or pb is None:
        return pb
    canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, size, size)
    canvas.fill(0x00000000)
    w, h = pb.get_width(), pb.get_height()
    x, y = (size - w) // 2, (size - h) // 2
    pb.composite(canvas, x, y, w, h, x, y, 1.0, 1.0, GdkPixbuf.InterpType.BILINEAR, 255)
    return canvas
