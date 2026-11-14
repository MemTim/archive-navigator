# -*- coding: utf-8 -*-
"""Convert a GSK render tree (GTK 4) into an editable SVG.

The exporter is used by ``tools/export_design.py`` to turn the live UI into
vector mockups: boxes, borders, gradients and icon paths stay vector shapes,
text stays real <text> (glyph ids are decoded back through the font cmap), and
only real images/thumbnails are embedded as PNG.

Tested with GTK 4.24 / PyGObject.  Only the node types that GTK actually emits
for this application are implemented; unknown nodes are skipped and reported.
"""
from __future__ import annotations

import base64
import ctypes
import math
import subprocess
from functools import lru_cache
from xml.sax.saxutils import escape

import gi

gi.require_version('Gsk', '4.0')
gi.require_version('Graphene', '1.0')
gi.require_version('Pango', '1.0')
gi.require_version('Gdk', '4.0')

from gi.repository import Gdk, GLib, Graphene, Gsk, Pango  # noqa: E402

try:
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf, Gio  # noqa: E402
except (ValueError, ImportError):  # pragma: no cover — необязательное сжатие
    GdkPixbuf = Gio = None

# ── ctypes access to GskTextNode glyphs ────────────────────────────────────
# PyGObject exposes Gsk.TextNode.get_glyphs() as an array of PangoGlyphInfo,
# but the generated wrapper walks the array with the wrong stride and returns
# garbage for all glyphs after the first one.  Reading the structs ourselves is
# reliable and keeps the text editable in the exported SVG.
_gtk = ctypes.CDLL('libgtk-4.so.1')
_gtk.gsk_text_node_get_glyphs.argtypes = [ctypes.c_void_p,
                                          ctypes.POINTER(ctypes.c_uint)]
_gtk.gsk_text_node_get_glyphs.restype = ctypes.c_void_p
_gtk.gsk_text_node_get_num_glyphs.argtypes = [ctypes.c_void_p]
_gtk.gsk_text_node_get_num_glyphs.restype = ctypes.c_uint


class _Geom(ctypes.Structure):
    _fields_ = [('width', ctypes.c_int),
                ('x_offset', ctypes.c_int),
                ('y_offset', ctypes.c_int)]


class _GlyphInfo(ctypes.Structure):
    _fields_ = [('glyph', ctypes.c_uint32),
                ('geometry', _Geom),
                ('attr', ctypes.c_uint32)]


def _boxed_ptr(obj):
    """Address of the C struct behind a PyGObject boxed wrapper."""
    # PyGBoxed is PyObject_HEAD (16 bytes) followed by the pointer; a couple of
    # PyGObject versions pad the header, so probe the two known offsets.
    for off in (24, 16):
        try:
            ptr = ctypes.c_void_p.from_address(id(obj) + off).value
        except Exception:
            ptr = None
        if ptr:
            return ptr
    raise RuntimeError('cannot find boxed pointer for %r' % (obj,))


def text_glyphs(node):
    """[(glyph_id, advance, x_offset, y_offset)] for a Gsk.TextNode."""
    ptr = _boxed_ptr(node)
    num = ctypes.c_uint(0)
    arr = _gtk.gsk_text_node_get_glyphs(ptr, ctypes.byref(num))
    if not arr:
        return []
    data = ctypes.cast(arr, ctypes.POINTER(_GlyphInfo))
    return [(data[i].glyph, data[i].geometry.width,
             data[i].geometry.x_offset, data[i].geometry.y_offset)
            for i in range(num.value)]


# ── font decoding: glyph id → character ────────────────────────────────────
def _fc_pattern(desc):
    """Fontconfig pattern for a Pango description (family + weight + slant)."""
    family = (desc.get_family() or 'sans-serif').replace(':', r'\:')
    pattern = family
    try:
        if desc.get_weight() >= Pango.Weight.SEMIBOLD:
            pattern += ':bold'
        elif desc.get_weight() <= Pango.Weight.LIGHT:
            pattern += ':light'
        if desc.get_style() in (Pango.Style.ITALIC, Pango.Style.OBLIQUE):
            pattern += ':italic'
    except Exception:
        pass
    return pattern


