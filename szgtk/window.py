# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from . import diagnostics
import traceback
from .i18n import _, N_, set_language
from .display import DISP, apply_display, format_size
from .utils import (TAR_COMPOUND, accel_pretty, accel_variants, archive_stem,
                    esc_label, fmt_num, fmt_time, handle_text_shortcut,
                    has_text_target, human, is_archive_name, parse_accel,
                    unique_path)
from .config import Config
from .backend import Job, Result, SevenZip, needs_password
from .theme import apply_theme, style_window
from .icons import clear_icon_cache
from .dialogs import (HistoryDialog, PasswordDialog, ProgressDialog, PromptDialog,
                      OpenWithDialog, alert, choose, confirm, hbox, lbl, pick, pick_icon,
                      text_dialog, vbox)
from .archive_dialogs import (AddDialog, ExtractDialog, SplitDialog,
                              build_add_switches, combine_worker, default_add_opts,
                              extract_switches, split_worker, FMT, FORMATS, LEVELS)
from .settings import EXTRA_ACCELS, HOTKEYS, SettingsDialog
from .benchmark import BenchmarkDialog
from .convert import (ConverterDialog, build_convert_menu, convert_files, kind_of,
                      supports as convert_supports)
from .properties import PropertiesDialog, read_archive_metadata
from .ops import (HASHES, add_thread_limit, count_conflicts, default_stem,
                  groups_from_model, names_for, prepare_add, widget_xy)
from .panel import COLUMNS, LIST_SIZES, TILE_SIZES, Panel
from .menu import MenuBar, MenuLayer
from .menu_layout import (contexts as menu_context_restrictions, hidden as hidden_menu_items,
                          load as load_menu_layout)
from . import vfs
from .favorites import make as fav_make, name as fav_name, path as fav_path
from .sidebar import Sidebar, special_places

