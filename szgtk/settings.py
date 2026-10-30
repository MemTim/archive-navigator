# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _, N_
from .display import DISP, format_date, format_size
from .utils import accel_label, accel_variants
from .icons import (FLAG_LINK, FLAG_NOREAD, FLAG_NOWRITE, clear_icon_cache,
                    make_icon_pixbuf)
from .dialogs import (DlgBase, _tab_label, alert, button_row, choose, grid_row,
                      hbox, lbl, make_dd, set_margins, vbox)
from .archive_dialogs import (EXTRACT_PATHMODES, FORMATS, LEVELS,
                              OVERWRITE_MODES)
from .favorites import make as fav_make, name as fav_name, path as fav_path
from .menu_layout import (ALL_CONTEXTS, CONTEXTS, LABELS as MENU_LABELS,
                          contexts as load_menu_contexts, group_selected,
                          hidden as menu_hidden, load as load_menu_layout,
                          normalize as normalize_menu_layout)

# ───────────────────────────── Горячие клавиши ─────────────────────────────
# (id, действие, подпись, по умолчанию, область: global — везде, list — только в списке файлов)
HOTKEYS = [
    ('open-archive', 'open-archive', N_('Open archive…'), '<Ctrl>o', 'global'),
    ('open-inside', 'open-inside', N_('Open inside'), '<Ctrl>Page_Down', 'global'),
    ('open-outside', 'open-outside', N_('Open outside'), '<Shift>Return', 'global'),
    ('view', 'view', N_('View'), 'F3', 'global'),
    ('edit', 'edit', N_('Edit'), 'F4', 'global'),
    ('rename', 'rename', N_('Rename'), 'F2', 'global'),
    ('copy', 'copy', N_('Copy to…'), 'F5', 'global'),
    ('move', 'move', N_('Move to…'), 'F6', 'global'),
    ('copy-selection', 'copy-selection', N_('Copy'), '<Ctrl>c', 'list'),
    ('cut-selection', 'cut-selection', N_('Cut'), '<Ctrl>x', 'list'),
    ('paste', 'paste', N_('Paste'), '<Ctrl>v', 'list'),
    ('undo', 'undo', N_('Undo'), '<Ctrl>z', 'list'),
    ('redo', 'redo', N_('Redo'), '<Ctrl>y', 'list'),
    ('select-all', 'select-all', N_('Select all'), '<Ctrl>a', 'list'),
    ('new-folder', 'new-folder', N_('Create folder'), 'F7', 'global'),
    ('new-file', 'new-file', N_('Create file'), '<Ctrl>n', 'global'),
    ('new-window', 'new-window', N_('New window'), '<Ctrl><Shift>n', 'global'),
    ('delete', 'delete', N_('Delete'), 'Delete', 'list'),
    ('delete-permanent', 'delete-permanent', N_('Delete permanently'), '<Shift>Delete', 'list'),
    ('properties', 'properties', N_('Properties'), '<Alt>Return', 'global'),
    ('add', 'add', N_('Add'), '<Alt>a', 'global'),
    ('extract', 'extract', N_('Extract'), '<Alt>e', 'global'),
    ('test', 'test', N_('Test'), '<Alt>t', 'global'),
    ('info', 'info', N_('Info'), '<Alt>i', 'global'),
    ('search', 'search', N_('Search'), '<Ctrl>f', 'global'),
    ('focus-address', 'focus-address', N_('Focus the address bar'), '<Ctrl>l', 'global'),
    ('refresh', 'refresh', N_('Refresh'), '<Ctrl>r', 'global'),
    ('up', 'up', N_('Up one level'), '<Alt>Up', 'global'),
    ('up-list', 'up', N_('Up one level (file list)'), 'BackSpace', 'list'),
    ('back', 'back', N_('Back'), '<Alt>Left', 'global'),
    ('forward', 'forward', N_('Forward'), '<Alt>Right', 'global'),
    ('root', 'root', N_('Open root folder'), '<Ctrl>backslash', 'global'),
    ('history', 'history', N_('Folders history…'), '<Alt>F12', 'global'),
    ('two-panels', 'two-panels', N_('2 panels'), 'F9', 'global'),
    ('switch-panel', 'switch-panel', N_('Switch panel'), 'Tab', 'list'),
    ('toggle-sidebar', 'toggle-sidebar', N_('Sidebar'), '<Ctrl>b', 'global'),
    ('select-mask', 'select-mask', N_('Select…'), 'KP_Add', 'list'),
    ('deselect-mask', 'deselect-mask', N_('Deselect…'), 'KP_Subtract', 'list'),
    ('invert-sel', 'invert-sel', N_('Invert selection'), 'KP_Multiply', 'list'),
    ('settings', 'settings', N_('Settings…'), '<Ctrl>comma', 'global'),
    ('help', 'help', N_('Contents…'), 'F1', 'global'),
    ('quit', 'quit', N_('Exit'), '<Ctrl>q', 'global'),
    ('view-list', 'view-list', N_('Details'), '<Ctrl>1', 'global'),
    ('view-tiles', 'view-tiles', N_('Tiles'), '<Ctrl>2', 'global'),
    ('zoom-in', 'zoom-in', N_('Zoom in'), '<Ctrl>plus', 'global'),
    ('zoom-out', 'zoom-out', N_('Zoom out'), '<Ctrl>minus', 'global'),
    ('zoom-reset', 'zoom-reset', N_('Actual size'), '<Ctrl>0', 'global'),
    ('open-root', 'open-as-root', N_('Open as root'), '<Ctrl><Shift>r', 'global'),
]
# дополнительные сочетания (работают, пока у основного действия есть сочетание)
EXTRA_ACCELS = {'zoom-in': ['<Ctrl>equal', '<Ctrl>KP_Add'], 'zoom-out': ['<Ctrl>KP_Subtract'],
                'zoom-reset': ['<Ctrl>KP_0']}


def same_accel(a, b):
    """Сочетания совпадают с точностью до русской/латинской раскладки."""
    return bool(a and b and set(accel_variants(a)) & set(accel_variants(b)))


DESIGNS = [
    ('classic', N_('Classic'), N_('Menu, toolbar and one file list')),
    ('dual', N_('Dual-panel'), N_('Source and destination side by side')),
    ('nav', N_('Navigation'), N_('Sidebar with places, favorites and devices')),
]
SCHEMES = [('midnight', N_('Midnight (as in the mockups)')), ('system', N_('Follow system')),
           ('light', N_('Light'))]
DENSITIES = [('compact', N_('Compact')), ('normal', N_('Normal')), ('comfortable', N_('Comfortable'))]
LANGUAGES = [('auto', N_('Auto (system)')), ('en', 'English'), ('ru', 'Русский')]


SIZE_MODES = [('bytes', N_('Bytes (exact)')), ('kb', N_('Kilobytes')), ('mb', N_('Megabytes')),
              ('gb', N_('Gigabytes')), ('adaptive', N_('Adaptive (B, KB, MB, GB…)'))]
SIZE_UNIT_CHOICES = [('si', N_('Decimal: 1000 (kB, MB, GB)')), ('win', N_('Windows: 1024 (KB, MB, GB)')),
                     ('iec', N_('Binary: 1024 (KiB, MiB, GiB)'))]
