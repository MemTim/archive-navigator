# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _, N_
from .display import DISP, format_date, format_size
from .utils import Item, dir_icon, icon_for, is_archive_name
from .backend import needs_password
from .icons import (FLAG_LINK, FLAG_NOREAD, FLAG_NOWRITE, badge_texture,
                    make_icon_pixbuf, square_pixbuf)
from .theme import PAL, DENSITY_YPAD
from . import vfs
from .dialogs import alert, hbox, lbl, pick_icon, set_margins, vbox

# ───────────────────────────── панель файлового менеджера ─────────────────────────────
(C_ICON, C_NAME, C_DIR, C_SIZE, C_PACKED, C_MTIME, C_ATTR, C_CRC, C_METHOD, C_ENC,
 C_FULL, C_FLAGS, C_ORD) = range(13)
C_EXT = 100
LIST_SIZES = [16, 32]          # ячейка списка поддерживает только 16 и 32 px
TILE_SIZES = [32, 48, 64, 80, 96, 128, 160, 192, 256]
THUMB_MAX_BYTES = 80 * 1024 * 1024
VIDEO_EXTS = {'mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'm4v', 'mpg', 'mpeg', 'ts', 'ogv'}
_thumb_state = {'pool': None, 'exts': None}


def thumb_pool():
    if _thumb_state['pool'] is None:
        import concurrent.futures
        _thumb_state['pool'] = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    return _thumb_state['pool']


def image_exts():
    if _thumb_state['exts'] is None:
        exts = set()
        if GdkPixbuf is not None:
            for f in GdkPixbuf.Pixbuf.get_formats():
                exts.update(e.lower() for e in f.get_extensions())
        _thumb_state['exts'] = exts
    return _thumb_state['exts']


def _system_thumb(path, mtime, size):
    """Миниатюра из общего кэша freedesktop (~/.cache/thumbnails), если она есть и актуальна."""
    import hashlib
    uri = Gio.File.new_for_path(path).get_uri()
    name = hashlib.md5(uri.encode()).hexdigest() + '.png'
    base = os.path.join(GLib.get_user_cache_dir(), 'thumbnails')
    order = ['normal', 'large', 'x-large', 'xx-large'] if size <= 128 else ['large', 'x-large', 'xx-large', 'normal']
    for d in order:
        p = os.path.join(base, d, name)
        if os.path.exists(p):
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(p)
                tm = pb.get_option('tEXt::Thumb::MTime')
                if tm and int(tm) != int(mtime):
                    continue
                return pb
            except Exception:
                continue
    return None


def make_thumbnail(path, size):
    """Выполняется в потоке. -> GdkPixbuf или None."""
    try:
        st = os.stat(path)
        ext = os.path.splitext(path)[1][1:].lower()
        pb = None
        if ext in image_exts() and st.st_size <= THUMB_MAX_BYTES:
            info = GdkPixbuf.Pixbuf.get_file_info(path)
            if info and info[0] is not None:
                if max(info[1], info[2]) <= size:
                    pb = GdkPixbuf.Pixbuf.new_from_file(path)
                else:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)
                pb = pb.apply_embedded_orientation() or pb
        if pb is None:
            pb = _system_thumb(path, st.st_mtime, size)
        if pb is None and ext in VIDEO_EXTS and shutil.which('ffmpegthumbnailer'):
            fd, tmp = tempfile.mkstemp(suffix='.png', prefix='7zgtk-th-')
            os.close(fd)
            try:
                subprocess.run(['ffmpegthumbnailer', '-i', path, '-o', tmp, '-s', str(size), '-f'],
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=20)
                if os.path.getsize(tmp) > 0:
                    pb = GdkPixbuf.Pixbuf.new_from_file(tmp)
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass
        if pb is not None and max(pb.get_width(), pb.get_height()) > size:
            pb = pb.scale_simple(*_fit(pb.get_width(), pb.get_height(), size), GdkPixbuf.InterpType.BILINEAR)
        return pb
    except Exception:
        return None


def _fit(w, h, size):
    k = size / float(max(w, h))
    return max(1, int(w * k)), max(1, int(h * k))

# (индекс, заголовок, вид) — все колонки, кроме «Имя»
COLUMNS = [(C_SIZE, N_('Size'), 'size'), (C_PACKED, N_('Packed Size'), 'size'),
           (C_MTIME, N_('Modified'), 'time'), (C_ATTR, N_('Attributes'), 'attr'),
           (C_CRC, 'CRC', 'text'), (C_METHOD, N_('Method'), 'text'), (C_ENC, N_('Encrypted'), 'text')]
ARC_ONLY_COLS = {C_PACKED, C_CRC, C_METHOD, C_ENC}


class TileItem(GObject.Object):
    """Элемент модели плиток (позиция в модели совпадает с индексом в отсортированной модели)."""

    def __init__(self, name, is_dir, full, size, icon, flags, index):
        super().__init__()
        self.name, self.is_dir, self.full, self.size = name, is_dir, full, size
        self.icon, self.flags, self.index = icon, flags, index


class TileParts:
    """Виджеты одной плитки (чтобы обновлять их без пересоздания)."""
    pass


class _InlineView(Gtk.TextView):
    """Многострочное поле переименования с фиксированным размером.

    Gtk.TextView измеряет высоту «для ширины» и при ширине 0 в оверлее
    запрашивает огромную высоту, поэтому измерение переопределяем.
    """
    def __init__(self):
        super().__init__()
        self.req = (120, 28)

    def do_measure(self, orientation, for_size):
        w, h = self.req
        if orientation == Gtk.Orientation.HORIZONTAL:
            return (w, w, -1, -1)
        return (h, h, -1, -1)


class ArcState:
    def __init__(self, path, header, entries, password, parent=None, tmp=None, source=None):
        self.path, self.header, self.entries = path, header, entries
        self.password, self.parent, self.tmp = password, parent, tmp
        self.source = source or path
        self.sub, self.flat = '', False
        if parent is None:
            self.display = vfs.display(self.source)
        else:
            self.display = (parent.display + ('/' + parent.sub if parent.sub else '') +
                            '/' + os.path.basename(path))

    def chain(self):
        a = self
        while a is not None:
            yield a
            a = a.parent

    def has_dir(self, sub):
        pre = sub + '/'
        return any(e.path == sub or e.path.startswith(pre) for e in self.entries)