@lru_cache(maxsize=64)
def _font_for(desc):
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return None
    pattern = _fc_pattern(desc)
    try:
        path = subprocess.run(
            ['fc-match', '-f', '%{file}', pattern],
            capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
    if not path:
        return None
    try:
        # Variable fonts expose named instances through fontconfig, but the
        # glyph ids are identical, so the default instance is enough.
        font = TTFont(path, lazy=True)
        cmap = font.getBestCmap() or {}
        rev = {}
        for cp, name in sorted(cmap.items()):
            gid = font.getGlyphID(name)
            if gid and gid not in rev:
                rev[gid] = chr(cp)
        # A few fonts (especially CJK) map many codepoints to one glyph; the
        # lowest codepoint is the best guess for UI text.
        return rev
    except Exception:
        return None


def _weight(desc):
    try:
        return {
            Pango.Weight.THIN: 100, Pango.Weight.ULTRALIGHT: 200,
            Pango.Weight.LIGHT: 300, Pango.Weight.SEMILIGHT: 350,
            Pango.Weight.BOOK: 380, Pango.Weight.NORMAL: 400,
            Pango.Weight.MEDIUM: 500, Pango.Weight.SEMIBOLD: 600,
            Pango.Weight.BOLD: 700, Pango.Weight.ULTRABOLD: 800,
            Pango.Weight.HEAVY: 900, Pango.Weight.ULTRAHEAVY: 1000,
        }.get(desc.get_weight(), 400)
    except Exception:
        return 400


def _style(desc):
    try:
        s = desc.get_style()
        if s == Pango.Style.ITALIC:
            return 'italic'
        if s == Pango.Style.OBLIQUE:
            return 'oblique'
    except Exception:
        pass
    return 'normal'


def _font_size_px(desc):
    size = desc.get_size() / float(Pango.SCALE)
    if not desc.get_size_is_absolute():
        size = size * 96.0 / 72.0
    return size


def _rgba(c, alpha_mul=1.0):
    return 'rgba(%d,%d,%d,%s)' % (
        max(0, min(255, round(c.red * 255))),
        max(0, min(255, round(c.green * 255))),
        max(0, min(255, round(c.blue * 255))),
        ('%.4f' % (c.alpha * alpha_mul)).rstrip('0').rstrip('.') or '0')


def _num(v):
    s = ('%.3f' % float(v)).rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


def _texture_png(tex, max_w, max_h):
    """PNG-байты текстуры, уменьшенные до размера, которым она рисуется.

    GTK часто хранит значки приложений в исходном разрешении (256–512 px), а
    выводит их по 16–24 px.  Без этого «Открыть с помощью…» весил бы мегабайты.
    """
    try:
        data = bytes(tex.save_to_png_bytes().get_data())
    except Exception:
        return None
    tw, th = tex.get_width(), tex.get_height()
    max_w = max(1.0, float(max_w))
    max_h = max(1.0, float(max_h))
    if tw <= max_w * 1.5 and th <= max_h * 1.5:
        return data
    if GdkPixbuf is None:
        return data
    try:
        stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(data))
        pb = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
        scale = min(max_w / float(tw), max_h / float(th), 1.0)
        nw = max(1, int(round(tw * scale)))
        nh = max(1, int(round(th * scale)))
        scaled = pb.scale_simple(nw, nh, GdkPixbuf.InterpType.BILINEAR)
        ok, buf = scaled.save_to_bufferv('png', [], [])
        return bytes(buf) if ok else data
    except Exception:
        return data


def _rect_attrs(b):
    return 'x="%s" y="%s" width="%s" height="%s"' % (
        _num(b.get_x()), _num(b.get_y()),
        _num(b.get_width()), _num(b.get_height()))


def _path_bounds(path):
    """Gsk.Path.get_bounds() -> Rect.

    В PyGObject метод возвращает кортеж результата ``(ok, bounds=Rect)``,
    а не сам прямоугольник, поэтому его нужно развернуть.
    """
    try:
        res = path.get_bounds()
    except Exception:
        return None
    if hasattr(res, 'get_x'):
        return res
    if isinstance(res, tuple):
        for item in res:
            if hasattr(item, 'get_x'):
                return item
    return getattr(res, 'bounds', None)


