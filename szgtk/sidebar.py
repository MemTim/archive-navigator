# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from urllib.parse import unquote
from .i18n import _, N_
from . import diagnostics
from . import vfs
from .dialogs import (alert, button_row, grid_row, hbox, lbl, make_dd,
                      new_dialog, pick_icon, vbox)
from .favorites import name as fav_name, path as fav_path
from .settings import (_drawing, _fav_sort_icon, _menu_eye_closed,
                       _menu_eye_open)

PLACES_SPEC = [
    ('home', 'user-home-symbolic', N_('Home folder'), None),
    ('desktop', 'user-desktop-symbolic', N_('Desktop'), GLib.UserDirectory.DIRECTORY_DESKTOP),
    ('downloads', 'folder-download-symbolic', N_('Downloads'), GLib.UserDirectory.DIRECTORY_DOWNLOAD),
    ('documents', 'folder-documents-symbolic', N_('Documents'), GLib.UserDirectory.DIRECTORY_DOCUMENTS),
    ('pictures', 'folder-pictures-symbolic', N_('Pictures'), GLib.UserDirectory.DIRECTORY_PICTURES),
    ('music', 'folder-music-symbolic', N_('Music'), GLib.UserDirectory.DIRECTORY_MUSIC),
    ('videos', 'folder-videos-symbolic', N_('Videos'), GLib.UserDirectory.DIRECTORY_VIDEOS),
]
PLACES_IDS = tuple(place_id for place_id, _icon, _label, _dir in PLACES_SPEC)

# Схемы GVfs, которыми обычно представлены телефоны и камеры.
PHONE_SCHEMES = ('mtp', 'gphoto2', 'afc')

# Сетевые подключения, которые можно открыть через GVfs.
NETWORK_SCHEMES = ('smb', 'sftp', 'ftp', 'dav', 'davs', 'nfs', 'afp')
REMOTE_SCHEMES = PHONE_SCHEMES + NETWORK_SCHEMES

# Префиксы имён каталогов gvfs-fuse. У SMB URI-схема одна, а точек
# монтирования две: smb-share: для ресурса и smb: для обзора сервера.
GVFS_PREFIXES = {
    'smb': ('smb-share:', 'smb:'),
    'davs': ('dav:', 'davs:'),
}

NETWORK_PROTOCOLS = (
    ('smb', 'SMB / Windows'),
    ('sftp', 'SFTP (SSH)'),
    ('ftp', 'FTP'),
    ('dav', 'WebDAV'),
    ('davs', 'WebDAV (HTTPS)'),
    ('nfs', 'NFS'),
    ('afp', 'AFP'),
)

SIDEBAR_GROUPS = [
    ('places', N_('PLACES')),
    ('favorites', N_('FAVORITES')),
    ('devices', N_('DEVICES')),
]
SIDEBAR_LABELS = dict(SIDEBAR_GROUPS)
SIDEBAR_IDS = tuple(group_id for group_id, _label in SIDEBAR_GROUPS)


def groups(conf):
    """Порядок групп боковой панели, дополненный новыми группами."""
    raw = conf.get('sidebar_groups') or []
    order, seen = [], set()
    for group_id in raw:
        if group_id in SIDEBAR_LABELS and group_id not in seen:
            order.append(group_id)
            seen.add(group_id)
    for group_id in SIDEBAR_IDS:
        if group_id not in seen:
            order.append(group_id)
    return order


def place_order(conf):
    """Порядок пунктов «Места», дополненный новыми пунктами."""
    raw = conf.get('sidebar_places') or []
    order, seen = [], set()
    for place_id in raw:
        if place_id in PLACES_IDS and place_id not in seen:
            order.append(place_id)
            seen.add(place_id)
    for place_id in PLACES_IDS:
        if place_id not in seen:
            order.append(place_id)
    return order


def hidden_places(conf):
    """Множество скрытых пунктов «Места»."""
    return {place_id for place_id in (conf.get('sidebar_hidden_places') or [])
            if place_id in PLACES_IDS}


def all_places():
    """Доступные пункты «Места»: (id, значок, подпись, путь)."""
    home = os.path.normpath(os.path.expanduser('~'))
    out = []
    for place_id, icon, label, directory in PLACES_SPEC:
        if place_id == 'home':
            path = home
        else:
            path = GLib.get_user_special_dir(directory)
        if not path or not os.path.isdir(path):
            continue
        path = os.path.normpath(path)
        if place_id != 'home' and path == home:
            continue
        out.append((place_id, icon, _(label), path))
    return out


def special_places():
    return [(icon, label, path) for _place_id, icon, label, path in all_places()]


def hidden_groups(conf):
    """Множество скрытых групп боковой панели."""
    return {group_id for group_id in (conf.get('sidebar_hidden') or [])
            if group_id in SIDEBAR_LABELS}


def _volume_monitor():
    return Gio.VolumeMonitor.get()


def _sidebar_job_ring(area, cr, w, h):
    """Круговой индикатор фоновой операции вместо карандаша."""
    c = area.get_color()
    cx, cy = w / 2.0, h / 2.0
    r = max(3.0, min(w, h) / 2.0 - 2.0)
    width = max(2.0, r * 0.34)
    cr.set_line_width(width)
    cr.set_line_cap(1)  # round
    # Дорожка.
    cr.set_source_rgba(c.red, c.green, c.blue, 0.22)
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.stroke()
    # Заполнение: дуга прогресса или вращающийся сегмент.
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    f = getattr(area, 'fraction', None)
    if f is None:
        a0 = getattr(area, 'rotation', 0.0)
        cr.arc(cx, cy, r, a0, a0 + 1.7)
    else:
        f = max(0.0, min(1.0, f))
        cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * f)
    cr.stroke()


def _job_action_text(action):
    """Короткое название операции для карточки в боковой панели."""
    return {
        'copy': _('Copying'),
        'move': _('Moving'),
        'archive': _('Archiving'),
        'extract': _('Extracting'),
    }.get(action, '')


def _sidebar_pencil(area, cr, w, h):
    """Карандаш из Vector 8.svg, перекрашенный в текущий цвет темы."""
    c = area.get_color()
    cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
    cr.save()
    cr.scale(w / 8.0, h / 8.0)
    cr.set_line_width(1.0)
    cr.set_line_join(1)
    # Кончик.
    cr.move_to(0.5, 7.35862)
    cr.line_to(0.5, 5.70004)
    cr.curve_to(0.5, 5.61095, 0.607714, 5.56633, 0.670711, 5.62933)
    cr.line_to(2.32929, 7.28791)
    cr.curve_to(2.39229, 7.3509, 2.34767, 7.45862, 2.25858, 7.45862)
    cr.line_to(0.6, 7.45862)
    cr.curve_to(0.544772, 7.45862, 0.5, 7.41385, 0.5, 7.35862)
    cr.close_path()
    cr.fill_preserve()
    cr.stroke()
    # Корпус.
    cr.move_to(5.42929, 0.529329)
    cr.line_to(1.57071, 4.38791)
    cr.curve_to(1.53166, 4.42696, 1.53166, 4.49028, 1.57071, 4.52933)
    cr.line_to(3.42929, 6.38791)
    cr.curve_to(3.46834, 6.42696, 3.53166, 6.42696, 3.57071, 6.38791)
    cr.line_to(7.42929, 2.52933)
    cr.curve_to(7.46834, 2.49028, 7.46834, 2.42696, 7.42929, 2.38791)
    cr.line_to(5.57071, 0.529329)
    cr.curve_to(5.53166, 0.490276, 5.46834, 0.490276, 5.42929, 0.529329)
    cr.close_path()
    cr.fill_preserve()
    cr.stroke()
    cr.restore()