class Panel(Gtk.Box):
    def __init__(self, win, path):
        super().__init__(orientation=V, spacing=0)
        self.win, self.mode, self.path, self.arc = win, 'fs', path, None
        self.design = win.conf['design']
        self.history, self.hpos, self.details = [], -1, True
        self._hist_view = []          # прокрутка и выделение для записей истории
        self.filter_text, self._last_loc, self.renderers = '', None, []
        self._renaming = False
        self.hdr = self.title_row = self.foot = None
        self.view_mode = win.conf['view_mode'] if win.conf['view_mode'] in ('list', 'tiles') else 'list'
        self._factory_size = None
        self._tiles_keep = set()
        self._scroll_seq = 0
        self._scroll_hid = self._scroll_vid = 0
        self._scroll_sig_adj = self._scroll_target = None
        self._scroll_until, self._scroll_busy = 0.0, False
        self.thumbs, self._thumb_pending, self._thumb_gen, self._thumb_timer = {}, set(), 0, 0
        self._ta_buf, self._ta_ok, self._ta_src = '', True, 0     # выбор набором букв
        self.add_css_class('sz-panel')

        self._build_header()
        self._build_addressbar()
        self._build_titlebar()
        self._build_list()
        self._build_tiles()
        self._build_stack()
        self._build_footer()
        self._attach_controllers(self.tree)
        self._attach_controllers(self.grid, rclick=False)
        # Рамка выделения — только при старте с пустого места: за плиткой сразу тянем файл.
        rb = Gtk.GestureClick()
        rb.set_button(1)
        rb.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        rb.connect('pressed', self._on_tiles_press)
        self.grid.add_controller(rb)
        fc = Gtk.EventControllerFocus()
        fc.connect('enter', lambda c: self.win.set_active(self))
        self.add_controller(fc)
        # плитки, отложенные до показа панели, собираем при её первом map (см. fill)
        self.connect('map', self._on_mapped)

    # ---------- построение ----------
    def _btn(self, icon, tip, cb):
        b = Gtk.Button.new_from_icon_name(icon)
        b.add_css_class('flat')
        b.set_tooltip_text(tip)
        b.set_focus_on_click(False)
        b.connect('clicked', lambda x: cb())
        return b

    def _build_header(self):
        if self.design != 'dual':
            return
        h = hbox(8)
        h.add_css_class('sz-hdr')
        h.append(Gtk.Image.new_from_icon_name(pick_icon('folder-open-symbolic', 'folder-symbolic')))
        self.hdr_role = lbl('')
        self.hdr_role.add_css_class('sz-hdr-role')
        self.hdr_name = lbl('')
        self.hdr_name.add_css_class('sz-muted')
        sp = Gtk.Box()
        sp.set_hexpand(True)
        self.hdr_badge = lbl('')
        self.hdr_badge.add_css_class('sz-badge')
        mb = Gtk.Button.new_from_icon_name('pan-down-symbolic')
        mb.add_css_class('flat')
        mb.set_focus_on_click(False)
        mb.connect('clicked', lambda b: self.win.open_panel_menu(self, b))
        for w in (self.hdr_role, self.hdr_name, sp, self.hdr_badge, mb):
            h.append(w)
        self.hdr = h
        self.append(h)

    def _build_addressbar(self):
        bar = hbox(4)
        bar.add_css_class('sz-pathbar')
        self.b_back = self._btn('go-previous-symbolic', _('Back'), self.back)
        self.b_fwd = self._btn('go-next-symbolic', _('Forward'), self.forward)
        self.b_up = self._btn('go-up-symbolic', _('Up one level'), self.go_up)
        self.entry = Gtk.Entry(hexpand=True)
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'folder-symbolic')
        self.entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'pan-down-symbolic')
        self.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, _('Folders history'))
        self.entry.connect('icon-press', lambda e, pos: self.win.open_history_menu(self)
                           if pos == Gtk.EntryIconPosition.SECONDARY else None)
        self.entry.connect('activate', lambda e: self.navigate_text(e.get_text()))
        self.btn_panels = Gtk.Button()
        self.btn_panels.add_css_class('sz-panels-btn')
        self.btn_panels.set_focus_on_click(False)
        self.btn_panels.set_tooltip_text(_('Top panels'))
        pb = hbox(6)
        pi = Gtk.Image.new_from_icon_name(pick_icon('view-dual-symbolic', 'view-restore-symbolic',
                                                   'view-grid-symbolic'))
        pi.set_pixel_size(16)
        chevron = Gtk.Image.new_from_icon_name('pan-down-symbolic')
        chevron.set_pixel_size(12)
        pb.append(pi)
        pb.append(lbl(_('Panels')))
        pb.append(chevron)
        self.btn_panels.set_child(pb)
        self.btn_panels.connect('clicked', lambda b: self.win.open_top_panels_menu(b))
        for w in (self.b_back, self.b_fwd, self.b_up, self.entry, self.btn_panels):
            bar.append(w)
        if self.design != 'dual':
            bar.append(self._btn('view-refresh-symbolic', _('Refresh'), lambda: self.reload()))
        self.append(bar)

    def _build_titlebar(self):
        if self.design != 'nav':
            return
        row = hbox(8)
        set_margins(row, 6)
        row.set_margin_start(12)
        self.title_lbl = lbl('')
        self.title_lbl.add_css_class('sz-title')
        self.count_lbl = lbl('')
        self.count_lbl.add_css_class('sz-muted')
        sp = Gtk.Box()
        sp.set_hexpand(True)
        vm = self._btn(pick_icon('view-grid-symbolic', 'view-list-symbolic'), _('Tiles'),
                       lambda: self.win.lookup_action('view-toggle').activate(None))
        lm = self._btn('view-list-symbolic', _('List (names only)'),
                       lambda: self.win.lookup_action('list-mode').activate(None))
        cb = Gtk.Button.new_from_icon_name(pick_icon('view-column-symbolic', 'preferences-other-symbolic',
                                                     'emblem-system-symbolic', 'view-list-symbolic'))
        cb.add_css_class('flat')
        cb.set_tooltip_text(_('Columns'))
        cb.set_focus_on_click(False)
        cb.connect('clicked', lambda b: self.win.open_columns_menu(b))
        for w in (self.title_lbl, self.count_lbl, sp, vm, lm, cb):
            row.append(w)
        self.title_row = row
        self.append(row)

    def _build_list(self):
        self.store = Gtk.ListStore(Gio.Icon, str, bool, GObject.TYPE_INT64, GObject.TYPE_INT64,
                                   GObject.TYPE_INT64, str, str, str, str, str, GObject.TYPE_INT64,
                                   GObject.TYPE_INT64)
        self.filter = Gtk.TreeModelFilter(child_model=self.store)
        self.filter.set_visible_func(self._visible)
        self.sorted = Gtk.TreeModelSort(model=self.filter)
        for c in (C_NAME, C_SIZE, C_PACKED, C_MTIME, C_ATTR, C_CRC, C_METHOD, C_ENC, C_EXT, C_ORD):
            self.sorted.set_sort_func(c, self._sort, c)
        self.sorted.set_sort_column_id(C_NAME, Gtk.SortType.ASCENDING)
        self.tree = Gtk.TreeView(model=None)
        self.tree.set_enable_search(False)
        sel = self.tree.get_selection()
        sel.set_mode(Gtk.SelectionMode.MULTIPLE)
        sel.connect('changed', lambda s: self.update_status())
        self.tree.connect('row-activated', self._on_row_activated)
        self._build_columns()

    def _build_tiles(self):
        self.tile_store = Gio.ListStore.new(TileItem)
        self.tile_sel = Gtk.MultiSelection.new(self.tile_store)
        self.tile_sel.connect('selection-changed', lambda m, p, n: self.update_status())
        self._bound, self._tiles_dirty = {}, True
        g = Gtk.GridView.new(self.tile_sel, self._make_factory())
        g.set_enable_rubberband(True)
        g.set_min_columns(1)
        g.set_max_columns(96)
        g.connect('activate', lambda v, pos: self._on_row_activated(None, Gtk.TreePath.new_from_indices([pos]), None))
        bl = Gtk.GestureClick()
        bl.set_button(3)
        bl.connect('pressed', self._on_grid_blank_click)
        g.add_controller(bl)
        self.grid = g
        self.sorted.connect('sort-column-changed', lambda m: self._tiles_changed())

    def _build_stack(self):
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        sw1 = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        sw1.set_child(self.tree)
        self.sw_list = sw1
        self.list_over = Gtk.Overlay()
        self.list_over.set_child(sw1)
        self.sw_tiles = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.tiles_over = Gtk.Overlay()
        # GridView сам реализует Scrollable: он должен быть непосредственным
        # ребёнком ScrolledWindow, иначе GTK не виртуализирует плитки и строит
        # виджеты для всех строк сразу (и прокрутка живёт в другом adjustment).
        self.sw_tiles.set_child(self.grid)
        self.tiles_over.set_child(self.sw_tiles)
        self.stack.add_named(self.list_over, 'list')
        self.stack.add_named(self.tiles_over, 'tiles')
        self.stack.set_visible_child_name(self.view_mode)
        self.stack_over = Gtk.Overlay()
        self.stack_over.set_vexpand(True)
        self.stack_over.set_hexpand(True)
        self.stack_over.set_child(self.stack)
        self.drop_ring = Gtk.Box()
        self.drop_ring.add_css_class('sz-drop-ring')
        self.drop_ring.set_can_target(False)
        self.drop_ring.set_focusable(False)
        self.drop_ring.set_halign(Gtk.Align.FILL)
        self.drop_ring.set_valign(Gtk.Align.FILL)
        self.drop_ring.set_visible(False)
        self.stack_over.add_overlay(self.drop_ring)
        self.stack_over.set_measure_overlay(self.drop_ring, False)
        self.append(self.stack_over)

    def _build_footer(self):
        if self.design != 'dual':
            return
        f = hbox(8)
        f.add_css_class('sz-foot')
        self.foot_l = lbl('')
        self.foot_l.add_css_class('sz-muted')
        sp = Gtk.Box()
        sp.set_hexpand(True)
        self.foot_r = lbl('')
        for w in (self.foot_l, sp, self.foot_r):
            f.append(w)
        self.foot = f
        self.append(f)

    def _attach_controllers(self, w, rclick=True):
        if rclick:
            g = Gtk.GestureClick()
            g.set_button(3)
            g.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            g.connect('pressed', self._on_right_click)
            w.add_controller(g)
        kc = Gtk.EventControllerKey()
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        kc.connect('key-pressed', self._on_key)
        w.add_controller(kc)
        sc = Gtk.EventControllerScroll()
        sc.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        sc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        sc.connect('scroll', self._on_scroll)
        w.add_controller(sc)
        src = Gtk.DragSource()
        src.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        src.connect('prepare', self._on_drag_prepare)
        w.add_controller(src)
        dt = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        dt.connect('enter', self._on_drop_enter)
        dt.connect('leave', self._on_drop_leave)
        dt.connect('drop', self._on_drop)
        w.add_controller(dt)

    def _build_columns(self):
        self.cols = {}
        col = Gtk.TreeViewColumn()
        col.set_title(_('Name'))
        ri, rt = Gtk.CellRendererPixbuf(), Gtk.CellRendererText()
        rt.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.renderers += [ri, rt]
        col.pack_start(ri, False)
        col.pack_start(rt, True)
        col.set_cell_data_func(ri, self._icon_cell, 'list')
        col.set_cell_data_func(rt, self._name_cell, 'list')
        col.set_resizable(True)
        col.set_expand(True)
        col.set_min_width(220)
        col.set_sort_column_id(C_NAME)
        self.tree.append_column(col)
        self.cols[C_NAME] = col
        for idx, title, kind in COLUMNS:
            r = Gtk.CellRendererText()
            self.renderers.append(r)
            c = Gtk.TreeViewColumn()
            c.set_title(_(title))
            c.pack_start(r, True)
            if kind in ('text', 'attr'):
                c.add_attribute(r, 'text', idx)
                if kind == 'attr':
                    r.set_property('family', 'monospace')
                    r.set_property('foreground', '#8B879C')
            elif kind == 'size':
                r.set_property('xalign', 1.0)
                c.set_cell_data_func(r, self._size_cell, idx)
            else:
                c.set_cell_data_func(r, self._time_cell, idx)
            c.set_resizable(True)
            c.set_sort_column_id(idx)
            self.tree.append_column(c)
            self.cols[idx] = c

    # ---------- представление: список / плитки ----------
    @property
    def view(self):
        return self.grid if self.view_mode == 'tiles' else self.tree

    def focus_view(self):
        self.view.grab_focus()

    def _has_focus(self, root):
        f = root.get_focus()
        while f is not None:
            if f is self.view:
                return True
            f = f.get_parent()
        return False

    def _set_models(self):
        """Таблица подключена к модели только в режиме списка — так быстрее заполняется."""
        self.tree.set_model(self.sorted if self.view_mode == 'list' else None)

    def icon_size_px(self, mode=None):
        c = self.win.conf
        return c['tile_icon_size'] if (mode or self.view_mode) == 'tiles' else c['list_icon_size']

    def _icon_cell(self, layout, cell, model, it, mode):
        """Значок в строке списка (плитки рисуются отдельными виджетами)."""
        icon = model.get_value(it, C_ICON)
        cell.set_property('sensitive',
                          not self.win.is_cut_path(model.get_value(it, C_FULL)))
        if icon is None:
            return
        size = self.icon_size_px('list')
        pb = make_icon_pixbuf(icon, size, model.get_value(it, C_FLAGS))
        # GTK ужимает картинку ячейки до «стандартного» размера значка — 16 или 32 px
        cell.set_property('icon-size', Gtk.IconSize.NORMAL if size <= 16 else Gtk.IconSize.LARGE)
        if pb is not None:
            cell.set_property('gicon', None)
            cell.set_property('pixbuf', pb)
        else:
            cell.set_property('pixbuf', None)
            cell.set_property('gicon', icon)

    # ----- плитки: GridView из обычных виджетов -----
    def _make_factory(self):
        size = self.win.conf['tile_icon_size']
        iw = max(112, size + 40)
        f = Gtk.SignalListItemFactory()
        f.connect('setup', self._tile_setup, size, iw)
        f.connect('bind', self._tile_bind, size)
        f.connect('unbind', self._tile_unbind)
        return f

    def _tile_setup(self, factory, li, size, iw):
        box = vbox(4)
        box.set_size_request(iw, -1)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        ov = Gtk.Overlay()
        ov.set_size_request(size, size)
        ov.set_halign(Gtk.Align.CENTER)
        img = Gtk.Image()
        img.set_pixel_size(size)
        ov.set_child(img)
        pic = Gtk.Picture()
        pic.set_size_request(size, size)
        pic.set_can_shrink(True)
        pic.set_can_target(False)
        pic.set_visible(False)
        ov.add_overlay(pic)
        badges = {}
        for flag, which, ha, va in ((FLAG_NOREAD, 'badge_noread', Gtk.Align.START, Gtk.Align.END),
                                    (FLAG_NOWRITE, 'badge_nowrite', Gtk.Align.END, Gtk.Align.END),
                                    (FLAG_LINK, 'badge_link', Gtk.Align.END, Gtk.Align.START)):
            b = Gtk.Picture()
            b.set_halign(ha)
            b.set_valign(va)
            b.set_can_target(False)
            b.set_visible(False)
            ov.add_overlay(b)
            ov.set_measure_overlay(b, False)
            badges[flag] = (which, b)
        box.append(ov)
        label = Gtk.Label()
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_lines(2)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_max_width_chars(max(8, (iw - 10) // 7))
        label_ov = Gtk.Overlay()
        label_ov.set_child(label)
        box.append(label_ov)
        g = Gtk.GestureClick()
        g.set_button(3)
        g.connect('pressed', self._tile_right_click, li)
        box.add_controller(g)
        parts = TileParts()
        parts.box, parts.ov, parts.img, parts.pic = box, ov, img, pic
        parts.badges, parts.label, parts.label_ov, parts.item, parts.size = badges, label, label_ov, None, size
        box._parts = parts
        li.set_child(box)

    def _tile_bind(self, factory, li, size):
        item, parts = li.get_item(), li.get_child()._parts
        parts.item = item
        self._bound.setdefault(item.full, []).append(parts)
        self._apply_tile(parts, item, size)
        self._thumb_want(item, size)

    def _tile_unbind(self, factory, li):
        parts = li.get_child()._parts
        lst = self._bound.get(parts.item.full) if parts.item is not None else None
        if lst and parts in lst:
            lst.remove(parts)
        if getattr(self, '_tile_edit_parts', None) is parts:
            self._tile_edit_close(False)
        parts.item = None

    def _apply_tile(self, parts, item, size):
        parts.label.set_text(item.name)
        parts.box.set_tooltip_text(item.name)
        thumb = None
        if (self.win.conf['show_thumbs'] and self.mode == 'fs' and not item.is_dir
                and not vfs.is_uri(item.full)):
            thumb = self.thumbs.get((item.full, size))
        if thumb is not None:
            parts.pic.set_paintable(thumb)
            parts.pic.set_visible(True)
            parts.img.set_visible(False)
        else:
            parts.pic.set_visible(False)
            parts.img.set_visible(True)
            pb = make_icon_pixbuf(item.icon, size) if isinstance(item.icon, Gio.FileIcon) else None
            if pb is not None:
                # Gtk.Image плохо показывает FileIcon на ICO (иконки .exe),
                # поэтому файловые значки рисуем через GdkPixbuf.
                parts.img.set_from_pixbuf(pb)
            else:
                parts.img.set_from_gicon(item.icon)
            parts.img.set_pixel_size(size)
        d = max(10, int(size * 0.46))
        for flag, (which, b) in parts.badges.items():
            tex = badge_texture(DISP[which], d) if (item.flags & flag and DISP[which] != 'none') else None
            b.set_visible(tex is not None)
            if tex is not None:
                b.set_paintable(tex)
                b.set_size_request(d, d)
        parts.box.set_opacity(0.45 if self.win.is_cut_path(item.full) else 1.0)

    def _tile_at(self, x, y):
        """Плитка под точкой (x, y) сетки или None."""
        w = self.grid.pick(x, y, Gtk.PickFlags.DEFAULT)
        while w is not None and w is not self.grid:
            if hasattr(w, '_parts'):
                return w._parts
            w = w.get_parent()
        return None

    def _tile_selected_names(self):
        bs = self.tile_sel.get_selection()
        return {self.tile_store.get_item(bs.get_nth(k)).name for k in range(bs.get_size())}

    def _tiles_changed(self):
        self._tiles_dirty = True
        self._sync_tiles()

    def refresh_cut(self):
        """Показать вырезанные элементы приглушённо (как в файловых менеджерах)."""
        if self.view_mode == 'tiles':
            for full, lst in list(self._bound.items()):
                op = 0.45 if self.win.is_cut_path(full) else 1.0
                for parts in lst:
                    parts.box.set_opacity(op)
        else:
            self.tree.queue_draw()

    def _sync_tiles(self, keep=None, reveal=True):
        """Пересобрать модель плиток по отсортированной модели таблицы (с сохранением выделения)."""
        if self.view_mode != 'tiles' or not self._tiles_dirty:
            return
        if keep is None:
            keep = self._tile_selected_names() if self.tile_store.get_n_items() else set()
        items = [TileItem(r[C_NAME], r[C_DIR], r[C_FULL], r[C_SIZE], r[C_ICON], r[C_FLAGS], i)
                 for i, r in enumerate(self.sorted)]
        # Снимаем выделение до изменения модели, иначе MultiSelection какое-то время
        # держит ссылки на уже удалённые строки (артефакты после удаления файла).
        self.tile_sel.unselect_all()
        self.tile_store.splice(0, self.tile_store.get_n_items(), items)
        self._tiles_dirty = False
        self._tiles_keep = set()
        first = None
        for i, it in enumerate(items):
            if it.name in keep:
                self.tile_sel.select_item(i, False)
                if first is None:
                    first = i
        if first is not None and reveal:
            # GridView пересчитывает раскладку после splice, поэтому прокручиваем
            # к выделенной плите в следующей итерации главного цикла.
            name = items[first].name
            seq = self._scroll_seq

            def reveal_tile():
                if seq == self._scroll_seq:
                    self._scroll_tile_to(name)
                return False
            GLib.idle_add(reveal_tile)
        self.update_status()

    def _scroll_tile_to(self, name, seq=None):
        if seq is not None and seq != self._scroll_seq:
            return False       # за это время камеру уже поставили точно (reload/back)
        prev = self.get_root().get_focus() if self.get_root() is not None else None
        for i in range(self.tile_store.get_n_items()):
            if self.tile_store.get_item(i).name == name:
                try:
                    # В GTK 4.24 scroll_to с флагом NONE не прокручивает к элементу,
                    # который ещё не был отрисован, поэтому используем FOCUS и затем
                    # возвращаем фокус туда, где он был.
                    self.grid.scroll_to(i, Gtk.ListScrollFlags.FOCUS, None)
                except (AttributeError, TypeError):
                    pass
                break
        if prev is not None and prev is not self.grid and prev.get_mapped():
            w = prev
            while w is not None and w is not self.grid:
                w = w.get_parent()
            if w is None:      # не возвращаем фокус на старую (уже перепривязанную) плитку
                prev.grab_focus()
        return False

    def apply_view(self, force=False):
        """Применить режим просмотра и размер значков из настроек."""
        self._cancel_scroll_restore()
        c = self.win.conf
        mode = c['view_mode'] if c['view_mode'] in ('list', 'tiles') else 'list'
        keep = {i.name for i in self.selected()} | self._tiles_keep
        if self._renaming:
            self.cancel_inline_rename()
        self.view_mode = mode
        self.stack.set_visible_child_name(mode)
        self.grid.set_single_click_activate(bool(c['single_click']))
        self._set_models()
        if mode == 'tiles':
            if self._factory_size != c['tile_icon_size']:
                # фабрика зависит от размера значка — пересоздаём только при его смене,
                # иначе каждое применение вида (в т.ч. при map окна) собирает все плитки заново
                self._factory_size = c['tile_icon_size']
                self.grid.set_factory(self._make_factory())
                force = True
            if force or self._tiles_dirty:
                if self.get_mapped():
                    self._sync_tiles(keep, reveal=False)
                else:
                    # панель ещё не показана — соберём плитки при map (см. _on_mapped)
                    self._tiles_keep = keep
                    self._tiles_dirty = True
        elif keep:
            self._restore_selection(keep)
        self.refresh_chrome()
        self.update_status()
        self.win.update_zoom_slider()

    def zoom(self, delta):
        c = self.win.conf
        key, sizes = ('tile_icon_size', TILE_SIZES) if self.view_mode == 'tiles' else ('list_icon_size', LIST_SIZES)
        cur = c[key]
        idx = min(range(len(sizes)), key=lambda i: abs(sizes[i] - cur))
        c[key] = sizes[max(0, min(len(sizes) - 1, idx + delta))]

    # ---------- миниатюры (запрашиваются, когда плитка попадает на экран) ----------
    def _thumb_want(self, item, size):
        if (not self.win.conf['show_thumbs'] or self.mode != 'fs' or item.is_dir or GdkPixbuf is None
                or vfs.is_uri(item.full)):
            return
        key = (item.full, size)
        if key in self.thumbs or key in self._thumb_pending:
            return
        ext = os.path.splitext(item.full)[1][1:].lower()
        if ext not in image_exts() and ext not in VIDEO_EXTS and ext not in ('pdf', 'svg', 'webp', 'avif', 'heic'):
            return
        self._thumb_pending.add(key)
        gen = self._thumb_gen

        def job(path=item.full, sz=size):
            return None if gen != self._thumb_gen else make_thumbnail(path, sz)
        fut = thumb_pool().submit(job)
        fut.add_done_callback(lambda f, k=key, g=gen: GLib.idle_add(self._thumb_done, k, f, g))

    def _thumb_done(self, key, fut, gen):
        self._thumb_pending.discard(key)
        if gen != self._thumb_gen:
            return False
        try:
            pb = fut.result()
        except Exception:
            pb = None
        tex = Gdk.Texture.new_for_pixbuf(square_pixbuf(pb, key[1])) if pb is not None else None
        self.thumbs[key] = tex          # None — «миниатюры нет», чтобы не пробовать снова
        if tex is not None:
            for parts in list(self._bound.get(key[0], [])):
                if parts.item is not None:
                    self._apply_tile(parts, parts.item, key[1])
        return False

    def _name_cell(self, layout, cell, model, it, mode):
        name = model.get_value(it, C_NAME) or ''
        if self.win.is_cut_path(model.get_value(it, C_FULL)):
            cell.set_property('markup', '<span foreground="%s">%s</span>'
                              % (PAL['muted'], GLib.markup_escape_text(name)))
        else:
            cell.set_property('text', name)

    @staticmethod
    def _size_cell(col, cell, model, it, idx):
        v = model.get_value(it, idx)
        cell.set_property('text', format_size(v) if v >= 0 else '')

    @staticmethod
    def _time_cell(col, cell, model, it, idx):
        cell.set_property('text', format_date(model.get_value(it, idx)))

    def _visible(self, model, it, data):
        if not self.filter_text:
            return True
        name = model.get_value(it, C_NAME)
        return name is None or self.filter_text in name.casefold()

    def _sort(self, model, a, b, col):
        if col == C_ORD:
            va, vb = model.get_value(a, C_ORD), model.get_value(b, C_ORD)
            return (va > vb) - (va < vb)
        da, db = model.get_value(a, C_DIR), model.get_value(b, C_DIR)
        if da != db:
            r = -1 if da else 1
            order = self.sorted.get_sort_column_id()[-1]
            return -r if order == Gtk.SortType.DESCENDING else r
        if col == C_EXT:
            va = os.path.splitext(model.get_value(a, C_NAME))[1].casefold()
            vb = os.path.splitext(model.get_value(b, C_NAME))[1].casefold()
        else:
            va, vb = model.get_value(a, col), model.get_value(b, col)
            if isinstance(va, str):
                va, vb = va.casefold(), vb.casefold()
        if va == vb and col != C_NAME:
            va, vb = model.get_value(a, C_NAME).casefold(), model.get_value(b, C_NAME).casefold()
        return (va > vb) - (va < vb)

    def sort_by(self, key):
        col = {'name': C_NAME, 'type': C_EXT, 'mtime': C_MTIME, 'size': C_SIZE}.get(key, C_ORD)
        self.sorted.set_sort_column_id(col, Gtk.SortType.ASCENDING)

    def set_details(self, on):
        self.details = on
        self._set_cols()

    def _set_cols(self):
        arc = self.mode == 'arc'
        hidden = set(self.win.conf['columns_hidden'])
        for idx, c in self.cols.items():
            vis = idx == C_NAME or (idx not in hidden and (arc or idx not in ARC_ONLY_COLS) and self.details)
            c.set_visible(vis)

    def apply_options(self, conf):
        self.tree.set_grid_lines(Gtk.TreeViewGridLines.BOTH if conf['grid'] else Gtk.TreeViewGridLines.NONE)
        self.tree.set_activate_on_single_click(bool(conf['single_click']))
        yp = DENSITY_YPAD.get(conf['density'], 2)
        for r in self.renderers:
            r.set_property('ypad', yp)
        self._set_cols()
        self.apply_view()
        self.tree.queue_draw()

    def set_filter(self, text):
        self.filter_text = (text or '').strip().casefold()
        self.filter.refilter()
        self._tiles_changed()
        self.update_status()

    def focus_address(self):
        self.entry.grab_focus()
        self.entry.select_region(0, -1)

    # ---------- выделение / статус (общие для списка и плиток) ----------
    def _sel_paths(self):
        if self.view_mode == 'tiles':
            bs = self.tile_sel.get_selection()
            return [Gtk.TreePath.new_from_indices([bs.get_nth(k)]) for k in range(bs.get_size())]
        return list(self.tree.get_selection().get_selected_rows()[1])

    def _select_path(self, p):
        if self.view_mode == 'tiles':
            self.tile_sel.select_item(p.get_indices()[0], False)
        else:
            self.tree.get_selection().select_path(p)

    def _unselect_path(self, p):
        if self.view_mode == 'tiles':
            self.tile_sel.unselect_item(p.get_indices()[0])
        else:
            self.tree.get_selection().unselect_path(p)

    def _is_selected(self, p):
        if self.view_mode == 'tiles':
            return self.tile_sel.is_selected(p.get_indices()[0])
        return self.tree.get_selection().path_is_selected(p)

    def selected(self):
        out = []
        for p in self._sel_paths():
            it = self.sorted.get_iter(p)
            out.append(Item(self.sorted.get_value(it, C_NAME), self.sorted.get_value(it, C_DIR),
                            self.sorted.get_value(it, C_FULL), self.sorted.get_value(it, C_SIZE)))
        return out

    def counts(self):
        return len(self.sorted), self.selected()

    def _loc_name(self):
        if self.mode == 'fs':
            return vfs.basename(self.path) or '/'
        a = self.arc
        return a.sub.rsplit('/', 1)[-1] if a.sub else vfs.basename(a.display.rstrip('/'))

    def refresh_chrome(self, total=None):
        total = len(self.sorted) if total is None else total
        active = self.win.active is self
        if self.hdr is not None:
            self.hdr_role.set_text(_('Source') if active else _('Destination'))
            self.hdr_name.set_text(self._loc_name())
            self.hdr_badge.set_text(_('ACTIVE') if active else _('{0} objects').format(total))
        if self.title_row is not None:
            title = (self.win.place_label(self.path) if self.mode == 'fs' else None) or self._loc_name()
            if self.mode == 'fs' and vfs.is_admin(self.path):
                title = _('Root') + ': ' + vfs.display(self.path)
            self.title_lbl.set_text(title)
            self.count_lbl.set_text(_('{0} objects').format(total))

    def update_status(self):
        total, sel = self.counts()
        if self.foot is not None:
            self.foot_l.set_text(_('Objects: {0}').format(total))
            if len(sel) == 1 and sel[0].is_dir:
                self.foot_r.set_text(_('Selected folder: {0}').format(sel[0].name))
            elif sel:
                self.foot_r.set_text(self.win.selected_text(sel))
            else:
                self.foot_r.set_text('')
            if self._ta_buf:
                self.foot_r.set_text(self._ta_text())
        self.refresh_chrome(total)
        self.win.panel_status_changed(self)

    def set_message(self, text):
        if self.foot is not None:
            self.foot_l.set_text(text)
        self.win.set_status_message(self, text)

    def select_all(self):
        if self.view_mode == 'tiles':
            self.tile_sel.select_all()
        else:
            self.tree.get_selection().select_all()

    def unselect_all(self):
        if self.view_mode == 'tiles':
            self.tile_sel.unselect_all()
        else:
            self.tree.get_selection().unselect_all()

    def invert_selection(self):
        for row in self.sorted:
            if self._is_selected(row.path):
                self._unselect_path(row.path)
            else:
                self._select_path(row.path)

    def select_mask(self, mask, select=True):
        for row in self.sorted:
            if fnmatch.fnmatch(row[C_NAME].casefold(), mask.casefold()):
                (self._select_path if select else self._unselect_path)(row.path)

    def _restore_selection(self, keep, scroll=True):
        first = None
        for row in self.sorted:
            if row[C_NAME] in keep:
                self._select_path(row.path)
                if first is None:
                    first = row.path.copy()
        if first is not None and scroll:
            if self.view_mode == 'tiles':
                idx = first.get_indices()[0]
                if 0 <= idx < self.tile_store.get_n_items():
                    self._scroll_tile_to(self.tile_store.get_item(idx).name)
            else:
                self.tree.scroll_to_cell(first, None, False, 0.0, 0.0)

    def _on_mapped(self, w):
        """Панель показана: собрать плитки, отложенные в fill()."""
        if self._tiles_dirty and self.view_mode == 'tiles':
            self._sync_tiles(self._tiles_keep)

    def fill(self, rows, keep=None):
        self._cancel_scroll_restore()
        self._scroll_seq += 1      # отменяем отложенный показ плитки из прошлой папки
        loc = self._display_loc()
        if loc != self._last_loc:
            self._last_loc = loc
            self._thumb_gen += 1
            self.thumbs.clear()
            self._ta_buf, self._ta_ok = '', True
            if self._ta_src:
                GLib.source_remove(self._ta_src)
                self._ta_src = 0
            if self.filter_text:
                self.filter_text = ''
                self.filter.refilter()
                self.win.clear_search()
        if self._renaming or getattr(self, '_rename_state', None) is not None:
            self.cancel_inline_rename()
        self._renaming = False
        self.tree.set_model(None)
        self.store.clear()
        for i, r in enumerate(rows):
            self.store.append(list(r) + [i])
        self._set_models()
        self._tiles_dirty = True
        self._tiles_keep = set(keep) if keep else set()
        # Плитки собираем только когда панель уже показана: до map у GridView нет
        # реального размера, и виджеты для всех строк создаются впустую.
        if self.get_mapped():
            self._sync_tiles(self._tiles_keep)
        if keep and self.view_mode == 'list':
            self._restore_selection(set(keep))
        self.update_status()
        self.win.panel_changed(self)

    # ---------- строки ----------
    def _fs_rows(self):
        rows, hidden = [], self.win.conf['show_hidden']
        try:
            entries = vfs.listdir(self.path)
        except OSError as e:
            alert(self.win, _('Cannot open folder'), str(e))
            return rows
        show_badges = bool(self.win.conf.get('show_badges', True))
        parent_writable = vfs.can_write(self.path)
        for de in entries:
            name = de.name
            if not hidden and name.startswith('.'):
                continue
            is_dir, is_link = de.is_dir, de.is_link
            flags = 0
            if show_badges:
                if is_link:
                    flags = FLAG_LINK
                elif not vfs.is_uri(self.path):
                    # в папке без прав на запись не помечаем замком каждый элемент:
                    # запрет записи показываем только внутри доступной папки
                    if parent_writable and not de.can_write:
                        flags |= FLAG_NOWRITE
                    if not de.can_read:
                        flags |= FLAG_NOREAD
            icon = (dir_icon(vfs.display(de.path)) if is_dir
                    else icon_for(name, False, de.path))
            rows.append((icon, name, is_dir, -1 if is_dir else de.size, -1,
                         de.mtime, '' if vfs.is_uri(de.path) else stat.filemode(de.mode),
                         '', '', '', de.path, flags))
        return rows

    @staticmethod
    def _entry_row(e, name):
        return (icon_for(name, False), name, False, e.size, e.packed, e.mtime, e.attrs,
                e.crc, e.method, '+' if e.enc else '', e.path, 0)

    def _arc_rows(self):
        a = self.arc
        prefix = a.sub + '/' if a.sub else ''
        if a.flat:
            return [self._entry_row(e, e.path[len(prefix):]) for e in a.entries
                    if not e.is_dir and e.path.startswith(prefix)]
        dirs, files = {}, []
        for e in a.entries:
            p = e.path
            if prefix:
                if not p.startswith(prefix):
                    continue
                rest = p[len(prefix):]
            else:
                rest = p
            if not rest:
                continue
            first, sep, tail = rest.partition('/')
            if sep or e.is_dir:
                d = dirs.setdefault(first, [0, 0, 0, None])
                d[2] = max(d[2], e.mtime)
                if sep:
                    if not e.is_dir:
                        d[0] += e.size
                        d[1] += e.packed
                else:
                    d[3] = e
            else:
                files.append(e)
        rows = []
        for name, (size, packed, mtime, ent) in dirs.items():
            rows.append((icon_for(name, True), name, True, size, packed, mtime,
                         ent.attrs if ent else 'D', '', '', '', prefix + name, 0))
        for e in files:
            rows.append(self._entry_row(e, e.path[len(prefix):]))
        return rows

    # ---------- навигация ----------
    def current_dir(self):
        return self.path if self.mode == 'fs' else os.path.dirname(self.arc.path)

    def location_text(self):
        return self.entry.get_text()

    def leave_archive(self):
        if self.arc is not None:
            for a in self.arc.chain():
                if a.tmp:
                    shutil.rmtree(a.tmp, ignore_errors=True)
            self.arc = None

    def navigate_fs(self, path, push=True, select=None):
        if push:
            self._capture_view_state()
        if vfs.is_admin(path):
            return self.navigate_admin(path, push, select)
        if vfs.is_uri(path):
            return self.navigate_uri(path, push, select)
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            if os.path.lexists(path) and not os.access(path, os.R_OK | os.X_OK):
                return self.navigate_admin(vfs.admin_uri(path), push, select)
            alert(self.win, _('Folder not found'), path)
            self.entry.set_text(self._display_loc())
            return False
        if not os.access(path, os.R_OK | os.X_OK):
            return self.navigate_admin(vfs.admin_uri(path), push, select)
        self.leave_archive()
        self.mode, self.path = 'fs', path
        self.entry.set_text(path)
        self._set_cols()
        self.fill(self._fs_rows(), [select] if select else None)
        if push:
            self._push(('fs', path))
        self.win.conf['last_dir'] = path
        return True

    def _admin_ready(self, uri, then):
        if vfs.exists(uri):
            then()
            return True
        self.set_message(_('Requesting root access…') if vfs.is_admin(uri)
                         else _('Connecting to server…'))
        try:
            # Gtk.MountOperation показывает диалог ввода логина и пароля;
            # Gio.MountOperation молча завершается ошибкой аутентификации.
            op = Gtk.MountOperation(parent=self.win)
        except Exception:
            op = Gio.MountOperation()

        def mounted(src, res):
            try:
                src.mount_enclosing_volume_finish(res)
            except GLib.Error as e:
                if e.code != Gio.IOErrorEnum.ALREADY_MOUNTED:
                    self.update_status()
                    alert(self.win, _('Cannot open folder'), e.message)
                    self.entry.set_text(self._display_loc())
                    return
            then()
        Gio.File.new_for_uri(uri).mount_enclosing_volume(Gio.MountMountFlags.NONE, op, None, mounted)
        return True

    def navigate_admin(self, path, push=True, select=None):
        if push:
            self._capture_view_state()
        uri = path if vfs.is_admin(path) else vfs.admin_uri(path)
        rest = uri[len(vfs.ADMIN):]
        uri = vfs.ADMIN + ('/' if rest in ('', '/') else rest.rstrip('/'))

        def go():
            if not vfs.is_dir(uri):
                alert(self.win, _('Folder not found'), vfs.display(uri))
                self.entry.set_text(self._display_loc())
                return
            self.leave_archive()
            self.mode, self.path = 'fs', uri
            self.entry.set_text(uri)
            self._set_cols()
            self.fill(self._fs_rows(), [select] if select else None)
            if push:
                self._push(('fs', uri))

        return self._admin_ready(uri, go)

    def navigate_uri(self, path, push=True, select=None):
        """Открыть сетевой URI напрямую через GIO.

        GVfs не всегда создаёт для сервера (например, smb://host/) точку
        монтирования в gvfs-fuse, поэтому полагаться на локальный путь нельзя:
        каталог читается через GIO, как это делает Nautilus.
        """
        if push:
            self._capture_view_state()
        head, sep, rest = path.partition('://')
        if sep and rest.count('/') > 1:
            path = head + sep + rest.rstrip('/')
        uri = path

        def go():
            if not vfs.is_dir(uri):
                alert(self.win, _('Folder not found'), uri)
                self.entry.set_text(self._display_loc())
                return
            self.leave_archive()
            self.mode, self.path = 'fs', uri
            self.entry.set_text(uri)
            self._set_cols()
            self.fill(self._fs_rows(), [select] if select else None)
            if push:
                self._push(('fs', uri))

        return self._admin_ready(uri, go)

    def _display_loc(self):
        if self.mode == 'fs':
            return self.path
        return self.arc.display + ('/' + self.arc.sub if self.arc.sub else '')

    def open_archive(self, path, push=True, sub='', parent_state=None, tmp=None, password=None, origin=None):
        if push and parent_state is None:
            self._capture_view_state()
        if vfs.is_uri(path):
            def start():
                self.set_message(_('Opening…'))

                def work():
                    try:
                        t, local = vfs.copy_to_temp(path)
                    except Exception as e:
                        GLib.idle_add(lambda: alert(self.win, _('Cannot open file "{0}" as archive').format(vfs.basename(path)), str(e)))
                        return
                    GLib.idle_add(lambda: self.open_archive(local, push, sub, parent_state, t, password, path))
                threading.Thread(target=work, daemon=True).start()
            self._admin_ready(path, start)
            return
        path = os.path.abspath(path)
        pw = password if password is not None else self.win.passwords.get(path)
        self.set_message(_('Opening…'))

        def cb(res, header, entries):
            if needs_password(res) and not header.get('Type'):
                def got(p):
                    if p is None:
                        self.update_status()
                        return
                    self.open_archive(path, push, sub, parent_state, tmp, p, origin)
                self.win.ask_password(path, got)
                return
            if not header.get('Type'):
                self.update_status()
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)
                alert(self.win, _('Cannot open file "{0}" as archive').format(os.path.basename(path)),
                      res.text(15))
                return
            if pw:
                self.win.passwords[path] = pw
            if parent_state is None:
                self.leave_archive()
            st = ArcState(path, header, entries, pw, parent_state, tmp, origin)
            s = sub
            while s and not st.has_dir(s):
                s = s.rpartition('/')[0]
            st.sub = s
            self.mode, self.arc = 'arc', st
            self._set_cols()
            self.show_arc()
            if push and parent_state is None:
                self._push(('arc', origin or path, s))
        self.win.list_async(path, pw, cb)

    def show_arc(self, keep=None):
        self.entry.set_text(self._display_loc())
        self.fill(self._arc_rows(), keep)

    def _visible_anchor(self):
        """Имена первых видимых строк списка — чтобы вернуть камеру после перезагрузки."""
        if self.view_mode != 'list' or self.tree.get_model() is None:
            return []
        rng = self.tree.get_visible_range()
        if not rng:
            return []
        start, end = rng
        out = []
        it = self.sorted.get_iter(start)
        while it is not None and len(out) < 32:
            out.append(self.sorted.get_value(it, C_NAME))
            if self.sorted.get_path(it).compare(end) == 0:
                break
            it = self.sorted.iter_next(it)
        return out

    def _restore_anchor(self, names):
        if not names:
            return
        want = set(names)
        for row in self.sorted:
            if row[C_NAME] in want:
                try:
                    self.tree.scroll_to_cell(row.path, None, True, 0.0, 0.0)
                except (AttributeError, TypeError):
                    pass
                return

    def reload(self, keep=None):
        adj = self._scroll_adj()
        scroll, up, pg = adj.get_value(), adj.get_upper(), adj.get_page_size()
        anchor = self._visible_anchor()
        keep = keep if keep is not None else [i.name for i in self.selected()]
        if self.mode == 'fs':
            if vfs.is_dir(self.path):
                self.fill(self._fs_rows(), keep)
                self._restore_anchor(anchor)
                self._restore_scroll(scroll, up, pg)
            else:
                self.navigate_fs(vfs.dirname(self.path) or '/')
            return
        a = self.arc

        def cb(res, header, entries):
            if self.arc is not a or not header.get('Type'):
                return
            a.header, a.entries = header, entries
            while a.sub and not a.has_dir(a.sub):
                a.sub = a.sub.rpartition('/')[0]
            self.show_arc(keep)
            self._restore_anchor(anchor)
            self._restore_scroll(scroll, up, pg)
        if os.path.exists(a.path):
            self.win.list_async(a.path, a.password, cb)

    def toggle_flat(self):
        if self.mode == 'arc':
            self.arc.flat = not self.arc.flat
            self.show_arc()

    def _push(self, entry):
        if self.hpos >= 0 and self.history[self.hpos] == entry:
            return
        del self.history[self.hpos + 1:]
        del self._hist_view[self.hpos + 1:]
        self.history.append(entry)
        self._hist_view.append(None)
        self.hpos = len(self.history) - 1

    def _scroll_adj(self):
        return self.grid.get_vadjustment() if self.view_mode == 'tiles' else self.sw_list.get_vadjustment()

    def _hist_entry_matches(self, e):
        """Относится ли запись истории к тому, что сейчас показано в панели."""
        if e[0] == 'fs':
            return self.mode == 'fs' and e[1] == self.path
        if self.mode != 'arc' or self.arc is None:
            return False
        root = self.arc
        while root.parent is not None:
            root = root.parent
        return e[1] == root.source and self.arc.sub == e[2]

    def _capture_view_state(self):
        """Запомнить прокрутку и выделение для текущей записи истории."""
        if 0 <= self.hpos < len(self.history) and self._hist_entry_matches(self.history[self.hpos]):
            adj = self._scroll_adj()
            self._hist_view[self.hpos] = {
                'sel': [i.name for i in self.selected()],
                'scroll': adj.get_value(),
                'upper': adj.get_upper(),
                'page': adj.get_page_size(),
            }

    def _cancel_scroll_restore(self):
        """Отменить отложенное восстановление прокрутки (модель меняется)."""
        adj = self._scroll_sig_adj
        if adj is not None:
            for attr in ('_scroll_hid', '_scroll_vid'):
                hid = getattr(self, attr, 0)
                if hid:
                    try:
                        if GObject.signal_handler_is_connected(adj, hid):
                            adj.disconnect(hid)
                    except (TypeError, AttributeError):
                        pass
                    setattr(self, attr, 0)
        self._scroll_sig_adj = self._scroll_target = None
        self._scroll_until = 0.0

    def _restore_scroll(self, value, upper=None, page=None):
        """Вернуть прокрутку так, чтобы камера не прыгала наверх.

        После замены модели GridView/TreeView ещё не знает новую высоту, и
        прокрутка сбрасывается в 0. Поэтому сразу подставляем сохранённые upper
        и value (первый кадр рисуется на месте), а затем на короткое время
        следим за adjustment: раскладка может пересчитать value уже после этого.
        """
        # отменяем отложенную прокрутку к выделенной плите: камера ставится точно
        self._scroll_seq += 1
        self._cancel_scroll_restore()
        if value <= 0:
            return
        adj = self._scroll_adj()
        if upper is not None and upper > adj.get_upper():
            # модель ещё не пересчитала высоту: вернём сохранённую, чтобы
            # value не обрезалось до 0 на первом кадре
            adj.set_upper(upper)
        if page is not None and page > 0 and abs(page - adj.get_page_size()) > 0.5:
            adj.set_page_size(page)
        maxv = max(0.0, adj.get_upper() - adj.get_page_size())
        if maxv >= value - 1:
            adj.set_value(min(value, maxv))
        self._scroll_sig_adj = adj
        self._scroll_target = value
        self._scroll_until = time.monotonic() + 0.6
        seq = self._scroll_seq

        def apply(a):
            if seq != self._scroll_seq:
                return
            if self._scroll_target is None or time.monotonic() > self._scroll_until:
                self._cancel_scroll_restore()
                return
            maxv = max(0.0, a.get_upper() - a.get_page_size())
            if maxv < value - 1:
                return
            target = min(value, maxv)
            if abs(a.get_value() - target) > 0.5 and not self._scroll_busy:
                self._scroll_busy = True
                try:
                    a.set_value(target)
                finally:
                    self._scroll_busy = False

        self._scroll_vid = adj.connect('value-changed', apply)
        self._scroll_hid = adj.connect('changed', apply)

        def expire():
            if seq == self._scroll_seq and self._scroll_target is not None:
                self._cancel_scroll_restore()
            return False
        GLib.timeout_add(600, expire)

    def _restore_view_state(self, st):
        if not st:
            return
        scroll = st.get('scroll', 0.0)
        if st.get('sel'):
            # при ненулевой сохранённой прокрутке не дёргаем вид к выделению
            self._restore_selection(set(st['sel']), scroll=scroll <= 0)
        self._restore_scroll(scroll, st.get('upper'), st.get('page'))

    def back(self):
        if self.hpos > 0:
            self._capture_view_state()
            self.hpos -= 1
            self._goto(self.history[self.hpos])

    def forward(self):
        if self.hpos < len(self.history) - 1:
            self._capture_view_state()
            self.hpos += 1
            self._goto(self.history[self.hpos])

    def _goto(self, e):
        st = self._hist_view[self.hpos] if 0 <= self.hpos < len(self._hist_view) else None
        if e[0] == 'fs':
            # При возврате в родительский каталог выделяем папку, из которой вышли
            # (как при «Вверх»), чтобы не потерять ориентир.
            sel = None
            if (self.mode == 'fs' and vfs.dirname(self.path) == e[1]
                    and not (st and st.get('sel'))):
                sel = vfs.basename(self.path)
            self.navigate_fs(e[1], push=False, select=sel)
        else:
            self.open_archive(e[1], push=False, sub=e[2])
        self._restore_view_state(st)

    def history_paths(self):
        out = []
        for e in self.history:
            t = e[1] + ('/' + e[2] if e[0] == 'arc' and e[2] else '')
            if t not in out:
                out.append(t)
        return out

    def _hist_state(self, kind, path):
        """Последнее сохранённое состояние просмотра для записи истории."""
        for i in range(min(self.hpos, len(self._hist_view)) - 1, -1, -1):
            if self._hist_view[i] and self.history[i][0] == kind and self.history[i][1] == path:
                return self._hist_view[i]
        return None

    def go_up(self):
        if self.mode == 'fs':
            parent = vfs.dirname(self.path)
            if vfs.is_remote(self.path) and parent and parent.rstrip('/').endswith(':'):
                return
            if parent and parent != self.path:
                # возвращаемся туда, где камера стояла до входа в папку
                st = self._hist_state('fs', parent)
                self.navigate_fs(parent, select=vfs.basename(self.path))
                if st:
                    # выделение не восстанавливаем: остаётся папка, из которой вышли
                    self._restore_scroll(st.get('scroll', 0.0), st.get('upper'), st.get('page'))
            return
        a = self.arc
        if a.sub:
            old = a.sub.rsplit('/', 1)[-1]
            a.sub = a.sub.rpartition('/')[0]
            self.show_arc([old])
        elif a.parent is not None:
            self.arc = a.parent
            if a.tmp:
                shutil.rmtree(a.tmp, ignore_errors=True)
            self.show_arc([os.path.basename(a.path)])
        else:
            src = a.source if vfs.is_uri(a.source) else a.path
            parent = vfs.dirname(src)
            st = self._hist_state('fs', parent)
            self.navigate_fs(parent, select=vfs.basename(src))
            if st:
                self._restore_scroll(st.get('scroll', 0.0), st.get('upper'), st.get('page'))

    def go_root(self):
        if vfs.is_remote(self.path):
            head, _, rest = self.path.partition('://')
            host = rest.split('/', 1)[0]
            self.navigate_fs('%s://%s/' % (head, host))
            return
        self.navigate_fs(vfs.ADMIN + '/' if vfs.is_admin(self.path) else '/')

    def navigate_text(self, text):
        raw = text.strip()
        if vfs.is_admin(raw):
            if vfs.is_file(raw):
                self.open_archive(raw)
            else:
                self.navigate_fs(raw)
                self.focus_view()
            return
        if vfs.is_uri(raw):
            self.navigate_fs(raw)
            self.focus_view()
            return
        t = os.path.expanduser(raw)
        if not t:
            return
        if os.path.isdir(t):
            self.navigate_fs(t)
            self.focus_view()
            return
        if os.path.isfile(t):
            self.open_archive(t if os.access(t, os.R_OK) else vfs.admin_uri(t))
            return
        parts = t.rstrip('/').split('/')
        for i in range(len(parts) - 1, 0, -1):
            pre = '/'.join(parts[:i]) or '/'
            if os.path.isfile(pre):
                self.open_archive(pre if os.access(pre, os.R_OK) else vfs.admin_uri(pre),
                                  sub='/'.join(parts[i:]))
                return
        alert(self.win, _('Folder not found'), t)
        self.entry.set_text(self._display_loc())

    # ---------- события ----------
    def _on_row_activated(self, tree, path, col):
        it = self.sorted.get_iter(path)
        item = Item(self.sorted.get_value(it, C_NAME), self.sorted.get_value(it, C_DIR),
                    self.sorted.get_value(it, C_FULL), self.sorted.get_value(it, C_SIZE))
        self.activate_item(item)

    def activate_item(self, it):
        if self.mode == 'fs':
            if it.is_dir:
                if not vfs.is_uri(it.full) and not IS_ROOT and not (
                        vfs.can_read(it.full) and vfs.can_exec(it.full)):
                    # Папка требует root: GVfs admin, polkit и то же окно.
                    self.win.op_open_as_root(target=it.full)
                else:
                    self.navigate_fs(it.full)
            else:
                target = it.full if vfs.is_uri(it.full) or vfs.can_read(it.full) else vfs.admin_uri(it.full)
                if is_archive_name(it.name):
                    self.open_archive(target)
                elif vfs.is_program(it.full):
                    self.win.run_executable(it.full)
                else:
                    self.win.open_external(target)
        else:
            if it.is_dir:
                self.arc.sub = it.full
                self.show_arc()
            elif is_archive_name(it.name):
                self.win.open_nested(self, it)
            else:
                self.win.open_from_archive(self, it, edit=True)

    # ---------- переименование на месте ----------
    def start_rename(self):
        sel = self.selected()
        if len(sel) != 1:
            return False
        if self.mode == 'arc' and self.arc.parent is not None:
            alert(self.win, _('Modifying nested archives is not supported'))
            return True
        if self.view_mode == 'list':
            paths = self._sel_paths()
            if not paths:
                return False
            self._rename_it = sel[0]
            self._list_edit_open(paths[0])
            return True
        self._renaming = True
        return self._tile_start_rename(sel[0])

    # --- переименование на месте в списке (своё поле поверх строки) ---
    def _list_edit_open(self, path):
        self._renaming = True
        e = getattr(self, 'list_edit', None)
        if e is None:
            e = Gtk.Entry()
            e.add_css_class('sz-inline-edit')
            e.set_halign(Gtk.Align.START)
            e.set_valign(Gtk.Align.START)
            e.set_visible(False)
            e.connect('activate', self._list_edit_commit)
            fc = Gtk.EventControllerFocus()
            fc.connect('leave', self._list_edit_focus_out)
            e.add_controller(fc)
            kc = Gtk.EventControllerKey()
            kc.connect('key-pressed', self._list_edit_key)
            e.add_controller(kc)
            self.list_over.add_overlay(e)
            self.list_edit = e
        self._rename_path = path
        self._rename_state = {'done': False}
        it = getattr(self, '_rename_it', None)
        e.set_text(it.name if it is not None else '')
        try:
            self.tree.scroll_to_cell(path, None, False, 0.0, 0.0)
        except Exception:
            pass
        adj = self.sw_list.get_vadjustment()
        if adj is not None and not getattr(self, '_list_adj_connected', False):
            adj.connect('value-changed', lambda *_: self._list_edit_place())
            self._list_adj_connected = True
        GLib.idle_add(self._list_edit_show)

    def _list_edit_show(self):
        e = getattr(self, 'list_edit', None)
        if e is None or not self._renaming:
            return False
        self._list_edit_place()
        if not self._renaming:
            return False
        e.set_visible(True)
        e.grab_focus()
        e.select_region(0, -1)
        return False

    def _list_edit_place(self):
        e = getattr(self, 'list_edit', None)
        path = getattr(self, '_rename_path', None)
        if e is None or path is None or not self._renaming:
            return
        area = self.tree.get_cell_area(path, self.cols[C_NAME])
        if area.width <= 0 or area.height <= 0:
            self._list_edit_close(False)
            return
        wx, wy = self.tree.convert_bin_window_to_widget_coords(area.x, area.y)
        res = self.tree.translate_coordinates(self.list_over, wx, wy)
        x, y = (res[1], res[2]) if isinstance(res, tuple) and len(res) >= 3 else (res[0], res[1])
        oh = self.list_over.get_height()
        if oh > 0 and (y + area.height <= 0 or y >= oh):
            self._list_edit_close(False)
            return
        off = 26
        w = max(80, int(area.width) - off - 4)
        e.set_size_request(w, int(area.height))
        e.set_margin_start(int(x) + off)
        e.set_margin_top(int(y))

    def _list_edit_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self._list_edit_close(False)
            return True
        return False

    def _list_edit_commit(self, *a):
        self._list_edit_close(True)

    def _list_edit_focus_out(self, *a):
        if self._renaming:
            self._list_edit_close(True)

    def _list_edit_close(self, commit):
        e = getattr(self, 'list_edit', None)
        state = getattr(self, '_rename_state', None)
        if e is None or state is None or state.get('done'):
            return
        state['done'] = True
        text = e.get_text()
        it = getattr(self, '_rename_it', None)
        e.set_visible(False)
        self._renaming = False
        self._rename_path = None
        self._rename_it = None
        if commit and it is not None:
            GLib.idle_add(self._finish_rename, it, text)

    def _finish_rename(self, it, text):
        self.win._do_rename(self, it, text)
        return False

    def cancel_inline_rename(self):
        """Отменить любое активное переименование на месте (список или плитки)."""
        if getattr(self, '_rename_state', None) is not None:
            self._list_edit_close(False)
        if getattr(self, '_tile_edit', None) is not None:
            self._tile_edit_close(False)
        self._renaming = False

    @staticmethod
    def _base_len(name):
        """Длина имени без расширения (как выделяет Nemo)."""
        i = name.rfind('.')
        return i if i > 0 else len(name)

    def _tile_start_rename(self, it):
        parts = next((p for p in self._bound.get(it.full, [])
                      if p.item is not None and getattr(p, 'box', None) is not None), None)
        if parts is None:
            self._renaming = False
            return False
        self._rename_it = it
        self._tile_edit_open(parts, it)
        return True

    def _tile_edit_open(self, parts, it):
        self._renaming = True
        tv = _InlineView()
        tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        tv.set_accepts_tab(False)
        tv.set_monospace(False)
        tv.set_justification(Gtk.Justification.CENTER)
        tv.set_top_margin(0)
        tv.set_bottom_margin(0)
        tv.set_left_margin(0)
        tv.set_right_margin(0)
        tv.add_css_class('sz-inline-text')
        tv.set_halign(Gtk.Align.START)
        tv.set_valign(Gtk.Align.START)
        tv.set_visible(False)
        buf = tv.get_buffer()
        buf.set_text(it.name)
        buf.connect('changed', lambda *_: self._tile_edit_place())
        state = {'done': False}
        tv.connect('destroy', lambda *_: self._tile_edit_close(False))
        fc = Gtk.EventControllerFocus()
        fc.connect('leave', lambda *_: self._tile_edit_close(True))
        tv.add_controller(fc)
        kc = Gtk.EventControllerKey()
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def key(c, keyval, keycode, mods):
            if keyval == Gdk.KEY_Escape:
                self._tile_edit_close(False)
                return True
            if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not (mods & Gdk.ModifierType.SHIFT_MASK):
                self._tile_edit_close(True)
                return True
            return False
        kc.connect('key-pressed', key)
        tv.add_controller(kc)
        self.tiles_over.add_overlay(tv)
        self._tile_edit = tv
        self._tile_edit_parts = parts
        self._tile_edit_state = state
        adj = self._scroll_adj()
        if adj is not None and not getattr(self, '_tile_adj_connected', False):
            adj.connect('value-changed', lambda *_: self._tile_edit_place())
            self._tile_adj_connected = True
        GLib.idle_add(self._tile_edit_show)

    def _tile_edit_show(self):
        tv = getattr(self, '_tile_edit', None)
        if tv is None or not self._renaming:
            return False
        if not self._tile_edit_place():
            return False
        if not self._renaming:
            return False
        tv.set_visible(True)
        tv.grab_focus()
        buf = tv.get_buffer()
        n = self._base_len(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False))
        it = buf.get_iter_at_offset(n)
        buf.select_range(buf.get_start_iter(), it)
        return False

    def _tile_edit_place(self):
        tv = getattr(self, '_tile_edit', None)
        parts = getattr(self, '_tile_edit_parts', None)
        if tv is None or parts is None or not self._renaming:
            return False
        ow = self.tiles_over.get_width()
        oh = self.tiles_over.get_height()
        if ow <= 0:
            return False
        loc = parts.label_ov.translate_coordinates(self.tiles_over, 0, 0)
        li = parts.box.get_parent()
        if li is not None:
            bx, by = li.translate_coordinates(self.tiles_over, 0, 0)
            bw = li.get_width()
        else:
            bx, by = parts.box.translate_coordinates(self.tiles_over, 0, 0)
            bw = parts.box.get_width()
        pad = 16                                     # padding+border поля (из CSS)
        w = max(48, int(bw) - pad)
        if ow - pad > 0:
            w = min(w, ow - pad)
        text = tv.get_buffer().get_text(tv.get_buffer().get_start_iter(),
                                        tv.get_buffer().get_end_iter(), False)
        lay = Pango.Layout(tv.get_pango_context())
        lay.set_width(int(w * Pango.SCALE))
        lay.set_wrap(Pango.WrapMode.WORD_CHAR)
        lay.set_text(text, -1)
        _, th = lay.get_pixel_size()
        h = th + 10
        x = int(bx)
        x = max(0, min(x, ow - w - pad))
        y = int(loc[1])
        if (y + h <= 0) or (y >= oh and oh > 0):
            self._tile_edit_close(False)
            return False
        tv.req = (w, h)
        tv.queue_resize()
        tv.set_margin_start(x)
        tv.set_margin_top(y)
        return True

    def _tile_edit_close(self, commit):
        tv = getattr(self, '_tile_edit', None)
        state = getattr(self, '_tile_edit_state', None)
        if tv is None or state is None or state.get('done'):
            return
        state['done'] = True
        buf = tv.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        it = getattr(self, '_rename_it', None)
        self._tile_edit = None
        self._tile_edit_parts = None
        self._tile_edit_state = None
        self._renaming = False

        def fin():
            if tv.get_parent() is self.tiles_over:
                self.tiles_over.remove_overlay(tv)
            if commit and it is not None:
                self.win._do_rename(self, it, text)
            return False
        GLib.idle_add(fin)

    def _on_key(self, ctrl, keyval, keycode, state):
        self._cancel_scroll_restore()
        if self._renaming:
            return False
        root = self.get_root()
        if root is None or not self._has_focus(root) or self.win.menus.is_open:
            return False
        mods = state & MODMASK
        if self._ta_buf and not mods:
            if keyval == Gdk.KEY_Escape:                  # Esc — стереть набранное
                self._ta_reset()
                return True
            if keyval == Gdk.KEY_BackSpace:               # Backspace — стереть последнюю букву
                self._ta_buf = self._ta_buf[:-1]
                if self._ta_buf:
                    self._ta_touch()
                    self._ta_apply()
                else:
                    self._ta_reset()
                return True
        kv = {Gdk.KEY_KP_Delete: Gdk.KEY_Delete}.get(keyval, keyval)
        act = self.win.list_keys.get((Gdk.keyval_to_lower(kv), int(mods)))
        if act:
            if act == 'switch-panel' and self.win.other_panel() is None:
                return False
            a = self.win.lookup_action(act)
            if a is not None and a.get_enabled():
                a.activate(None)
                return True
            return False
        return self._ta_key(keyval, state)

    # ---------- выбор файла набором букв ----------
    def _ta_text(self):
        return '⌨ ' + self._ta_buf + ('' if self._ta_ok else '  ✗')

    def _ta_reset(self):
        self._ta_buf, self._ta_ok = '', True
        if self._ta_src:
            GLib.source_remove(self._ta_src)
            self._ta_src = 0
        self.update_status()

    def _ta_expire(self):
        self._ta_src = 0
        self._ta_buf, self._ta_ok = '', True
        self.update_status()
        return False

    def _ta_touch(self):
        if self._ta_src:
            GLib.source_remove(self._ta_src)
            self._ta_src = 0
        t = int(self.win.conf['typeahead_timeout'])
        if t > 0:
            self._ta_src = GLib.timeout_add(t, self._ta_expire)

    def _ta_find(self, prefix):
        p = prefix.casefold()
        return [row.path.copy() for row in self.sorted if row[C_NAME].casefold().startswith(p)]

    def _ta_go(self, path):
        self.unselect_all()
        i = path.get_indices()[0]
        if self.view_mode == 'tiles':
            self.tile_sel.select_item(i, True)
            try:
                self.grid.scroll_to(i, Gtk.ListScrollFlags.FOCUS, None)
            except (AttributeError, TypeError):
                pass
        else:
            self.tree.set_cursor(path, None, False)
            self.tree.scroll_to_cell(path, None, False, 0.0, 0.0)
            self._select_path(path)

    def _ta_apply(self):
        buf = self._ta_buf
        matches = self._ta_find(buf)
        if not matches and len(buf) >= 2 and len(set(buf)) == 1:
            # та же буква нажата повторно — переходим к следующему имени на эту букву (по кругу)
            allm = self._ta_find(buf[0])
            if allm:
                cur = [p.get_indices()[0] for p in self._sel_paths()]
                later = [p for p in allm if cur and p.get_indices()[0] > cur[0]]
                matches = [(later or allm)[0]]
        self._ta_ok = bool(matches)
        if matches:
            self._ta_go(matches[0])
        self.update_status()

    def _ta_key(self, keyval, state):
        if not self.win.conf['typeahead']:
            return False
        if state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.ALT_MASK |
                    Gdk.ModifierType.SUPER_MASK | Gdk.ModifierType.META_MASK):
            return False
        code = Gdk.keyval_to_unicode(keyval)
        if not code:
            return False
        ch = chr(code)
        if not ch.isprintable() or (ch == ' ' and not self._ta_buf):
            return False
        self._ta_buf += ch
        self._ta_touch()
        self._ta_apply()
        return True

    def _on_scroll(self, ctrl, dx, dy):
        """Ctrl + колесо мыши — масштаб значков."""
        self._cancel_scroll_restore()
        if not (ctrl.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
            return False
        self._zoom_acc = getattr(self, '_zoom_acc', 0.0) + dy
        if abs(self._zoom_acc) >= 1.0:
            self.win.op_zoom(-1 if self._zoom_acc > 0 else 1)
            self._zoom_acc = 0.0
        return True

    def _on_right_click(self, gesture, n, x, y):
        """Правый щелчок в таблице."""
        self.win.set_active(self)
        w = gesture.get_widget()
        w.grab_focus()
        bx, by = self.tree.convert_widget_to_bin_window_coords(int(x), int(y))
        hit = self.tree.get_path_at_pos(bx, by)
        if hit:
            if not self._is_selected(hit[0]):
                self.unselect_all()
                self._select_path(hit[0])
        else:
            self.unselect_all()
        self.win.open_context_menu(self, w, x, y)
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _tile_right_click(self, gesture, n, x, y, li):
        self.win.set_active(self)
        pos = li.get_position()
        if not self.tile_sel.is_selected(pos):
            self.tile_sel.select_item(pos, True)
        self.grid.grab_focus()
        self.win.open_context_menu(self, gesture.get_widget(), x, y)
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_tiles_press(self, gesture, n, x, y):
        """Рамка выделения — только при старте с пустого места; с плитки сразу начинаем перетаскивание."""
        self.grid.set_enable_rubberband(self._tile_at(x, y) is None)

    def _tile_select_for_drag(self, parts, state):
        """Выделить плитку, с которой начинается перетаскивание, если она ещё не выделена."""
        pos = parts.item.index if parts.item is not None else -1
        if pos < 0 or self.tile_sel.is_selected(pos):
            return
        mod = bool(state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK))
        if not mod:
            self.tile_sel.unselect_all()
        self.tile_sel.select_item(pos, not mod)

    def _on_grid_blank_click(self, gesture, n, x, y):
        self.win.set_active(self)
        self.grid.grab_focus()
        self.unselect_all()
        self.win.open_context_menu(self, self.grid, x, y)

    def _on_drag_prepare(self, src, x, y):
        if self.view_mode == 'tiles':
            parts = self._tile_at(x, y)
            if parts is None or parts.item is None:      # пустое место — это рамка выделения
                return None
            self._tile_select_for_drag(parts, src.get_current_event_state())
        items = self.selected()
        if not items or any(vfs.is_uri(i.full) for i in items):
            return None
        paths = self.win.drag_paths(self, items)
        if not paths:
            return None
        fl = Gdk.FileList.new_from_list([Gio.File.new_for_path(p) for p in paths])
        v = GObject.Value()
        v.init(Gdk.FileList)
        v.set_boxed(fl)
        return Gdk.ContentProvider.new_for_value(v)

    def _on_drop_enter(self, target, x, y):
        self.drop_ring.set_visible(True)
        return target.get_actions()

    def _on_drop_leave(self, target):
        self.drop_ring.set_visible(False)

    def _on_drop(self, target, value, x, y):
        self.drop_ring.set_visible(False)
        paths = [f.get_path() for f in value.get_files() if f.get_path()]
        if not paths:
            return False
        move = False
        if self.mode == 'fs':
            try:
                mods = target.get_current_event_state()
            except Exception:
                mods = 0
            ctrl = bool(mods & Gdk.ModifierType.CONTROL_MASK)
            shift = bool(mods & Gdk.ModifierType.SHIFT_MASK)
            if shift:
                move = True
            elif not ctrl:
                # Как в файловых менеджерах: в пределах одного устройства
                # перетаскивание перемещает, между устройствами — копирует.
                try:
                    dev = os.stat(self.path).st_dev
                    move = all(os.stat(p).st_dev == dev for p in paths)
                except OSError:
                    move = False
        self.win.drop_files(self, paths, move)
        return True