def _path_png(path, bounds, color, even_odd=False, size=64):
    """Растеризовать очень сложную заливку (значки приложений) в маленький PNG.

    Некоторые значки из темы приходят как путь на 512 px с тысячами сегментов,
    а рисуются по 16–24 px.  В SVG это даёт сотни килобайт на одну иконку, хотя
    при таком размере разница не видна.  Контуры интерфейса остаются векторными,
    растрируются только такие «тяжёлые» значки.
    """
    bw, bh = bounds.get_width(), bounds.get_height()
    if bw <= 0 or bh <= 0:
        return None
    try:
        import cairo
    except Exception:
        return None
    scale = min(1.0, float(size) / max(bw, bh))
    W = max(1, int(round(bw * scale)))
    H = max(1, int(round(bh * scale)))
    try:
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        cr = cairo.Context(surf)
        cr.scale(W / bw, H / bh)
        cr.translate(-bounds.get_x(), -bounds.get_y())
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD if even_odd else cairo.FILL_RULE_WINDING)
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        path.to_cairo(cr)
        cr.fill()
        import io
        buf = io.BytesIO()
        surf.write_to_png(buf)
        return buf.getvalue()
    except Exception:
        return None


def _rounded_d(b, corners):
    """SVG path for a rounded rectangle. corners = [(tl),(tr),(br),(bl)]."""
    x, y = b.get_x(), b.get_y()
    w, h = b.get_width(), b.get_height()
    tl, tr, br, bl = (min(max(0.0, c), min(w, h) / 2.0) for c in corners)
    parts = ['M %s %s' % (_num(x + tl), _num(y))]
    if tr:
        parts.append('L %s %s' % (_num(x + w - tr), _num(y)))
        parts.append('Q %s %s %s %s' % (_num(x + w), _num(y),
                                        _num(x + w), _num(y + tr)))
    else:
        parts.append('L %s %s' % (_num(x + w), _num(y)))
    if br:
        parts.append('L %s %s' % (_num(x + w), _num(y + h - br)))
        parts.append('Q %s %s %s %s' % (_num(x + w), _num(y + h),
                                        _num(x + w - br), _num(y + h)))
    else:
        parts.append('L %s %s' % (_num(x + w), _num(y + h)))
    if bl:
        parts.append('L %s %s' % (_num(x + bl), _num(y + h)))
        parts.append('Q %s %s %s %s' % (_num(x), _num(y + h),
                                        _num(x), _num(y + h - bl)))
    else:
        parts.append('L %s %s' % (_num(x), _num(y + h)))
    if tl:
        parts.append('L %s %s' % (_num(x), _num(y + tl)))
        parts.append('Q %s %s %s %s' % (_num(x), _num(y),
                                        _num(x + tl), _num(y)))
    else:
        parts.append('L %s %s' % (_num(x), _num(y)))
    parts.append('Z')
    return ' '.join(parts)


def _rounded_corners(rr):
    try:
        return [max(c.width, c.height) for c in rr.corner]
    except Exception:
        r = rr.bounds
        return [0, 0, 0, 0]