class MainWindow(Gtk.ApplicationWindow):
    @property
    def clipboard_data(self):
        app = self.get_application()
        if app is not None and hasattr(app, 'clipboard_data'):
            return app.clipboard_data
        return getattr(self, '_clipboard_data', None)

    @clipboard_data.setter
    def clipboard_data(self, value):
        app = self.get_application()
        if app is not None and hasattr(app, 'clipboard_data'):
            app.clipboard_data = value
        else:
            self._clipboard_data = value

    @property
    def _clip_serial(self):
        app = self.get_application()
        if app is not None and hasattr(app, 'clip_serial'):
            return app.clip_serial
        return getattr(self, '_clip_serial_local', 0)

    @_clip_serial.setter
    def _clip_serial(self, value):
        app = self.get_application()
        if app is not None and hasattr(app, 'clip_serial'):
            app.clip_serial = value
        else:
            self._clip_serial_local = value

    def __init__(self, app, sz, conf, restore=None):
        super().__init__(application=app, title=APP_NAME + (' — root' if IS_ROOT else ''))
        self.sz, self.conf = sz, conf
        self.passwords, self.temp_dirs, self.closing, self.rebuilding = {}, [], False, False
        self._active_archives = set()
        self.clipboard_data, self._clipboard_own = None, False
        self._clip_serial = 0
        self.undo_stack, self.redo_stack, self._history_busy = [], [], False
        self._clipboard = self.get_clipboard()
        self._clip_sig = self._clipboard.connect('changed', self._on_clipboard_changed)
        self.connect('destroy', self._on_destroy_clipboard)
        if conf['design'] not in ('classic', 'dual', 'nav'):
            conf['design'] = 'classic'
        self.design = conf['design']
        self.accels, self.list_keys, self.active, self.sidebar = {}, {}, None, None
        self.side_paned, self._side_save_id = None, 0
        self._side_clamped = False
        self._toolbar_sync_id = 0
        self._status_override = ''
        self._status_timer = 0
        self._progress_timer = 0
        self._p2_shown_once = False
        self._mapped_once = False
        self._disk_seq = 0
        self.set_default_size(conf['width'], conf['height'])
        self.set_icon_name(APP_ID)
        apply_theme(conf)
        apply_display(conf)
        clear_icon_cache()
        style_window(self, conf['scheme'])
        self._register_actions()

        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)
        root = vbox(0)
        self.overlay.set_child(root)
        self.menus = MenuLayer(self, self.overlay)
        self.menubar = MenuBar(self, self._build_menu())
        self.menus.on_close = lambda owner: self.menubar.clear_marks()
        root.append(self.menubar)
        if IS_ROOT:
            ban = hbox(8)
            ban.add_css_class('sz-root-banner')
            ban.append(lbl(_('Running as root: changes are made with full system privileges')))
            root.append(ban)
        kc = Gtk.EventControllerKey()
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        kc.connect('key-pressed', self._on_menu_key)
        self.add_controller(kc)
        self.connect('map', self._on_map)

        if restore:
            start = restore['p1'] if os.path.isdir(restore['p1']) else os.path.expanduser('~')
        elif conf['restore_last_dir'] and os.path.isdir(conf['last_dir']):
            start = conf['last_dir']
        else:
            start = os.path.expanduser('~')
        self.p1, self.p2 = Panel(self, start), Panel(self, start)
        self.active = self.p1
        self.p1.add_css_class('sz-active')
        self.toolbar = self._build_toolbar()
        self.searchbar = self._build_searchbar()
        self.btn_search.bind_property('active', self.searchbar, 'search-mode-enabled',
                                      GObject.BindingFlags.BIDIRECTIONAL)
        self.paned = Gtk.Paned(orientation=H, vexpand=True)
        self.paned.set_start_child(self.p1)
        self.paned.set_end_child(self.p2)
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)
        self.paned.set_shrink_start_child(False)
        self.paned.set_shrink_end_child(False)
        self.statusbar = self._build_statusbar()
        if self.design == 'nav':
            self.sidebar = Sidebar(self)
            right = vbox(0)
            right.set_hexpand(True)
            for w in (self.toolbar, self.searchbar, self.paned):
                right.append(w)
            self.side_paned = Gtk.Paned(orientation=H, vexpand=True)
            self.side_paned.add_css_class('sz-side-paned')
            self.side_paned.set_start_child(self.sidebar)
            self.side_paned.set_end_child(right)
            self.side_paned.set_resize_start_child(False)
            self.side_paned.set_resize_end_child(True)
            self.side_paned.set_shrink_start_child(False)
            self.side_paned.set_shrink_end_child(False)
            try:
                width = int(self.conf.get('sidebar_width') or 220)
            except (TypeError, ValueError):
                width = 220
            self.side_paned.set_position(max(160, width))
            self.side_paned.connect('notify::position', self._on_side_paned_position)
            self.side_paned.connect('notify::max-position', self._on_side_max_position)
            root.append(self.side_paned)
        else:
            for w in (self.toolbar, self.searchbar, self.paned):
                root.append(w)
        root.append(self.statusbar)
        self._sync_toolbar_labels()
        self.apply_top_panels()
        self._toolbar_sync_id = GLib.timeout_add(250, self._sync_toolbar_labels)

        two = True if self.design == 'dual' else bool(conf['two_panels'])
        self.p2.set_visible(two)
        self._p2_shown_once = two
        self.lookup_action('two-panels').set_state(GLib.Variant.new_boolean(two))
        self.lookup_action('two-panels').set_enabled(self.design != 'dual')
        self.lookup_action('hidden').set_state(GLib.Variant.new_boolean(bool(conf['show_hidden'])))
        self.apply_hotkeys()
        for p in (self.p1, self.p2):
            p.apply_options(conf)
        self.p1.navigate_fs(start)
        if two:
            # скрытую вторую панель наполняем при первом показе (см. op_two_panels)
            self.p2.navigate_fs(start)
        if restore:
            self.passwords.update(restore['passwords'])
            self.temp_dirs = restore['temp']
            if restore['p1'] != start:
                self.p1.navigate_text(restore['p1'])
            if two and restore['p2'] and restore['p2'] != start:
                self.p2.navigate_text(restore['p2'])
            self.set_active(self.p2 if restore['active'] == 1 and two else self.p1)
        self.update_statusbar()
        self.connect('close-request', self._on_close)
        self.active.focus_view()

    # ───────────── действия / меню ─────────────
    def reg(self, name, cb, param=None, state=None, sstate=None):
        if sstate is not None:
            act = Gio.SimpleAction.new_stateful(name, GLib.VariantType.new('s'), GLib.Variant.new_string(sstate))
        elif state is not None:
            act = Gio.SimpleAction.new_stateful(name, None, GLib.Variant.new_boolean(state))
        elif param:
            act = Gio.SimpleAction.new(name, GLib.VariantType.new(param))
        else:
            act = Gio.SimpleAction.new(name, None)
        act.connect('activate', cb)
        self.add_action(act)

    def _register_actions(self):
        A = self.reg
        A('open-archive', self.op_open_archive_dialog)
        A('open-sel', self.op_open_sel)
        A('open-inside', self.op_open_inside)
        A('open-outside', self.op_open_outside)
        A('open-with', self.op_open_with)
        A('run', self.op_run)
        A('view', self.op_view)
        A('edit', self.op_edit)
        A('rename', self.op_rename)
        A('copy', self.op_copy)
        A('move', self.op_move)
        A('copy-selection', self.op_copy_selection)
        A('cut-selection', lambda *a: self.op_copy_selection(cut=True))
        A('paste', self.op_paste)
        A('undo', self.op_undo)
        A('redo', self.op_redo)
        A('delete', self.op_delete)
        A('delete-permanent', lambda *a: self.op_delete(permanent=True))
        A('split', self.op_split)
        A('combine', self.op_combine)
        A('properties', self.op_properties)
        A('hash', self.op_hash, param='s')
        A('new-folder', self.op_new_folder)
        A('new-file', self.op_new_file)
        A('new-window', self.op_new_window)
        A('quit', self.op_quit)
        A('select-all', lambda *a: self.active.select_all())
        A('deselect-all', lambda *a: self.active.unselect_all())
        A('invert-sel', lambda *a: self.active.invert_selection())
        A('select-mask', lambda *a: self.op_select_mask(select=True))
        A('deselect-mask', lambda *a: self.op_select_mask(select=False))
        A('sort', lambda a, p: self.active.sort_by(p.get_string()), param='s')
        A('flat', lambda a, p: (self._toggle(a), self.active.toggle_flat()), state=False)
        A('list-mode', self.op_list_mode, state=False)
        A('two-panels', self.op_two_panels, state=False)
        A('menu-bar', self.op_menu_bar, state=True)
        A('toolbar', self.op_toolbar, state=True)
        A('panels-button', self.op_panels_button, state=not bool(self.conf.get('hide_panels_button')))
        A('hidden', self.op_hidden, state=False)
        A('root', lambda *a: self.active.go_root())
        A('up', lambda *a: self.active.go_up())
        A('back', lambda *a: self.active.back())
        A('forward', lambda *a: self.active.forward())
        A('history', self.op_history)
        A('refresh', lambda *a: self.reload_all())
        A('focus-address', lambda *a: self.active.focus_address())
        A('switch-panel', self.op_switch_panel)
        A('toggle-sidebar', self.op_toggle_sidebar)
        A('search', self.op_search)
        A('view-mode', self.op_view_mode, param='s', sstate=self.conf['view_mode'])
        A('view-list', lambda *a: self.set_view_mode('list'))
        A('view-tiles', lambda *a: self.set_view_mode('tiles'))
        A('view-toggle', lambda *a: self.set_view_mode('list' if self.conf['view_mode'] == 'tiles' else 'tiles'))
        A('thumbs', self.op_thumbs, state=bool(self.conf['show_thumbs']))
        A('zoom-in', lambda *a: self.op_zoom(1))
        A('zoom-out', lambda *a: self.op_zoom(-1))
        A('zoom-reset', lambda *a: self.op_zoom(0))
        A('open-as-root', self.op_open_as_root)
        hidden_cols = set(self.conf['columns_hidden'])
        for _idx, _title, _kind in COLUMNS:
            A('col-%d' % _idx, lambda a, p, i=_idx: self.set_column_visible(i, self._toggle(a)),
              state=_idx not in hidden_cols)
        A('fav-add', self.op_fav_add)
        A('fav-remove', self.op_fav_remove, param='i')
        A('fav-rename', self.op_fav_rename, param='i')
        A('fav-save', self.op_fav_save, param='i')
        A('fav-open', self.op_fav_open, param='i')
        A('settings', self.op_settings)
        A('benchmark', lambda *a: BenchmarkDialog(self, self.sz).present())
        A('clean-temp', self.op_clean_temp)
        A('help', self.op_help)
        A('about', self.op_about)
        A('add', self.op_add)
        A('add-7z', lambda *a: self.op_add(fmt='7z'))
        A('add-zip', lambda *a: self.op_add(fmt='zip'))
        A('extract', self.op_extract)
        A('extract-here', lambda *a: self.op_extract(here=True))
        A('extract-dir', lambda *a: self.op_extract(to_dir=True))
        A('test', self.op_test)
        A('info', self.op_info)
        A('convert', self.op_convert)
        A('convert-to', self.op_convert, param='s')
        self._update_undo_actions()


    # ───────────── значки, меню, вид, root ─────────────
    def _on_map(self, w):
        # вид применяем один раз: повторный map (например, разворачивание окна)
        # не должен заново собирать все плитки
        if self._mapped_once:
            return
        self._mapped_once = True
        for p in (self.p1, self.p2):
            if p.get_visible():
                p.apply_view()
        GLib.timeout_add(250, self._refresh_disk_space)

    def accel_text(self, name):
        for hid, action, label, default, scope in HOTKEYS:
            if action == name and self.accels.get(hid):
                return accel_pretty(self.accels[hid])
        return ''

    def _matches_accel(self, hid, keyval, state):
        acc = self.accels.get(hid)
        if not acc:
            return False
        mods = state & MODMASK
        keyval = Gdk.keyval_to_lower(keyval)
        for variant in accel_variants(acc):
            p = parse_accel(variant)
            if p and Gdk.keyval_to_lower(p[0]) == keyval and p[1] == mods:
                return True
        return False

    def open_context_menu(self, panel, widget, x, y):
        pt = widget_xy(widget, self.overlay, x, y) or (x, y)
        self.menus.open(groups_from_model(self.context_menu(panel)), point=pt, owner=('ctx', id(panel)))

    def open_panel_menu(self, panel, button):
        self.menus.open(groups_from_model(self.panel_menu_model), anchor=button, owner=('panel', id(panel)))

    def open_columns_menu(self, button):
        self.menus.open(groups_from_model(self.columns_menu_model), anchor=button, owner=('cols', 0))

    def open_history_menu(self, panel):
        paths = panel.history_paths()[-15:]
        if not paths:
            return
        entries = [dict(label=p, callback=lambda p=p: panel.navigate_text(p)) for p in reversed(paths)]
        self.menus.open([entries], anchor=panel.entry, owner=('hist', id(panel)),
                        min_width=panel.entry.get_width())

    def open_top_panels_menu(self, button):
        hm = bool(self.conf.get('hide_menu_bar'))
        ht = bool(self.conf.get('hide_toolbar'))
        hs = bool(self.conf.get('hide_sidebar'))
        hb = bool(self.conf.get('hide_panels_button'))
        pop = Gtk.Popover()
        pop.add_css_class('sz-panels-popover')
        pop.set_has_arrow(False)
        box = vbox(3)
        box.add_css_class('sz-panels-pop')
        box.set_size_request(324, -1)

        head = vbox(1)
        head.add_css_class('sz-panels-head')
        title = lbl(_('Top panels'))
        title.add_css_class('sz-panels-title')
        sub = lbl(self.top_panels_status())
        sub.add_css_class('sz-panels-sub')
        sub.set_wrap(True)
        sub.set_max_width_chars(38)
        head.append(title)
        head.append(sub)
        box.append(head)

        def add(icon, label, subtitle, cb, checked=None, enabled=True):
            b = Gtk.Button()
            b.add_css_class('flat')
            b.add_css_class('sz-panels-row')
            b.set_focus_on_click(False)
            b.set_sensitive(enabled)
            row = hbox(10)
            if checked is None:
                im = Gtk.Image.new_from_icon_name(icon or 'object-select-symbolic')
            else:
                im = Gtk.Image.new_from_icon_name('object-select-symbolic' if checked else 'checkbox-symbolic')
                im.add_css_class('sz-panels-check' if checked else 'sz-panels-uncheck')
            im.set_pixel_size(16)
            row.append(im)
            txt = vbox(1)
            tl = lbl(label)
            tl.add_css_class('sz-panels-row-title')
            txt.append(tl)
            if subtitle:
                sl = lbl(subtitle)
                sl.add_css_class('sz-panels-note')
                sl.set_wrap(True)
                sl.set_max_width_chars(38)
                txt.append(sl)
            txt.set_hexpand(True)
            row.append(txt)
            b.set_child(row)
            b.connect('clicked', lambda x: (pop.popdown(), cb()))
            box.append(b)
            return b

        add(None, _('Show menu bar') if hm else _('Hide menu bar'), None,
            lambda: self.set_top_panels(hide_menu=not hm), checked=not hm)
        add(None, _('Show action panel') if ht else _('Hide action panel'), None,
            lambda: self.set_top_panels(hide_toolbar=not ht), checked=not ht)
        if self.sidebar is not None:
            add(None, _('Show sidebar') if hs else _('Hide sidebar'),
                _('Places, favorites and devices') if not hs else None,
                lambda: self.set_top_panels(hide_sidebar=not hs), checked=not hs)
        add(None, _('Show “Panels” button') if hb else _('Hide “Panels” button'),
            _('You can restore it later from View → Panels button') if not hb and not hm else None,
            lambda: self.set_top_panels(hide_panels_button=not hb), checked=not hb)
        sep = Gtk.Separator()
        sep.add_css_class('sz-panels-sep')
        box.append(sep)
        add(None, _('Show both panels'), _('The hiding mode will be turned off.'),
            lambda: self.set_top_panels(show_all=True),
            checked=not hm and not ht, enabled=hm or ht)
        sep = Gtk.Separator()
        sep.add_css_class('sz-panels-sep')
        box.append(sep)
        add('emblem-system-symbolic', _('Interface settings…'), None,
            lambda: self.op_settings(page=3))

        pop.set_child(box)
        pop.set_parent(button)
        pop.connect('closed', lambda p: p.unparent())
        pop.popup()
        return pop

    def _on_menu_key(self, ctrl, keyval, keycode, state):
        if handle_text_shortcut(self, keyval, state):
            return True
        m = self.menus
        if not m.is_open:
            if keyval == Gdk.KEY_F10 and not (state & MODMASK):
                self.menubar.open_index(0, focus=True)
                return True
            if not has_text_target(self):
                if self._matches_accel('undo', keyval, state):
                    self.op_undo()
                    return True
                if self._matches_accel('redo', keyval, state):
                    self.op_redo()
                    return True
            return False
        if keyval == Gdk.KEY_Escape:
            m.close()
            return True
        o, depth = m.owner, len(m.levels)
        if keyval == Gdk.KEY_Right:
            focus = self.get_focus()
            for b, e in m.levels[-1]['rows']:
                if b is focus and e.get('submenu') is not None:
                    m._open_sub(e, b, depth - 1)
                    m.focus_first(len(m.levels) - 1)
                    return True
            if o and o[0] == 'bar' and depth == 1:
                self.menubar.open_index((o[1] + 1) % len(self.menubar.items), focus=True)
                return True
        if keyval == Gdk.KEY_Left:
            if depth > 1:
                m._remove_levels(depth - 1)
                m.focus_first(len(m.levels) - 1)
                return True
            if o and o[0] == 'bar':
                self.menubar.open_index((o[1] - 1) % len(self.menubar.items), focus=True)
                return True
        return False

    def set_view_mode(self, mode):
        self.conf['view_mode'] = mode
        self.lookup_action('view-mode').set_state(GLib.Variant.new_string(mode))
        for p in (self.p1, self.p2):
            p.apply_view()

    def op_view_mode(self, action, param):
        self.set_view_mode(param.get_string())

    def op_thumbs(self, action, param):
        self.conf['show_thumbs'] = self._toggle(action)
        for p in (self.p1, self.p2):
            p.apply_view(force=True)      # перепривязать плитки, чтобы запросить/убрать миниатюры
            p.view.queue_draw()

    def op_zoom(self, delta):
        if delta == 0:
            key = 'tile_icon_size' if self.active.view_mode == 'tiles' else 'list_icon_size'
            self.conf[key] = Config.DEFAULTS[key]
        else:
            self.active.zoom(delta)
        for p in (self.p1, self.p2):
            p.apply_view()

    def op_open_as_root(self, *a, target=None):
        """Открыть папку от root в текущем окне через GVfs admin (polkit)."""
        if IS_ROOT:
            return
        p = self.active
        if target is None:
            if p.mode == 'fs':
                dirs = [i for i in p.selected() if i.is_dir]
                target = dirs[0].full if dirs else p.path
            else:
                target = vfs.dirname(p.arc.display)
        if vfs.is_uri(target):
            return
        if not vfs.is_admin(target) and not vfs.is_dir(target):
            parent = vfs.dirname(target)
            if parent:
                target = parent
        p.navigate_admin(target if vfs.is_admin(target) else vfs.admin_uri(target))

    def apply_hotkeys(self):
        app = self.get_application()
        over = self.conf['accels']
        self.accels, self.list_keys = {}, {}
        glob = {}
        for hid, action, label, default, scope in HOTKEYS:
            acc = over.get(hid, default)
            self.accels[hid] = acc
            app.set_accels_for_action('win.' + action, [])
        for hid, action, label, default, scope in HOTKEYS:
            acc = self.accels[hid]
            if not acc:
                continue
            if scope == 'global':
                for a in accel_variants(acc):
                    glob.setdefault(action, []).append(a)
                for extra in EXTRA_ACCELS.get(hid, []):
                    glob[action].extend(accel_variants(extra))
            else:
                for a in accel_variants(acc):
                    p = parse_accel(a)
                    if p:
                        self.list_keys[(Gdk.keyval_to_lower(p[0]), p[1])] = action
        for action, lst in glob.items():
            unique = []
            for a in lst:
                if a not in unique:
                    unique.append(a)
            app.set_accels_for_action('win.' + action, unique)
        self.update_hints()

    def update_hints(self):
        if not self.conf['show_hints']:
            self.st_hint.set_text('')
            return
        parts = []
        sw = accel_pretty(self.accels.get('switch-panel', ''))
        if self.design == 'dual' and sw:
            parts.append(sw + ' — ' + _('switch panel'))
        parts.append('Enter — ' + _('open'))
        up = accel_pretty(self.accels.get('up', ''))
        if up:
            parts.append(up + ' — ' + (_('up') if self.design == 'dual' else _('to the parent folder')))
        self.st_hint.set_text('  ·  '.join(parts))

    @staticmethod
    def _toggle(action):
        v = not action.get_state().get_boolean()
        action.set_state(GLib.Variant.new_boolean(v))
        return v

    def _build_menu(self):
        def sec(*items):
            s = Gio.Menu()
            for it in items:
                if isinstance(it, Gio.Menu):
                    s.append_submenu(it.label, it)
                else:
                    s.append(it[0], it[1])
            return s

        def item_t(label, action, target):
            it = Gio.MenuItem.new(label, None)
            it.set_action_and_target_value(action, target)
            return it

        hashm = Gio.Menu()
        for alg in HASHES:
            hashm.append_item(item_t(esc_label(alg), 'win.hash', GLib.Variant.new_string(alg)))
        sortm = Gio.Menu()
        for lab, key in ((_('Name'), 'name'), (_('Type'), 'type'), (_('Modified'), 'mtime'),
                         (_('Size'), 'size'), (_('Unsorted'), 'none')):
            sortm.append_item(item_t(lab, 'win.sort', GLib.Variant.new_string(key)))
        favsave = Gio.Menu()
        for n in range(10):
            favsave.append_item(item_t(_('Bookmark') + ' %d' % n, 'win.fav-save', GLib.Variant.new_int32(n)))
        self.fav_list = Gio.Menu()
        self.fav_remove = Gio.Menu()
        self.fav_rename = Gio.Menu()
        colm = Gio.Menu()
        for _idx, _title, _kind in COLUMNS:
            colm.append(_(_title), 'win.col-%d' % _idx)
        self.columns_menu_model = colm
        pm = Gio.Menu()
        for lab, act in ((_('Refresh'), 'win.refresh'), (_('Show hidden files'), 'win.hidden'),
                         (_('Flat view'), 'win.flat'), (_('Select all'), 'win.select-all')):
            pm.append(lab, act)
        pm.append_submenu(_('Sort by'), sortm)
        self.panel_menu_model = pm

        m = Gio.Menu()
        f = Gio.Menu()
        f.append_section(None, sec((_('Open archive…'), 'win.open-archive'), (_('Open inside'), 'win.open-inside'),
                                   (_('Open outside'), 'win.open-outside'), (_('Open with…'), 'win.open-with'),
                                   (_('View'), 'win.view'), (_('Edit'), 'win.edit')))
        f.append_section(None, sec((_('Rename'), 'win.rename'), (_('Copy to…'), 'win.copy'),
                                   (_('Move to…'), 'win.move'), (_('Delete'), 'win.delete')))
        s3 = sec((_('Split file…'), 'win.split'), (_('Combine files…'), 'win.combine'))
        f.append_section(None, s3)
        s4 = sec((_('Properties'), 'win.properties'))
        s4.append_submenu(_('Checksum'), hashm)
        f.append_section(None, s4)
        f.append_section(None, sec((_('Create folder'), 'win.new-folder'), (_('Create file'), 'win.new-file')))
        f.append_section(None, sec((_('New window'), 'win.new-window')))
        if not IS_ROOT:
            f.append_section(None, sec((_('Open as root'), 'win.open-as-root')))
        f.append_section(None, sec((_('Exit'), 'win.quit')))
        m.append_submenu(_('File'), f)

        e = Gio.Menu()
        e.append_section(None, sec((_('Undo'), 'win.undo'), (_('Redo'), 'win.redo')))
        e.append_section(None, sec((_('Copy'), 'win.copy-selection'), (_('Cut'), 'win.cut-selection'),
                                   (_('Paste'), 'win.paste')))
        e.append_section(None, sec((_('Select all'), 'win.select-all'), (_('Deselect all'), 'win.deselect-all'),
                                   (_('Invert selection'), 'win.invert-sel'), (_('Select…'), 'win.select-mask'),
                                   (_('Deselect…'), 'win.deselect-mask')))
        m.append_submenu(_('Edit'), e)

        v = Gio.Menu()
        s = Gio.Menu()
        s.append_item(item_t(_('Details'), 'win.view-mode', GLib.Variant.new_string('list')))
        s.append_item(item_t(_('Tiles'), 'win.view-mode', GLib.Variant.new_string('tiles')))
        s.append(_('Show thumbnails'), 'win.thumbs')
        s.append(_('Zoom in'), 'win.zoom-in')
        s.append(_('Zoom out'), 'win.zoom-out')
        s.append(_('Actual size'), 'win.zoom-reset')
        v.append_section(None, s)
        s = Gio.Menu()
        s.append_submenu(_('Columns'), colm)
        s.append(_('List (names only)'), 'win.list-mode')
        s.append(_('Flat view'), 'win.flat')
        s.append(_('2 panels'), 'win.two-panels')
        s.append(_('Menu bar'), 'win.menu-bar')
        s.append(_('Action panel'), 'win.toolbar')
        if self.design == 'nav':
            s.append(_('Sidebar'), 'win.toggle-sidebar')
        s.append(_('Panels button'), 'win.panels-button')
        s.append(_('Search'), 'win.search')
        s.append(_('Show hidden files'), 'win.hidden')
        v.append_section(None, s)
        s = Gio.Menu()
        s.append_submenu(_('Sort by'), sortm)
        v.append_section(None, s)
        v.append_section(None, sec((_('Open root folder'), 'win.root'), (_('Up one level'), 'win.up'),
                                   (_('Back'), 'win.back'), (_('Forward'), 'win.forward'),
                                   (_('Folders history…'), 'win.history'), (_('Refresh'), 'win.refresh')))
        m.append_submenu(_('View'), v)

        fv = Gio.Menu()
        s = Gio.Menu()
        s.append(_('Add current folder to Favorites'), 'win.fav-add')
        s.append_submenu(_('Add folder to Favorites as'), favsave)
        fv.append_section(None, s)
        fv.append_section(None, self.fav_list)
        s = Gio.Menu()
        s.append_submenu(_('Remove from Favorites'), self.fav_remove)
        s.append_submenu(_('Rename favorite'), self.fav_rename)
        fv.append_section(None, s)
        m.append_submenu(_('Favorites'), fv)
        self._rebuild_fav()

        t = Gio.Menu()
        t.append_section(None, sec((_('Convert…'), 'win.convert'),
                                   (_('Settings…'), 'win.settings'), (_('Benchmark'), 'win.benchmark'),
                                   (_('Delete temporary files'), 'win.clean-temp')))
        m.append_submenu(_('Tools'), t)
        h = Gio.Menu()
        h.append_section(None, sec((_('Contents…'), 'win.help'), (_('About Archive Navigator…'), 'win.about')))
        m.append_submenu(_('Help'), h)
        return m

    def _build_toolbar(self):
        horiz = self.design != 'classic'
        bar = hbox(2)
        self._toolbar_labels = []
        self._toolbar_full_width = 0
        self._toolbar_compact = False
        bar.add_css_class('sz-toolbar')
        if horiz:
            bar.add_css_class('sz-toolbar-h')
        for icon, text, cb, primary in (
                ('list-add-symbolic', N_('Add'), self.op_add, True),
                ('folder-download-symbolic', N_('Extract'), self.op_extract, True),
                ('object-select-symbolic', N_('Test'), self.op_test, False),
                ('edit-copy-symbolic', N_('Copy'), self.op_copy, False),
                ('go-next-symbolic', N_('Move'), self.op_move, False),
                ('edit-delete-symbolic', N_('Delete'), self.op_delete, False),
                ('dialog-information-symbolic', N_('Info'), self.op_info, False),
                (pick_icon('security-high-symbolic', 'dialog-password-symbolic', 'emblem-system-symbolic'),
                 N_('As root'), self.op_open_as_root, False)):
            if cb == self.op_open_as_root and IS_ROOT:
                continue
            b = Gtk.Button()
            b.add_css_class('flat')
            if primary:
                b.add_css_class('sz-primary')
            b.set_focus_on_click(False)
            box = hbox(8) if horiz else vbox(2)
            img = Gtk.Image.new_from_icon_name(icon)
            img.set_pixel_size(16 if horiz else 22)
            box.append(img)
            lab = lbl(_(text), 0.5)
            # подписи прячутся, когда панель действий не помещается: иначе она
            # увеличивает минимальную ширину окна и «съедает» боковую панель
            lab.set_ellipsize(Pango.EllipsizeMode.END)
            box.append(lab)
            self._toolbar_labels.append(lab)
            b.set_child(box)
            b.set_tooltip_text(_(text))
            b.connect('clicked', lambda x, c=cb: c())
            bar.append(b)
        sp = Gtk.Box()
        sp.set_hexpand(True)
        bar.append(sp)
        self.btn_search = Gtk.ToggleButton()
        self.btn_search.set_icon_name('system-search-symbolic')
        self.btn_search.add_css_class('flat')
        self.btn_search.set_tooltip_text(_('Search'))
        self.btn_search.set_focus_on_click(False)
        bar.append(self.btn_search)
        # запоминаем ширину «как есть», пока подписи ещё видны
        self._toolbar_full_width = bar.measure(Gtk.Orientation.HORIZONTAL, -1)[1]
        return bar

    def _toolbar_available_width(self):
        """Сколько места реально есть у панели действий."""
        if self.side_paned is not None:
            end = self.side_paned.get_end_child()
            end_w = end.get_width() if end is not None else 0
            if end_w > 1:
                return end_w
        width = self.get_width()
        if width > 1:
            return width
        try:
            width = int(self.conf.get('width') or 1100)
        except (TypeError, ValueError):
            width = 1100
        try:
            width -= int(self.conf.get('sidebar_width') or 220)
        except (TypeError, ValueError):
            width -= 220
        return width

    def _sync_toolbar_labels(self):
        """Спрятать подписи кнопок, если панель действий не помещается по ширине."""
        labels = getattr(self, '_toolbar_labels', None)
        bar = getattr(self, 'toolbar', None)
        if not labels or bar is None:
            return True
        if not self._toolbar_full_width:
            self._toolbar_full_width = bar.measure(Gtk.Orientation.HORIZONTAL, -1)[1]
        compact = self._toolbar_available_width() < self._toolbar_full_width
        if compact != self._toolbar_compact:
            self._toolbar_compact = compact
            for lab in labels:
                lab.set_visible(not compact)
        return True

    def _build_searchbar(self):
        sb = Gtk.SearchBar()
        e = Gtk.SearchEntry()
        e.set_hexpand(True)
        e.set_placeholder_text(_('Filter by name…'))
        sb.set_child(e)
        sb.connect_entry(e)
        e.connect('search-changed', lambda en: self.active.set_filter(en.get_text()))
        sb.connect('notify::search-mode-enabled', self._on_search_mode)
        self.search_entry = e
        return sb

    def _on_search_mode(self, sb, pspec):
        if sb.get_search_mode():
            self.search_entry.grab_focus()
        else:
            self.search_entry.set_text('')
            for p in (self.p1, self.p2):
                p.set_filter('')
            self.active.focus_view()

    def clear_search(self):
        if self.search_entry.get_text():
            self.search_entry.set_text('')

    def _build_statusbar(self):
        bar = hbox(12)
        bar.add_css_class('sz-statusbar')
        self.st_main = lbl('')
        self.st_main.add_css_class('sz-st-main')
        self.st_sel = lbl('')
        self.st_sel.add_css_class('sz-muted')
        self.st_disk = lbl('')
        self.st_disk.add_css_class('sz-muted')
        self.st_progress = Gtk.ProgressBar()
        self.st_progress.add_css_class('sz-st-progress')
        self.st_progress.set_show_text(False)
        self.st_progress.set_valign(Gtk.Align.CENTER)
        self.st_progress.set_visible(False)
        sp = Gtk.Box()
        sp.set_hexpand(True)
        self.st_hint = lbl('')
        self.st_hint.add_css_class('sz-muted')
        self.zoom_scale = Gtk.Scale.new_with_range(H, 0, 8, 1)
        self.zoom_scale.set_draw_value(False)
        self.zoom_scale.set_round_digits(0)
        self.zoom_scale.set_size_request(130, -1)
        self.zoom_scale.set_focus_on_click(False)
        self.zoom_scale.set_tooltip_text(_('Icon size'))
        self._zoom_lock = False
        self.zoom_scale.connect('value-changed', self._on_zoom_slider)
        for w in (self.st_main, self.st_sel, self.st_disk, self.st_progress,
                  sp, self.st_hint, self.zoom_scale):
            bar.append(w)
        return bar

    def update_zoom_slider(self):
        if not hasattr(self, 'zoom_scale') or self.active is None:
            return
        tiles = self.active.view_mode == 'tiles'
        sizes = TILE_SIZES if tiles else LIST_SIZES
        cur = self.conf['tile_icon_size' if tiles else 'list_icon_size']
        self._zoom_lock = True
        self.zoom_scale.set_range(0, len(sizes) - 1)
        self.zoom_scale.set_value(min(range(len(sizes)), key=lambda i: abs(sizes[i] - cur)))
        self._zoom_lock = False

    def _on_zoom_slider(self, scale):
        if self._zoom_lock:
            return
        tiles = self.active.view_mode == 'tiles'
        sizes = TILE_SIZES if tiles else LIST_SIZES
        self.conf['tile_icon_size' if tiles else 'list_icon_size'] = sizes[int(round(scale.get_value()))]
        for p in (self.p1, self.p2):
            p.apply_view()

    @staticmethod
    def selected_text(sel):
        size = sum(i.size for i in sel if i.size > 0)
        if size:
            return _('Selected: {0} · {1}').format(len(sel), format_size(size, with_unit=True))
        return _('Selected: {0}').format(len(sel))

    def update_statusbar(self):
        if not hasattr(self, 'st_main') or self.active is None:
            return
        if self._status_override:
            self.st_main.set_text(self._status_override)
            self.st_sel.set_text('')
            return
        total, sel = self.active.counts()
        self.st_main.set_text(_('Objects: {0}').format(total))
        if self.active._ta_buf:
            self.st_sel.set_text(self.active._ta_text())
        else:
            self.st_sel.set_text(self.selected_text(sel) if sel else '')

    def _refresh_disk_space(self):
        """Запросить свободное место на диске активной панели.

        Запрос асинхронный и запускается уже после первого кадра, поэтому
        старт окна не задерживается даже на сетевых ФС.
        """
        if (not hasattr(self, 'st_disk') or self.active is None
                or self.closing or not self.get_mapped()):
            return False
        loc = self.active.current_dir()
        if not loc or vfs.is_uri(loc):
            self.st_disk.set_text('')
            self.st_disk.set_tooltip_text(None)
            return False
        self._disk_seq += 1
        Gio.File.new_for_path(loc).query_filesystem_info_async(
            'filesystem::free,filesystem::size', GLib.PRIORITY_LOW, None,
            self._disk_info_done, self._disk_seq)
        return False

    def _disk_info_done(self, gfile, res, seq):
        if seq != self._disk_seq or self.closing:
            return
        free = size = None
        try:
            info = gfile.query_filesystem_info_finish(res)
            if info.has_attribute('filesystem::free'):
                free = info.get_attribute_uint64('filesystem::free')
            if info.has_attribute('filesystem::size'):
                size = info.get_attribute_uint64('filesystem::size')
        except GLib.Error:
            pass
        if free is None:
            self.st_disk.set_text('')
            self.st_disk.set_tooltip_text(None)
            return
        # Для диска всегда показываем адаптивные единицы, даже если размеры
        # файлов в настройках выводятся в байтах.
        cfg = dict(DISP, size_mode='adaptive')
        text = format_size(free, cfg)
        self.st_disk.set_text(_('Free: {0}').format(text))
        if size:
            self.st_disk.set_tooltip_text(
                _('Free space: {0} of {1}').format(text, format_size(size, cfg)))
        else:
            self.st_disk.set_tooltip_text(_('Free space: {0}').format(text))

    def panel_status_changed(self, panel):
        if panel is self.active:
            self.update_statusbar()

    def set_status_message(self, panel, text):
        if self._status_override:
            return
        if panel is self.active and hasattr(self, 'st_main'):
            self.st_main.set_text(text)
            self.st_sel.set_text('')

    def begin_status_progress(self, text):
        """Показать в статусбаре процесс извлечения с индикатором."""
        self._set_status_override(text)
        self._stop_status_timer()
        if not hasattr(self, 'st_progress'):
            return
        self.st_progress.set_visible(True)
        self.st_progress.pulse()
        if not self._progress_timer:
            self._progress_timer = GLib.timeout_add(100, self._pulse_status_progress)

    def _pulse_status_progress(self):
        if not hasattr(self, 'st_progress') or not self.st_progress.get_visible():
            self._progress_timer = 0
            return False
        self.st_progress.pulse()
        return True

    def _stop_status_progress(self):
        if self._progress_timer:
            GLib.source_remove(self._progress_timer)
            self._progress_timer = 0
        if hasattr(self, 'st_progress'):
            self.st_progress.set_visible(False)

    def end_status_progress(self, note=None, seconds=4.0):
        self._stop_status_progress()
        if note:
            self.show_status_note(note, seconds)
        else:
            self._set_status_override('')
            self.update_statusbar()

    def show_status_note(self, text, seconds=4.0):
        """Показать сообщение в статусбаре вместо счётчика объектов."""
        self._set_status_override(text)
        self._stop_status_timer()
        if seconds > 0:
            self._status_timer = GLib.timeout_add(
                int(seconds * 1000), self._clear_status_note)

    def _set_status_override(self, text):
        self._status_override = text or ''
        if hasattr(self, 'st_main'):
            self.st_main.set_text(self._status_override)
            self.st_sel.set_text('')

    def _stop_status_timer(self):
        if self._status_timer:
            GLib.source_remove(self._status_timer)
            self._status_timer = 0

    def _clear_status_note(self):
        self._status_timer = 0
        self._status_override = ''
        self.update_statusbar()
        return False

    def panel_changed(self, panel):
        if self.sidebar is not None and panel is self.active:
            self.sidebar.set_active(panel.current_dir() if panel.mode == 'fs' and not vfs.is_uri(panel.path) else None)
        if panel is self.active:
            self._refresh_disk_space()

    def place_label(self, path):
        if vfs.is_uri(path):
            return None
        norm = os.path.normpath(path)
        if self.sidebar is not None:
            device = self.sidebar.device_label(norm)
            if device:
                return device
        for icon, label, p in special_places():
            if p == norm:
                return label
        return _('File system') if norm == '/' else None

    def set_column_visible(self, idx, vis):
        hidden = set(self.conf['columns_hidden'])
        (hidden.discard if vis else hidden.add)(idx)
        self.conf['columns_hidden'] = sorted(hidden)
        act = self.lookup_action('col-%d' % idx)
        if act is not None:
            act.set_state(GLib.Variant.new_boolean(bool(vis)))
        for p in (self.p1, self.p2):
            p._set_cols()

    def _active_menu_contexts(self, panel, sel):
        # Ситуации взаимоисключающие: внутри архива важнее выделения,
        # несколько элементов — важнее их типов.
        if panel.mode != 'fs':
            return {'inside'}
        if not sel:
            return {'empty'}
        if len(sel) > 1:
            return {'multi'}
        item = sel[0]
        if item.is_dir:
            return {'folder'}
        if is_archive_name(item.name):
            return {'archive'}
        kind = kind_of(item.full)
        if kind in ('audio', 'video', 'image'):
            return {kind}
        return {'file'}

    def context_menu(self, panel):
        sel = panel.selected()
        fs = panel.mode == 'fs'
        active_contexts = self._active_menu_contexts(panel, sel)
        restrictions = menu_context_restrictions(self.conf)
        entries, subs = {}, {}

        if sel:
            entries['open'] = (_('Open'), 'win.open-sel')
        if sel and fs and not sel[0].is_dir:
            if vfs.is_program(sel[0].full):
                entries['run'] = (_('Run'), 'win.run')
            entries['open-with'] = (_('Open with…'), 'win.open-with')
        if sel and fs:
            conv = [i.full for i in sel if not i.is_dir and kind_of(i.full)]
            if conv:
                entries['convert'] = (_('Convert…'), 'win.convert')
                entries['convert-to'] = (_('Convert to'), None)
                subs['convert-to'] = build_convert_menu(conv)
        if fs:
            archives = [i for i in sel if not i.is_dir and is_archive_name(i.name)]
            if sel:
                stem = default_stem([i.full for i in sel])
                entries['add'] = (_('Add to archive…'), 'win.add')
                entries['add-7z'] = (_('Add to "{0}.7z"').format(esc_label(stem)), 'win.add-7z')
                entries['add-zip'] = (_('Add to "{0}.zip"').format(esc_label(stem)), 'win.add-zip')
            if archives:
                entries['extract'] = (_('Extract files…'), 'win.extract')
                entries['extract-here'] = (_('Extract here'), 'win.extract-here')
                entries['extract-dir'] = (
                    _('Extract to "{0}/"').format(esc_label(archive_stem(archives[0].name))),
                    'win.extract-dir')
                entries['test'] = (_('Test archive'), 'win.test')
            elif sel and not sel[0].is_dir:
                entries['open-inside'] = (_('Open inside'), 'win.open-inside')
        else:
            entries['extract'] = (_('Extract files…'), 'win.extract')
            entries['test'] = (_('Test archive'), 'win.test')
            entries['add-files'] = (_('Add files…'), 'win.add')
        if sel:
            entries['rename'] = (_('Rename'), 'win.rename')
            entries['copy-selection'] = (_('Copy'), 'win.copy-selection')
            entries['cut-selection'] = (_('Cut'), 'win.cut-selection')
            entries['copy'] = (_('Copy to…'), 'win.copy')
            entries['move'] = (_('Move to…'), 'win.move')
            entries['delete'] = (_('Delete'), 'win.delete')
            if fs:
                entries['checksum'] = (_('Checksum'), None)
                hm = Gio.Menu()
                for alg in HASHES:
                    it = Gio.MenuItem.new(esc_label(alg), None)
                    it.set_action_and_target_value('win.hash', GLib.Variant.new_string(alg))
                    hm.append_item(it)
                subs['checksum'] = hm
            entries['properties'] = (_('Properties'), 'win.properties')
        entries['paste'] = (_('Paste'), 'win.paste')
        entries['new-folder'] = (_('Create folder'), 'win.new-folder')
        entries['select-all'] = (_('Select all'), 'win.select-all')
        entries['refresh'] = (_('Refresh'), 'win.refresh')
        if fs and not IS_ROOT and not vfs.is_uri(p.path):
            entries['open-as-root'] = (_('Open as root'), 'win.open-as-root')

        hidden = hidden_menu_items(self.conf)
        menu = Gio.Menu()
        current_section, section_menu = None, None
        for item_id, section in load_menu_layout(self.conf):
            if item_id in hidden or item_id not in entries:
                continue
            allowed = restrictions.get(item_id)
            if allowed is not None and not (allowed & active_contexts):
                continue
            if section != current_section:
                if section_menu is not None and section_menu.get_n_items():
                    menu.append_section(None, section_menu)
                section_menu, current_section = Gio.Menu(), section
            label, action = entries[item_id]
            if action is None:
                section_menu.append_submenu(label, subs[item_id])
            else:
                section_menu.append(label, action)
        if section_menu is not None and section_menu.get_n_items():
            menu.append_section(None, section_menu)
        return menu

    def _rebuild_fav(self):
        for m in (self.fav_list, self.fav_remove, self.fav_rename):
            m.remove_all()
        for n in range(10):
            v = self.conf['favorites'].get(str(n))
            if not fav_path(v):
                continue
            label = '%d: %s' % (n, fav_name(v))
            it = Gio.MenuItem.new(label, None)
            it.set_action_and_target_value('win.fav-open', GLib.Variant.new_int32(n))
            self.fav_list.append_item(it)
            rm = Gio.MenuItem.new(label, None)
            rm.set_action_and_target_value('win.fav-remove', GLib.Variant.new_int32(n))
            self.fav_remove.append_item(rm)
            rn = Gio.MenuItem.new(label, None)
            rn.set_action_and_target_value('win.fav-rename', GLib.Variant.new_int32(n))
            self.fav_rename.append_item(rn)

    def _each_window(self):
        """Все окна приложения (или только это, если приложение тестовое)."""
        app = self.get_application()
        wins = list(getattr(app, 'wins', None) or []) if app is not None else []
        return wins or [self]

    def _fav_changed(self):
        self.conf.save()
        for win in self._each_window():
            win._rebuild_fav()
            if win.sidebar is not None:
                win.sidebar.rebuild()

    def op_fav_add(self, *a):
        loc, favs = self.active.location_text(), self.conf['favorites']
        if loc in [fav_path(v) for v in favs.values()]:
            return
        for n in range(10):
            if not favs.get(str(n)):
                favs[str(n)] = loc
                self._fav_changed()
                return
        alert(self, _('All 10 favorite slots are used'), _('Remove one first (Favorites → Remove from Favorites).'))

    def op_fav_remove(self, action, param):
        self.conf['favorites'].pop(str(param.get_int32()), None)
        self._fav_changed()

    def op_fav_rename(self, action, param):
        key = str(param.get_int32())
        v = self.conf['favorites'].get(key)
        if not v:
            return

        def done(new):
            new = (new or '').strip()
            if not new:
                return
            self.conf['favorites'][key] = fav_make(fav_path(v), new)
            self._fav_changed()
        PromptDialog(self, _('Rename favorite'), _('Name:'), fav_name(v), _('OK'), done).present()

    # ───────────── панели ─────────────
    def set_active(self, panel):
        if panel is self.active:
            return
        self.active.remove_css_class('sz-active')
        self.active = panel
        self.update_zoom_slider()
        panel.add_css_class('sz-active')
        for p in (self.p1, self.p2):
            p.refresh_chrome()
        self.update_statusbar()
        self._refresh_disk_space()
        self.panel_changed(panel)

    def other_panel(self):
        o = self.p2 if self.active is self.p1 else self.p1
        return o if o.get_visible() else None

    def reload_all(self):
        for p in (self.p1, self.p2):
            if p.get_visible():
                p.reload()

    def list_async(self, path, pw, cb):
        def work():
            tmp, local = None, path
            if vfs.is_uri(path):
                try:
                    tmp, local = vfs.copy_to_temp(path)
                except Exception as e:
                    GLib.idle_add(lambda: alert(self, _('Cannot open file'), str(e)))
                    return
            r = self.sz.list_archive(local, pw)

            def fin():
                try:
                    cb(*r)
                finally:
                    if tmp:
                        shutil.rmtree(tmp, ignore_errors=True)
                return False
            GLib.idle_add(fin)
        threading.Thread(target=work, daemon=True).start()

    def ask_password(self, path, cb):
        PasswordDialog(self, os.path.basename(path), cb).present()

    # ───────────── фоновые задачи ─────────────
    def run_job(self, title, worker, on_done, parent=None, subtitle=None, pausable=False,
                icon=''):
        job = Job()
        job.subtitle = subtitle or (title + '…')
        job.pausable = pausable
        job.icon = icon
        dlg = ProgressDialog(parent or self, title, job)
        res = {}
        app = self.get_application()
        if app is not None:
            # пока идёт задание, приложение не должно завершиться, даже если
            # закрыть все окна — иначе 7-Zip останется сиротой, а результат
            # потеряется
            app.hold()
        started = time.monotonic()
        diagnostics.log('задание «%s» начато (RSS=%s МБ)', title, diagnostics.rss_mb())

        def target():
            try:
                res['v'] = worker(job)
            except Exception as e:  # noqa
                res['e'] = e
                diagnostics.log('задание «%s»: исключение:\n%s', title,
                                traceback.format_exc().rstrip('\n'))
            GLib.idle_add(fin)

        def fin():
            diagnostics.log('задание «%s» завершено за %.1f с (отменено=%s, RSS=%s МБ)',
                            title, time.monotonic() - started, job.cancelled,
                            diagnostics.rss_mb())
            dlg.finish()
            try:
                on_done(res.get('v'), res.get('e'), job)
            except Exception:  # noqa
                diagnostics.log('задание «%s»: ошибка обработчика:\n%s', title,
                                traceback.format_exc().rstrip('\n'))
            finally:
                if app is not None:
                    app.release()
            return False
        threading.Thread(target=target, daemon=True).start()

    def run7(self, title, command, switches, positional, on_done, cwd=None, archive=None, password=None):
        pw = password if password is not None else self.passwords.get(archive)

        def work(job):
            return self.sz.run(command, switches, positional, cwd=cwd, job=job, password=pw)

        def done(res, err, job):
            if err is not None:
                alert(self, str(err))
                on_done(Result(255, str(err)))
                return
            if archive and needs_password(res):
                def got(p):
                    if p is None:
                        on_done(res)
                    else:
                        self.run7(title, command, switches, positional, on_done, cwd, archive, p)
                self.ask_password(archive, got)
                return
            if res.ok and archive and pw:
                self.passwords[archive] = pw
            on_done(res)
        icon = ('package-x-generic-symbolic' if command in ('a', 'u', 'x')
                else 'text-x-generic-symbolic')
        self.run_job(title, work, done, pausable=True, icon=icon)

    def report(self, res, title=None):
        if res is None or res.cancelled:
            return False
        if res.rc == 0:
            return True
        text = res.text(200) or _('Unknown error')
        text_dialog(self, title or '7-Zip', (_('Warning') + ':\n' if res.rc == 1 else '') + text)
        return res.rc == 1

    def batch(self, title, archives, runner, on_complete, password=None):
        """Запускает runner(arc, pw, job) для каждого архива; повторяет с паролем при необходимости."""
        def work(job):
            out = []
            for arc in archives:
                if job.cancelled:
                    break
                job.text = os.path.basename(arc)
                job.fraction = None
                pw = password or self.passwords.get(arc)
                out.append((arc, runner(arc, pw, job), pw))
            return out

        def done(results, err, job):
            if err is not None:
                alert(self, str(err))
                return
            for arc, r, pw in results:
                if r.ok and pw:
                    self.passwords[arc] = pw
            retry = [a for a, r, pw in results if needs_password(r)]
            if retry:
                def got(p):
                    good = [(a, r) for a, r, pw in results if a not in retry]
                    if p is None:
                        on_complete(good + [(a, r) for a, r, pw in results if a in retry])
                    else:
                        self.batch(title, retry, runner, lambda rs: on_complete(good + rs), p)
                self.ask_password(retry[0], got)
                return
            on_complete([(a, r) for a, r, pw in results])
        self.run_job(title, work, done)

    def ask_conflict(self, msg, cb, no_skip=False):
        if no_skip:
            def got(i):
                if i == 1:
                    cb('rename')
                elif i == 2:
                    cb('overwrite')
            choose(self, msg, [_('Cancel'), _('Auto rename'), _('Overwrite')],
                   got, default=2, cancel=0)
            return

        def got(i):
            if i == 1:
                cb('skip')
            elif i == 2:
                cb('rename')
            elif i == 3:
                cb('overwrite')
        choose(self, msg, [_('Cancel'), _('Skip existing'), _('Auto rename'), _('Overwrite')],
               got, default=3, cancel=0)

    # ───────────── открытие файлов ─────────────
    def _prepare_open(self, path):
        """Для admin:// копирует во временный файл; возвращает локальный путь."""
        if not vfs.is_uri(path):
            return path
        try:
            tmp, local = vfs.copy_to_temp(path)
        except Exception as e:
            alert(self, _('Cannot open file'), str(e))
            return None
        self.temp_dirs.append(tmp)
        self._watch_admin(local, path)
        return local

    def open_external(self, path, cmd=''):
        local = self._prepare_open(path)
        if local is None:
            return
        if cmd:
            try:
                subprocess.Popen(shlex.split(cmd) + [local], start_new_session=True)
                return
            except (OSError, ValueError) as e:
                alert(self, _('Cannot start the program'), str(e))
                return
        self.launch_default(local)

    def _content_type(self, gfile):
        try:
            info = gfile.query_info('standard::content-type',
                                    Gio.FileQueryInfoFlags.NONE, None)
            return info.get_content_type()
        except GLib.Error:
            return None

    def launch_default(self, path):
        gfile = Gio.File.new_for_path(path)
        ctype = self._content_type(gfile)
        app = None
        if ctype:
            try:
                app = Gio.AppInfo.get_default_for_type(ctype, False)
            except GLib.Error:
                app = None
        if app is not None:
            try:
                app.launch([gfile], None)
                return
            except GLib.Error:
                pass
        self.open_with(path)

    def open_with(self, path):
        local = self._prepare_open(path)
        if local is not None:
            OpenWithDialog(self, local).present()

    def run_executable(self, path):
        local = self._prepare_open(path)
        if local is None:
            return
        try:
            subprocess.Popen([local], cwd=os.path.dirname(local), start_new_session=True)
        except (OSError, ValueError) as e:
            alert(self, _('Cannot start the program'), str(e))

    def _watch_admin(self, local, remote):
        st = {'m': os.path.getmtime(local), 'busy': False}

        def poll():
            if self.closing or not os.path.exists(local):
                return False
            try:
                m = os.path.getmtime(local)
            except OSError:
                return False
            if m != st['m'] and not st['busy']:
                st['busy'] = True

                def save():
                    try:
                        vfs.copy_from_temp(local, remote)
                    except Exception as e:
                        alert(self, _('Error'), str(e))
                    else:
                        st['m'] = os.path.getmtime(local)
                        self.reload_all()
                    st['busy'] = False

                def skip():
                    st['m'] = m
                    st['busy'] = False

                def got(i):
                    (save if i == 1 else skip)()
                choose(self, _('File "{0}" was modified.').format(vfs.basename(remote)),
                       [_('Do not save'), _('Save to root folder')], got,
                       detail=_('Save changes back to {0}?').format(vfs.display(remote)),
                       default=1, cancel=0)
            return True
        GLib.timeout_add_seconds(2, poll)

    def open_nested(self, panel, item):
        a = panel.arc
        tmp = tempfile.mkdtemp(prefix='7zgtk-')
        self.temp_dirs.append(tmp)

        def done(res):
            target = os.path.join(tmp, item.full)
            if res.cancelled or not os.path.exists(target):
                self.report(res)
                shutil.rmtree(tmp, ignore_errors=True)
                return
            panel.open_archive(target, push=False, parent_state=a, tmp=tmp)
        self.run7(_('Extracting'), 'x', ['-y', '-o' + tmp, '-aoa'], [a.path, item.full], done, archive=a.path)

    def open_from_archive(self, panel, item, edit=True):
        a = panel.arc
        tmp = tempfile.mkdtemp(prefix='7zgtk-')
        self.temp_dirs.append(tmp)

        def done(res):
            target = os.path.join(tmp, item.full)
            if not os.path.exists(target):
                self.report(res)
                return
            self.open_external(target, self.conf['editor'] if edit else self.conf['viewer'])
            if edit and a.parent is None:
                self.watch(target, a, item.full, tmp)
        self.run7(_('Extracting'), 'x', ['-y', '-o' + tmp, '-aoa'], [a.path, item.full], done, archive=a.path)

    def _sync_archive(self, a):
        if not vfs.is_uri(getattr(a, 'source', '')):
            return
        try:
            vfs.copy(a.path, a.source)
        except Exception as e:
            alert(self, _('Error'), str(e))

    def watch(self, target, arc, inner, tmp):
        st = {'m': os.path.getmtime(target), 'busy': False}

        def poll():
            if self.closing or not os.path.exists(target):
                return False
            try:
                m = os.path.getmtime(target)
            except OSError:
                return False
            if m != st['m'] and not st['busy']:
                st['busy'], st['m'] = True, m

                def upd():
                    sw = ['-y'] + (['-l'] if self.sz.is_p7zip else [])

                    def fin(res):
                        st['busy'] = False
                        if self.report(res, _('Update')):
                            self._sync_archive(arc)
                            self.reload_all()
                    self.run7(_('Updating'), 'a', sw, [arc.path, inner], fin, cwd=tmp, archive=arc.path)

                def no():
                    st['busy'] = False
                choose(self, _('File "{0}" was modified.').format(os.path.basename(inner)),
                       [_('No'), _('Update archive')], lambda i: upd() if i == 1 else no(),
                       detail=_('Do you want to update it in the archive?'), default=1, cancel=0)
            return True
        GLib.timeout_add_seconds(2, poll)

    def drag_paths(self, panel, items):
        if panel.mode == 'fs':
            return [i.full for i in items]
        a = panel.arc
        if sum(i.size for i in items if i.size > 0) > 512 * 1024 * 1024:
            return None
        tmp = tempfile.mkdtemp(prefix='7zgtk-')
        self.temp_dirs.append(tmp)
        res = self.sz.run('x', ['-y', '-o' + tmp, '-aoa'], [a.path] + names_for(items), password=a.password)
        if res.rc not in (0, 1):
            return None
        return [os.path.join(tmp, i.full) for i in items if os.path.exists(os.path.join(tmp, i.full))]

    def drop_files(self, panel, paths, move=False):
        self.set_active(panel)
        if panel.mode == 'arc':
            self.add_into_archive(panel, paths)
            return
        if all(os.path.dirname(p.rstrip('/')) == panel.path for p in paths):
            return
        self.fs_transfer(paths, panel.path, move)

    # ───────────── операции: открыть / просмотр ─────────────
    def op_open_archive_dialog(self, *a):
        pick(self, 'open', _('Open archive'), lambda p: self.active.open_archive(p[0]),
             initial=self.active.current_dir())

    def op_open_sel(self, *a):
        sel = self.active.selected()
        if sel:
            self.active.activate_item(sel[0])

    def op_open_with(self, *a):
        sel = [i for i in self.active.selected() if not i.is_dir]
        if sel:
            self.open_with(sel[0].full)

    def op_run(self, *a):
        sel = [i for i in self.active.selected() if not i.is_dir]
        if sel:
            self.run_executable(sel[0].full)

    def op_open_inside(self, *a):
        p = self.active
        sel = p.selected()
        if not sel:
            return
        if p.mode == 'fs' and not sel[0].is_dir:
            p.open_archive(sel[0].full)
        elif p.mode == 'arc' and not sel[0].is_dir:
            self.open_nested(p, sel[0])
        else:
            p.activate_item(sel[0])

    def op_open_outside(self, *a):
        p = self.active
        sel = p.selected()
        if not sel:
            return
        if p.mode == 'fs':
            self.open_external(sel[0].full)
        elif not sel[0].is_dir:
            self.open_from_archive(p, sel[0], edit=False)

    def op_view(self, *a):
        p = self.active
        sel = [i for i in p.selected() if not i.is_dir]
        if not sel:
            return
        if p.mode == 'fs':
            self.open_external(sel[0].full, self.conf['viewer'])
        else:
            self.open_from_archive(p, sel[0], edit=False)

    def op_edit(self, *a):
        p = self.active
        sel = [i for i in p.selected() if not i.is_dir]
        if not sel:
            return
        if p.mode == 'fs':
            self.open_external(sel[0].full, self.conf['editor'])
        else:
            self.open_from_archive(p, sel[0], edit=True)

    # ───────────── добавление в архив ─────────────
    def op_add(self, *a, fmt=None):
        p = self.active
        if p.mode == 'arc':
            pick(self, 'multi', _('Add files'), lambda paths: self.add_into_archive(p, paths))
            return
        sel = p.selected()
        if not sel:
            alert(self, _('Select files and folders to add first'))
            return
        paths = [i.full for i in sel]
        stem = default_stem(paths)
        f0 = fmt or (self.conf['add_format'] if self.conf['add_format'] in FORMATS else '7z')
        name = vfs.join(p.path, stem + '.' + FMT[f0]['ext'])
        if fmt:
            self.start_add(paths, default_add_opts(fmt, name))
        else:
            AddDialog(self, name, lambda o: self.start_add(paths, o), f0, self.conf['add_level']).present()

    def start_add(self, paths, opts, subdir=''):
        archive = opts['archive']
        dest_admin = vfs.is_uri(archive)
        tmp_arc = src_tmp = None
        local_archive = archive
        if dest_admin:
            tmp_arc = tempfile.mkdtemp(prefix='7zgtk-arc-')
            local_archive = os.path.join(tmp_arc, vfs.basename(archive.rstrip('/')) or 'archive.7z')
            if vfs.exists(archive):
                vfs.copy(archive, local_archive)
        else:
            archive = os.path.abspath(os.path.expanduser(archive))
            local_archive = archive
        if any(vfs.is_uri(x) for x in paths):
            src_tmp = tempfile.mkdtemp(prefix='7zgtk-src-')
            staged = []
            for x in paths:
                dst = os.path.join(src_tmp, vfs.basename(x.rstrip('/')))
                vfs.copy(x, dst)
                staged.append(dst)
            paths = staged
        opts['archive'] = archive
        exists = os.path.exists(local_archive)
        if local_archive in self._active_archives:
            alert(self, _('This archive is already being written to'))
            return
        self.conf['add_format'], self.conf['add_level'] = opts['fmt'], opts['level']
        if not opts.get('threads'):
            limit = add_thread_limit(opts.get('level'), opts.get('fmt'))
            if limit:
                opts = dict(opts, threads=str(limit))
        sw = build_add_switches(opts, exists, self.sz.is_p7zip) + ['-y']
        names, cwd, tmp = prepare_add(paths, subdir, opts['pathmode'])
        cmd = 'a' if opts['update'] == 'add' else 'u'
        diagnostics.log('добавление: архив=%s, элементов=%d, режим=%s, ключи=%s',
                        local_archive, len(names), cmd, ' '.join(sw))

        def done(res):
            self._active_archives.discard(local_archive)
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
            if src_tmp:
                shutil.rmtree(src_tmp, ignore_errors=True)
            if dest_admin and res is not None and res.rc in (0, 1) and not res.cancelled:
                try:
                    vfs.copy(local_archive, archive)
                except Exception as e:
                    alert(self, _('Error'), str(e))
            if tmp_arc:
                shutil.rmtree(tmp_arc, ignore_errors=True)
            if self.report(res, _('Add to Archive')):
                self.reload_all()
        self._active_archives.add(local_archive)
        self.run7(_('Adding to archive'), cmd, sw, [local_archive] + names, done, cwd=cwd,
                  archive=local_archive if exists else None, password=opts.get('password') or None)

    def add_into_archive(self, panel, paths):
        a = panel.arc
        if a.parent is not None:
            alert(self, _('Modifying nested archives is not supported'))
            return
        src_tmp = None
        if any(vfs.is_uri(x) for x in paths):
            src_tmp = tempfile.mkdtemp(prefix='7zgtk-src-')
            staged = []
            for x in paths:
                dst = os.path.join(src_tmp, vfs.basename(x.rstrip('/')))
                vfs.copy(x, dst)
                staged.append(dst)
            paths = staged
        names, cwd, tmp = prepare_add(paths, a.sub, 'relative')
        sw = ['-y'] + (['-l'] if self.sz.is_p7zip else [])

        def done(res):
            for d in (tmp, src_tmp):
                if d:
                    shutil.rmtree(d, ignore_errors=True)
            if self.report(res, _('Add to Archive')):
                self._sync_archive(a)
                self.reload_all()
        self.run7(_('Adding to archive'), 'a', sw, [a.path] + names, done, cwd=cwd, archive=a.path)

    # ───────────── распаковка ─────────────
    def op_extract(self, *a, here=False, to_dir=False, move=False):
        p = self.active
        if p.mode == 'fs':
            archives = [i.full for i in p.selected() if not i.is_dir]
            if not archives:
                alert(self, _('Select archive file(s) first'))
                return
            base = p.path
            stem = archive_stem(vfs.basename(archives[0]))
            opts = self._default_extract_opts()
            if here:
                self.extract_start(archives, base, opts)
            elif to_dir:
                self.extract_start(archives, vfs.join(base, '*'), opts)
            else:
                dest = vfs.join(base, '*' if len(archives) > 1 else stem)
                self._extract_dialog(_('Extract'), dest,
                              lambda d, o: self.extract_start(archives, d, o)).present()
        else:
            arc = p.arc
            sel = p.selected()
            names = names_for(sel) if sel else None
            other = self.other_panel()
            dest = other.path if other is not None and other.mode == 'fs' else vfs.dirname(arc.path)
            after = (lambda: self.delete_in_archive(p, sel)) if (move and sel and arc.parent is None) else None
            title = _('Move') if move else _('Extract')
            self._extract_dialog(title, dest,
                          lambda d, o: self.extract_start([arc.path], d, o, names, arc.entries, after)).present()

    def _conflicts_for(self, arc, names, dest, pathmode):
        if vfs.is_uri(dest):
            return 0
        pw = self.passwords.get(arc)
        tmp = None
        try:
            if vfs.is_uri(arc):
                tmp, arc = vfs.copy_to_temp(arc)
            if TAR_COMPOUND.search(arc):
                if os.path.getsize(arc) > 256 * 1024 * 1024:
                    return 0
                entries = self.sz.list_tar_compound(arc, pw)[1]
            else:
                entries = self.sz.list_archive(arc, pw)[2]
        except (OSError, GLib.Error):
            return 0
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)
        return count_conflicts(entries, names, dest, pathmode)

    def _default_extract_opts(self):
        return dict(pathmode=self.conf['extract_pathmode'], overwrite=self.conf['extract_overwrite'],
                    nodup=False, password='')

    def _extract_dialog(self, title, dest, on_ok):
        return ExtractDialog(self, title, dest, on_ok, pathmode=self.conf['extract_pathmode'],
                             overwrite=self.conf['extract_overwrite'])

    def extract_start(self, archives, dest_tpl, opts, names=None, entries=None, after=None):
        def dest_for(arc):
            if vfs.is_admin(dest_tpl):
                raw = dest_tpl.rstrip('/')
                d = (vfs.ADMIN + '/') if raw == vfs.ADMIN.rstrip('/') else raw
            else:
                d = dest_tpl.rstrip('/') or '/'
            if vfs.basename(d) == '*':
                d = vfs.join(vfs.dirname(d) or '/', archive_stem(vfs.basename(arc)))
            return d

        def run(o):
            self._extract_run(archives, dest_for, o, names, after)

        if opts['overwrite'] != 'ask':
            run(opts)
            return

        def proceed(n):
            if n:
                self.ask_conflict(_('{0} file(s) already exist in the destination folder.').format(n),
                                  lambda m: run(dict(opts, overwrite=m)),
                                  no_skip=bool(opts.get('no_skip')))
            else:
                run(dict(opts, overwrite='overwrite'))
        if entries is not None:
            dest0 = dest_for(archives[0])
            proceed(0 if vfs.is_uri(dest0) else
                    count_conflicts(entries, names, dest0, opts['pathmode']))
            return

        def work():
            n = sum(self._conflicts_for(x, names, dest_for(x), opts['pathmode']) for x in archives)
            GLib.idle_add(lambda: proceed(n) and False)
        threading.Thread(target=work, daemon=True).start()

    def _copy_extracted(self, src, dest, opts):
        if not vfs.exists(dest):
            vfs.mkdirs(dest)
        for e in os.scandir(src):
            target = vfs.join(dest, e.name)
            if vfs.exists(target):
                mode = opts.get('overwrite')
                if mode == 'skip':
                    continue
                if mode == 'rename':
                    target = vfs.unique(target)
            vfs.copy(e.path, target)

    def _extract_run(self, archives, dest_for, opts, names, after):
        def runner(arc, pw, job):
            dest = dest_for(arc)
            tmp_arc = tmp_out = None
            try:
                local = arc
                if vfs.is_uri(arc):
                    tmp_arc, local = vfs.copy_to_temp(arc)
                if vfs.is_uri(dest):
                    tmp_out = tempfile.mkdtemp(prefix='7zgtk-out-')
                    cmd, sw = extract_switches(opts, tmp_out)
                    if names is None and TAR_COMPOUND.search(local) and cmd == 'x':
                        res = self.sz.extract_tar_compound(local, tmp_out,
                                                           [x for x in sw if x.startswith('-ao')], job, pw)
                    else:
                        res = self.sz.run(cmd, sw, [local] + (names or []), job=job, password=pw)
                    if res.rc in (0, 1) and not res.cancelled:
                        self._copy_extracted(tmp_out, dest, opts)
                    return res
                cmd, sw = extract_switches(opts, dest)
                if names is None and TAR_COMPOUND.search(local) and cmd == 'x':
                    return self.sz.extract_tar_compound(local, dest,
                                                        [x for x in sw if x.startswith('-ao')], job, pw)
                return self.sz.run(cmd, sw, [local] + (names or []), job=job, password=pw)
            finally:
                if tmp_out:
                    shutil.rmtree(tmp_out, ignore_errors=True)
                if tmp_arc:
                    shutil.rmtree(tmp_arc, ignore_errors=True)

        def complete(results):
            bad = [r for a, r in results if r.rc not in (0, 1) and not r.cancelled]
            warn = [r for a, r in results if r.rc == 1]
            if bad:
                self.report(bad[0], _('Extract'))
            elif warn:
                self.report(warn[0], _('Extract'))
            if not bad and results and not any(r.cancelled for a, r in results):
                if after:
                    after()
            self.reload_all()
        self.batch(_('Extracting'), archives, runner, complete, password=opts.get('password') or None)

    def op_test(self, *a):
        p = self.active
        archives = [p.arc.path] if p.mode == 'arc' else [i.full for i in p.selected() if not i.is_dir]
        if not archives:
            alert(self, _('Select archive file(s) first'))
            return

        def runner(arc, pw, job):
            tmp, local = None, arc
            if vfs.is_uri(arc):
                tmp, local = vfs.copy_to_temp(arc)
            try:
                return self.sz.run('t', ['-y'], [local], job=job, password=pw)
            finally:
                if tmp:
                    shutil.rmtree(tmp, ignore_errors=True)

        def complete(results):
            bad = [(a, r) for a, r in results if not r.ok and not r.cancelled]
            if not results or any(r.cancelled for a, r in results):
                return
            if not bad:
                alert(self, _('There are no errors'),
                      '\n'.join(os.path.basename(a) for a, r in results))
            else:
                text_dialog(self, _('Test'), '\n\n'.join('%s\n%s' % (a, r.text(100)) for a, r in bad))
        self.batch(_('Testing'), archives, runner, complete)

    # ───────────── правка внутри архива / ФС ─────────────
    def delete_in_archive(self, panel, items):
        a = panel.arc
        if a.parent is not None:
            alert(self, _('Modifying nested archives is not supported'))
            return

        def done(res):
            if self.report(res, _('Delete')):
                self._sync_archive(a)
                self.reload_all()
        self.run7(_('Deleting'), 'd', ['-y'], [a.path] + names_for(items), done, archive=a.path)

    def op_delete(self, *a, permanent=False):
        p = self.active
        sel = p.selected()
        if not sel:
            return
        if p.mode == 'arc':
            confirm(self, _('Are you sure you want to delete {0} item(s) from the archive?').format(len(sel)),
                    None, _('Delete'), lambda: self.delete_in_archive(p, sel))
            return
        paths = [i.full for i in sel]
        perm = permanent or not self.conf['use_trash'] or any(vfs.is_uri(x) for x in paths)
        msg = (_('Are you sure you want to permanently delete {0} item(s)?') if perm else
               _('Are you sure you want to move {0} item(s) to the Trash?')).format(len(paths))

        def go():
            trashed = []

            def work(job):
                errs = []
                for i, pth in enumerate(paths):
                    if job.cancelled:
                        break
                    job.text, job.fraction = vfs.basename(pth), i / len(paths)
                    try:
                        if perm:
                            vfs.remove(pth)
                        else:
                            dst = vfs.trash_with_path(pth)
                            if dst:
                                trashed.append((dst, pth))
                    except (OSError, GLib.Error) as e:
                        errs.append('%s: %s' % (pth, getattr(e, 'message', e)))
                return errs

            def done(errs, err, job):
                errs = [str(err)] if err else errs
                if errs:
                    text_dialog(self, _('Error'), '\n'.join(errs))
                if trashed:
                    self._push_undo({'kind': 'trash', 'pairs': list(trashed)})
                self.reload_all()
            self.run_job(_('Deleting'), work, done)
        if self.conf['confirm_delete'] or permanent:
            confirm(self, msg, None, _('Delete'), go)
        else:
            go()

    def op_rename(self, *a):
        self.active.start_rename()

    def _do_rename(self, p, it, new):
        new = (new or '').strip()
        if not new or new == it.name:
            return
        if new in ('.', '..') or '/' in new:
            alert(self, _('Invalid name'))
            return
        if p.mode == 'fs':
            try:
                newpath = vfs.rename(it.full, new)
            except (OSError, GLib.Error) as e:
                alert(self, _('Error'), getattr(e, 'message', e))
                return
            p.reload([new])
            self._push_undo({'kind': 'rename', 'old': it.full, 'new': newpath})
            return
        a = p.arc
        if a.parent is not None:
            alert(self, _('Modifying nested archives is not supported'))
            return
        parent = it.full.rpartition('/')[0]
        newfull = (parent + '/' if parent else '') + new
        pairs = []
        for e in a.entries:
            if e.path == it.full or e.path.startswith(it.full + '/'):
                pairs += [e.path, newfull + e.path[len(it.full):]]
        if not pairs:
            return

        def done(res):
            if self.report(res, _('Rename')):
                self._sync_archive(a)
                p.reload([new])
        self.run7(_('Renaming'), 'rn', ['-y'], [a.path] + pairs, done, archive=a.path)

    def op_new_folder(self, *a):
        self._new_item(folder=True)

    def op_new_file(self, *a):
        self._new_item(folder=False)

    def op_new_window(self, *a):
        app = self.get_application()
        if app is not None:
            app.new_window()

    def op_quit(self, *a):
        app = self.get_application()
        wins = list(getattr(app, 'wins', [])) if app is not None else []
        if not wins:
            self.close()
            return
        for win in wins:
            win.close()

    def _new_item(self, folder):
        p = self.active
        title = _('Create folder') if folder else _('Create file')
        label = _('Folder name:') if folder else _('File name:')
        default = _('New folder') if folder else _('New file')

        def make(name):
            if '/' in name:
                alert(self, _('Invalid name'))
                return
            if p.mode == 'fs':
                path = vfs.join(p.path, name)
                try:
                    ok = vfs.mkdir(path) if folder else vfs.touch(path)
                    if not ok:
                        raise OSError(_('Already exists'))
                except (OSError, GLib.Error) as e:
                    alert(self, _('Error'), getattr(e, 'message', e))
                    return
                p.reload([name])
                self._push_undo({'kind': 'new', 'path': path, 'folder': folder})
                return
            a = p.arc
            if a.parent is not None:
                alert(self, _('Modifying nested archives is not supported'))
                return
            tmp = tempfile.mkdtemp(prefix='7zgtk-add-')
            base = os.path.join(tmp, a.sub) if a.sub else tmp
            os.makedirs(base, exist_ok=True)
            if folder:
                os.makedirs(os.path.join(base, name))
            else:
                open(os.path.join(base, name), 'w').close()
            top = a.sub.split('/')[0] if a.sub else name

            def done(res):
                shutil.rmtree(tmp, ignore_errors=True)
                if self.report(res, title):
                    self._sync_archive(a)
                    p.reload([name])
            self.run7(title, 'a', ['-y'], [a.path, top], done, cwd=tmp, archive=a.path)
        PromptDialog(self, title, label, default, _('OK'), make).present()

    # ───────────── отмена и повтор операций ─────────────
    def _update_undo_actions(self):
        for name, stack in (('undo', self.undo_stack), ('redo', self.redo_stack)):
            action = self.lookup_action(name)
            if action is not None:
                action.set_enabled(bool(stack))

    def _push_undo(self, rec):
        if not rec:
            return
        self.undo_stack.append(rec)
        if len(self.undo_stack) > 100:
            del self.undo_stack[0]
        self.redo_stack.clear()
        self._update_undo_actions()

    def op_undo(self, *a):
        if self._history_busy or not self.undo_stack:
            return
        self._run_history(self.undo_stack[-1], True)

    def op_redo(self, *a):
        if self._history_busy or not self.redo_stack:
            return
        self._run_history(self.redo_stack[-1], False)

    def _run_history(self, rec, undo):
        if self._history_busy:
            return
        stack = self.undo_stack if undo else self.redo_stack
        if not any(x is rec for x in stack):
            return
        self._history_busy = True
        title = _('Undo') if undo else _('Redo')
        new_pairs = []

        def work(job):
            errs = []
            self._apply_history(rec, undo, job, errs, new_pairs)
            return errs

        def done(errs, err, job):
            self._history_busy = False
            errs = [str(err)] if err else (errs or [])
            cancelled = bool(job and job.cancelled)
            if not errs and not cancelled:
                for i, x in enumerate(stack):
                    if x is rec:
                        del stack[i]
                        break
                (self.redo_stack if undo else self.undo_stack).append(rec)
                if new_pairs:
                    rec['pairs'] = new_pairs
            elif errs:
                text_dialog(self, _('Error'), '\n'.join(errs))
            self._update_undo_actions()
            self.reload_all()

        self.run_job(title, work, done)

    def _apply_history(self, rec, undo, job, errs, new_pairs):
        kind = rec.get('kind')

        def fail(path, exc):
            errs.append('%s: %s' % (vfs.display(path), getattr(exc, 'message', exc)))

        if kind == 'rename':
            old, new = rec['old'], rec['new']
            src, dst = (new, old) if undo else (old, new)
            try:
                if not vfs.exists(src):
                    raise OSError(_('File not found'))
                if vfs.exists(dst):
                    raise OSError(_('Destination already exists'))
                vfs.move(src, dst)
            except (OSError, GLib.Error, shutil.Error) as e:
                fail(src, e)
            return

        if kind == 'new':
            path = rec['path']
            try:
                if undo:
                    if not vfs.exists(path):
                        return
                    if rec.get('folder') and vfs.is_dir(path) and vfs.listdir(path):
                        raise OSError(_('Folder is not empty'))
                    vfs.remove(path)
                else:
                    if vfs.exists(path):
                        raise OSError(_('Already exists'))
                    ok = vfs.mkdir(path) if rec.get('folder') else vfs.touch(path)
                    if not ok:
                        raise OSError(_('Cannot create'))
            except (OSError, GLib.Error) as e:
                fail(path, e)
            return

        if kind in ('copy', 'move'):
            pairs = list(rec.get('pairs') or [])
            if undo and kind == 'copy':
                for i, (_src, dst) in enumerate(pairs):
                    if job.cancelled:
                        break
                    job.text, job.fraction = vfs.basename(dst), i / max(1, len(pairs))
                    try:
                        if vfs.exists(dst):
                            vfs.remove(dst)
                    except (OSError, GLib.Error, shutil.Error) as e:
                        fail(dst, e)
                return
            if undo and kind == 'move':
                pairs = list(reversed(pairs))
            for i, (src, dst) in enumerate(pairs):
                if job.cancelled:
                    break
                a, b = (dst, src) if undo else (src, dst)
                job.text, job.fraction = vfs.basename(a), i / max(1, len(pairs))
                try:
                    if not vfs.exists(a):
                        raise OSError(_('File not found'))
                    if vfs.exists(b):
                        raise OSError(_('Destination already exists'))
                    if undo:
                        vfs.move(a, b)
                    elif kind == 'copy':
                        vfs.copy(a, b)
                    else:
                        vfs.move(a, b)
                except (OSError, GLib.Error, shutil.Error) as e:
                    fail(a, e)
            return

        if kind == 'trash':
            pairs = list(reversed(rec.get('pairs') or [])) if undo else list(rec.get('pairs') or [])
            for i, (trashed, original) in enumerate(pairs):
                if job.cancelled:
                    break
                job.text, job.fraction = vfs.basename(original), i / max(1, len(pairs))
                try:
                    if undo:
                        if not vfs.exists(trashed):
                            raise OSError(_('File not found'))
                        if vfs.exists(original):
                            raise OSError(_('Destination already exists'))
                        vfs.move(trashed, original)
                    else:
                        if not vfs.exists(original):
                            raise OSError(_('File not found'))
                        new = vfs.trash_with_path(original)
                        if not new:
                            raise OSError(_('Cannot move to Trash'))
                        new_pairs.append((new, original))
                except (OSError, GLib.Error) as e:
                    fail(original, e)
            return

        errs.append(_('Cannot undo') if undo else _('Cannot redo'))

    # ───────────── буфер обмена ─────────────
    def _on_destroy_clipboard(self, *_a):
        try:
            self._clipboard.disconnect(self._clip_sig)
        except Exception:
            pass

    def _on_clipboard_changed(self, clip):
        if self._clipboard_own:
            return
        data = self.clipboard_data
        if data is None:
            return
        # На Wayland сигнал 'changed' приходит асинхронно — иногда уже после
        # того, как мы сняли _clipboard_own в idle. Содержимое при этом всё ещё
        # наше, и состояние «вырезано» терять нельзя.
        try:
            if clip.is_local():
                return
        except Exception:
            pass
        self._verify_clipboard(data)

    def _verify_clipboard(self, data):
        """Отменить наше состояние, только если в буфере чужие файлы.

        Пустой буфер или текст (например, после нашего же очищения либо работы
        менеджера буфера обмена) состояние «вырезано» не сбрасывают.
        """
        serial = self._clip_serial

        def files_done(c, res, _u=None):
            if serial != self._clip_serial or self.clipboard_data is not data:
                return
            paths = []
            try:
                fl = c.read_value_finish(res)
                if hasattr(fl, 'get_boxed'):
                    fl = fl.get_boxed()
                paths = [f.get_path() for f in fl.get_files() if f.get_path()]
            except Exception:
                paths = []
            if not paths:
                return
            if (data.get('kind') == 'fs' and
                    set(paths) == set(data.get('paths') or ())):
                return                          # тот же набор файлов — это мы
            diagnostics.log('буфер обмена заменён другим приложением — сбрасываю '
                            'состояние «вырезано»')
            self.clipboard_data = None
            self.refresh_cut_marks()

        try:
            self.get_clipboard().read_value_async(
                Gdk.FileList, GLib.PRIORITY_DEFAULT, None, files_done, None)
        except Exception:
            pass

    def _own_clipboard(self):
        self._clipboard_own = True
        GLib.idle_add(self._release_clipboard)

    def _release_clipboard(self):
        self._clipboard_own = False
        return False

    def _set_file_clipboard(self, paths):
        try:
            files = [Gio.File.new_for_uri(p) if vfs.is_uri(p) else Gio.File.new_for_path(p)
                     for p in paths]
            fl = Gdk.FileList.new_from_list(files)
            v = GObject.Value()
            v.init(Gdk.FileList)
            v.set_boxed(fl)
            self._own_clipboard()
            self.get_clipboard().set_content(Gdk.ContentProvider.new_for_value(v))
        except Exception:
            pass

    def _clear_system_clipboard(self):
        try:
            self._own_clipboard()
            self.get_clipboard().set_content(None)
        except Exception:
            pass

    def _clear_clipboard(self, data=None):
        if data is not None and self.clipboard_data is not data:
            return
        self._clip_serial += 1
        self.clipboard_data = None
        self.refresh_cut_marks()
        self._clear_system_clipboard()

    def is_cut_path(self, path):
        d = self.clipboard_data
        return bool(d and d.get('cut') and d.get('kind') == 'fs' and
                    path in (d.get('paths') or ()))

    def refresh_cut_marks(self):
        """Перерисовать панели всех окон: вырезанные элементы приглушаются."""
        app = self.get_application()
        wins = list(getattr(app, 'wins', []) or []) if app is not None else [self]
        if self not in wins:
            wins.append(self)
        for w in wins:
            for p in (getattr(w, 'p1', None), getattr(w, 'p2', None)):
                if p is not None:
                    try:
                        p.refresh_cut()
                    except Exception:
                        pass

    def op_copy_selection(self, *a, cut=False):
        p = self.active
        sel = p.selected()
        if not sel:
            diagnostics.log('буфер: %s — ничего не выделено',
                            'вырезать' if cut else 'копировать')
            return
        self._clip_serial += 1
        if p.mode == 'arc':
            a = p.arc
            if cut and a.parent is not None:
                alert(self, _('Cut from nested archives is not supported'))
                return
            self._clear_system_clipboard()
            self.clipboard_data = {
                'kind': 'arc', 'arc': a, 'names': names_for(sel),
                'items': sel, 'cut': cut,
            }
        else:
            paths = [i.full for i in sel]
            self.clipboard_data = {'kind': 'fs', 'paths': paths, 'cut': cut}
            self._set_file_clipboard(paths)
        self.refresh_cut_marks()
        diagnostics.log('буфер: %s %d элемент(ов), панель=%s',
                        'вырезано' if cut else 'скопировано', len(sel), p.path)
        text = _('Cut: {0}') if cut else _('Copied: {0}')
        self.set_status_message(p, text.format(len(sel)))

    def op_paste(self, *a):
        p = self.active
        data = self.clipboard_data
        if data is not None:
            diagnostics.log('вставка: внутренний буфер (%s), в %s',
                            'вырезано' if data.get('cut') else 'копия', p.path)
            self._paste_clipboard(p, data)
        else:
            diagnostics.log('вставка: внутреннего буфера нет — читаю системный, в %s',
                            p.path)
            self._paste_external(p)

    def _paste_clipboard(self, p, data):
        if data['kind'] == 'fs':
            paths = [x for x in data['paths'] if vfs.exists(x)]
            if not paths:
                self._clear_clipboard(data)
                alert(self, _('Clipboard is empty'))
                return
            self._paste_fs_paths(p, paths, bool(data.get('cut')), data)
        else:
            self._paste_archive(p, data)

    def _paste_fs_paths(self, p, paths, move, data=None):
        if p.mode == 'arc':
            if move:
                alert(self, _('Use Copy to add files to an archive'))
                return
            self.add_into_archive(p, paths)
            return

        def done(errs, cancelled):
            if data is not None and move and not errs and not cancelled:
                self._clear_clipboard(data)
        diagnostics.log('перенос: %s %d элемент(ов) в %s',
                        'перемещение' if move else 'копирование', len(paths), p.path)
        self.fs_transfer(paths, p.path, move, on_done=done)

    def _paste_archive(self, p, data):
        if p.mode == 'arc':
            alert(self, _('Pasting into archives is not supported'))
            return
        arc = data['arc']
        if not vfs.exists(arc.path):
            self._clear_clipboard(data)
            alert(self, _('Archive is no longer available'))
            return

        opts = self._default_extract_opts()
        after = None
        if data.get('cut'):
            if opts['overwrite'] == 'skip':
                opts['overwrite'] = 'rename'
            opts['no_skip'] = True

            def after():
                self._delete_archive_entries(
                    arc, data['items'], lambda: self._clear_clipboard(data))
        self.extract_start([arc.path], p.path, opts,
                           data['names'], arc.entries, after)

    def _delete_archive_entries(self, arc, items, on_done=None):
        if arc.parent is not None:
            alert(self, _('Modifying nested archives is not supported'))
            return

        def done(res):
            if self.report(res, _('Delete')):
                self._sync_archive(arc)
                self.reload_all()
                if on_done is not None:
                    on_done()
        self.run7(_('Deleting'), 'd', ['-y'], [arc.path] + names_for(items),
                  done, archive=arc.path)

    def _paste_external(self, p):
        def done(c, res, _data=None):
            paths = []
            try:
                fl = c.read_value_finish(res)
                if hasattr(fl, 'get_boxed'):
                    fl = fl.get_boxed()
                paths = [f.get_path() for f in fl.get_files() if f.get_path()]
            except Exception:
                paths = []
            if paths:
                diagnostics.log('системный буфер: %d файл(ов) — вставляю как копию',
                                len(paths))
                self._paste_fs_paths(p, paths, False)
            else:
                self._paste_external_text(p)
        try:
            self.get_clipboard().read_value_async(
                Gdk.FileList, GLib.PRIORITY_DEFAULT, None, done, None)
        except Exception:
            pass

    def _paste_external_text(self, p):
        def done(c, res, _data=None):
            try:
                text = c.read_text_finish(res) or ''
            except Exception:
                return
            paths = []
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    if line.startswith('file://'):
                        path = Gio.File.new_for_uri(line).get_path()
                    elif line.startswith('/') or line.startswith('~'):
                        path = os.path.abspath(os.path.expanduser(line))
                    else:
                        continue
                except Exception:
                    continue
                if path and vfs.exists(path):
                    paths.append(path)
            if paths:
                self._paste_fs_paths(p, paths, False)
        try:
            self.get_clipboard().read_text_async(None, done, None)
        except Exception:
            pass

    def op_copy(self, *a, move=False):
        p = self.active
        sel = p.selected()
        if not sel:
            return
        other = self.other_panel()
        if p.mode == 'arc':
            self.op_extract(move=move)
            return
        paths = [i.full for i in sel]
        if other is not None and other.mode == 'arc':
            if move:
                alert(self, _('Use Copy to add files to an archive'))
                return
            self.add_into_archive(other, paths)
            return
        default = other.path if other is not None else p.path
        PromptDialog(self, _('Move') if move else _('Copy'),
                     _('Move to:') if move else _('Copy to:'), default, _('OK'),
                     lambda d: self.fs_transfer(paths, d if vfs.is_uri(d) else os.path.expanduser(d), move),
                     folder_browse=True).present()

    def op_move(self, *a):
        self.op_copy(move=True)

    @staticmethod
    def _drop_partial(target, created):
        """Убрать недокопированный объект, если он создан этим заданием."""
        if not created:
            return
        try:
            vfs.remove(target)
        except (OSError, GLib.Error):
            pass

    def fs_transfer(self, paths, dest, move, on_done=None, record=True):
        if not vfs.is_uri(dest):
            dest = os.path.abspath(os.path.expanduser(dest))
        try:
            if vfs.is_uri(dest):
                if not vfs.mkdirs(dest):
                    raise OSError(_('Cannot create folder'))
            else:
                os.makedirs(dest, exist_ok=True)
        except (OSError, GLib.Error) as e:
            alert(self, _('Error'), str(e))
            return
        clash = [x for x in paths if vfs.exists(vfs.join(dest, vfs.basename(x.rstrip('/'))))]

        def go(mode):
            pairs = []

            def work(job):
                errs = []
                job.files_label = (_('Files moved: {0} of {1}') if move
                                   else _('Files copied: {0} of {1}'))
                job.text = _('Calculating size…')
                job.fraction = None
                total = files_total = 0
                if not move:
                    for src in paths:
                        if job.cancelled:
                            return errs
                        job.wait_if_paused()
                        b, f = vfs.measure(src)
                        total += b
                        files_total += f
                    job.bytes_total = total
                    job.files_total = files_total
                done = files_done = 0
                for i, src in enumerate(paths):
                    if job.cancelled:
                        break
                    job.wait_if_paused()
                    if job.cancelled:
                        break
                    name = vfs.basename(src.rstrip('/'))
                    job.text = name
                    job.icon = ('folder-symbolic' if vfs.is_dir(src) and not vfs.is_link(src)
                                else 'text-x-generic-symbolic')
                    if not total:
                        job.fraction = i / len(paths)
                    target = vfs.join(dest, vfs.basename(src.rstrip('/')))
                    same = vfs.uri(src) == vfs.uri(target)
                    try:
                        created = not vfs.exists(target)
                        if vfs.exists(target):
                            if mode == 'skip':
                                continue
                            if mode == 'rename' or same:
                                target = vfs.unique(target)
                                created = True
                        isdir = vfs.is_dir(src) and not vfs.is_link(src)
                        if move:
                            cross = not vfs.same_device(src, target)
                            if cross or (isdir and vfs.is_dir(target)):
                                # Копирование между устройствами (или слияние
                                # каталогов) — показываем реальный прогресс,
                                # а не замираем на rename внутри GIO.
                                job.text = _('Calculating size…')
                                job.fraction = None
                                b, f = vfs.measure(src)
                                job.bytes_total = b
                                job.files_total = f
                                job.text = name
                                vfs.copy_with_progress(src, target, job, b, 0, name,
                                                       files_total=f)
                                if job.cancelled:
                                    self._drop_partial(target, created)
                                    break
                                vfs.remove(src)
                                created = False
                            else:
                                vfs.move(src, target)
                        else:
                            done, files_done = vfs.copy_with_progress(
                                src, target, job, total, done, name,
                                files_done, files_total)
                            if job.cancelled:
                                self._drop_partial(target, created)
                                break
                        if created:
                            pairs.append((src, target))
                    except (OSError, GLib.Error, shutil.Error) as e:
                        if job.cancelled:
                            break
                        errs.append('%s: %s' % (src, getattr(e, 'message', e)))
                if not job.cancelled:
                    job.fraction = 1.0
                return errs

            def done(errs, err, job):
                errs = [str(err)] if err else errs
                if errs:
                    text_dialog(self, _('Error'), '\n'.join(errs))
                if record and pairs:
                    self._push_undo({'kind': 'move' if move else 'copy', 'pairs': list(pairs)})
                if on_done is not None:
                    on_done(errs, bool(job and job.cancelled))
                self.reload_all()
            icon = ('folder-symbolic' if any(vfs.is_dir(p) and not vfs.is_link(p) for p in paths)
                    else 'text-x-generic-symbolic')
            self.run_job(_('Moving files') if move else _('Copying files'), work, done,
                         subtitle=(_('Moving') if move else _('Copying')) + '…',
                         pausable=True, icon=icon)
        if clash:
            self.ask_conflict(_('{0} item(s) already exist in the destination folder.').format(len(clash)), go)
        else:
            go('overwrite')

    def op_select_mask(self, *a, select=True):
        PromptDialog(self, _('Select') if select else _('Deselect'), _('Mask:'), '*', _('OK'),
                     lambda m: self.active.select_mask(m, select)).present()

    # ───────────── сервисные ─────────────
    def op_hash(self, action, param):
        alg = param.get_string()
        p = self.active
        sel = p.selected()
        if p.mode != 'fs' or not sel:
            alert(self, _('Checksums are calculated for files on disk. Select files first.'))
            return
        paths = [i.full for i in sel]

        def work(job):
            tmps, local = [], []
            try:
                for pth in paths:
                    if vfs.is_uri(pth):
                        t, l = vfs.copy_to_temp(pth)
                        tmps.append(t)
                        local.append(l)
                    else:
                        local.append(pth)
                return self.sz.run('h', ['-scrc' + alg], local, job=job)
            finally:
                for t in tmps:
                    shutil.rmtree(t, ignore_errors=True)

        def done(res, err, job):
            if err is not None or res is None or res.cancelled:
                return
            text_dialog(self, _('Checksum') + ' ' + alg, res.out)
        self.run_job(_('Calculating checksum'), work, done)

    def op_split(self, *a):
        p = self.active
        sel = [i for i in p.selected() if not i.is_dir]
        if p.mode != 'fs' or not sel:
            alert(self, _('Select a file to split first'))
            return
        src = sel[0].full

        def go(dest, size):
            def worker(job):
                tmp_src = tmp_out = None
                try:
                    local = src
                    if vfs.is_uri(src):
                        tmp_src, local = vfs.copy_to_temp(src)
                    if vfs.is_uri(dest):
                        tmp_out = tempfile.mkdtemp(prefix='7zgtk-split-')
                        out = tmp_out
                    else:
                        out = os.path.abspath(os.path.expanduser(dest))
                        os.makedirs(out, exist_ok=True)
                    n = split_worker(local, out, size, job)
                    if tmp_out:
                        if not vfs.exists(dest):
                            vfs.mkdirs(dest)
                        for e in os.scandir(tmp_out):
                            vfs.copy(e.path, vfs.join(dest, e.name))
                    return n
                finally:
                    for d in (tmp_src, tmp_out):
                        if d:
                            shutil.rmtree(d, ignore_errors=True)
            self.run_job(_('Splitting'), worker,
                         lambda r, e, j: (alert(self, _('Error'), str(e)) if e else None, self.reload_all()))
        dlg = SplitDialog(self, vfs.display(src) if vfs.is_uri(src) else src, go)
        if vfs.is_uri(src):
            dlg.e_dest.set_text(vfs.dirname(src))
        dlg.present()

    def op_combine(self, *a):
        p = self.active
        sel = [i for i in p.selected() if not i.is_dir and re.search(r'\.001$', i.name)]
        if p.mode != 'fs' or not sel:
            alert(self, _('Select the first part (*.001) first'))
            return
        first = sel[0].full

        def go(out):
            def worker(job):
                tmp_src = tmp_out = None
                try:
                    local_first = first
                    if vfs.is_uri(first):
                        parent = vfs.dirname(first)
                        base = vfs.basename(first)[:-4]
                        pat = re.compile('^' + re.escape(base) + r'\.[0-9]{3}$')
                        names = sorted(e.name for e in vfs.listdir(parent) if pat.match(e.name))
                        tmp_src = tempfile.mkdtemp(prefix='7zgtk-parts-')
                        local_parts = []
                        for name in names:
                            dst = os.path.join(tmp_src, name)
                            vfs.copy(vfs.join(parent, name), dst)
                            local_parts.append(dst)
                        if not local_parts:
                            raise OSError(_('No parts found'))
                        local_first = local_parts[0]
                    local_out = out
                    if vfs.is_uri(out):
                        tmp_out = tempfile.mkdtemp(prefix='7zgtk-join-')
                        local_out = os.path.join(tmp_out, vfs.basename(out))
                    n = combine_worker(local_first, local_out, job)
                    if tmp_out:
                        vfs.copy(local_out, out)
                    return n
                finally:
                    for d in (tmp_src, tmp_out):
                        if d:
                            shutil.rmtree(d, ignore_errors=True)
            self.run_job(_('Combining'), worker,
                         lambda r, e, j: (alert(self, _('Error'), str(e)) if e else None, self.reload_all()))
        PromptDialog(self, _('Combine files'), _('Combine to:'), first[:-4], _('OK'), go).present()

    def op_convert(self, action=None, param=None):
        target = param.get_string() if param is not None else None
        p = self.active
        if p.mode != 'fs':
            alert(self, _('Conversion is available only for files on disk'))
            return
        paths = [i.full for i in p.selected() if not i.is_dir and kind_of(i.full)]
        if not paths:
            alert(self, _('Select audio, video or image files to convert'))
            return
        if target is not None:
            paths = [p for p in paths if convert_supports(p, target)]
            if not paths:
                alert(self, _('No compatible files selected'))
                return

        def started(items, quality):
            def worker(job):
                return convert_files(items, job, quality)

            def done(res, err, job):
                if err is not None:
                    alert(self, _('Conversion error'), str(err))
                self.reload_all()
            self.run_job(_('Converting'), worker, done)
        ConverterDialog(self, paths, target=target, on_ok=started).present()

    def _archive_counts(self, path, cb):
        """Количество файлов и папок внутри архива для вкладки «Основные»."""
        def done(res, _header, entries):
            if res is None or not res.ok or entries is None:
                cb(None)
                return
            files = sum(1 for e in entries if not e.is_dir)
            cb((files, len(entries) - files))
        self.list_async(path, self.passwords.get(path), done)

    def op_properties(self, *a):
        p = self.active
        sel = p.selected()
        if not sel:
            return
        if p.mode == 'arc':
            by_path = {e.path: e for e in p.arc.entries}
            if len(sel) == 1:
                e = by_path.get(sel[0].full)
                if e is not None:
                    meta_reader = None
                    if not e.is_dir and kind_of(e.path):
                        arc = p.arc

                        def meta_reader(ent, kind, arc=arc):
                            return read_archive_metadata(
                                self.sz.bin, arc.path, ent.path, kind, arc.password)
                    PropertiesDialog(self, entry=e, archive_path=p.arc.display,
                                     entry_meta=meta_reader).present()
                    return
            lines = []
            for i in sel:
                e = by_path.get(i.full)
                lines.append(_('Name') + ': ' + i.full)
                if e:
                    lines += [_('Size') + ': ' + fmt_num(e.size), _('Packed Size') + ': ' + fmt_num(e.packed),
                              _('Modified') + ': ' + fmt_time(e.mtime), _('Attributes') + ': ' + e.attrs,
                              'CRC: ' + e.crc, _('Method') + ': ' + e.method]
                lines.append('')
            text_dialog(self, _('Properties'), '\n'.join(lines), 520, 320)
            return
        paths = [i.full for i in sel]
        if len(paths) == 1:
            PropertiesDialog(self, paths=paths, archive_info=self._archive_counts).present()
            return

        def work(job):
            files = dirs = size = 0

            def visit(pth):
                nonlocal files, dirs, size
                if job.cancelled:
                    return
                if vfs.is_dir(pth) and not vfs.is_link(pth):
                    dirs += 1
                    try:
                        children = vfs.listdir(pth)
                    except OSError:
                        return
                    for e in children:
                        visit(e.path)
                else:
                    files += 1
                    try:
                        size += vfs.stat(pth).st_size
                    except (OSError, GLib.Error):
                        pass
            for pth in paths:
                visit(pth)
            return None if job.cancelled else (files, dirs, size)

        def done(r, e, job):
            if not r:
                return
            files, dirs, size = r
            lines = []
            if len(paths) == 1:
                st = vfs.stat(paths[0])
                gi = vfs.gfile(paths[0]).query_info('standard::content-type', 0, None)
                lines += [_('Name') + ': ' + vfs.basename(paths[0]),
                          _('Location') + ': ' + (vfs.dirname(paths[0]) or '/'),
                          _('Type') + ': ' + (Gio.content_type_get_description(gi.get_content_type()) or ''),
                          _('Modified') + ': ' + fmt_time(int(st.st_mtime)),
                          _('Attributes') + ': ' + stat.filemode(st.st_mode)]
            lines += [_('Size') + ': ' + fmt_num(size) + ' B (' + human(size) + ')',
                      _('Files') + ': ' + fmt_num(files), _('Folders') + ': ' + fmt_num(dirs)]
            text_dialog(self, _('Properties'), '\n'.join(lines), 520, 260)
        self.run_job(_('Properties'), work, done)

    def op_info(self, *a):
        p = self.active
        if p.mode == 'arc':
            self._show_info(p.arc.display, p.arc.header, p.arc.entries)
            return
        sel = p.selected()
        if sel and not sel[0].is_dir and is_archive_name(sel[0].name):
            path = sel[0].full

            def cb(res, header, entries):
                if header.get('Type'):
                    self._show_info(vfs.display(path), header, entries)
                else:
                    alert(self, _('Cannot open file "{0}" as archive').format(os.path.basename(path)), res.text(10))
            self.list_async(path, self.passwords.get(path), cb)
        else:
            self.op_properties()

    def _show_info(self, title, header, entries):
        files = [e for e in entries if not e.is_dir]
        size, packed = sum(e.size for e in files), sum(e.packed for e in files)
        lines = ['%s = %s' % (k, v) for k, v in header.items()]
        lines += ['', _('Files') + ' = %s' % fmt_num(len(files)),
                  _('Folders') + ' = %s' % fmt_num(len(entries) - len(files)),
                  _('Size') + ' = %s' % fmt_num(size), _('Packed Size') + ' = %s' % fmt_num(packed)]
        if size:
            lines.append(_('Ratio') + ' = %d%%' % (100 * packed // size))
        text_dialog(self, title, '\n'.join(lines), 560, 380)

    # ───────────── вид / избранное / сервис ─────────────
    def op_list_mode(self, action, param):
        v = self._toggle(action)
        for p in (self.p1, self.p2):
            p.set_details(not v)

    def op_two_panels(self, action, param):
        if self.design == 'dual':
            return
        v = self._toggle(action)
        self.conf['two_panels'] = v
        self.p2.set_visible(v)
        if v and not self._p2_shown_once:
            self._p2_shown_once = True
            self.p2.navigate_fs(self.p1.current_dir())

    def top_panels_status(self):
        hm = bool(self.conf.get('hide_menu_bar'))
        ht = bool(self.conf.get('hide_toolbar'))
        hs = bool(self.conf.get('hide_sidebar'))
        hb = bool(self.conf.get('hide_panels_button'))
        if hm and ht:
            status = _('Both panels are hidden')
        elif hm:
            status = _('Menu bar is hidden')
        elif ht:
            status = _('Action panel is hidden')
        else:
            status = _('Both panels are visible')
        extra = []
        if hs:
            extra.append(_('Sidebar is hidden'))
        if hb:
            extra.append(_('“Panels” button is hidden'))
        if extra:
            status += ' · ' + ' · '.join(extra)
        return status

    def apply_top_panels(self):
        hm = bool(self.conf.get('hide_menu_bar'))
        ht = bool(self.conf.get('hide_toolbar'))
        hs = bool(self.conf.get('hide_sidebar'))
        hb = bool(self.conf.get('hide_panels_button'))
        if hasattr(self, 'menubar'):
            self.menubar.set_visible(not hm)
        if hasattr(self, 'toolbar'):
            self.toolbar.set_visible(not ht)
            # подписи прячем до пересчёта минимума, иначе панель «растянет» окно
            self._sync_toolbar_labels()
        if self.sidebar is not None:
            self.sidebar.set_visible(not hs)
        for name, hidden in (('menu-bar', hm), ('toolbar', ht), ('panels-button', hb)):
            act = self.lookup_action(name)
            if act is not None:
                act.set_state(GLib.Variant.new_boolean(not hidden))
        status = self.top_panels_status()
        for p in (getattr(self, 'p1', None), getattr(self, 'p2', None)):
            if p is not None and hasattr(p, 'btn_panels'):
                p.btn_panels.set_visible(not hb)
                p.btn_panels.set_tooltip_text(_('Top panels') + ': ' + status)

    def set_top_panels(self, hide_menu=None, hide_toolbar=None, hide_sidebar=None,
                       hide_panels_button=None, show_all=False, persist=True):
        """Изменить видимость верхних панелей, боковой панели и кнопки «Панели»."""
        hm = bool(self.conf.get('hide_menu_bar'))
        ht = bool(self.conf.get('hide_toolbar'))
        hs = bool(self.conf.get('hide_sidebar'))
        hb = bool(self.conf.get('hide_panels_button'))
        if show_all:
            hide_menu = hide_toolbar = False
        new_m = hm if hide_menu is None else bool(hide_menu)
        new_t = ht if hide_toolbar is None else bool(hide_toolbar)
        new_s = hs if hide_sidebar is None else bool(hide_sidebar)
        new_b = hb if hide_panels_button is None else bool(hide_panels_button)

        def apply():
            self._apply_top_panels_values(new_m, new_t, new_s, new_b, persist)

        # Меню и кнопка «Панели» — единственные пути в настройки без горячих клавиш.
        if new_m and new_b and not (hm and hb):
            self._confirm_last_settings_route(hm, hb, apply)
            return False
        apply()
        return True

    def _apply_top_panels_values(self, hide_menu, hide_toolbar, hide_sidebar,
                                 hide_panels_button, persist=True):
        self.conf['hide_menu_bar'] = bool(hide_menu)
        self.conf['hide_toolbar'] = bool(hide_toolbar)
        self.conf['hide_sidebar'] = bool(hide_sidebar)
        self.conf['hide_panels_button'] = bool(hide_panels_button)
        self.apply_top_panels()
        if persist:
            self.conf.save()

    def _confirm_last_settings_route(self, menu_hidden, button_hidden, on_ok):
        """Предупредить, если скрывается последний путь в настройки через интерфейс."""
        hotkey = self.accel_text('settings')
        if button_hidden and not menu_hidden:
            head = _('The “Panels” button will be hidden, and the menu bar is already hidden.')
        elif menu_hidden and not button_hidden:
            head = _('The menu bar will be hidden, and the “Panels” button is already hidden.')
        else:
            head = _('The menu bar and the “Panels” button will be hidden.')
        if not hotkey:
            alert(self, _('No way left to open Settings'),
                  head + '\n\n' + _('Settings has no hotkey assigned. Assign one first, '
                                    'otherwise the settings will be impossible to open.'))
            return False
        detail = (head + '\n\n' +
                  _('This is the last way to open Settings without hotkeys. '
                    'To open Settings, press {0}.').format(hotkey) + '\n\n' +
                  _('There you can bring the panels and the “Panels” button back.'))
        choose(self, _('The last way to open Settings will be hidden'),
               [_('Cancel'), _('Hide anyway')],
               lambda i: on_ok() if i == 1 else None,
               detail=detail, default=0, cancel=0)
        return False

    def op_menu_bar(self, action, param):
        self.set_top_panels(hide_menu=not bool(self.conf.get('hide_menu_bar')))

    def op_toolbar(self, action, param):
        self.set_top_panels(hide_toolbar=not bool(self.conf.get('hide_toolbar')))

    def op_panels_button(self, action, param):
        self.set_top_panels(hide_panels_button=not bool(self.conf.get('hide_panels_button')))

    def op_hidden(self, action, param):
        self.conf['show_hidden'] = self._toggle(action)
        self.reload_all()

    def op_history(self, *a):
        p = self.active
        HistoryDialog(self, p.history_paths(), p.navigate_text).present()

    def op_fav_save(self, action, param):
        self.conf['favorites'][str(param.get_int32())] = self.active.location_text()
        self._fav_changed()

    def op_fav_open(self, action, param):
        path = fav_path(self.conf['favorites'].get(str(param.get_int32())))
        if path:
            self.active.navigate_text(path)

    def op_settings(self, *a, page=0):
        SettingsDialog(self, self.conf, self.apply_settings, page=page).present()

    def apply_settings(self, rebuild):
        self.conf.save()
        if rebuild:
            set_language(self.conf['language'])
            self.get_application().rebuild()
            return
        apply_theme(self.conf)
        apply_display(self.conf)
        for win in self._each_window():
            win.apply_live_settings()

    def apply_live_settings(self):
        """Применить настройки без пересоздания окна (для всех окон приложения)."""
        self.apply_hotkeys()
        self.apply_top_panels()
        self.lookup_action('hidden').set_state(GLib.Variant.new_boolean(bool(self.conf['show_hidden'])))
        self.lookup_action('view-mode').set_state(GLib.Variant.new_string(self.conf['view_mode']))
        self.lookup_action('thumbs').set_state(GLib.Variant.new_boolean(bool(self.conf['show_thumbs'])))
        for p in (self.p1, self.p2):
            p.apply_options(self.conf)
        self._rebuild_fav()
        if self.sidebar is not None:
            self.sidebar.rebuild()
        self.reload_all()
        self.update_statusbar()

    def op_switch_panel(self, *a):
        o = self.other_panel()
        if o is not None:
            o.focus_view()

    def _side_width_to_save(self):
        """Ширина боковой панели, выбранная пользователем (0 — не сохранять)."""
        paned = self.side_paned
        if paned is None:
            return 0
        width = paned.get_position()
        if width <= 0:
            return 0
        try:
            desired = int(self.conf.get('sidebar_width') or 0)
        except (TypeError, ValueError):
            desired = 0
        max_pos = paned.get_property('max-position')
        if 0 < desired < width and width >= max_pos:
            # Разделитель упёрся в правый край: это ограничение, а не выбор ширины.
            return 0
        end = paned.get_end_child()
        if end is not None:
            need = end.measure(Gtk.Orientation.HORIZONTAL, -1)[0]
            # Разделитель упёрся в минимум рабочей области: это не выбор пользователя,
            # иначе широкая панель «сжималась» бы в памяти при маленьком окне.
            if paned.get_width() - width <= need + 1:
                return 0
        return int(width)

    def _on_side_max_position(self, paned, _pspec):
        # Когда окно/рабочая область стали шире, возвращаем выбранную ширину панели.
        try:
            desired = int(self.conf.get('sidebar_width') or 220)
        except (TypeError, ValueError):
            desired = 220
        max_pos = paned.get_property('max-position')
        if paned.get_position() < desired <= max_pos:
            paned.set_position(desired)

    def _on_side_paned_position(self, paned, _pspec):
        width = paned.get_position()
        try:
            desired = int(self.conf.get('sidebar_width') or 0)
        except (TypeError, ValueError):
            desired = 0
        # Разделитель упёрся в правый край — запоминаем, что ширина ограничена,
        # и не сохраняем её вместо выбранной пользователем.
        if width > 0 and desired and desired < width and width >= paned.get_property('max-position'):
            self._side_clamped = True
            return
        self._side_clamped = False
        width = self._side_width_to_save()
        if width > 0:
            self.conf['sidebar_width'] = width
            if self._side_save_id:
                GLib.source_remove(self._side_save_id)
            self._side_save_id = GLib.timeout_add(400, self._save_sidebar_width)

    def _save_sidebar_width(self):
        self._side_save_id = 0
        self.conf.save()
        return False

    def op_toggle_sidebar(self, *a):
        if self.sidebar is not None:
            self.set_top_panels(hide_sidebar=not bool(self.conf.get('hide_sidebar')))

    def op_search(self, *a):
        self.searchbar.set_search_mode(not self.searchbar.get_search_mode())

    def op_clean_temp(self, *a):
        in_use = set()
        for p in (self.p1, self.p2):
            if p.arc is not None:
                in_use |= {x.tmp for x in p.arc.chain() if x.tmp}
        left = []
        for t in self.temp_dirs:
            if t in in_use:
                left.append(t)
            else:
                shutil.rmtree(t, ignore_errors=True)
        self.temp_dirs = left

    def op_help(self, *a):
        l = Gtk.UriLauncher.new('https://7-zip.org/faq.html')
        l.launch(self, None, lambda lau, res: None)

    def op_about(self, *a):
        d = Gtk.AboutDialog(transient_for=self, modal=True)
        d.set_program_name(APP_NAME)
        d.set_version(VERSION)
        d.set_logo_icon_name(APP_ID)
        d.set_comments(_('Two-panel GTK4 file manager and archiver') + '\n' + (self.sz.version or _('7z not found')))
        d.set_website('https://github.com/MemTim/archive-navigator')
        d.set_website_label(_('Project page on GitHub'))
        d.set_license_type(Gtk.License.CUSTOM)
        d.set_license('PolyForm Noncommercial License 1.0.0\n'
                      'https://polyformproject.org/licenses/noncommercial/1.0.0')
        d.set_debug_info(_('Log file:') + ' ' + (diagnostics.log_path() or '—'))
        d.present()

    # ───────────── командная строка ─────────────
    def cli_open(self, path):
        if os.path.isdir(path):
            self.p1.navigate_fs(path)
        elif os.path.isfile(path):
            self.p1.navigate_fs(os.path.dirname(path))
            self.p1.open_archive(path)

    def cli_add(self, paths):
        paths = [p for p in paths if os.path.exists(p)]
        if not paths:
            return
        f0 = self.conf['add_format'] if self.conf['add_format'] in FORMATS else '7z'
        name = os.path.join(os.path.dirname(paths[0]), default_stem(paths) + '.' + FMT[f0]['ext'])
        AddDialog(self, name, lambda o: self.start_add(paths, o), f0, self.conf['add_level']).present()

    def cli_extract(self, archives, here=False):
        archives = [p for p in archives if os.path.isfile(p)]
        if not archives:
            return
        base = os.path.dirname(archives[0])
        opts = self._default_extract_opts()
        if here:
            self.extract_start(archives, base, opts)
        else:
            dest = os.path.join(base, '*' if len(archives) > 1 else archive_stem(os.path.basename(archives[0])))
            self._extract_dialog(_('Extract'), dest, lambda d, o: self.extract_start(archives, d, o)).present()

    def _on_close(self, w):
        diagnostics.log('окно %s: _on_close', hex(id(self)))
        self.closing = True
        if self.sidebar is not None:
            self.sidebar.disconnect_monitor()
        self._on_destroy_clipboard()
        try:
            w_, h_ = self.get_width(), self.get_height()
            if w_ > 200 and h_ > 150:
                self.conf['width'], self.conf['height'] = w_, h_
        except Exception:
            pass
        if self._side_save_id:
            GLib.source_remove(self._side_save_id)
            self._side_save_id = 0
        if self._toolbar_sync_id:
            GLib.source_remove(self._toolbar_sync_id)
            self._toolbar_sync_id = 0
        self._stop_status_timer()
        self._stop_status_progress()
        if self.side_paned is not None and not self._side_clamped:
            width = self._side_width_to_save()
            if width > 0:
                self.conf['sidebar_width'] = width
        if self.design != 'dual':
            self.conf['two_panels'] = self.p2.get_visible()
        self.conf.save()
        if self.rebuilding:
            return False
        for p in (self.p1, self.p2):
            p.leave_archive()
        for t in self.temp_dirs:
            shutil.rmtree(t, ignore_errors=True)
        return False