class Sidebar(Gtk.Box):
    """Боковая панель дизайна «Навигационный»: Места / Избранное / Устройства."""

    def __init__(self, win):
        super().__init__(orientation=V)
        self.win, self.items = win, []
        self.group_order = groups(win.conf)
        self.hidden = hidden_groups(win.conf)
        self.group_rows = []
        self.group_drag_id = None
        self.group_drop = None
        self.place_order = place_order(win.conf)
        self.place_hidden = hidden_places(win.conf)
        self.place_rows = []
        self.place_drag_id = None
        self.place_drop = None
        self.editing = False
        self._alive = True
        self._devices_id = 0
        self._monitor = None
        self._monitor_ids = []
        try:
            self._monitor = _volume_monitor()
            for signal in ('mount-added', 'mount-changed',
                           'volume-added', 'volume-removed', 'volume-changed',
                           'drive-connected', 'drive-disconnected', 'drive-changed'):
                try:
                    self._monitor_ids.append(
                        self._monitor.connect(signal, self._on_devices_changed))
                except Exception:
                    pass
            try:
                self._monitor_ids.append(
                    self._monitor.connect('mount-removed', self._on_mount_removed))
            except Exception:
                pass
        except Exception:
            self._monitor = None
        self.add_css_class('sz-sidebar')
        self.set_hexpand(False)
        self.set_size_request(160, -1)
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll = sw
        self.inner = vbox(2)
        self.inner.set_margin_start(8)
        self.inner.set_margin_end(8)
        sw.set_child(self.inner)
        self.append(sw)
        card = hbox(8)
        card.add_css_class('sz-usercard')
        info = vbox(2)
        info.set_hexpand(True)
        name = GLib.get_real_name()
        if not name or name == 'Unknown':
            name = GLib.get_user_name()
        n = lbl(name)
        n.add_css_class('sz-hdr-role')
        p = lbl(os.path.expanduser('~'))
        p.add_css_class('sz-muted')
        p.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        info.append(n)
        info.append(p)
        self.edit_btn = Gtk.Button()
        self.edit_btn.add_css_class('flat')
        self.edit_btn.add_css_class('sz-side-edit')
        self.edit_btn.set_focus_on_click(False)
        self.edit_btn.set_valign(Gtk.Align.CENTER)
        self.edit_btn.set_child(_drawing(18, 18, _sidebar_pencil, 'sz-side-edit-icon'))
        self.edit_btn.connect('clicked', self._toggle_edit)
        self.job_dialogs = []
        self._job_timer = 0
        self._job_popup = None
        self.job_area = _drawing(20, 20, _sidebar_job_ring, 'sz-side-job')
        self.job_area.fraction = None
        self.job_area.rotation = -math.pi / 2
        self.job_btn = Gtk.Button()
        self.job_btn.add_css_class('flat')
        self.job_btn.add_css_class('sz-side-edit')
        self.job_btn.add_css_class('sz-side-job-btn')
        self.job_btn.set_focus_on_click(False)
        self.job_btn.set_valign(Gtk.Align.CENTER)
        self.job_btn.set_child(self.job_area)
        self.job_btn.set_tooltip_text(_('Operation in progress'))
        self.job_btn.connect('clicked', self._open_job_popup)
        self.corner = Gtk.Stack()
        self.corner.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.corner.set_transition_duration(120)
        self.corner.add_named(self.edit_btn, 'edit')
        self.corner.add_named(self.job_btn, 'job')
        card.append(info)
        card.append(self.corner)
        self.append(card)
        self._sync_edit_btn()
        self.rebuild()

    def _sync_edit_btn(self):
        text = _('Done editing') if self.editing else _('Edit sidebar')
        self.edit_btn.set_tooltip_text(text)
        self.edit_btn.update_property([Gtk.AccessibleProperty.LABEL], [text])
        (self.edit_btn.add_css_class if self.editing
         else self.edit_btn.remove_css_class)('sz-side-edit-on')

    def _toggle_edit(self, *a):
        self.editing = not self.editing
        self._sync_edit_btn()
        self.rebuild()

    # ───────── индикатор фоновых операций ─────────
    def add_job_dialog(self, dlg):
        if dlg not in self.job_dialogs:
            self.job_dialogs.append(dlg)
        self._sync_job_indicator()

    def remove_job_dialog(self, dlg):
        if dlg in self.job_dialogs:
            self.job_dialogs.remove(dlg)
        self._sync_job_indicator()

    def _sync_job_indicator(self):
        active = bool(self.job_dialogs)
        had_popup = self._job_popup is not None
        self.corner.set_visible_child_name('job' if active else 'edit')
        if active and not self._job_timer:
            self._job_timer = GLib.timeout_add(100, self._job_tick)
        elif not active and self._job_timer:
            GLib.source_remove(self._job_timer)
            self._job_timer = 0
        if active:
            self._job_tick()
            if had_popup:
                self._close_job_popup()
                self._open_job_popup()
        else:
            self._close_job_popup()

    def _job_tick(self):
        if not self._alive or not self.job_dialogs:
            self._job_timer = 0
            if self._alive and self.corner.get_visible_child_name() != 'edit':
                self.corner.set_visible_child_name('edit')
            return False
        dlg = self.job_dialogs[-1]
        f = dlg.job.fraction
        if f is None:
            self.job_area.rotation = ((getattr(self.job_area, 'rotation', 0.0) + 0.18)
                                      % (2 * math.pi))
        self.job_area.fraction = f
        self.job_area.queue_draw()
        snap = dlg.progress_snapshot()
        tip = _job_action_text(snap['action']) or snap['title'] or _('Operation in progress')
        if snap['pct']:
            tip += ' · ' + snap['pct']
        if len(self.job_dialogs) > 1:
            tip += ' · %d' % len(self.job_dialogs)
        self.job_btn.set_tooltip_text(tip)
        self._update_job_popup()
        return True

    def _job_popup_row(self, dlg, first):
        if not first:
            sep = Gtk.Separator()
            sep.add_css_class('sz-job-sep')
            return sep
        return None

    def _open_job_popup(self, *a):
        if not self.job_dialogs:
            return
        if self._job_popup is not None:
            pop = self._job_popup['pop']
            was_visible = pop.get_visible()
            self._close_job_popup()
            if was_visible:
                return
        pop = Gtk.Popover()
        pop.add_css_class('sz-job-popover')
        pop.set_has_arrow(True)
        box = vbox(9)
        box.add_css_class('sz-job-pop')
        box.set_size_request(340, -1)
        sections = []
        for i, dlg in enumerate(self.job_dialogs):
            sep = self._job_popup_row(dlg, i == 0)
            if sep is not None:
                box.append(sep)
            action_l = lbl('')
            action_l.add_css_class('sz-job-action')
            title = lbl('')
            title.add_css_class('sz-job-title')
            file_l = lbl('')
            file_l.add_css_class('sz-job-file')
            file_l.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            file_l.set_max_width_chars(48)
            bar = Gtk.ProgressBar()
            bar.add_css_class('sz-job-bar')
            bar.set_show_text(False)
            info = hbox(10)
            pct = lbl('')
            pct.add_css_class('sz-job-info')
            pct.set_hexpand(True)
            eta = lbl('', xalign=1.0)
            eta.add_css_class('sz-job-info')
            info.append(pct)
            info.append(eta)
            size = lbl('')
            size.add_css_class('sz-job-info')
            speed = lbl('')
            speed.add_css_class('sz-job-info')
            files = lbl('')
            files.add_css_class('sz-job-info')
            btns = hbox(6)
            btns.set_halign(Gtk.Align.END)
            stop = Gtk.Button(label=_('Stop'))
            stop.add_css_class('sz-job-stop')
            stop.connect('clicked', lambda b, d=dlg: d.job.cancel())
            show = Gtk.Button()
            show.add_css_class('sz-job-show')
            shb = hbox(6)
            shb.append(Gtk.Image.new_from_icon_name('window-new-symbolic'))
            shb.append(lbl(_('Show window')))
            show.set_child(shb)
            show.connect('clicked', lambda b, d=dlg: self._show_job(d))
            btns.append(stop)
            btns.append(show)
            for w in (action_l, title, file_l, bar, info, size, speed, files, btns):
                box.append(w)
            sections.append(dict(dlg=dlg, action=action_l, title=title, file=file_l,
                                 bar=bar, pct=pct, eta=eta, size=size, speed=speed,
                                 files=files, stop=stop, show=show))
        pop.set_child(box)
        pop.set_parent(self.job_btn)
        pop.connect('closed', self._on_job_popup_closed)
        self._job_popup = dict(pop=pop, sections=sections)
        self._update_job_popup()
        pop.popup()

    def _on_job_popup_closed(self, pop):
        if self._job_popup is not None and self._job_popup['pop'] is pop:
            self._job_popup = None
        if pop.get_parent() is not None:
            pop.unparent()

    def _close_job_popup(self):
        item, self._job_popup = self._job_popup, None
        if item is None:
            return
        pop = item['pop']
        if pop.get_visible():
            pop.popdown()
        if pop.get_parent() is not None:
            pop.unparent()

    def _show_job(self, dlg):
        self._close_job_popup()
        dlg.show_full()

    def _update_job_popup(self):
        item = self._job_popup
        if item is None:
            return
        for sec in item['sections']:
            dlg = sec['dlg']
            snap = dlg.progress_snapshot()
            if not snap['alive']:
                continue
            action = _job_action_text(snap['action'])
            if action:
                sec['action'].set_text(_('Operation') + ': ' + action)
                sec['action'].set_visible(True)
                sec['title'].set_visible(False)
            else:
                sec['action'].set_visible(False)
                sec['title'].set_text(snap['title'])
                sec['title'].set_visible(True)
            sec['file'].set_text(snap['text'] or snap['sub'])
            f = snap['fraction']
            if f is None:
                sec['bar'].pulse()
            else:
                sec['bar'].set_fraction(max(0.0, min(1.0, f)))
            pct = _('Paused') if snap['paused'] else snap['pct']
            sec['pct'].set_text(pct or '')
            sec['eta'].set_text('' if snap['paused'] else snap['eta'])
            for key, label, text in (
                    ('size', sec['size'], snap['bytes']),
                    ('speed', sec['speed'], snap['speed']),
                    ('files', sec['files'], snap['files'])):
                label.set_visible(bool(text))
                if key == 'size':
                    label.set_text(_('Size') + ': ' + text)
                elif key == 'speed':
                    label.set_text(_('Speed') + ': ' + text)
                else:
                    label.set_text(text)
            sec['stop'].set_sensitive(not snap['cancelled'])

    def _group_header(self, group_id):
        hidden = group_id in self.hidden
        row = hbox(6)
        row.add_css_class('sz-side-section-row')
        if hidden:
            row.add_css_class('sz-menu-hidden')
        label = lbl(_(SIDEBAR_LABELS[group_id]))
        label.add_css_class('sz-section')
        label.add_css_class('sz-side-group-label')
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        handle = Gtk.DrawingArea()
        handle.set_content_width(16)
        handle.set_content_height(16)
        handle.add_css_class('sz-menu-handle')
        handle.add_css_class('sz-side-handle')
        handle.set_draw_func(_fav_sort_icon)
        handle.set_tooltip_text(_('Drag to reorder'))
        handle.update_property([Gtk.AccessibleProperty.LABEL], [_('Drag to reorder')])
        handle.set_cursor(Gdk.Cursor.new_from_name('grab'))
        drag = Gtk.GestureDrag()
        drag.connect('drag-begin', self._group_drag_begin, group_id)
        drag.connect('drag-update', self._group_drag_update, group_id)
        drag.connect('drag-end', self._group_drag_end, group_id)
        handle.add_controller(drag)
        eye = Gtk.Button()
        eye.add_css_class('sz-menu-eye')
        eye.add_css_class('sz-side-eye')
        eye.set_child(_drawing(16, 16, _menu_eye_closed if hidden else _menu_eye_open,
                               'sz-menu-eye-icon'))
        eye.set_tooltip_text(_('Show') if hidden else _('Hide'))
        eye.update_property([Gtk.AccessibleProperty.LABEL], [eye.get_tooltip_text()])
        eye.connect('clicked', lambda b, g=group_id: self._toggle_group(g))
        row.append(label)
        row.append(handle)
        row.append(eye)
        self.group_rows.append({'id': group_id, 'row': row, 'eye': eye})
        self.inner.append(row)

    def _group_drag_begin(self, gesture, start_x, start_y, group_id):
        self.group_drag_id = group_id
        self.group_drop = None
        for r in self.group_rows:
            if r['id'] == group_id:
                r['row'].add_css_class('sz-menu-dragging')

    def _group_drag_update(self, gesture, offset_x, offset_y, group_id):
        for r in self.group_rows:
            r['row'].remove_css_class('sz-menu-drop')
        self.group_drop = None
        if Graphene is None:
            return
        ok, sx, sy = gesture.get_start_point()
        if not ok:
            return
        ok, pt = gesture.get_widget().compute_point(
            self.inner, Graphene.Point().init(sx + offset_x, sy + offset_y))
        if not ok:
            return
        rows = self.group_rows
        for index, r in enumerate(rows):
            alloc = r['row'].get_allocation()
            bottom = (rows[index + 1]['row'].get_allocation().y
                      if index + 1 < len(rows) else self.inner.get_height())
            if alloc.y <= pt.y < bottom and r['id'] != group_id:
                r['row'].add_css_class('sz-menu-drop')
                self.group_drop = (r['id'], pt.y > alloc.y + alloc.height / 2)
                break

    def _group_drag_end(self, gesture, offset_x, offset_y, group_id):
        for r in self.group_rows:
            r['row'].remove_css_class('sz-menu-dragging')
            r['row'].remove_css_class('sz-menu-drop')
        drop, self.group_drop, self.group_drag_id = self.group_drop, None, None
        if drop:
            self._move_group(group_id, drop[0], drop[1])

    def _move_group(self, src_id, dst_id, after):
        if src_id == dst_id:
            return
        order = list(self.group_order)
        if src_id not in order or dst_id not in order:
            return
        order.remove(src_id)
        order.insert(order.index(dst_id) + (1 if after else 0), src_id)
        self.group_order = order
        self._save_groups()
        self.rebuild()

    def _toggle_group(self, group_id):
        if group_id in self.hidden:
            self.hidden.discard(group_id)
        else:
            self.hidden.add(group_id)
        self._save_groups()
        self.rebuild()

    def _save_groups(self):
        self.win.conf['sidebar_groups'] = list(self.group_order)
        self.win.conf['sidebar_hidden'] = [group_id for group_id in self.group_order
                                           if group_id in self.hidden]
        self.win.conf.save()
        app = self.win.get_application()
        for w in (getattr(app, 'wins', None) or []):
            sb = getattr(w, 'sidebar', None)
            if sb is not None and sb is not self:
                sb.sync_groups()

    def _place_row(self, place_id, icon, label, path):
        hidden = place_id in self.place_hidden
        row = hbox(6)
        row.add_css_class('sz-menu-item')
        row.add_css_class('sz-menu-row')
        row.add_css_class('sz-side-edit-row')
        row.add_css_class('sz-side-place-row')
        if hidden:
            row.add_css_class('sz-menu-hidden')
        img = Gtk.Image.new_from_icon_name(icon)
        img.set_pixel_size(16)
        row.append(img)
        text = lbl(label)
        text.add_css_class('sz-side-group-label')
        text.set_hexpand(True)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        handle = Gtk.DrawingArea()
        handle.set_content_width(16)
        handle.set_content_height(16)
        handle.add_css_class('sz-menu-handle')
        handle.add_css_class('sz-side-handle')
        handle.set_draw_func(_fav_sort_icon)
        handle.set_tooltip_text(_('Drag to reorder'))
        handle.update_property([Gtk.AccessibleProperty.LABEL], [_('Drag to reorder')])
        handle.set_cursor(Gdk.Cursor.new_from_name('grab'))
        drag = Gtk.GestureDrag()
        drag.connect('drag-begin', self._place_drag_begin, place_id)
        drag.connect('drag-update', self._place_drag_update, place_id)
        drag.connect('drag-end', self._place_drag_end, place_id)
        handle.add_controller(drag)
        eye = Gtk.Button()
        eye.add_css_class('sz-menu-eye')
        eye.add_css_class('sz-side-eye')
        eye.set_child(_drawing(16, 16, _menu_eye_closed if hidden else _menu_eye_open,
                               'sz-menu-eye-icon'))
        eye.set_tooltip_text(_('Show') if hidden else _('Hide'))
        eye.update_property([Gtk.AccessibleProperty.LABEL], [eye.get_tooltip_text()])
        eye.connect('clicked', lambda b, p=place_id: self._toggle_place(p))
        row.append(text)
        row.append(handle)
        row.append(eye)
        self.place_rows.append({'id': place_id, 'row': row, 'eye': eye})
        self.inner.append(row)

    def _place_drag_begin(self, gesture, start_x, start_y, place_id):
        self.place_drag_id = place_id
        self.place_drop = None
        for r in self.place_rows:
            if r['id'] == place_id:
                r['row'].add_css_class('sz-menu-dragging')

    def _place_drag_update(self, gesture, offset_x, offset_y, place_id):
        for r in self.place_rows:
            r['row'].remove_css_class('sz-menu-drop')
        self.place_drop = None
        if Graphene is None:
            return
        ok, sx, sy = gesture.get_start_point()
        if not ok:
            return
        ok, pt = gesture.get_widget().compute_point(
            self.inner, Graphene.Point().init(sx + offset_x, sy + offset_y))
        if not ok:
            return
        rows = self.place_rows
        for index, r in enumerate(rows):
            alloc = r['row'].get_allocation()
            bottom = (rows[index + 1]['row'].get_allocation().y
                      if index + 1 < len(rows) else self.inner.get_height())
            if alloc.y <= pt.y < bottom and r['id'] != place_id:
                r['row'].add_css_class('sz-menu-drop')
                self.place_drop = (r['id'], pt.y > alloc.y + alloc.height / 2)
                break

    def _place_drag_end(self, gesture, offset_x, offset_y, place_id):
        for r in self.place_rows:
            r['row'].remove_css_class('sz-menu-dragging')
            r['row'].remove_css_class('sz-menu-drop')
        drop, self.place_drop, self.place_drag_id = self.place_drop, None, None
        if drop:
            self._move_place(place_id, drop[0], drop[1])

    def _move_place(self, src_id, dst_id, after):
        if src_id == dst_id:
            return
        order = list(self.place_order)
        if src_id not in order or dst_id not in order:
            return
        order.remove(src_id)
        order.insert(order.index(dst_id) + (1 if after else 0), src_id)
        self.place_order = order
        self._save_places()
        self.rebuild()

    def _toggle_place(self, place_id):
        if place_id in self.place_hidden:
            self.place_hidden.discard(place_id)
        else:
            self.place_hidden.add(place_id)
        self._save_places()
        self.rebuild()

    def _save_places(self):
        self.win.conf['sidebar_places'] = list(self.place_order)
        self.win.conf['sidebar_hidden_places'] = [place_id for place_id in self.place_order
                                                  if place_id in self.place_hidden]
        self.win.conf.save()
        app = self.win.get_application()
        for w in (getattr(app, 'wins', None) or []):
            sb = getattr(w, 'sidebar', None)
            if sb is not None and sb is not self:
                sb.sync_groups()

    def sync_groups(self):
        self.group_order = groups(self.win.conf)
        self.hidden = hidden_groups(self.win.conf)
        self.place_order = place_order(self.win.conf)
        self.place_hidden = hidden_places(self.win.conf)
        self.rebuild()

    def _section(self, text):
        l = lbl(text)
        l.add_css_class('sz-section')
        self.inner.append(l)

    def _item(self, icon, text, path):
        b = Gtk.Button()
        b.add_css_class('flat')
        b.add_css_class('sz-side-item')
        b.set_focus_on_click(False)
        row = hbox(10)
        row.append(Gtk.Image.new_from_icon_name(icon))
        l = lbl(text)
        l.set_ellipsize(Pango.EllipsizeMode.END)
        row.append(l)
        b.set_child(row)
        b.connect('clicked', lambda x: self._go(path))
        self.items.append((os.path.normpath(path), b))
        self.inner.append(b)

    def _go(self, path):
        p = self.win.active
        p.navigate_text(path)
        p.focus_view()

    def _build_places(self):
        known = {place_id: (icon, label, path)
                 for place_id, icon, label, path in all_places()}
        for place_id in self.place_order:
            if place_id not in known:
                continue
            icon, label, path = known[place_id]
            if self.editing:
                self._place_row(place_id, icon, label, path)
            elif place_id not in self.place_hidden:
                self._item(icon, label, path)

    def _build_favorites(self):
        favs = self.win.conf['favorites']
        shown = False
        for k in sorted(favs, key=lambda x: int(x) if str(x).isdigit() else 99):
            p = fav_path(favs[k])
            if p:
                shown = True
                self._item('folder-symbolic', fav_name(favs[k]), p)
        if not shown:
            l = lbl(_('No favorites yet'))
            l.add_css_class('sz-muted')
            l.set_margin_start(10)
            self.inner.append(l)

    def _on_devices_changed(self, *a):
        if not self._alive or self._devices_id:
            return
        self._devices_id = GLib.timeout_add(150, self._refresh_devices)

    def _on_mount_removed(self, monitor, mount):
        # Диск размонтирован (в том числе извне) — уходим из его папки.
        self._leave_mount(mount)
        self._on_devices_changed()

    def _leave_mount(self, mount):
        path = self._mount_local_path(mount)
        if path:
            self._leave_path(path)
            return
        # точка монтирования могла исчезнуть раньше сигнала (телефон отключён)
        gvfs = self._gvfs_root()
        if not gvfs:
            return
        gvfs = os.path.normpath(gvfs)
        for panel in (self.win.p1, self.win.p2):
            if panel is None or panel.mode != 'fs':
                continue
            try:
                current = os.path.normpath(panel.path)
            except (TypeError, ValueError):
                continue
            if (current.startswith(gvfs + os.sep)
                    and not os.path.isdir(current)):
                self._leave_path(current)

    def _leave_path(self, mount_path):
        """Перейти из папки размонтированного диска в его родительскую папку."""
        try:
            base = os.path.normpath(mount_path)
        except (TypeError, ValueError):
            return
        if not base or base == os.sep:
            return
        home = os.path.normpath(os.path.expanduser('~'))
        gvfs = self._gvfs_root()
        if gvfs and (base == os.path.normpath(gvfs) or
                     base.startswith(os.path.normpath(gvfs) + os.sep)):
            # из служебного каталога GVfs уходим домой, а не в пустой gvfs
            dest = home
        else:
            dest = os.path.dirname(base) or home
        if not os.path.isdir(dest) or os.path.normpath(dest) == base:
            dest = home
        if not os.path.isdir(dest):
            dest = os.sep
        for panel in (self.win.p1, self.win.p2):
            if panel is None or panel.mode != 'fs':
                continue
            try:
                current = os.path.normpath(panel.path)
            except (TypeError, ValueError):
                continue
            if current == base or current.startswith(base + os.sep):
                panel.navigate_fs(dest)

    def _refresh_devices(self):
        self._devices_id = 0
        if self._alive:
            self.rebuild()
        return False

    def disconnect_monitor(self):
        """Отписаться от VolumeMonitor при закрытии окна."""
        self._alive = False
        if self._job_timer:
            GLib.source_remove(self._job_timer)
            self._job_timer = 0
        self._close_job_popup()
        self.job_dialogs = []
        if self._devices_id:
            GLib.source_remove(self._devices_id)
            self._devices_id = 0
        monitor, ids = self._monitor, self._monitor_ids
        self._monitor_ids = []
        if monitor is None:
            return
        for handler_id in ids:
            try:
                monitor.disconnect(handler_id)
            except Exception:
                pass

    @staticmethod
    def _icon_name_from(obj):
        if obj is None:
            return None
        try:
            for attr in ('get_symbolic_icon', 'get_icon'):
                getter = getattr(obj, attr, None)
                if getter is None:
                    continue
                gicon = getter()
                if isinstance(gicon, Gio.ThemedIcon):
                    names = [name for name in gicon.get_names() if name]
                    if names:
                        return pick_icon(*names)
        except Exception:
            pass
        return None

    def _gvfs_root(self):
        runtime = GLib.get_user_runtime_dir()
        return os.path.join(runtime, 'gvfs') if runtime else None

    def _gvfs_names(self):
        root = self._gvfs_root()
        if not root:
            return set()
        try:
            return {name for name in os.listdir(root)
                    if os.path.isdir(os.path.join(root, name))}
        except OSError:
            return set()

    @staticmethod
    def _uri_scheme(uri):
        if not uri:
            return ''
        try:
            return (Gio.File.new_for_uri(uri).get_uri_scheme() or '').lower()
        except Exception:
            return uri.split(':', 1)[0].lower() if ':' in uri else ''

    @staticmethod
    def _volume_uri(volume):
        if volume is None:
            return None
        try:
            root = volume.get_activation_root()
            return root.get_uri() if root is not None else None
        except Exception:
            return None

    def _is_phone_volume(self, volume):
        return self._uri_scheme(self._volume_uri(volume)) in PHONE_SCHEMES

    def _mount_root_uri(self, mount):
        try:
            root = mount.get_root()
            return root.get_uri() if root is not None else None
        except Exception:
            return None

    def _volume_for_mount(self, mount):
        """Том, соответствующий точке монтирования (у GVfs он может не отдаваться)."""
        try:
            volume = mount.get_volume()
            if volume is not None:
                return volume
        except Exception:
            pass
        uri = self._mount_root_uri(mount)
        if not uri or self._monitor is None:
            return None
        try:
            for volume in self._monitor.get_volumes():
                try:
                    if volume.get_mount() is mount:
                        return volume
                except Exception:
                    pass
                if self._volume_uri(volume) == uri:
                    return volume
        except Exception:
            pass
        return None

    def _is_phone_mount(self, mount):
        if self._is_phone_volume(self._volume_for_mount(mount)):
            return True
        return self._uri_scheme(self._mount_root_uri(mount)) in PHONE_SCHEMES

    def _is_network_volume(self, volume):
        return self._uri_scheme(self._volume_uri(volume)) in NETWORK_SCHEMES

    def _is_network_mount(self, mount):
        if self._is_network_volume(self._volume_for_mount(mount)):
            return True
        return self._uri_scheme(self._mount_root_uri(mount)) in NETWORK_SCHEMES

    @staticmethod
    def _gvfs_prefixes(scheme):
        if not scheme:
            return ()
        return GVFS_PREFIXES.get(scheme, (scheme + ':',))

    @staticmethod
    def _uri_parts(uri):
        """(host, share, user) из URI. urlparse не годится: MTP-хост в скобках."""
        if not uri or '://' not in uri:
            return '', '', ''
        rest = uri.split('://', 1)[1]
        authority, _, path = rest.partition('/')
        user = ''
        if '@' in authority:
            user, authority = authority.rsplit('@', 1)
        host = authority
        if authority.startswith('['):
            end = authority.find(']')
            if end > 0:
                host = authority[1:end]
        elif ':' in authority:
            host = authority.split(':', 1)[0]
        share = path.split('?', 1)[0].split('#', 1)[0].split('/', 1)[0]
        return unquote(host), unquote(share), unquote(user)

    @staticmethod
    def _uri_port(uri):
        if not uri or '://' not in uri:
            return ''
        authority = uri.split('://', 1)[1].split('/', 1)[0]
        if '@' in authority:
            authority = authority.rsplit('@', 1)[1]
        if authority.startswith('['):
            end = authority.find(']')
            rest = authority[end + 1:] if end > 0 else ''
            return rest[1:] if rest.startswith(':') else ''
        return authority.split(':', 1)[1] if ':' in authority else ''

    @staticmethod
    def _looks_like_mount_spec(name):
        """Служебное имя вида mtp/sftp/host=… вместо человеческого названия."""
        if not name:
            return True
        low = name.lower()
        return ('://' in name or 'host=' in low or low in REMOTE_SCHEMES or
                any(low.startswith(scheme + ':') for scheme in REMOTE_SCHEMES))

    def _network_uri_label(self, uri):
        scheme = self._uri_scheme(uri)
        if scheme not in NETWORK_SCHEMES:
            return None
        host, share, user = self._uri_parts(uri)
        if not host:
            return None
        if scheme == 'smb':
            return _('{0} on {1}').format(share, host) if share else host
        if scheme in ('sftp', 'ftp'):
            label = '{0}@{1}'.format(user, host) if user else host
            port = self._uri_port(uri)
            return label + (':' + port if port else '')
        if scheme in ('dav', 'davs'):
            return '{0}/{1}'.format(host, share) if share else host
        if scheme in ('nfs', 'afp') and share:
            return _('{0} on {1}').format(share, host)
        return host

    def _network_label(self, mount, volume=None):
        """Понятное имя сетевой точки монтирования для панели и заголовка."""
        if volume is None:
            volume = self._volume_for_mount(mount)
        candidates = []
        if volume is not None:
            try:
                candidates.append(volume.get_name())
            except Exception:
                pass
        try:
            candidates.append(mount.get_name())
        except Exception:
            pass
        for name in candidates:
            if name and not self._looks_like_mount_spec(name):
                return name
        label = self._network_uri_label(self._mount_root_uri(mount))
        return (label or next((name for name in candidates if name), None)
                or _('Network server'))

    def _gvfs_path_for_uri(self, uri):
        """Каталог gvfs-fuse для телефона/камеры или сетевого подключения."""
        root = self._gvfs_root()
        scheme = self._uri_scheme(uri)
        if not root or scheme not in REMOTE_SCHEMES:
            return None
        prefixes = self._gvfs_prefixes(scheme)
        try:
            names = [name for name in os.listdir(root)
                     if name.startswith(prefixes) and
                     os.path.isdir(os.path.join(root, name))]
        except OSError:
            return None
        if not names:
            return None
        host, share, user = self._uri_parts(uri)
        if scheme == 'smb':
            # Для ресурса и для обзора сервера GVfs использует разные префиксы:
            # smb-share:server=…,share=… и smb:server=…. Не подменяем корень
            # сервера первым попавшимся ресурсом.
            prefer = 'smb-share:' if share else 'smb:'
            names = [name for name in names if name.startswith(prefer)]
            if not names:
                return None
        tokens = [host] if host else []
        if scheme != 'smb' and user and not (scheme == 'ftp' and user == 'anonymous'):
            tokens.append(user)
        if scheme in ('smb', 'nfs', 'afp') and share:
            tokens.append(share)
        if scheme in ('dav', 'davs') and share:
            tokens.append(share)
        port = self._uri_port(uri)
        if port:
            tokens.append(port)
        if tokens:
            matched = [name for name in names
                       if all(token.lower() in unquote(name).lower()
                              for token in tokens)]
            if not matched and len(tokens) > 1:
                # хост есть в имени, а пользователь/ресурс может не попасть
                matched = [name for name in names
                           if host.lower() in unquote(name).lower()]
            if matched:
                names = matched
        if not names:
            return None
        return os.path.join(root, sorted(names)[0])

    def _mount_relative(self, uri, mount):
        """Путь внутри точки монтирования: smb://host/share/sub → sub."""
        root = self._mount_root_uri(mount)
        if not root:
            return ''
        base = root.rstrip('/')
        want = uri.rstrip('/')
        if want.lower() == base.lower():
            return ''
        if not want.lower().startswith(base.lower() + '/'):
            return ''
        return '/'.join(unquote(part) for part in want[len(base) + 1:].split('/')
                        if part)

    def _mount_local_path(self, mount, before=None):
        """Локальный путь точки монтирования (для GVfs — каталог gvfs-fuse)."""
        root = None
        try:
            root = mount.get_root()
        except Exception:
            pass
        path = None
        if root is not None:
            try:
                path = root.get_path()
            except Exception:
                path = None
        if path:
            return path
        uri = None
        if root is not None:
            try:
                uri = root.get_uri()
            except Exception:
                pass
        path = self._gvfs_path_for_uri(uri)
        if path:
            return path
        if before is not None:
            root_dir = self._gvfs_root()
            if not root_dir:
                return None
            scheme = self._uri_scheme(uri)
            prefixes = self._gvfs_prefixes(scheme)
            new = sorted(self._gvfs_names() - set(before))
            preferred = [name for name in new
                         if prefixes and name.startswith(prefixes)]
            for name in preferred + [name for name in new if name not in preferred]:
                candidate = os.path.join(root_dir, name)
                if os.path.isdir(candidate):
                    return candidate
        return None

    def device_label(self, path):
        """Название устройства/сетевого ресурса для заголовка панели на точке GVfs."""
        try:
            norm = os.path.normpath(path)
        except (TypeError, ValueError):
            return None
        gvfs = self._gvfs_root()
        if not gvfs or self._monitor is None:
            return None
        gvfs = os.path.normpath(gvfs)
        if not (norm == gvfs or norm.startswith(gvfs + os.sep)):
            return None
        try:
            for mount in self._monitor.get_mounts():
                if self._mount_local_path(mount) != norm:
                    continue
                volume = self._volume_for_mount(mount)
                if self._is_network_mount(mount):
                    return self._network_label(mount, volume)
                name = (volume.get_name() if volume is not None
                        and volume.get_name() else mount.get_name())
                return name or None
        except Exception:
            pass
        return None

    def _device_icon(self, volume=None, mount=None):
        if (self._is_network_volume(volume) or
                (mount is not None and self._is_network_mount(mount))):
            return pick_icon('network-server-symbolic', 'network-workgroup-symbolic',
                             'folder-remote-symbolic', 'network-wired-symbolic')
        drive = volume.get_drive() if volume is not None else None
        if drive is None and mount is not None:
            drive = mount.get_drive()
        for obj in (volume, mount, drive):
            name = self._icon_name_from(obj)
            if name:
                return name
        return pick_icon('media-removable-symbolic', 'drive-removable-media-symbolic',
                         'drive-harddisk-symbolic')

    def _mount_ejectable(self, mount):
        try:
            if self._is_phone_mount(mount):
                # у телефона всегда показываем кнопку отключения
                return True
            if self._is_network_mount(mount):
                # у сетевого ресурса — кнопку отключения
                return True
            if mount.can_eject():
                return True
            volume = self._volume_for_mount(mount)
            if volume is not None and volume.can_eject():
                return True
            drive = mount.get_drive()
            if drive is not None:
                if drive.can_eject():
                    return True
                if drive.is_media_removable() and mount.can_unmount():
                    return True
        except Exception:
            pass
        return False

    def _device_row(self, icon, text, path, mount=None, volume=None):
        row = hbox(0)
        row.add_css_class('sz-side-device-row')
        button = Gtk.Button()
        button.add_css_class('flat')
        button.add_css_class('sz-side-item')
        button.add_css_class('sz-side-bar')
        button.set_focus_on_click(False)
        button.set_hexpand(True)
        content = hbox(10)
        content.append(Gtk.Image.new_from_icon_name(icon))
        label = lbl(text)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        content.append(label)
        button.set_child(content)
        phone = volume is not None and self._is_phone_volume(volume)
        if volume is not None and mount is None:
            button.add_css_class('sz-side-unmounted')
            button.set_tooltip_text(_('Click to connect phone') if phone
                                    else _('Click to mount'))
            button.connect('clicked', lambda x, v=volume: self._mount_volume(v))
        else:
            button.connect('clicked', lambda x, p=path: self._go(p))
        row.append(button)
        if mount is not None and self._mount_ejectable(mount):
            phone = self._is_phone_mount(mount)
            network = self._is_network_mount(mount)
            if phone:
                eject_text = _('Disconnect phone')
                eject_icon = pick_icon('media-eject-symbolic', 'media-eject',
                                       'eject-symbolic')
            elif network:
                eject_text = _('Disconnect')
                eject_icon = pick_icon('network-offline-symbolic',
                                       'network-error-symbolic',
                                       'window-close-symbolic')
            else:
                eject_text = _('Eject')
                eject_icon = pick_icon('media-eject-symbolic', 'media-eject',
                                       'eject-symbolic')
            eject = Gtk.Button.new_from_icon_name(eject_icon)
            eject.add_css_class('flat')
            eject.add_css_class('sz-side-eject')
            eject.set_focus_on_click(False)
            eject.set_tooltip_text(eject_text)
            eject.update_property([Gtk.AccessibleProperty.LABEL], [eject_text])
            eject.connect('clicked', lambda x, m=mount: self._eject_mount(m))
            row.append(eject)
        if path:
            self.items.append((os.path.normpath(path), row))
        self.inner.append(row)

    def _mount_volume(self, volume):
        phone = self._is_phone_volume(volume)
        op = Gtk.MountOperation(parent=self.win)
        if self.win.active is not None:
            self.win.active.set_message(_('Connecting phone…') if phone
                                        else _('Mounting disk…'))
        before = self._gvfs_names()

        def done(src, res):
            try:
                src.mount_finish(res)
            except GLib.Error as e:
                if e.code != Gio.IOErrorEnum.ALREADY_MOUNTED:
                    alert(self.win, _('Cannot connect phone') if phone
                          else _('Cannot mount disk'), e.message)
                    if self.win.active is not None:
                        self.win.active.update_status()
                    return
            except Exception:
                if self.win.active is not None:
                    self.win.active.update_status()
                return
            if not self._alive:
                return
            mount = src.get_mount()
            if mount is None:
                self.rebuild()
                if self.win.active is not None:
                    self.win.active.update_status()
                return
            self._open_mounted(mount, before, 'phone' if phone else 'disk')

        try:
            volume.mount(Gio.MountMountFlags.NONE, op, None, done)
        except Exception as e:
            alert(self.win, _('Cannot connect phone') if phone
                  else _('Cannot mount disk'), str(e))
            if self.win.active is not None:
                self.win.active.update_status()

    def _open_mounted(self, mount, before, kind='disk', attempt=0, progress=False):
        """Дождаться появления точки монтирования и открыть её."""
        if not self._alive:
            return
        path = self._mount_local_path(mount, before)
        note = {'phone': _('Phone connected'),
                'network': _('Server connected')}.get(kind)
        if path:
            self.rebuild()
            self._go(path)
            if progress:
                self.win.end_status_progress(note)
            elif note:
                self.win.show_status_note(note)
            return
        limit = 30 if kind == 'network' else 20
        if attempt < limit:
            def retry():
                self._open_mounted(mount, before, kind, attempt + 1, progress)
                return False
            GLib.timeout_add(100, retry)
            return
        self.rebuild()
        if progress:
            self.win.end_status_progress()
        elif self.win.active is not None:
            self.win.active.update_status()
        if kind == 'phone':
            alert(self.win, _('Cannot connect phone'),
                  _('The phone was connected, but its folder could not be opened.'))
        elif kind == 'network':
            alert(self.win, _('Cannot connect to server'),
                  _('The server was connected, but its folder could not be opened.'))
        else:
            alert(self.win, _('Disk mounted'),
                  _('The disk was mounted, but its folder could not be opened.'))

    def _eject_mount(self, mount):
        phone = self._is_phone_mount(mount)
        network = self._is_network_mount(mount)
        target, eject = mount, False
        try:
            volume = self._volume_for_mount(mount)
            if phone:
                # телефон физически не извлекаем — отмонтируем его
                if not mount.can_unmount() and volume is not None and volume.can_eject():
                    target, eject = volume, True
            elif network:
                # сетевой ресурс только отключаем, без извлечения
                if not mount.can_unmount() and volume is not None and volume.can_eject():
                    target, eject = volume, True
            elif mount.can_eject():
                eject = True
            elif volume is not None and volume.can_eject():
                target, eject = volume, True
            else:
                drive = mount.get_drive()
                if drive is not None and drive.can_eject():
                    target, eject = drive, True
        except Exception:
            pass
        mount_path = self._mount_local_path(mount)
        op = Gtk.MountOperation(parent=self.win)
        if phone:
            progress_text = _('Disconnecting phone…')
            success_text = _('Phone disconnected')
            error_text = _('Cannot disconnect phone')
        elif network:
            progress_text = _('Disconnecting…')
            success_text = _('Disconnected from server')
            error_text = _('Cannot disconnect from server')
        else:
            progress_text = _('Ejecting disk…')
            success_text = _('Ejected successfully')
            error_text = _('Cannot eject disk')
        self.win.begin_status_progress(progress_text)

        def done(src, res):
            try:
                if eject:
                    src.eject_with_operation_finish(res)
                else:
                    src.unmount_with_operation_finish(res)
            except GLib.Error as e:
                if not self._alive:
                    return
                self.win.end_status_progress()
                if e.code not in (Gio.IOErrorEnum.NOT_MOUNTED, Gio.IOErrorEnum.NOT_FOUND):
                    alert(self.win, error_text, e.message)
                return
            except Exception:
                if self._alive:
                    self.win.end_status_progress()
                return
            if not self._alive:
                return
            if mount_path:
                self._leave_path(mount_path)
            self.rebuild()
            self.win.end_status_progress(success_text)

        try:
            if eject:
                target.eject_with_operation(Gio.MountUnmountFlags.NONE, op, None, done)
            else:
                target.unmount_with_operation(Gio.MountUnmountFlags.NONE, op, None, done)
        except Exception as e:
            self.win.end_status_progress()
            alert(self.win, error_text, str(e))

    def _build_devices(self):
        self._item('drive-harddisk-symbolic', _('File system'), '/')
        monitor = self._monitor
        if monitor is not None:
            mounted_paths = set()
            try:
                for mount in monitor.get_mounts():
                    path = self._mount_local_path(mount)
                    if not path or path == '/' or not os.path.isdir(path):
                        continue
                    path = os.path.normpath(path)
                    if path in mounted_paths:
                        continue
                    mounted_paths.add(path)
                    volume = self._volume_for_mount(mount)
                    if self._is_network_mount(mount):
                        name = self._network_label(mount, volume)
                    else:
                        name = (volume.get_name() if volume is not None
                                and volume.get_name() else mount.get_name())
                    self._device_row(self._device_icon(volume=volume, mount=mount), name,
                                     path, mount=mount, volume=volume)
            except Exception:
                pass
            try:
                for volume in monitor.get_volumes():
                    if volume.get_mount() is not None:
                        continue
                    drive = volume.get_drive()
                    if (drive is not None and not drive.has_media()
                            and not self._is_phone_volume(volume)):
                        continue
                    if not volume.can_mount():
                        continue
                    name = volume.get_name()
                    if not name:
                        continue
                    self._device_row(self._device_icon(volume=volume), name, None,
                                     volume=volume)
            except Exception:
                pass
        self._connect_row()

    def _connect_row(self):
        """Пункт «Подключиться к серверу…» в разделе устройств."""
        button = Gtk.Button()
        button.add_css_class('flat')
        button.add_css_class('sz-side-item')
        button.add_css_class('sz-side-connect')
        button.set_focus_on_click(False)
        row = hbox(10)
        row.append(Gtk.Image.new_from_icon_name(
            pick_icon('network-server-symbolic', 'network-workgroup-symbolic',
                      'folder-remote-symbolic')))
        row.append(lbl(_('Connect to server…')))
        button.set_child(row)
        button.set_tooltip_text(_('Connect to server…'))
        button.connect('clicked', lambda x: self._network_dialog())
        self.inner.append(button)

    @staticmethod
    def _network_uri(scheme, address):
        """Собрать URI подключения из протокола и введённого адреса."""
        address = (address or '').strip()
        if not address:
            return None
        if '://' in address:
            prefix, rest = address.split('://', 1)
            if prefix.lower() in ('http', 'https'):
                uri = ('davs://' if prefix.lower() == 'https' else 'dav://') + rest
            else:
                uri = address
            # сервер без пути: добавляем '/', иначе GVfs может не найти точку
            if '/' not in uri.split('://', 1)[1].split('?', 1)[0]:
                uri += '/'
            return uri
        if scheme not in NETWORK_SCHEMES:
            return None
        rest = address.lstrip('/')
        if not rest:
            return None
        uri = '%s://%s' % (scheme, rest)
        if '/' not in rest.split('?', 1)[0]:
            uri += '/'
        return uri

    def _find_network_mount(self, uri):
        """Найти точку монтирования, соответствующую URI (если GVfs не отдал её)."""
        scheme = self._uri_scheme(uri)
        if scheme not in NETWORK_SCHEMES or self._monitor is None:
            return None
        want = uri.rstrip('/')
        host, share, user = self._uri_parts(uri)
        try:
            mounts = self._monitor.get_mounts()
        except Exception:
            return None
        for mount in mounts:
            root_uri = self._mount_root_uri(mount)
            if not root_uri:
                continue
            if root_uri.rstrip('/') == want:
                return mount
            root_scheme = self._uri_scheme(root_uri)
            if root_scheme != scheme and {root_scheme, scheme} != {'dav', 'davs'}:
                continue
            r_host, r_share, r_user = self._uri_parts(root_uri)
            if r_host != host:
                continue
            if scheme == 'smb' and r_share != share:
                continue
            if user and r_user != user:
                continue
            return mount
        return None

    def _connect_network(self, uri, anonymous=False):
        """Подключить сетевой ресурс через GVfs и открыть его папку."""
        scheme = self._uri_scheme(uri)
        if scheme not in NETWORK_SCHEMES:
            alert(self.win, _('Unsupported protocol'), uri)
            return
        try:
            gfile = Gio.File.new_for_uri(uri)
        except GLib.Error as e:
            alert(self.win, _('Invalid server address'), e.message)
            return
        op = Gtk.MountOperation(parent=self.win)
        if anonymous:
            op.set_anonymous(True)
        else:
            op.set_username(self._uri_parts(uri)[2] or GLib.get_user_name())

            def answer_anonymous(operation, message, default_user,
                                 default_domain, flags):
                # некоторые бэкенды (например, SMB) всё равно спрашивают
                # учётные данные — для анонимного входа отвечаем сразу
                operation.set_username('')
                operation.set_password('')
                operation.reply(Gio.MountOperationResult.HANDLED)
                return True

            op.connect('ask-password', answer_anonymous)
        self.win.begin_status_progress(_('Connecting to server…'))
        before = self._gvfs_names()

        def done(src, res):
            try:
                src.mount_enclosing_volume_finish(res)
            except GLib.Error as e:
                if not self._alive:
                    return
                if e.code != Gio.IOErrorEnum.ALREADY_MOUNTED:
                    self.win.end_status_progress()
                    alert(self.win, _('Cannot connect to server'), e.message)
                    return
            except Exception:
                if self._alive:
                    self.win.end_status_progress()
                return
            if not self._alive:
                return
            diagnostics.log('сеть: %s смонтирован, ищу точку монтирования', uri)
            resolve(0)

        def resolve(attempt):
            """Найти точку монтирования, иначе открыть URI напрямую через GIO."""
            if not self._alive:
                return False
            mount = self._find_network_mount(uri)
            path = None
            if mount is not None:
                path = self._mount_local_path(mount, before)
                rel = self._mount_relative(uri, mount) if path else ''
                if rel:
                    cand = os.path.join(path, rel)
                    if os.path.isdir(cand):
                        path = cand
            if path is None:
                path = self._gvfs_path_for_uri(uri)
                if path is None:
                    root = self._gvfs_root()
                    if root and before is not None:
                        prefs = self._gvfs_prefixes(scheme)
                        fresh = sorted(self._gvfs_names() - set(before))
                        for name in [n for n in fresh if n.startswith(prefs)] + fresh:
                            cand = os.path.join(root, name)
                            if os.path.isdir(cand):
                                path = cand
                                break
            if path and os.path.isdir(path):
                diagnostics.log('сеть: открываю каталог %s с попытки %d',
                                path, attempt + 1)
                self.rebuild()
                self._go(path)
                self.win.end_status_progress(_('Server connected'))
                return False
            # Для серверов SMB GVfs часто не создаёт ни GMount, ни каталог
            # в gvfs-fuse (например, smb://host/). Nautilus читает такой
            # каталог прямо через GIO — так же поступаем и мы.
            if vfs.is_dir(uri):
                diagnostics.log('сеть: %s открываю напрямую через GIO', uri)
                self.rebuild()
                self._go(uri)
                self.win.end_status_progress(_('Server connected'))
                return False
            if attempt < 30:
                GLib.timeout_add(100, lambda: resolve(attempt + 1))
                return False
            diagnostics.log('сеть: не удалось открыть %s', uri)
            self.win.end_status_progress()
            self.rebuild()
            alert(self.win, _('Cannot connect to server'),
                  _('The server was connected, but its folder could not be opened.'))
            return False

        try:
            gfile.mount_enclosing_volume(Gio.MountMountFlags.NONE, op, None, done)
        except Exception as e:
            self.win.end_status_progress()
            alert(self.win, _('Cannot connect to server'), str(e))

    def _network_dialog(self):
        """Диалог подключения к сетевому серверу."""
        last = self.win.conf.get('network_last') or {}
        schemes = [scheme for scheme, _label in NETWORK_PROTOCOLS]
        last_scheme = last.get('scheme')
        selected = schemes.index(last_scheme) if last_scheme in schemes else 0
        address = last.get('address', '') if last_scheme in schemes else ''
        dlg = new_dialog(self.win, _('Connect to server'), 520, 0)
        root = vbox(10, 16)
        dlg.set_child(root)
        grid = Gtk.Grid(row_spacing=8, column_spacing=10)
        root.append(grid)
        dd = make_dd([label for _scheme, label in NETWORK_PROTOCOLS], selected)
        grid_row(grid, 0, _('Protocol:'), dd)
        entry = Gtk.Entry(hexpand=True, text=address, activates_default=True)
        entry.set_size_request(360, -1)
        entry.set_placeholder_text(_('server/share or user@server'))
        grid_row(grid, 1, _('Server address:'), entry)
        hint = lbl(_('For example: server/share, user@server, server:2222'))
        hint.add_css_class('sz-muted')
        root.append(hint)
        anon = Gtk.CheckButton(label=_('Anonymous'))
        anon.set_active(bool(last.get('anonymous')))
        anon.set_tooltip_text(_('Use anonymous access if the server allows it'))
        root.append(anon)

        def connect():
            scheme = NETWORK_PROTOCOLS[max(0, dd.get_selected())][0]
            address_text = entry.get_text().strip()
            uri = self._network_uri(scheme, address_text)
            if not uri:
                alert(dlg, _('Enter server address'))
                return
            if self._uri_scheme(uri) not in NETWORK_SCHEMES:
                alert(dlg, _('Unsupported protocol'), uri)
                return
            try:
                Gio.File.new_for_uri(uri)
            except GLib.Error as e:
                alert(dlg, _('Invalid server address'), e.message)
                return
            self.win.conf['network_last'] = {'scheme': scheme,
                                             'address': address_text,
                                             'anonymous': anon.get_active()}
            self.win.conf.save()
            dlg.close()
            self._connect_network(uri, anon.get_active())

        row, _ok = button_row(dlg, _('Connect'), connect)
        root.append(row)
        dlg.present()
        entry.grab_focus()

    def rebuild(self):
        adj = self.scroll.get_vadjustment()
        value = adj.get_value() if adj is not None else 0
        child = self.inner.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.inner.remove(child)
            child = nxt
        self.items = []
        self.group_rows = []
        self.place_rows = []
        builders = {'places': self._build_places,
                    'favorites': self._build_favorites,
                    'devices': self._build_devices}
        for group_id in self.group_order:
            hidden = group_id in self.hidden
            show_section = not hidden
            if show_section and not self.editing and group_id == 'places':
                show_section = any(place_id not in self.place_hidden
                                   for place_id, _icon, _label, _path in all_places())
            if self.editing:
                self._group_header(group_id)
            elif show_section:
                self._section(_(SIDEBAR_LABELS[group_id]))
            if not hidden:
                build = builders.get(group_id)
                if build is not None:
                    build()
        self.set_active(self.win.active.current_dir() if self.win.active is not None
                        and self.win.active.mode == 'fs' else None)
        if adj is not None:
            def restore():
                adj.set_value(min(value, max(0, adj.get_upper() - adj.get_page_size())))
                return False
            GLib.idle_add(restore)

    def set_active(self, path):
        norm = os.path.normpath(path) if path else None
        for p, b in self.items:
            (b.add_css_class if p == norm else b.remove_css_class)('sz-side-active')