SIZE_GROUP_CHOICES = [('space', N_('Space')), ('none', N_('None')), ('comma', N_('Comma')), ('dot', N_('Dot'))]
DATE_STYLE_CHOICES = [('iso', N_('Year-Month-Day (2026-10-11)')), ('dmy', N_('Day.Month.Year (11.10.2026)')),
                      ('mdy', N_('Month/Day/Year (10/11/2026)')), ('dmony', N_('Day Month Year (11 Oct 2026)')),
                      ('custom', N_('Custom pattern')), ('none', N_('Hide date'))]
TIME_STYLE_CHOICES = [('hm', N_('24-hour (18:34)')), ('hms', N_('24-hour with seconds (18:34:05)')),
                      ('hm12', N_('12-hour (6:34 PM)')), ('none', N_('Hide time'))]
VIEW_MODES = [('list', N_('Details')), ('tiles', N_('Tiles'))]
BADGE_CHOICES = [('lock', N_('Lock')), ('cross', N_('Cross')), ('link', N_('Link arrow')),
                 ('key', N_('Key')), ('none', N_('None'))]
BADGE_PLATES = [('white', N_('White circle behind the icon')),
                ('theme', N_('Theme background, accent outline and icon'))]


def build_preview(design):
    """Схематичный макет окна (боксы + CSS) для выбора дизайна."""
    def blk(cls, w=-1, h=-1, hexp=False):
        b = Gtk.Box()
        b.add_css_class(cls)
        b.set_size_request(w, h)
        b.set_hexpand(hexp)
        return b

    def rows(n, sel=1):
        v = vbox(3)
        for i in range(n):
            r = blk('sz-pv-rowsel' if i == sel else 'sz-pv-row', (70, 52, 84, 60, 76, 46, 66)[i % 7], 3)
            r.set_halign(Gtk.Align.START)
            v.append(r)
        return v
    root = vbox(3)
    root.add_css_class('sz-pv')
    root.set_size_request(220, 146)
    root.append(blk('sz-pv-menu', -1, 5))
    if design == 'nav':
        body = hbox(3)
        side = vbox(4)
        side.add_css_class('sz-pv-side')
        side.set_size_request(44, -1)
        for w in (30, 24, 28, 22):
            r = blk('sz-pv-row', w, 3)
            r.set_margin_start(4)
            r.set_margin_top(4)
            r.set_halign(Gtk.Align.START)
            side.append(r)
        main = vbox(3)
        main.set_hexpand(True)
        main.append(blk('sz-pv-tool', -1, 12))
        main.append(blk('sz-pv-addr', -1, 8))
        main.append(rows(6))
        body.append(side)
        body.append(main)
    elif design == 'dual':
        root.append(blk('sz-pv-tool', -1, 12))
        body = hbox(4)
        for k in (0, 1):
            col = vbox(3)
            col.set_hexpand(True)
            col.append(blk('sz-pv-hdr', -1, 7))
            col.append(blk('sz-pv-addr' if k == 0 else 'sz-pv-hdr', -1, 8))
            col.append(rows(5, 1 if k == 0 else 2))
            body.append(col)
    else:
        root.append(blk('sz-pv-tool', -1, 12))
        body = vbox(3)
        body.append(blk('sz-pv-addr', -1, 8))
        body.append(rows(7))
    body.set_vexpand(True)
    root.append(body)
    root.append(blk('sz-pv-stat', -1, 4))
    return root


class KeyCaptureDialog(DlgBase):
    def __init__(self, parent, title, scope, on_pick):
        super().__init__(title=_('Shortcut'), modal=True, transient_for=parent, destroy_with_parent=True)
        self.on_pick, self.scope = on_pick, scope
        root = vbox(10, 22)
        self.set_child(root)
        root.append(lbl(_('Press the new shortcut for:')))
        t = lbl(_(title))
        t.add_css_class('sz-title')
        root.append(t)
        h = lbl(_('Esc — cancel, Backspace — clear'))
        h.add_css_class('sz-muted')
        root.append(h)
        kc = Gtk.EventControllerKey()
        kc.connect('key-pressed', self._key)
        self.add_controller(kc)

    def _key(self, ctrl, keyval, keycode, state):
        mods = state & MODMASK
        if not mods and keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if not mods and keyval == Gdk.KEY_BackSpace and self.scope == 'global':
            self.close()
            self.on_pick('')
            return True
        if keyval in MODIFIER_KEYS:
            return True
        if (self.scope == 'global' and not (mods & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK))
                and Gdk.keyval_to_unicode(keyval) != 0):
            alert(self, _('Use Ctrl or Alt together with a letter or digit'))
            return True
        name = Gtk.accelerator_name(Gdk.keyval_to_lower(keyval), mods)
        self.close()
        self.on_pick(name)
        return True


def _fav_arrow(area, cr, w, h):
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    cr.set_line_width(1.6)
    cr.set_line_cap(1)
    y = h / 2
    cr.move_to(1, y)
    cr.line_to(w - 7, y)
    cr.stroke()
    cr.move_to(w - 8, y - 4)
    cr.line_to(w - 2, y)
    cr.line_to(w - 8, y + 4)
    cr.stroke()


def _fav_sort_icon(area, cr, w, h):
    """Ручка перетаскивания: две стрелки и четыре линии (20×21)."""
    c = area.get_color()
    cr.save()
    s = min(w / 20.0, h / 21.0)
    cr.translate((w - 20.0 * s) / 2.0, (h - 21.0 * s) / 2.0)
    cr.scale(s, s)
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    for flip in (False, True):
        cr.save()
        if flip:
            cr.translate(0, 20.917)
            cr.scale(1, -1)
        cr.move_to(3.289, 0.529)
        cr.line_to(0.531, 3.288)
        cr.line_to(2.360, 3.459)
        cr.line_to(2.360, 6.459)
        cr.line_to(4.360, 6.459)
        cr.line_to(4.360, 3.459)
        cr.line_to(6.118, 3.459)
        cr.close_path()
        cr.set_line_width(1)
        cr.set_line_join(1)
        cr.fill_preserve()
        cr.stroke()
        cr.restore()
    cr.set_line_width(2)
    cr.set_line_cap(1)
    for k in range(4):
        y = 4.46 + 4 * k
        cr.move_to(8.36, y)
        cr.line_to(18.36, y)
    cr.stroke()
    cr.restore()


def _fav_x(area, cr, w, h):
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    cr.set_line_width(2.2)
    cr.set_line_cap(1)
    cr.move_to(4, 4)
    cr.line_to(w - 4, h - 4)
    cr.move_to(w - 4, 4)
    cr.line_to(4, h - 4)
    cr.stroke()


def _fav_plus(area, cr, w, h):
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    cr.set_line_width(3.0)
    cr.set_line_cap(1)
    cx, cy = w / 2, h / 2
    cr.move_to(cx - 9, cy)
    cr.line_to(cx + 9, cy)
    cr.move_to(cx, cy - 9)
    cr.line_to(cx, cy + 9)
    cr.stroke()