class GskToSvg:
    def __init__(self):
        self.body = []
        self.defs = []
        self._seq = 0
        self.unknown = {}
        self._png_cache = {}

    # ── helpers ──
    def _id(self, prefix):
        self._seq += 1
        return '%s%d' % (prefix, self._seq)

    def _clip(self, d, prefix='clip'):
        cid = self._id(prefix)
        self.defs.append('<clipPath id="%s"><path d="%s"/></clipPath>' % (cid, d))
        return cid

    # ── public ──
    def render(self, node, width, height):
        self.body = []
        self.defs = []
        self._seq = 0
        body = self._node(node)
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'xmlns:xlink="http://www.w3.org/1999/xlink" '
                'width="%d" height="%d" viewBox="0 0 %d %d">\n'
                '<defs>%s</defs>\n%s\n</svg>\n'
                % (width, height, width, height, ''.join(self.defs), body))

    def _node(self, node):
        if node is None:
            return ''
        nick = node.get_node_type().value_nick
        fn = getattr(self, 'n_' + nick.replace('-', '_'), None)
        if fn is None:
            self.unknown[nick] = self.unknown.get(nick, 0) + 1
            return ''
        try:
            return fn(node)
        except Exception as exc:  # keep the export going; report at the end
            key = '%s: %s' % (nick, exc)
            self.unknown[key] = self.unknown.get(key, 0) + 1
            return ''

    # ── primitives ──
    def n_container_node(self, node):
        return ''.join(self._node(node.get_child(i))
                       for i in range(node.get_n_children()))

    def n_color_node(self, node):
        b = node.get_bounds()
        return '<rect %s fill="%s"/>' % (_rect_attrs(b), _rgba(node.get_color()))

    def n_border_node(self, node):
        rr = node.get_outline()
        b = rr.bounds
        widths = node.get_widths()
        colors = node.get_colors()
        if len(widths) < 4 or len(colors) < 4:
            return ''
        corners = _rounded_corners(rr)
        if len(set((round(c.red, 4), round(c.green, 4), round(c.blue, 4),
                    round(c.alpha, 4)) for c in colors)) == 1:
            w = max(widths)
            if w <= 0:
                return ''
            inner = Graphene.Rect().init(
                b.get_x() + w / 2.0, b.get_y() + w / 2.0,
                max(0.0, b.get_width() - w), max(0.0, b.get_height() - w))
            d = _rounded_d(inner, [max(0.0, c - w / 2.0) for c in corners])
            return ('<path d="%s" fill="none" stroke="%s" stroke-width="%s"/>'
                    % (d, _rgba(colors[0]), _num(w)))
        # Different colors per side: draw four straight bands.  Corners are
        # left square, which is accurate for the 1 px separators used here.
        x, y, bw, bh = b.get_x(), b.get_y(), b.get_width(), b.get_height()
        top, right, bottom, left = widths
        out = []
        if top > 0:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
                       % (_num(x), _num(y), _num(bw), _num(top), _rgba(colors[0])))
        if right > 0:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
                       % (_num(x + bw - right), _num(y), _num(right), _num(bh),
                          _rgba(colors[1])))
        if bottom > 0:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
                       % (_num(x), _num(y + bh - bottom), _num(bw), _num(bottom),
                          _rgba(colors[2])))
        if left > 0:
            out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
                       % (_num(x), _num(y), _num(left), _num(bh),
                          _rgba(colors[3])))
        return ''.join(out)

    def n_transform_node(self, node):
        # Gsk.TransformNode stores a GskTransform, not a graphene matrix.
        m = node.get_transform().to_matrix()
        mat = [m.get_value(r, c) for r in range(4) for c in range(4)]
        tr = 'matrix(%s,%s,%s,%s,%s,%s)' % (
            _num(mat[0]), _num(mat[4]), _num(mat[1]),
            _num(mat[5]), _num(mat[12]), _num(mat[13]))
        return '<g transform="%s">%s</g>' % (tr, self._node(node.get_child()))

    def n_opacity_node(self, node):
        return '<g opacity="%s">%s</g>' % (_num(node.get_opacity()),
                                           self._node(node.get_child()))

    def n_clip_node(self, node):
        b = node.get_clip()
        d = _rounded_d(b, [0, 0, 0, 0])
        cid = self._clip(d)
        return '<g clip-path="url(#%s)">%s</g>' % (cid, self._node(node.get_child()))

    def n_rounded_clip_node(self, node):
        rr = node.get_clip()
        d = _rounded_d(rr.bounds, _rounded_corners(rr))
        cid = self._clip(d)
        return '<g clip-path="url(#%s)">%s</g>' % (cid, self._node(node.get_child()))

    def n_fill_node(self, node):
        path = node.get_path()
        d = path.to_string()
        child = node.get_child()
        nick = child.get_node_type().value_nick if child is not None else ''
        if len(d) > 12000 and nick == 'color-node':
            # Очень сложная заливка (значок приложения) — в PNG, иначе файл
            # раздувается на сотни килобайт ради иконки 20×20.
            c = child.get_color()
            b = _path_bounds(path)
            if b is None or b.get_width() <= 0 or b.get_height() <= 0:
                b = node.get_bounds()
            key = (round(len(d)), round(b.get_x(), 2), round(b.get_y(), 2),
                   round(b.get_width(), 2), round(b.get_height(), 2),
                   round(c.red, 3), round(c.green, 3), round(c.blue, 3),
                   round(c.alpha, 3))
            data = self._png_cache.get(key)
            if data is None:
                data = _path_png(path, b, c,
                                 node.get_fill_rule() == Gsk.FillRule.EVEN_ODD)
                self._png_cache[key] = data
            if data:
                b64 = base64.b64encode(data).decode('ascii')
                return ('<image %s preserveAspectRatio="none" '
                        'xlink:href="data:image/png;base64,%s"/>'
                        % (_rect_attrs(b), b64))
        cid = self._clip(d, 'fill')
        return '<g clip-path="url(#%s)">%s</g>' % (cid, self._node(child))

    def n_stroke_node(self, node):
        # Rare (custom focus rings): approximate by drawing the child inside
        # a mask shaped by the stroked path.
        path = node.get_path()
        d = path.to_string()
        cid = self._clip(d, 'stroke')
        return '<g clip-path="url(#%s)">%s</g>' % (cid, self._node(node.get_child()))

    def n_text_node(self, node):
        b = node.get_bounds()
        font = node.get_font()
        desc = font.describe()
        glyphs = text_glyphs(node)
        cmap = _font_for(desc)
        text = ''.join((cmap or {}).get(g, '') for g, _w, _x, _y in glyphs)
        if not text:
            return ''
        off = node.get_offset()
        family = escape(desc.get_family() or 'sans-serif', {'"': '&quot;'})
        return ('<text x="%s" y="%s" font-family="%s" font-size="%s" '
                'font-weight="%d" font-style="%s" fill="%s" '
                'xml:space="preserve">%s</text>'
                % (_num(off.x), _num(off.y), family,
                   _num(_font_size_px(desc)), _weight(desc), _style(desc),
                   _rgba(node.get_color()), escape(text)))

    def n_texture_node(self, node):
        b = node.get_bounds()
        tex = node.get_texture()
        data = _texture_png(tex, b.get_width(), b.get_height())
        if not data:
            return ''
        b64 = base64.b64encode(data).decode('ascii')
        return ('<image %s preserveAspectRatio="none" '
                'xlink:href="data:image/png;base64,%s"/>'
                % (_rect_attrs(b), b64))

    def n_linear_gradient_node(self, node):
        b = node.get_bounds()
        start, end = node.get_start(), node.get_end()
        gid = self._id('lg')
        stops = ''.join(
            '<stop offset="%s" stop-color="%s"/>'
            % (_num(s.offset), _rgba(s.color))
            for s in node.get_color_stops())
        self.defs.append(
            '<linearGradient id="%s" gradientUnits="userSpaceOnUse" '
            'x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>'
            % (gid, _num(start.x), _num(start.y), _num(end.x), _num(end.y), stops))
        return '<rect %s fill="url(#%s)"/>' % (_rect_attrs(b), gid)

    def n_radial_gradient_node(self, node):
        b = node.get_bounds()
        c = node.get_center()
        hr, vr = node.get_hradius(), node.get_vradius()
        gid = self._id('rg')
        stops = ''.join(
            '<stop offset="%s" stop-color="%s"/>'
            % (_num(s.offset), _rgba(s.color))
            for s in node.get_color_stops())
        self.defs.append(
            '<radialGradient id="%s" gradientUnits="userSpaceOnUse" '
            'cx="%s" cy="%s" r="%s" gradientTransform="translate(%s,%s) '
            'scale(1,%s) translate(%s,%s)">%s</radialGradient>'
            % (gid, _num(c.x), _num(c.y), _num(max(hr, 0.001)),
               _num(c.x), _num(c.y), _num(vr / hr if hr else 1.0),
               _num(-c.x), _num(-c.y), stops))
        return '<rect %s fill="url(#%s)"/>' % (_rect_attrs(b), gid)

    def n_outset_shadow_node(self, node):
        rr = node.get_outline()
        b = rr.bounds
        color = node.get_color()
        dx, dy = node.get_dx(), node.get_dy()
        spread = node.get_spread()
        blur = max(0.001, node.get_blur_radius())
        fid = self._id('shadow')
        self.defs.append(
            '<filter id="%s" x="-50%%" y="-50%%" width="200%%" height="200%%">'
            '<feGaussianBlur stdDeviation="%s"/></filter>' % (fid, _num(blur / 2.0)))
        sb = Graphene.Rect().init(b.get_x() + dx - spread,
                                  b.get_y() + dy - spread,
                                  b.get_width() + 2 * spread,
                                  b.get_height() + 2 * spread)
        d = _rounded_d(sb, [max(0.0, c + spread) for c in _rounded_corners(rr)])
        return '<path d="%s" fill="%s" filter="url(#%s)"/>' % (d, _rgba(color), fid)

    def n_inset_shadow_node(self, node):
        rr = node.get_outline()
        b = rr.bounds
        color = node.get_color()
        dx, dy = node.get_dx(), node.get_dy()
        blur = max(1.0, node.get_blur_radius())
        fid = self._id('inset')
        self.defs.append(
            '<filter id="%s" x="-50%%" y="-50%%" width="200%%" height="200%%">'
            '<feOffset dx="%s" dy="%s" result="o"/>'
            '<feGaussianBlur in="o" stdDeviation="%s" result="b"/>'
            '<feComposite in="b" in2="SourceGraphic" operator="arithmetic" '
            'k2="-1" k3="1"/></filter>'
            % (fid, _num(dx), _num(dy), _num(blur / 2.0)))
        d = _rounded_d(b, _rounded_corners(rr))
        return '<path d="%s" fill="%s" filter="url(#%s)"/>' % (d, _rgba(color), fid)

    def n_shadow_node(self, node):
        child = self._node(node.get_child())
        shadows = []
        n = node.get_n_shadows()
        for i in range(n):
            s = node.get_shadow(i)
            shadows.append('<feDropShadow dx="%s" dy="%s" stdDeviation="%s" '
                           'flood-color="%s"/>'
                           % (_num(s.dx), _num(s.dy), _num(max(0.001, s.radius / 2.0)),
                              _rgba(s.color)))
        if not shadows:
            return child
        fid = self._id('sh')
        self.defs.append('<filter id="%s" x="-50%%" y="-50%%" width="200%%" '
                         'height="200%%">%s</filter>' % (fid, ''.join(shadows)))
        return '<g filter="url(#%s)">%s</g>' % (fid, child)

    def n_blur_node(self, node):
        blur = max(0.001, node.get_radius())
        fid = self._id('blur')
        self.defs.append('<filter id="%s" x="-50%%" y="-50%%" width="200%%" '
                         'height="200%%"><feGaussianBlur stdDeviation="%s"/>'
                         '</filter>' % (fid, _num(blur / 2.0)))
        return '<g filter="url(#%s)">%s</g>' % (fid, self._node(node.get_child()))

    def n_blend_node(self, node):
        mode = {
            'multiply': 'multiply', 'screen': 'screen', 'overlay': 'overlay',
            'darken': 'darken', 'lighten': 'lighten',
            'color-dodge': 'color-dodge', 'color-burn': 'color-burn',
            'hard-light': 'hard-light', 'soft-light': 'soft-light',
            'difference': 'difference', 'exclusion': 'exclusion',
            'hue': 'hue', 'saturation': 'saturation', 'color': 'color',
            'luminosity': 'luminosity',
        }.get(node.get_blend_mode().value_nick, 'normal')
        return ('<g style="isolation:isolate">%s'
                '<g style="mix-blend-mode:%s">%s</g></g>'
                % (self._node(node.get_bottom_child()), mode,
                   self._node(node.get_top_child())))

    def n_cross_fade_node(self, node):
        p = max(0.0, min(1.0, node.get_progress()))
        return ('%s<g opacity="%s">%s</g>'
                % (self._node(node.get_start_child()), _num(p),
                   self._node(node.get_end_child())))

    def n_cairo_node(self, node):
        b = node.get_bounds()
        surf = node.get_surface()
        if surf is None:
            return ''
        w = max(1, int(math.ceil(b.get_width())))
        h = max(1, int(math.ceil(b.get_height())))
        try:
            import cairo
            img = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            cr = cairo.Context(img)
            cr.set_source_surface(surf, 0, 0)
            cr.paint()
            tmp = '/tmp/sz-gsk2svg-%s.png' % self._id('cairo')
            img.write_to_png(tmp)
            with open(tmp, 'rb') as fh:
                data = fh.read()
            import os
            os.unlink(tmp)
        except Exception:
            return ''
        b64 = base64.b64encode(data).decode('ascii')
        return ('<image %s preserveAspectRatio="none" '
                'xlink:href="data:image/png;base64,%s"/>'
                % (_rect_attrs(b), b64))

    def n_repeat_node(self, node):
        b = node.get_bounds()
        child = self._node(node.get_child())
        return '<g clip-path="url(#%s)">%s</g>' % (
            self._clip(_rounded_d(b, [0, 0, 0, 0]), 'repeat'), child)

    def n_mask_node(self, node):
        source = self._node(node.get_source())
        mask = self._node(node.get_mask())
        mid = self._id('mask')
        self.defs.append('<mask id="%s">%s</mask>' % (mid, mask))
        return '<g mask="url(#%s)">%s</g>' % (mid, source)

    def n_copy_node(self, node):
        return self._node(node.get_child())

    def n_isolation_node(self, node):
        return '<g style="isolation:isolate">%s</g>' % self._node(node.get_child())

    def n_texture_scale_node(self, node):
        b = node.get_bounds()
        tex = node.get_texture()
        data = _texture_png(tex, b.get_width(), b.get_height())
        if not data:
            return ''
        b64 = base64.b64encode(data).decode('ascii')
        return ('<image %s preserveAspectRatio="none" '
                'xlink:href="data:image/png;base64,%s"/>'
                % (_rect_attrs(b), b64))