def _menu_eye_open(area, cr, w, h):
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    cr.set_line_width(1.7)
    cr.set_line_cap(1)
    cy = h / 2
    cr.move_to(2, cy)
    cr.curve_to(w * 0.22, 3, w * 0.78, 3, w - 2, cy)
    cr.curve_to(w * 0.78, h - 3, w * 0.22, h - 3, 2, cy)
    cr.stroke()
    cr.arc(w / 2, cy, 3.0, 0, 2 * math.pi)
    cr.fill()


def _menu_eye_closed(area, cr, w, h):
    c = area.get_color()
    _menu_eye_open(area, cr, w, h)
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    cr.set_line_width(2.0)
    cr.set_line_cap(1)
    cr.move_to(3, h - 3)
    cr.line_to(w - 3, 3)
    cr.stroke()


def _menu_more(area, cr, w, h):
    """Вертикальное троеточие."""
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    for y in (h / 2 - 6, h / 2, h / 2 + 6):
        cr.arc(w / 2, y, 1.8, 0, 2 * math.pi)
        cr.fill()


def _menu_group_icon(area, cr, w, h):
    """Иконка группы: два перекрывающихся скруглённых квадрата."""
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    scale = min(w, h) / 18.0
    cr.save()
    cr.translate((w - 18 * scale) / 2, (h - 18 * scale) / 2)
    cr.scale(scale, scale)
    for x, y in ((0, 0), (6, 6)):
        r = 1.615
        cr.new_sub_path()
        cr.arc(x + 12 - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + 12 - r, y + 12 - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + 12 - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
    cr.fill()
    cr.restore()


def _drawing(w, h, fn, cls):
    a = Gtk.DrawingArea()
    a.set_content_width(w)
    a.set_content_height(h)
    a.set_halign(Gtk.Align.CENTER)
    a.set_valign(Gtk.Align.CENTER)
    a.set_can_target(False)
    a.set_focusable(False)
    a.add_css_class(cls)
    a.set_draw_func(fn)
    return a


class SettingsDialog(DlgBase):
    def __init__(self, win, conf, on_apply, page=0):
        super().__init__(title=_('Settings'), modal=True, transient_for=win, destroy_with_parent=True)
        self.win, self.conf, self.on_apply = win, conf, on_apply
        self.add_css_class('sz-settings')
        self.set_default_size(820, 680)
        self.accels = {h[0]: conf['accels'].get(h[0], h[3]) for h in HOTKEYS}
        root = vbox(10, 14)
        self.set_child(root)
        nb = Gtk.Notebook(vexpand=True)
        self.nb = nb
        root.append(nb)
        nb.append_page(self._page_general(), _tab_label(_('General')))
        nb.append_page(self._page_favorites(), _tab_label(_('Favorites')))
        nb.append_page(self._page_appearance(), _tab_label(_('Appearance')))
        nb.append_page(self._page_display(), _tab_label(_('Display')))
        nb.append_page(self._page_language(), _tab_label(_('Language')))
        nb.append_page(self._page_hotkeys(), _tab_label(_('Hotkeys')))
        nb.set_current_page(max(0, min(int(page), nb.get_n_pages() - 1)))
        brow, ok = button_row(self, _('OK'), self._ok)
        root.append(brow)

    # ---------- Общие ----------
    def _page_general(self):
        c = self.conf
        pg = vbox(8, 16)
        self.checks = {}
        for key, text in (('show_hidden', N_('Show hidden files')),
                          ('single_click', N_('Single-click to open an item')),
                          ('use_trash', N_('Move deleted files to the Trash')),
                          ('confirm_delete', N_('Confirm file deletion'))):
            cb = Gtk.CheckButton(label=_(text))
            cb.set_active(bool(c[key]))
            self.checks[key] = cb
            pg.append(cb)
        g = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.dd_start = make_dd([_('Home folder'), _('Last used folder')],
                                1 if c['restore_last_dir'] else 0)
        grid_row(g, 0, _('On startup:'), self.dd_start)
        self.e_view = Gtk.Entry(hexpand=True, text=c['viewer'], placeholder_text='xdg-open')
        self.e_edit = Gtk.Entry(hexpand=True, text=c['editor'], placeholder_text='xdg-open')
        grid_row(g, 1, _('Viewer:'), self.e_view)
        grid_row(g, 2, _('Editor:'), self.e_edit)
        fm = c['add_format'] if c['add_format'] in FORMATS else '7z'
        lv = [x[0] for x in LEVELS]
        self.dd_fmt = make_dd(FORMATS, FORMATS.index(fm))
        self.dd_lvl = make_dd([_(x[1]) for x in LEVELS], lv.index(c['add_level']) if c['add_level'] in lv else 3)
        ov = [x[0] for x in OVERWRITE_MODES]
        pm = [x[0] for x in EXTRACT_PATHMODES]
        self.dd_over = make_dd([_(x[1]) for x in OVERWRITE_MODES], ov.index(c['extract_overwrite']) if c['extract_overwrite'] in ov else 0)
        self.dd_pm = make_dd([_(x[1]) for x in EXTRACT_PATHMODES], pm.index(c['extract_pathmode']) if c['extract_pathmode'] in pm else 0)
        grid_row(g, 3, _('Default archive format:'), self.dd_fmt)
        grid_row(g, 4, _('Default compression level:'), self.dd_lvl)
        grid_row(g, 5, _('Default overwrite mode:'), self.dd_over)
        grid_row(g, 6, _('Default path mode:'), self.dd_pm)
        pg.append(g)
        self.c_ta = Gtk.CheckButton(label=_('Select files by typing their name'))
        self.c_ta.set_active(bool(c['typeahead']))
        pg.append(self.c_ta)
        g2 = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.sp_ta = Gtk.SpinButton.new_with_range(0, 10000, 100)
        self.sp_ta.set_value(int(c['typeahead_timeout']))
        self.sp_ta.set_tooltip_text(_('Typed text is cleared after this pause. 0 — only Esc clears it.'))
        grid_row(g2, 0, _('Reset typed text after (ms):'), self.sp_ta)
        pg.append(g2)
        n = lbl(_('Type a name (e.g. "Docu") to select the first match; Esc or a pause clears the text.'))
        n.add_css_class('sz-muted')
        n.set_wrap(True)
        pg.append(n)
        return pg

    # ---------- Избранное ----------
    def _page_favorites(self):
        pg = vbox(8, 16)
        self.fav_model = []
        for k in sorted(self.conf['favorites'], key=lambda x: int(x) if str(x).isdigit() else 99):
            v = self.conf['favorites'][k]
            p = fav_path(v)
            if p:
                self.fav_model.append((p, fav_name(v)))
        self.fav_sel = 0 if self.fav_model else -1
        self.fav_rows_box = vbox(8)
        pg.append(self.fav_rows_box)
        self.fav_add = Gtk.Button()
        self.fav_add.add_css_class('sz-fav-add')
        self.fav_add.set_tooltip_text(_('Add'))
        self.fav_add.set_child(_drawing(28, 28, _fav_plus, 'sz-fav-plus'))
        self.fav_add.connect('clicked', lambda b: self._fav_add())
        pg.append(self.fav_add)
        sw = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(pg)
        self._fav_rebuild()
        return sw

    def _fav_row(self, idx):
        path, name = self.fav_model[idx]
        row = hbox(8)
        row.add_css_class('sz-fav-row')
        if idx == self.fav_sel:
            row.add_css_class('sz-fav-sel')
        click = Gtk.GestureClick()
        click.connect('pressed', lambda g, n, x, y, i=idx: self._fav_select(i))
        row.add_controller(click)
        num = lbl('%d.' % (idx + 1), 0.5)
        num.add_css_class('sz-fav-num')
        num.set_size_request(30, -1)
        e_path = Gtk.Entry(hexpand=True, text=path, placeholder_text=_('Path'))
        e_path.add_css_class('sz-fav-field')
        e_path.set_size_request(-1, 34)
        arrow = _drawing(44, 18, _fav_arrow, 'sz-fav-arrow')
        e_name = Gtk.Entry(hexpand=True, text=name, placeholder_text=_('Name'))
        e_name.add_css_class('sz-fav-field')
        e_name.set_size_request(-1, 34)
        e_name.set_tooltip_text(_('Leave empty to use the folder name'))
        for entry in (e_path, e_name):
            fc = Gtk.EventControllerFocus()
            fc.connect('enter', lambda c, i=idx: self._fav_select(i))
            entry.add_controller(fc)
        sort = Gtk.Button()
        sort.add_css_class('sz-fav-sort')
        sort.update_property([Gtk.AccessibleProperty.LABEL], [_('Change order')])
        sort.set_child(_drawing(22, 22, _fav_sort_icon, 'sz-fav-sort-icon'))
        sort.connect('clicked', lambda b, i=idx: self._fav_sort_menu(b, i))
        rm = Gtk.Button()
        rm.add_css_class('sz-fav-del')
        rm.set_tooltip_text(_('Remove from Favorites'))
        rm.set_child(_drawing(20, 20, _fav_x, 'sz-fav-x'))
        rm.connect('clicked', lambda b, i=idx: self._fav_remove(i))
        for w in (num, e_path, arrow, e_name, sort, rm):
            if isinstance(w, (Gtk.Label, Gtk.Entry)):
                w.set_valign(Gtk.Align.CENTER)
            row.append(w)
        self.fav_rows.append({'row': row, 'path': e_path, 'name': e_name, 'num': num, 'sort': sort})
        return row

    def _fav_collect(self):
        if not hasattr(self, 'fav_rows'):
            return
        self.fav_model = [(r['path'].get_text(), r['name'].get_text()) for r in self.fav_rows]

    def _fav_select(self, idx):
        if idx == self.fav_sel or not (0 <= idx < len(getattr(self, 'fav_rows', ()))):
            return
        self.fav_sel = idx
        for i, r in enumerate(self.fav_rows):
            if i == idx:
                r['row'].add_css_class('sz-fav-sel')
            else:
                r['row'].remove_css_class('sz-fav-sel')

    def _fav_rebuild(self):
        ch = self.fav_rows_box.get_first_child()
        while ch is not None:
            nxt = ch.get_next_sibling()
            self.fav_rows_box.remove(ch)
            ch = nxt
        self.fav_rows = []
        if self.fav_model:
            self.fav_sel = max(0, min(getattr(self, 'fav_sel', 0), len(self.fav_model) - 1))
        else:
            self.fav_sel = -1
        for i in range(len(self.fav_model)):
            self.fav_rows_box.append(self._fav_row(i))
        self.fav_add.set_sensitive(len(self.fav_model) < 10)

    def _fav_add(self):
        if len(self.fav_model) >= 10:
            return
        self._fav_collect()
        self.fav_model.append(('', ''))
        self.fav_sel = len(self.fav_model) - 1
        self._fav_rebuild()
        GLib.idle_add(lambda: (self.fav_rows[-1]['path'].grab_focus(), False)[1])

    def _fav_remove(self, idx):
        self._fav_collect()
        if 0 <= idx < len(self.fav_model):
            del self.fav_model[idx]
            if self.fav_sel > idx:
                self.fav_sel -= 1
            elif self.fav_sel == idx:
                self.fav_sel = min(idx, len(self.fav_model) - 1)
            self._fav_rebuild()

    def _fav_move(self, idx, delta):
        self._fav_collect()
        j = idx + delta
        if 0 <= j < len(self.fav_model):
            self.fav_model[idx], self.fav_model[j] = self.fav_model[j], self.fav_model[idx]
            self.fav_sel = j
            self._fav_rebuild()

    def _fav_sort_menu(self, btn, idx):
        self._fav_select(idx)
        pop = Gtk.Popover()
        box = vbox(2, 6)
        up = Gtk.Button(label=_('Move up'))
        up.set_sensitive(idx > 0)
        down = Gtk.Button(label=_('Move down'))
        down.set_sensitive(idx < len(self.fav_model) - 1)

        def move(delta):
            pop.popdown()
            pop.unparent()
            self._fav_move(idx, delta)

        up.connect('clicked', lambda b: move(-1))
        down.connect('clicked', lambda b: move(1))
        for w in (up, down):
            w.set_halign(Gtk.Align.FILL)
            box.append(w)
        pop.set_child(box)
        pop.set_parent(btn)
        pop.connect('closed', lambda p: p.unparent())
        pop.popup()

    # ---------- Оформление ----------
    def _page_appearance(self):
        c = self.conf
        pg = vbox(10, 16)
        t = lbl(_('Design'))
        t.add_css_class('sz-title')
        pg.append(t)
        row = hbox(10)
        row.set_homogeneous(True)
        self.design_radios, self.cards, first = {}, {}, None
        for key, name, desc in DESIGNS:
            card = vbox(6)
            card.add_css_class('sz-card')
            card.append(build_preview(key))
            rb = Gtk.CheckButton(label=_(name))
            if first is None:
                first = rb
            else:
                rb.set_group(first)
            card.append(rb)
            cap = lbl(_(desc))
            cap.add_css_class('sz-muted')
            cap.set_wrap(True)
            cap.set_max_width_chars(26)
            card.append(cap)
            g = Gtk.GestureClick()
            g.connect('pressed', lambda gg, n, x, y, r=rb: r.set_active(True))
            card.add_controller(g)
            rb.connect('toggled', lambda r: self._sync_cards())
            self.design_radios[key], self.cards[key] = rb, card
            row.append(card)
        self.design_radios[c['design'] if c['design'] in self.design_radios else 'classic'].set_active(True)
        self._sync_cards()
        pg.append(row)
        g = Gtk.Grid(row_spacing=8, column_spacing=12)
        sc = [x[0] for x in SCHEMES]
        dn = [x[0] for x in DENSITIES]
        self.dd_scheme = make_dd([_(x[1]) for x in SCHEMES], sc.index(c['scheme']) if c['scheme'] in sc else 0)
        self.dd_density = make_dd([_(x[1]) for x in DENSITIES], dn.index(c['density']) if c['density'] in dn else 1)
        grid_row(g, 0, _('Color scheme:'), self.dd_scheme)
        grid_row(g, 1, _('Row density:'), self.dd_density)
        bp = [x[0] for x in BADGE_PLATES]
        current_plate = c.get('badge_plate', 'white')
        self.dd_badge_plate = make_dd([_(x[1]) for x in BADGE_PLATES],
                                      bp.index(current_plate) if current_plate in bp else 0)
        grid_row(g, 2, _('Badge background:'), self.dd_badge_plate)
        pg.append(g)
        self.c_hints = Gtk.CheckButton(label=_('Show shortcut hints in the status bar'))
        self.c_hints.set_active(bool(c['show_hints']))
        self.c_grid = Gtk.CheckButton(label=_('Show grid lines'))
        self.c_grid.set_active(bool(c['grid']))
        pg.append(self.c_hints)
        pg.append(self.c_grid)
        n = lbl(_('The window is reloaded when the design or language changes.'))
        n.add_css_class('sz-muted')
        pg.append(n)
        return pg

    def _sync_cards(self):
        for k, rb in self.design_radios.items():
            (self.cards[k].add_css_class if rb.get_active() else self.cards[k].remove_css_class)('sz-card-sel')


    # ---------- Отображение (размер, дата, вид) ----------
    def _page_display(self):
        c = self.conf

        def idx(choices, val, default=0):
            keys = [x[0] for x in choices]
            return keys.index(val) if val in keys else default

        def title(text):
            t = lbl(text)
            t.add_css_class('sz-title')
            return t
        pg = vbox(10, 16)
        top = vbox(8)
        top.add_css_class('sz-top-panels')
        head = hbox(10)
        txt = vbox(1)
        t = lbl(_('Hide top panels'))
        t.add_css_class('sz-title')
        d = lbl(_('More space for files'))
        d.add_css_class('sz-muted')
        txt.append(t)
        txt.append(d)
        txt.set_hexpand(True)
        self.lbl_top_state = lbl(_('Off'))
        self.sw_top = Gtk.Switch()
        self.sw_top.set_valign(Gtk.Align.CENTER)
        head.append(txt)
        head.append(self.lbl_top_state)
        head.append(self.sw_top)
        top.append(head)
        hint = lbl(_('Turn off the mode so both panels are always visible.'))
        hint.add_css_class('sz-muted')
        hint.set_wrap(True)
        top.append(hint)
        self.top_radios = {}
        first = None
        for key, name, desc in (
                ('menu', _('Hide menu bar'), _('File, Edit, View and other menus')),
                ('toolbar', _('Hide action panel'), _('Add, Extract, Test and other commands')),
                ('both', _('Hide both panels'), _('Menu bar and action panel'))):
            rb = Gtk.CheckButton()
            rb.add_css_class('sz-radio-card')
            rb.set_hexpand(True)
            if first is None:
                first = rb
            else:
                rb.set_group(first)
            body = vbox(2)
            body.set_hexpand(True)
            tl = lbl(name)
            tl.add_css_class('sz-radio-card-title')
            dl = lbl(desc)
            dl.add_css_class('sz-radio-card-desc')
            dl.set_wrap(True)
            body.append(tl)
            body.append(dl)
            rb.set_child(body)
            rb.connect('toggled', lambda r: self._sync_top_panels())
            self.top_radios[key] = rb
            top.append(rb)
        self.sw_top.connect('notify::active', lambda s, p: self._sync_top_panels())
        hide_menu = bool(c.get('hide_menu_bar'))
        hide_toolbar = bool(c.get('hide_toolbar'))
        mode = ('both' if hide_menu and hide_toolbar else
                'menu' if hide_menu else 'toolbar' if hide_toolbar else 'both')
        self.top_radios[mode].set_active(True)
        self.sw_top.set_active(hide_menu or hide_toolbar)
        self._sync_top_panels()
        top.append(self._top_panels_info())
        pg.append(top)
        pg.append(title(_('File size')))
        g = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.dd_smode = make_dd([_(x[1]) for x in SIZE_MODES], idx(SIZE_MODES, c['size_mode']))
        self.dd_sunits = make_dd([_(x[1]) for x in SIZE_UNIT_CHOICES], idx(SIZE_UNIT_CHOICES, c['size_units']))
        self.dd_sdec = make_dd(['0', '1', '2', '3'], max(0, min(3, int(c['size_decimals']))))
        self.dd_sgrp = make_dd([_(x[1]) for x in SIZE_GROUP_CHOICES], idx(SIZE_GROUP_CHOICES, c['size_group']))
        self.c_sbyte = Gtk.CheckButton(label=_('Show "B" after byte counts'))
        self.c_sbyte.set_active(bool(c['size_bytes_unit']))
        grid_row(g, 0, _('Size format:'), self.dd_smode)
        grid_row(g, 1, _('Units:'), self.dd_sunits)
        grid_row(g, 2, _('Decimal places:'), self.dd_sdec)
        grid_row(g, 3, _('Thousands separator:'), self.dd_sgrp)
        pg.append(g)
        pg.append(self.c_sbyte)
        pg.append(title(_('Date and time')))
        g2 = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.dd_dstyle = make_dd([_(x[1]) for x in DATE_STYLE_CHOICES], idx(DATE_STYLE_CHOICES, c['date_style']))
        self.dd_tstyle = make_dd([_(x[1]) for x in TIME_STYLE_CHOICES], idx(TIME_STYLE_CHOICES, c['time_style']))
        self.e_custom = Gtk.Entry(hexpand=True, text=c['date_custom'], placeholder_text='%d.%m.%Y %H:%M')
        self.e_custom.set_tooltip_text('%Y %m %d %H %M %S %b %B %a %A %p %I')
        grid_row(g2, 0, _('Date format:'), self.dd_dstyle)
        grid_row(g2, 1, _('Time format:'), self.dd_tstyle)
        grid_row(g2, 2, _('Custom pattern:'), self.e_custom)
        pg.append(g2)
        self.lbl_preview = lbl('')
        self.lbl_preview.set_wrap(True)
        self.lbl_preview.add_css_class('sz-muted')
        pg.append(self.lbl_preview)
        pg.append(title(_('Access badges')))
        self.c_badges = Gtk.CheckButton(label=_('Show access badges'))
        self.c_badges.set_active(bool(c.get('show_badges', True)))
        self.c_badges.set_tooltip_text(_('Lock — no write access, cross — no read access, link — symbolic link'))
        pg.append(self.c_badges)
        g4 = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.badge_dd, self.badge_img = {}, {}
        for r, (key, text, flag) in enumerate((('badge_nowrite', N_('No write access (cannot edit):'), FLAG_NOWRITE),
                                               ('badge_noread', N_('No read access:'), FLAG_NOREAD),
                                               ('badge_link', N_('Symbolic link:'), FLAG_LINK))):
            dd = make_dd([_(x[1]) for x in BADGE_CHOICES], idx(BADGE_CHOICES, c[key]))
            img = Gtk.Image()
            img.set_pixel_size(48)
            row = hbox(10)
            row.append(dd)
            row.append(img)
            grid_row(g4, r, _(text), row)
            dd.connect('notify::selected', self._update_preview)
            self.badge_dd[key], self.badge_img[key] = dd, (img, flag)
        pg.append(g4)
        self.c_badges.connect('toggled', self._update_preview)
        pg.append(title(_('View')))
        g3 = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.dd_view = make_dd([_(x[1]) for x in VIEW_MODES], idx(VIEW_MODES, c['view_mode']))
        grid_row(g3, 0, _('Default view:'), self.dd_view)
        pg.append(g3)
        self.c_thumbs = Gtk.CheckButton(label=_('Show thumbnails in tile view'))
        self.c_thumbs.set_active(bool(c['show_thumbs']))
        pg.append(self.c_thumbs)
        pg.append(title(_('Context menu')))
        hint_row = hbox(8)
        hint = lbl(_('Drag items to reorder. Click the eye to hide or show an item, '
                     'and the three-dot button to choose when it is shown. '
                     'Select two or more items to group them.'))
        hint.add_css_class('sz-muted')
        hint.set_wrap(True)
        hint.set_hexpand(True)
        hint_row.append(hint)
        self.menu_group_btn = Gtk.Button()
        self.menu_group_btn.add_css_class('sz-menu-group')
        self.menu_group_btn.set_focus_on_click(False)
        self.menu_group_btn.set_valign(Gtk.Align.CENTER)
        self.menu_group_btn.set_visible(False)
        self.menu_group_btn.set_tooltip_text(_('Group selected items'))
        group_box = hbox(6)
        group_box.append(_drawing(18, 18, _menu_group_icon, 'sz-menu-group-icon'))
        group_box.append(lbl(_('Group'), 0.5))
        self.menu_group_btn.set_child(group_box)
        self.menu_group_btn.connect('clicked', lambda b: self._menu_group_selected())
        hint_row.append(self.menu_group_btn)
        pg.append(hint_row)
        self.menu_layout = load_menu_layout(c)
        self.menu_hidden = menu_hidden(c)
        self.menu_contexts = load_menu_contexts(c)
        self.menu_selected = set()
        self.menu_rows = []
        self.menu_drag_id = None
        self.menu_drop = None
        self.menu_panel = vbox(0)
        self.menu_panel.add_css_class('sz-menu')
        self.menu_panel.set_size_request(324, -1)
        self.menu_panel.set_halign(Gtk.Align.START)
        self.menu_panel.set_hexpand(False)
        self.menu_box = vbox(0)
        msw = Gtk.ScrolledWindow()
        msw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        msw.set_size_request(-1, 300)
        msw.set_child(self.menu_box)
        self.menu_panel.append(msw)
        pg.append(self.menu_panel)
        self.menu_scroll = msw
        self._menu_rebuild()
        for dd in (self.dd_smode, self.dd_sunits, self.dd_sdec, self.dd_sgrp, self.dd_dstyle, self.dd_tstyle):
            dd.connect('notify::selected', self._update_preview)
        self.e_custom.connect('changed', self._update_preview)
        self.c_sbyte.connect('toggled', self._update_preview)
        self._update_preview()
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(pg)
        return sw

    def _sync_top_panels(self, *a):
        if not hasattr(self, 'sw_top'):
            return
        active = self.sw_top.get_active()
        self.lbl_top_state.set_text(_('On') if active else _('Off'))
        for rb in self.top_radios.values():
            rb.set_sensitive(active)

    def _top_panels_info(self):
        row = hbox(10)
        row.add_css_class('sz-info-box')
        btn = hbox(6)
        btn.add_css_class('sz-panels-preview')
        icon = Gtk.Image.new_from_icon_name('view-dual-symbolic')
        icon.set_pixel_size(16)
        chevron = Gtk.Image.new_from_icon_name('pan-down-symbolic')
        chevron.set_pixel_size(12)
        btn.append(icon)
        btn.append(lbl(_('Panels')))
        btn.append(chevron)
        btn.set_valign(Gtk.Align.CENTER)
        text = lbl(_('You can bring the panels back with the “Panels” button in the navigation bar. '
                     'It is always available.'))
        text.set_wrap(True)
        text.set_hexpand(True)
        row.append(btn)
        row.append(text)
        return row

    def _display_cfg(self):
        return dict(size_mode=SIZE_MODES[self.dd_smode.get_selected()][0],
                    size_units=SIZE_UNIT_CHOICES[self.dd_sunits.get_selected()][0],
                    size_decimals=self.dd_sdec.get_selected(),
                    size_group=SIZE_GROUP_CHOICES[self.dd_sgrp.get_selected()][0],
                    size_bytes_unit=self.c_sbyte.get_active(),
                    date_style=DATE_STYLE_CHOICES[self.dd_dstyle.get_selected()][0],
                    time_style=TIME_STYLE_CHOICES[self.dd_tstyle.get_selected()][0],
                    date_custom=self.e_custom.get_text() or '%Y-%m-%d %H:%M',
                    show_badges=self.c_badges.get_active(),
                    **{k: BADGE_CHOICES[dd.get_selected()][0] for k, dd in self.badge_dd.items()})

    def _update_preview(self, *a):
        if not hasattr(self, 'lbl_preview'):
            return
        cfg = self._display_cfg()
        mode = cfg['size_mode']
        self.c_sbyte.set_sensitive(mode == 'bytes')
        self.dd_sunits.set_sensitive(mode != 'bytes')
        self.dd_sdec.set_sensitive(mode != 'bytes')
        self.e_custom.set_sensitive(cfg['date_style'] == 'custom')
        self.dd_tstyle.set_sensitive(cfg['date_style'] not in ('custom',))
        show_badges = self.c_badges.get_active()
        for dd in self.badge_dd.values():
            dd.set_sensitive(show_badges)
        if GdkPixbuf is not None and hasattr(self, 'badge_img'):
            saved = {k: DISP[k] for k in self.badge_img}
            DISP.update({k: cfg[k] for k in self.badge_img})
            clear_icon_cache()
            fold = Gio.ThemedIcon.new('folder')
            for k, (img, flag) in self.badge_img.items():
                flags = flag if show_badges else 0
                pb = make_icon_pixbuf(fold, 48, flags) or make_icon_pixbuf(Gio.ThemedIcon.new('text-x-generic'), 48, flags)
                if pb is not None:
                    img.set_from_paintable(Gdk.Texture.new_for_pixbuf(pb))
            DISP.update(saved)
            clear_icon_cache()
        sizes = [872, 45279, 1000000, 4269860, 7503829728]
        self.lbl_preview.set_text(_('Preview') + ':  ' + '  ·  '.join(format_size(n, cfg) for n in sizes) +
                                  '\n' + format_date(time.time() - 3 * 86400, cfg))

    # ---------- Контекстное меню ----------
    def _menu_rebuild(self):
        adj = self.menu_scroll.get_vadjustment() if hasattr(self, 'menu_scroll') else None
        value = adj.get_value() if adj is not None else 0
        ch = self.menu_box.get_first_child()
        while ch is not None:
            nxt = ch.get_next_sibling()
            self.menu_box.remove(ch)
            ch = nxt
        self.menu_rows = []
        self.menu_selected.clear()
        if hasattr(self, 'menu_group_btn'):
            self.menu_group_btn.set_visible(False)
        prev_section = None
        for item_id, section in self.menu_layout:
            if prev_section is not None and section != prev_section:
                sep = Gtk.Box()
                sep.add_css_class('sz-menu-sep')
                sep.set_size_request(-1, 1)
                self.menu_box.append(sep)
            prev_section = section
            self.menu_box.append(self._menu_row(item_id))
        if adj is not None:
            def restore():
                adj.set_value(min(value, max(0, adj.get_upper() - adj.get_page_size())))
                return False
            GLib.idle_add(restore)

    def _menu_row(self, item_id):
        hidden = item_id in self.menu_hidden
        row = hbox(6)
        row.add_css_class('sz-menu-item')
        row.add_css_class('sz-menu-row')
        if hidden:
            row.add_css_class('sz-menu-hidden')
        click = Gtk.GestureClick()
        click.set_button(1)
        click.connect('released', self._menu_row_clicked, item_id)
        row.add_controller(click)
        label = lbl(_(MENU_LABELS[item_id]))
        label.add_css_class('sz-menu-label')
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_tooltip_text(_(MENU_LABELS[item_id]))
        handle = Gtk.DrawingArea()
        handle.set_content_width(22)
        handle.set_content_height(22)
        handle.add_css_class('sz-menu-handle')
        handle.set_draw_func(_fav_sort_icon)
        handle.set_tooltip_text(_('Drag to reorder'))
        handle.update_property([Gtk.AccessibleProperty.LABEL], [_('Drag to reorder')])
        handle.set_cursor(Gdk.Cursor.new_from_name('grab'))
        drag = Gtk.GestureDrag()
        drag.connect('drag-begin', self._menu_drag_begin, item_id)
        drag.connect('drag-update', self._menu_drag_update, item_id)
        drag.connect('drag-end', self._menu_drag_end, item_id)
        handle.add_controller(drag)
        eye = Gtk.Button()
        eye.add_css_class('sz-menu-eye')
        eye.set_child(_drawing(22, 22, _menu_eye_closed if hidden else _menu_eye_open,
                               'sz-menu-eye-icon'))
        eye.set_tooltip_text(_('Show') if hidden else _('Hide'))
        eye.update_property([Gtk.AccessibleProperty.LABEL], [eye.get_tooltip_text()])
        eye.connect('clicked', lambda b, i=item_id: self._menu_toggle(i))
        more = Gtk.Button()
        more.add_css_class('sz-menu-more')
        more.set_child(_drawing(20, 20, _menu_more, 'sz-menu-more-icon'))
        conditions_label = _('Display conditions') + ': ' + _(MENU_LABELS[item_id])
        more.set_tooltip_text(conditions_label)
        more.update_property([Gtk.AccessibleProperty.LABEL], [conditions_label])
        more.connect('clicked', lambda b, i=item_id: self._menu_conditions(b, i))
        if item_id in self.menu_contexts:
            more.add_css_class('sz-menu-filtered')
        row.append(label)
        row.append(handle)
        row.append(eye)
        row.append(more)
        self.menu_rows.append({'id': item_id, 'row': row, 'label': label,
                               'eye': eye, 'more': more})
        return row

    def _menu_toggle(self, item_id):
        if item_id in self.menu_hidden:
            self.menu_hidden.discard(item_id)
        else:
            self.menu_hidden.add(item_id)
        hidden = item_id in self.menu_hidden
        for r in self.menu_rows:
            if r['id'] != item_id:
                continue
            (r['row'].add_css_class if hidden else r['row'].remove_css_class)('sz-menu-hidden')
            r['eye'].set_child(_drawing(22, 22, _menu_eye_closed if hidden else _menu_eye_open,
                                        'sz-menu-eye-icon'))
            text = _('Show') if hidden else _('Hide')
            r['eye'].set_tooltip_text(text)
            r['eye'].update_property([Gtk.AccessibleProperty.LABEL], [text])
            break

    def _menu_row_clicked(self, gesture, n_press, x, y, item_id):
        if n_press != 1:
            return
        row = gesture.get_widget()
        target = row.pick(x, y, Gtk.PickFlags.DEFAULT)
        widget = target
        while widget is not None and widget is not row:
            if isinstance(widget, Gtk.Button) or widget.has_css_class('sz-menu-handle'):
                return
            widget = widget.get_parent()
        self._menu_select_toggle(item_id)

    def _menu_select_toggle(self, item_id):
        if item_id in self.menu_selected:
            self.menu_selected.discard(item_id)
        else:
            self.menu_selected.add(item_id)
        for r in self.menu_rows:
            if r['id'] == item_id:
                (r['row'].add_css_class if item_id in self.menu_selected
                 else r['row'].remove_css_class)('sz-menu-selected')
                break
        count = len(self.menu_selected)
        self.menu_group_btn.set_visible(count >= 2)
        if count >= 2:
            self.menu_group_btn.set_tooltip_text(
                _('Group selected items ({0})').format(count))

    def _menu_group_selected(self):
        if len(self.menu_selected) < 2:
            return
        self.menu_layout = group_selected(self.menu_layout, self.menu_selected)
        self._menu_rebuild()

    def _menu_conditions(self, btn, item_id):
        pop = Gtk.Popover()
        box = vbox(4, 10)
        title = lbl(_('Display conditions'))
        title.add_css_class('sz-title')
        box.append(title)
        hint = lbl(_('If all are checked, there are no additional restrictions. '
                     'If none are checked, the item is never shown.'))
        hint.add_css_class('sz-muted')
        hint.set_wrap(True)
        hint.set_max_width_chars(32)
        box.append(hint)
        allowed = self.menu_contexts.get(item_id)
        checked = set(ALL_CONTEXTS) if allowed is None else set(allowed)
        for context_id, text in CONTEXTS:
            cb = Gtk.CheckButton(label=_(text))
            cb.set_active(context_id in checked)
            cb.connect('toggled', lambda c, cid=context_id, i=item_id:
                       self._menu_context_toggle(i, cid, c.get_active()))
            box.append(cb)
        pop.set_child(box)
        pop.set_parent(btn)
        pop.connect('closed', lambda p: p.unparent())
        pop.popup()

    def _menu_context_toggle(self, item_id, context_id, active):
        allowed = set(self.menu_contexts.get(item_id, ALL_CONTEXTS))
        if active:
            allowed.add(context_id)
        else:
            allowed.discard(context_id)
        if allowed == set(ALL_CONTEXTS):
            self.menu_contexts.pop(item_id, None)
        else:
            self.menu_contexts[item_id] = allowed
        self._menu_update_more(item_id)

    def _menu_update_more(self, item_id):
        for r in self.menu_rows:
            if r['id'] != item_id:
                continue
            (r['more'].add_css_class if item_id in self.menu_contexts
             else r['more'].remove_css_class)('sz-menu-filtered')
            break

    def _menu_drag_begin(self, gesture, start_x, start_y, item_id):
        self.menu_drag_id = item_id
        self.menu_drop = None
        for r in self.menu_rows:
            if r['id'] == item_id:
                r['row'].add_css_class('sz-menu-dragging')

    def _menu_drag_update(self, gesture, offset_x, offset_y, item_id):
        for r in self.menu_rows:
            r['row'].remove_css_class('sz-menu-drop')
        self.menu_drop = None
        if Graphene is None:
            return
        ok, sx, sy = gesture.get_start_point()
        if not ok:
            return
        ok, pt = gesture.get_widget().compute_point(
            self.menu_box, Graphene.Point().init(sx + offset_x, sy + offset_y))
        if not ok:
            return
        for r in self.menu_rows:
            alloc = r['row'].get_allocation()
            if alloc.y <= pt.y <= alloc.y + alloc.height:
                if r['id'] != item_id:
                    r['row'].add_css_class('sz-menu-drop')
                    self.menu_drop = (r['id'], pt.y > alloc.y + alloc.height / 2)
                break

    def _menu_drag_end(self, gesture, offset_x, offset_y, item_id):
        for r in self.menu_rows:
            r['row'].remove_css_class('sz-menu-dragging')
            r['row'].remove_css_class('sz-menu-drop')
        drop, self.menu_drop, self.menu_drag_id = self.menu_drop, None, None
        if drop:
            self._menu_move(item_id, drop[0], drop[1])

    def _menu_move(self, src_id, dst_id, after):
        if src_id == dst_id:
            return
        ids = [item_id for item_id, _section in self.menu_layout]
        if src_id not in ids or dst_id not in ids:
            return
        entry = self.menu_layout.pop(ids.index(src_id))
        ids = [item_id for item_id, _section in self.menu_layout]
        dst = ids.index(dst_id)
        section = self.menu_layout[dst][1]
        self.menu_layout.insert(dst + (1 if after else 0), (entry[0], section))
        self.menu_layout = normalize_menu_layout(self.menu_layout)
        self._menu_rebuild()

    # ---------- Язык ----------
    def _page_language(self):
        pg = vbox(10, 16)
        t = lbl(_('Interface language'))
        t.add_css_class('sz-title')
        pg.append(t)
        codes = [x[0] for x in LANGUAGES]
        self.dd_lang = make_dd([_(x[1]) for x in LANGUAGES],
                               codes.index(self.conf['language']) if self.conf['language'] in codes else 0)
        self.dd_lang.set_halign(Gtk.Align.START)
        pg.append(self.dd_lang)
        n = lbl(_('The window is reloaded when the design or language changes.'))
        n.add_css_class('sz-muted')
        pg.append(n)
        return pg

    # ---------- Горячие клавиши ----------
    def _page_hotkeys(self):
        pg = vbox(8, 12)
        n = lbl(_('Click a shortcut to change it. Shortcuts marked "list" work only in the file list.'))
        n.add_css_class('sz-muted')
        n.set_wrap(True)
        pg.append(n)
        self.hk_list = Gtk.ListBox()
        self.hk_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.hk_buttons = {}
        for hid, action, label, default, scope in HOTKEYS:
            r = hbox(8)
            set_margins(r, 4)
            l = lbl(_(label))
            l.set_hexpand(True)
            r.append(l)
            if scope == 'list':
                tag = lbl(_('list'))
                tag.add_css_class('sz-muted')
                r.append(tag)
            b = Gtk.Button()
            b.set_size_request(170, -1)
            b.connect('clicked', lambda x, h=hid: self._capture(h))
            rst = Gtk.Button(label='↺')
            rst.set_tooltip_text(_('Reset'))
            rst.connect('clicked', lambda x, h=hid: self._set_accel(h, self._default(h)))
            r.append(b)
            r.append(rst)
            self.hk_buttons[hid] = b
            self.hk_list.append(r)
        self._refresh_hk()
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(self.hk_list)
        pg.append(sw)
        reset = Gtk.Button(label=_('Reset all shortcuts'))
        reset.set_halign(Gtk.Align.START)
        reset.connect('clicked', self._reset_all)
        pg.append(reset)
        return pg

    @staticmethod
    def _default(hid):
        return next(h[3] for h in HOTKEYS if h[0] == hid)

    def _refresh_hk(self):
        for hid, b in self.hk_buttons.items():
            b.set_label(accel_label(self.accels[hid]) or '—')

    def _set_accel(self, hid, acc):
        self.accels[hid] = acc
        self._refresh_hk()

    def _reset_all(self, b):
        self.accels = {h[0]: h[3] for h in HOTKEYS}
        self._refresh_hk()

    def _capture(self, hid):
        hk = next(h for h in HOTKEYS if h[0] == hid)

        def picked(acc):
            if acc:
                clash = [o for o in HOTKEYS if o[0] != hid and same_accel(self.accels[o[0]], acc)]
                if clash:
                    def replace():
                        for o in clash:
                            self.accels[o[0]] = ''
                        self._set_accel(hid, acc)
                    choose(self, _('Shortcut already used by "{0}"').format(_(clash[0][2])),
                           [_('Cancel'), _('Replace')], lambda i: replace() if i == 1 else None, cancel=0)
                    return
            self._set_accel(hid, acc)
        KeyCaptureDialog(self, hk[2], hk[4], picked).present()

    # ---------- OK ----------
    def _ok(self):
        c = self.conf
        before = (c['design'], c['language'])
        for k, cb in self.checks.items():
            c[k] = cb.get_active()
        c['restore_last_dir'] = self.dd_start.get_selected() == 1
        c['viewer'], c['editor'] = self.e_view.get_text().strip(), self.e_edit.get_text().strip()
        c['add_format'] = FORMATS[self.dd_fmt.get_selected()]
        c['add_level'] = LEVELS[self.dd_lvl.get_selected()][0]
        c['extract_overwrite'] = OVERWRITE_MODES[self.dd_over.get_selected()][0]
        c['extract_pathmode'] = EXTRACT_PATHMODES[self.dd_pm.get_selected()][0]
        c['design'] = next(k for k, rb in self.design_radios.items() if rb.get_active())
        c['scheme'] = SCHEMES[self.dd_scheme.get_selected()][0]
        c['density'] = DENSITIES[self.dd_density.get_selected()][0]
        c['badge_plate'] = BADGE_PLATES[self.dd_badge_plate.get_selected()][0]
        c['show_hints'] = self.c_hints.get_active()
        c['grid'] = self.c_grid.get_active()
        c['language'] = LANGUAGES[self.dd_lang.get_selected()][0]
        c.update(self._display_cfg())
        if self.sw_top.get_active():
            mode = next((k for k, rb in self.top_radios.items() if rb.get_active()), 'both')
            c['hide_menu_bar'] = mode in ('menu', 'both')
            c['hide_toolbar'] = mode in ('toolbar', 'both')
        else:
            c['hide_menu_bar'] = c['hide_toolbar'] = False
        c['typeahead'] = self.c_ta.get_active()
        c['typeahead_timeout'] = int(self.sp_ta.get_value())
        c['view_mode'] = VIEW_MODES[self.dd_view.get_selected()][0]
        c['show_thumbs'] = self.c_thumbs.get_active()
        c['menu_layout'] = [[item_id, section] for item_id, section in self.menu_layout]
        c['menu_hidden'] = [item_id for item_id, _section in self.menu_layout
                            if item_id in self.menu_hidden]
        c['menu_contexts'] = {
            item_id: [context_id for context_id in ALL_CONTEXTS if context_id in allowed]
            for item_id, allowed in self.menu_contexts.items()
            if set(allowed) != set(ALL_CONTEXTS)}
        c['accels'] = {h[0]: self.accels[h[0]] for h in HOTKEYS if self.accels[h[0]] != h[3]}
        self._fav_collect()
        favs, n = {}, 0
        for path, name in self.fav_model:
            path = os.path.expanduser(path.strip())
            if not path:
                continue
            favs[str(n)] = fav_make(path, name)
            n += 1
        c['favorites'] = favs
        c.save()
        self.close()
        self.on_apply((c['design'], c['language']) != before)
