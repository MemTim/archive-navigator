# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from urllib.parse import unquote
from .i18n import _, N_
from . import diagnostics
from . import vfs
from .dialogs import (alert, button_row, confirm, grid_row, hbox, lbl,
                      make_dd, new_dialog, pick_icon, PromptDialog, vbox)
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

# Флаги (типы) групп боковой панели. Флаг решает, что группа показывает:
# места, избранное, устройства, сетевые диски или только перетащенные в неё
# элементы.
GROUP_TYPES = [
    ('places', N_('Places')),
    ('favorites', N_('Favorites')),
    ('devices', N_('Devices')),
    ('network', N_('Network drives')),
    ('custom', N_('Custom group')),
]
GROUP_TYPE_NAMES = dict(GROUP_TYPES)
GROUP_TYPE_TITLES = {
    'places': N_('PLACES'),
    'favorites': N_('FAVORITES'),
    'devices': N_('DEVICES'),
    'network': N_('NETWORK'),
    'custom': N_('GROUP'),
}
DEFAULT_GROUPS = [
    {'id': 'places', 'type': 'places', 'title': '', 'hidden': False},
    {'id': 'favorites', 'type': 'favorites', 'title': '', 'hidden': False},
    {'id': 'devices', 'type': 'devices', 'title': '', 'hidden': False},
    {'id': 'network', 'type': 'network', 'title': '', 'hidden': False},
]


def group_type(group):
    return group.get('type') if group.get('type') in GROUP_TYPE_NAMES else 'custom'


def group_title(group):
    """Подпись группы: пользовательская или по её флагу."""
    title = str(group.get('title') or '').strip()
    if title:
        return title
    return _(GROUP_TYPE_TITLES.get(group_type(group), N_('GROUP')))


def _normalize_group(item):
    if isinstance(item, str):
        gtype = item if item in GROUP_TYPE_NAMES else 'custom'
        return {'id': item, 'type': gtype, 'title': '', 'hidden': False}
    if not isinstance(item, dict):
        return None
    group_id = str(item.get('id') or '').strip()
    if not group_id:
        return None
    return {'id': group_id,
            'type': item.get('type') if item.get('type') in GROUP_TYPE_NAMES else 'custom',
            'title': str(item.get('title') or ''),
            'hidden': bool(item.get('hidden'))}


def sidebar_groups(conf):
    """Группы боковой панели с флагами и пользовательскими названиями."""
    raw = conf.get('sidebar_groups') or []
    legacy_hidden = set(conf.get('sidebar_hidden') or [])
    out, seen = [], set()
    for item in raw:
        group = _normalize_group(item)
        if group is None or group['id'] in seen:
            continue
        if group['id'] in legacy_hidden:
            group['hidden'] = True
        seen.add(group['id'])
        out.append(group)
    # Старые конфиги хранили только список идентификаторов, а новый формат —
    # словари с флагами. Дополняем стандартными группами только старый формат:
    # удалённые пользователем группы не должны возвращаться после перезапуска.
    if not any(isinstance(item, dict) for item in raw):
        for default in DEFAULT_GROUPS:
            if default['id'] in seen:
                continue
            group = dict(default)
            group['hidden'] = group['id'] in legacy_hidden
            out.append(group)
    return out


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


def place_groups(conf):
    """Какая группа содержит каждый пункт «Места»."""
    raw = conf.get('sidebar_place_groups') or {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if value}


def favorite_groups(conf):
    """Какая группа содержит каждое избранное (по пути)."""
    raw = conf.get('sidebar_fav_groups') or {}
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if value}


def favorite_order(conf):
    """Пользовательский порядок избранного."""
    raw = conf.get('sidebar_fav_order') or []
    out, seen = [], set()
    for path in raw:
        if path and path not in seen:
            out.append(path)
            seen.add(path)
    return out


def _saved_order(conf, key):
    """Сохранённый порядок строк боковой панели (устройств или сети)."""
    raw = conf.get(key) or []
    out, seen = [], set()
    for item in raw:
        item = str(item)
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def device_order(conf):
    return _saved_order(conf, 'sidebar_device_order')


def network_order(conf):
    return _saved_order(conf, 'sidebar_network_order')


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
        self.groups = sidebar_groups(win.conf)
        self.group_order = [group['id'] for group in self.groups]
        self.group_rows = []
        self.group_drag_id = None
        self.group_drop = None
        self.place_order = place_order(win.conf)
        self.place_hidden = hidden_places(win.conf)
        self.place_group = place_groups(win.conf)
        self.fav_order = favorite_order(win.conf)
        self.fav_group = favorite_groups(win.conf)
        self.device_order = device_order(win.conf)
        self.network_order = network_order(win.conf)
        self.place_rows = []
        self.fav_rows = []
        self.device_rows = []
        self.network_rows = []
        self.picked = None
        self.editing = False
        self._group_popup = None
        self._drag = None
        self._drop = None
        self._device_drag = None
        self._device_drop = None
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
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll = sw
        self.inner = vbox(2)
        self.inner.set_margin_start(8)
        self.inner.set_margin_end(8)
        sw.set_child(self.inner)
        self.append(sw)
        self.add_group_btn = Gtk.Button()
        self.add_group_btn.add_css_class('flat')
        self.add_group_btn.add_css_class('sz-side-add-group')
        add_row = hbox(8)
        add_row.append(Gtk.Image.new_from_icon_name('list-add-symbolic'))
        add_row.append(lbl(_('New group')))
        self.add_group_btn.set_child(add_row)
        self.add_group_btn.set_tooltip_text(_('New group'))
        self.add_group_btn.update_property([Gtk.AccessibleProperty.LABEL], [_('New group')])
        self.add_group_btn.connect('clicked', self._add_group)
        self.add_group_btn.set_hexpand(True)
        self.add_group_btn.set_visible(False)
        self.reset_group_btn = Gtk.Button()
        self.reset_group_btn.add_css_class('flat')
        self.reset_group_btn.add_css_class('sz-side-reset')
        self.reset_group_btn.set_child(Gtk.Image.new_from_icon_name(
            'edit-undo-symbolic'))
        self.reset_group_btn.set_tooltip_text(_('Reset groups'))
        self.reset_group_btn.update_property(
            [Gtk.AccessibleProperty.LABEL], [_('Reset groups')])
        self.reset_group_btn.connect('clicked', self._reset_groups_ask)
        self.reset_group_btn.set_visible(False)
        self.group_tools = hbox(6)
        self.group_tools.set_margin_start(8)
        self.group_tools.set_margin_end(8)
        self.group_tools.append(self.add_group_btn)
        self.group_tools.append(self.reset_group_btn)
        self.group_tools.set_visible(False)
        self.append(self.group_tools)
        card = hbox(8)
        card.add_css_class('sz-usercard')
        info = vbox(2)
        info.set_hexpand(True)
        name = GLib.get_real_name()
        if not name or name == 'Unknown':
            name = GLib.get_user_name()
        n = lbl(name)
        n.add_css_class('sz-hdr-role')
        n.set_ellipsize(Pango.EllipsizeMode.END)
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
        self.picked = None
        self.group_tools.set_visible(self.editing)
        self.add_group_btn.set_visible(self.editing)
        self.reset_group_btn.set_visible(self.editing)
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
            action_l.set_ellipsize(Pango.EllipsizeMode.END)
            action_l.set_max_width_chars(28)
            title = lbl('')
            title.add_css_class('sz-job-title')
            title.set_ellipsize(Pango.EllipsizeMode.END)
            title.set_max_width_chars(32)
            file_l = lbl('')
            file_l.add_css_class('sz-job-file')
            file_l.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            # Имя файла постоянно меняется; не даём ему растягивать карточку.
            file_l.set_width_chars(1)
            file_l.set_max_width_chars(1)
            file_l.set_hexpand(True)
            bar = Gtk.ProgressBar()
            bar.add_css_class('sz-job-bar')
            bar.set_show_text(False)
            info = hbox(10)
            pct = lbl('')
            pct.add_css_class('sz-job-info')
            pct.set_hexpand(True)
            eta = lbl('', xalign=1.0)
            eta.add_css_class('sz-job-info')
            eta.set_ellipsize(Pango.EllipsizeMode.END)
            eta.set_max_width_chars(18)
            info.append(pct)
            info.append(eta)
            size = lbl('')
            size.add_css_class('sz-job-info')
            size.set_ellipsize(Pango.EllipsizeMode.END)
            size.set_max_width_chars(34)
            speed = lbl('')
            speed.add_css_class('sz-job-info')
            speed.set_ellipsize(Pango.EllipsizeMode.END)
            speed.set_max_width_chars(24)
            files = lbl('')
            files.add_css_class('sz-job-info')
            files.set_ellipsize(Pango.EllipsizeMode.END)
            files.set_max_width_chars(40)
            btns = hbox(6)
            btns.set_halign(Gtk.Align.END)
            stop = Gtk.Button(label=_('Stop'))
            stop.add_css_class('sz-job-stop')
            stop.add_css_class('sz-danger')
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

    # ───────────── группы и плитки в режиме редактирования ─────────────
    def _find_group(self, group_id):
        for group in self.groups:
            if group['id'] == group_id:
                return group
        return None

    def _default_group_id(self, gtype):
        for group in self.groups:
            if group_type(group) == gtype:
                return group['id']
        return self.group_order[0] if self.group_order else None

    def _group_header(self, group):
        group_id = group['id']
        hidden = bool(group.get('hidden'))
        row = hbox(4)
        row.add_css_class('sz-side-section-row')
        row.add_css_class('sz-side-group-row')
        label = lbl(group_title(group))
        label.add_css_class('sz-section')
        label.add_css_class('sz-side-group-label')
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_tooltip_text(_('Double-click to rename the group'))
        click = Gtk.GestureClick()
        click.connect('pressed', lambda g, n, x, y, gr=group: self._group_label_pressed(g, n, gr))
        label.add_controller(click)
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
        more = Gtk.Button.new_from_icon_name('view-more-symbolic')
        more.add_css_class('flat')
        more.add_css_class('sz-menu-more')
        more.set_focus_on_click(False)
        more.set_tooltip_text(_('Edit group'))
        more.update_property([Gtk.AccessibleProperty.LABEL], [_('Edit group')])
        more.connect('clicked', lambda b, gr=group: self._group_menu(gr, b))
        row.append(label)
        row.append(handle)
        row.append(eye)
        row.append(more)
        self.group_rows.append({'id': group_id, 'row': row, 'eye': eye, 'group': group})
        self.inner.append(row)

    def _group_label_pressed(self, gesture, n_press, group):
        if n_press == 2:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self._rename_group(group)

    def _group_menu(self, group, button):
        if self._group_popup is not None:
            self._group_popup.popdown()
            self._group_popup = None
        pop = Gtk.Popover()
        pop.add_css_class('sz-menu')
        box = vbox(6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_size_request(240, -1)
        title = lbl(group_title(group))
        title.add_css_class('sz-menu-label')
        title.set_ellipsize(Pango.EllipsizeMode.END)
        box.append(title)
        rename = Gtk.Button(label=_('Rename group') + '…')
        rename.add_css_class('flat')
        rename.add_css_class('sz-menu-item')
        rename.set_halign(Gtk.Align.FILL)

        def do_rename(b):
            pop.popdown()
            self._rename_group(group)
        rename.connect('clicked', do_rename)
        box.append(rename)
        flag_row = hbox(8)
        flag_row.set_margin_top(4)
        flag_row.append(lbl(_('Group flag') + ':'))
        types = [gtype for gtype, _name in GROUP_TYPES]
        dd = make_dd([_(GROUP_TYPE_NAMES[gtype]) for gtype in types],
                     types.index(group_type(group)))
        dd.set_hexpand(True)
        dd.connect('notify::selected',
                   lambda d, pspec, ts=types, gid=group['id']:
                   self._set_group_type(gid, ts[d.get_selected()]))
        flag_row.append(dd)
        box.append(flag_row)
        delete = Gtk.Button(label=_('Delete group'))
        delete.add_css_class('flat')
        delete.add_css_class('sz-menu-item')
        delete.add_css_class('sz-danger')
        delete.set_halign(Gtk.Align.FILL)
        delete.set_margin_top(4)

        def do_delete(b):
            pop.popdown()
            self._delete_group(group['id'])
        delete.connect('clicked', do_delete)
        box.append(delete)
        pop.set_child(box)
        pop.set_parent(button)
        pop.connect('closed', self._on_group_popup_closed)
        self._group_popup = pop
        pop.popup()

    def _on_group_popup_closed(self, pop):
        if self._group_popup is pop:
            self._group_popup = None
        if pop.get_parent() is not None:
            pop.unparent()

    def _set_group_type(self, group_id, gtype):
        group = self._find_group(group_id)
        if group is None or group_type(group) == gtype:
            return
        if self._group_popup is not None:
            pop, self._group_popup = self._group_popup, None
            pop.popdown()
        group['type'] = gtype
        self._save_groups()
        self.rebuild()

    def _rename_group(self, group):
        group_id = group['id']
        default = str(group.get('title') or '') or group_title(group)

        def done(name):
            group = self._find_group(group_id)
            if group is None:
                return
            name = (name or '').strip()
            builtin = _(GROUP_TYPE_TITLES.get(group_type(group), N_('GROUP')))
            group['title'] = '' if not name or name == builtin else name
            self._save_groups()
            self.rebuild()
        PromptDialog(self.win, _('Rename group'), _('Name:'), default,
                     _('OK'), done).present()

    def _new_group(self, title=''):
        numbers = []
        for group in self.groups:
            tail = group['id'].rsplit('-', 1)[-1]
            if tail.isdigit():
                numbers.append(int(tail))
        number = max(numbers, default=0) + 1
        group_id = 'group-%d' % number
        if not title:
            title = _('Group {0}').format(number)
        self.groups.append({'id': group_id, 'type': 'custom',
                            'title': title, 'hidden': False})
        self.group_order = [group['id'] for group in self.groups]
        return group_id

    def _add_group(self, *a):
        def done(name):
            name = (name or '').strip()
            if not name:
                return
            self._new_group(name)
            self._save_groups()
            self.rebuild()
        PromptDialog(self.win, _('New group'), _('Name:'), _('New group'),
                     _('OK'), done).present()

    def _delete_group(self, group_id):
        group = self._find_group(group_id)
        if group is None or len(self.groups) <= 1:
            return
        rest = [g for g in self.groups if g['id'] != group_id]
        fallback = next((g['id'] for g in rest
                         if group_type(g) == group_type(group)), rest[0]['id'])
        for place_id, gid in list(self.place_group.items()):
            if gid == group_id:
                self.place_group[place_id] = fallback
        for path, gid in list(self.fav_group.items()):
            if gid == group_id:
                self.fav_group[path] = fallback
        self.groups = rest
        self.group_order = [g['id'] for g in rest]
        self._save_groups()
        self.rebuild()

    def _reset_groups_ask(self, *a):
        confirm(self.win, _('Reset sidebar groups?'),
                _('Custom groups will be removed and the standard groups restored.'),
                _('Reset'), self._reset_groups)

    def _reset_groups(self):
        self.groups = [dict(group) for group in DEFAULT_GROUPS]
        self.group_order = [group['id'] for group in self.groups]
        self.place_group = {}
        self.fav_group = {}
        self._save_groups()
        self._save_layout()
        self.rebuild()

    def _group_drag_begin(self, gesture, start_x, start_y, group_id):
        self.group_drag_id = group_id
        self.group_drop = None
        for r in self.group_rows:
            if r['id'] == group_id:
                r['row'].add_css_class('sz-menu-dragging')

    def _group_drag_update(self, gesture, offset_x, offset_y, group_id):
        self._clear_drop()
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
        if rows and pt.y < rows[0]['row'].get_allocation().y:
            first = rows[0]
            if first['id'] != group_id:
                self._mark_drop(first['row'], False)
                self.group_drop = (first['id'], False)
            return
        for index, r in enumerate(rows):
            alloc = r['row'].get_allocation()
            bottom = (rows[index + 1]['row'].get_allocation().y
                      if index + 1 < len(rows) else self.inner.get_height())
            if alloc.y <= pt.y < bottom and r['id'] != group_id:
                after = pt.y > alloc.y + alloc.height / 2
                self._mark_drop(r['row'], after)
                self.group_drop = (r['id'], after)
                break

    def _group_drag_end(self, gesture, offset_x, offset_y, group_id):
        for r in self.group_rows:
            r['row'].remove_css_class('sz-menu-dragging')
        self._clear_drop()
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
        by_id = {group['id']: group for group in self.groups}
        self.group_order = order
        self.groups = [by_id[group_id] for group_id in order if group_id in by_id]
        self._save_groups()
        self.rebuild()

    def _toggle_group(self, group_id):
        group = self._find_group(group_id)
        if group is None:
            return
        group['hidden'] = not group.get('hidden')
        self._save_groups()
        self.rebuild()

    def _save_groups(self):
        conf = self.win.conf
        conf['sidebar_groups'] = [dict(group) for group in self.groups]
        conf['sidebar_hidden'] = [group['id'] for group in self.groups
                                  if group.get('hidden')]
        conf.save()
        app = self.win.get_application()
        for w in (getattr(app, 'wins', None) or []):
            sb = getattr(w, 'sidebar', None)
            if sb is not None and sb is not self:
                sb.sync_groups()

    def _place_group_id(self, place_id):
        gid = self.place_group.get(place_id)
        return gid if gid in self.group_order else self._default_group_id('places')

    def _favorite_group_id(self, path):
        gid = self.fav_group.get(path)
        return gid if gid in self.group_order else self._default_group_id('favorites')

    def _favorite_entries(self):
        """Избранное в пользовательском порядке: [(путь, название)]."""
        conf = self.win.conf
        favs = conf.get('favorites') or {}
        pairs, seen = [], set()
        for key in sorted(favs, key=lambda x: int(x) if str(x).isdigit() else 99):
            path = fav_path(favs[key])
            if not path or path in seen:
                continue
            seen.add(path)
            pairs.append((path, fav_name(favs[key])))
        by_path = dict(pairs)
        ordered = [(path, by_path[path]) for path in self.fav_order if path in by_path]
        ordered += [(path, name) for path, name in pairs if path not in set(self.fav_order)]
        return ordered

    def _tile_row(self, kind, item_id, icon, label, path, group_id, hidden=False):
        row = hbox(4)
        row.add_css_class('sz-menu-item')
        row.add_css_class('sz-menu-row')
        row.add_css_class('sz-side-edit-row')
        row.add_css_class('sz-side-place-row')
        img = Gtk.Image.new_from_icon_name(icon)
        img.set_pixel_size(16)
        # Значок и текст отстоят друг от друга так же, как в обычной плитке;
        # справа ручка и глаз идут плотнее.
        body = hbox(10)
        body.set_hexpand(True)
        body.append(img)
        text = lbl(label)
        # Обычный размер и цвет, как у плитки вне режима правки.
        text.add_css_class('sz-side-name')
        text.set_hexpand(True)
        text.set_ellipsize(Pango.EllipsizeMode.END)
        body.append(text)
        row.append(body)
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
        drag.connect('drag-begin', self._tile_drag_begin, kind, item_id)
        drag.connect('drag-update', self._tile_drag_update, kind, item_id)
        drag.connect('drag-end', self._tile_drag_end, kind, item_id)
        handle.add_controller(drag)
        row.append(handle)
        eye = None
        if kind == 'place':
            eye = Gtk.Button()
            eye.add_css_class('sz-menu-eye')
            eye.add_css_class('sz-side-eye')
            eye.set_child(_drawing(16, 16, _menu_eye_closed if hidden else _menu_eye_open,
                                   'sz-menu-eye-icon'))
            eye.set_tooltip_text(_('Show') if hidden else _('Hide'))
            eye.update_property([Gtk.AccessibleProperty.LABEL], [eye.get_tooltip_text()])
            eye.connect('clicked', lambda b, p=item_id: self._toggle_place(p))
            row.append(eye)
        pick = Gtk.GestureClick()
        pick.connect('pressed', lambda g, n, x, y, k=kind, i=item_id:
                     self._pick_tile(k, i) if n == 1 else None)
        row.add_controller(pick)
        entry = {'id': item_id, 'kind': kind, 'group': group_id, 'row': row, 'eye': eye}
        (self.place_rows if kind == 'place' else self.fav_rows).append(entry)
        self.items.append((os.path.normpath(path), row))
        self.inner.append(row)
        if self.picked == (kind, item_id):
            row.add_css_class('sz-side-picked')

    def _place_row(self, place_id, icon, label, path, group_id):
        self._tile_row('place', place_id, icon, label, path, group_id,
                       hidden=place_id in self.place_hidden)

    def _fav_row(self, path, name, group_id):
        self._tile_row('fav', path, 'folder-symbolic', name, path, group_id)

    def _pick_tile(self, kind, item_id):
        self.picked = None if self.picked == (kind, item_id) else (kind, item_id)
        for entry in self.place_rows + self.fav_rows:
            picked = self.picked == (entry['kind'], entry['id'])
            (entry['row'].add_css_class if picked
             else entry['row'].remove_css_class)('sz-side-picked')

    def _tile_rows(self):
        return self.place_rows + self.fav_rows

    def _clear_drop(self):
        rows = self.group_rows + self._tile_rows() + self.device_rows + self.network_rows
        for entry in rows:
            for cls in ('sz-side-drop', 'sz-drop-before', 'sz-drop-after'):
                entry['row'].remove_css_class(cls)
        self.add_group_btn.remove_css_class('sz-side-drop')

    @staticmethod
    def _mark_drop(row, after):
        """Подсветить строку и линию вставки: сверху или снизу."""
        row.add_css_class('sz-side-drop')
        row.add_css_class('sz-drop-after' if after else 'sz-drop-before')

    def _drop_target(self, gesture, offset_x, offset_y):
        if Graphene is None:
            return None
        ok, sx, sy = gesture.get_start_point()
        if not ok:
            return None
        widget = gesture.get_widget()
        point = Graphene.Point().init(sx + offset_x, sy + offset_y)
        ok, pt = widget.compute_point(self.inner, point)
        if ok:
            for entry in self.group_rows:
                alloc = entry['row'].get_allocation()
                if alloc.y <= pt.y < alloc.y + alloc.height:
                    return ('group', entry, False)
            for entry in self._tile_rows():
                alloc = entry['row'].get_allocation()
                if alloc.y <= pt.y < alloc.y + alloc.height:
                    return ('tile', entry, pt.y > alloc.y + alloc.height / 2)
        ok, pt = widget.compute_point(self.add_group_btn, point)
        if ok and 0 <= pt.x <= self.add_group_btn.get_width() \
                and 0 <= pt.y <= self.add_group_btn.get_height():
            return ('new', None, False)
        return None

    def _tile_drag_begin(self, gesture, start_x, start_y, kind, item_id):
        self._drag = (kind, item_id)
        self._drop = None
        for entry in self._tile_rows():
            if entry['kind'] == kind and entry['id'] == item_id:
                entry['row'].add_css_class('sz-menu-dragging')

    def _tile_drag_update(self, gesture, offset_x, offset_y, kind, item_id):
        self._clear_drop()
        self._drop = self._drop_target(gesture, offset_x, offset_y)
        if self._drop is None:
            return
        if self._drop[0] == 'new':
            self.add_group_btn.add_css_class('sz-side-drop')
        else:
            self._mark_drop(self._drop[1]['row'], self._drop[2])

    def _tile_drag_end(self, gesture, offset_x, offset_y, kind, item_id):
        for entry in self._tile_rows():
            entry['row'].remove_css_class('sz-menu-dragging')
        self._clear_drop()
        drop, self._drop, self._drag = self._drop, None, None
        if drop is not None:
            self._apply_drop(kind, item_id, drop)

    def _apply_drop(self, kind, item_id, drop):
        where, entry, after = drop
        created = where == 'new'
        if created:
            group_id = self._new_group()
            dst = None
        elif where == 'group':
            group_id = entry['id']
            dst = None
        else:
            group_id = entry['group']
            dst = entry['id'] if entry['kind'] == kind else None
        if kind == 'place':
            order = list(self.place_order)
            if item_id not in order:
                order.append(item_id)
            else:
                order.remove(item_id)
            if dst is not None and dst in order:
                order.insert(order.index(dst) + (1 if after else 0), item_id)
            else:
                order.append(item_id)
            self.place_order = order
            default = self._default_group_id('places')
            if group_id == default:
                self.place_group.pop(item_id, None)
            else:
                self.place_group[item_id] = group_id
        elif kind == 'fav':
            order = [path for path, _name in self._favorite_entries()
                     if path != item_id]
            if dst is not None and dst in order:
                order.insert(order.index(dst) + (1 if after else 0), item_id)
            else:
                order.append(item_id)
            self.fav_order = order
            default = self._default_group_id('favorites')
            if group_id == default:
                self.fav_group.pop(item_id, None)
            else:
                self.fav_group[item_id] = group_id
        if created:
            self._save_groups()
        self._save_layout()
        self.rebuild()

    # ───────────── порядок устройств и сетевых дисков ─────────────
    def _device_rows_for(self, kind):
        return self.device_rows if kind == 'device' else self.network_rows

    def _device_order_for(self, kind):
        if kind == 'device':
            return self.device_order
        return self.network_order

    def _set_device_order(self, kind, order):
        if kind == 'device':
            self.device_order = order
        else:
            self.network_order = order

    def _ordered_device_entries(self, entries, order):
        """Расставить строки по сохранённому порядку, новые — в конце."""
        by_key, seen = {}, set()
        for entry in entries:
            key = entry.get('key')
            if not key or key in seen:
                continue
            seen.add(key)
            by_key[key] = entry
        saved = [key for key in order if key in by_key]
        saved_set = set(saved)
        rest = [key for key in by_key if key not in saved_set]
        return [by_key[key] for key in saved + rest]

    def _device_drag_begin(self, gesture, start_x, start_y, kind, key):
        self._device_drag = (kind, key)
        self._device_drop = None
        for entry in self._device_rows_for(kind):
            if entry['key'] == key:
                entry['row'].add_css_class('sz-menu-dragging')

    def _device_drag_update(self, gesture, offset_x, offset_y, kind, key):
        self._clear_drop()
        self._device_drop = None
        if Graphene is None:
            return
        ok, sx, sy = gesture.get_start_point()
        if not ok:
            return
        ok, pt = gesture.get_widget().compute_point(
            self.inner, Graphene.Point().init(sx + offset_x, sy + offset_y))
        if not ok:
            return
        rows = [entry for entry in self._device_rows_for(kind)
                if entry['key'] != key]
        for index, entry in enumerate(rows):
            alloc = entry['row'].get_allocation()
            bottom = (rows[index + 1]['row'].get_allocation().y
                      if index + 1 < len(rows) else self.inner.get_height())
            if alloc.y <= pt.y < bottom:
                after = pt.y > alloc.y + alloc.height / 2
                self._mark_drop(entry['row'], after)
                self._device_drop = (entry['key'], after)
                break

    def _device_drag_end(self, gesture, offset_x, offset_y, kind, key):
        for entry in self._device_rows_for(kind):
            entry['row'].remove_css_class('sz-menu-dragging')
        self._clear_drop()
        drop, self._device_drop, self._device_drag = self._device_drop, None, None
        if drop is not None:
            self._move_device(kind, key, drop[0], drop[1])

    def _move_device(self, kind, src_key, dst_key, after):
        if src_key == dst_key:
            return
        order = list(self._device_order_for(kind))
        current = [entry['key'] for entry in self._device_rows_for(kind)]
        for key in current:
            if key not in order:
                order.append(key)
        if src_key not in order or dst_key not in order:
            return
        order.remove(src_key)
        order.insert(order.index(dst_key) + (1 if after else 0), src_key)
        self._set_device_order(kind, order)
        self._save_layout()
        self.rebuild()

    def _toggle_place(self, place_id):
        if place_id in self.place_hidden:
            self.place_hidden.discard(place_id)
        else:
            self.place_hidden.add(place_id)
        self._save_layout()
        self.rebuild()

    def _save_layout(self):
        conf = self.win.conf
        conf['sidebar_places'] = list(self.place_order)
        conf['sidebar_hidden_places'] = [place_id for place_id in self.place_order
                                         if place_id in self.place_hidden]
        conf['sidebar_place_groups'] = dict(self.place_group)
        conf['sidebar_fav_groups'] = dict(self.fav_group)
        conf['sidebar_fav_order'] = [path for path, _name in self._favorite_entries()]
        conf['sidebar_device_order'] = list(self.device_order)
        conf['sidebar_network_order'] = list(self.network_order)
        conf.save()
        app = self.win.get_application()
        for w in (getattr(app, 'wins', None) or []):
            sb = getattr(w, 'sidebar', None)
            if sb is not None and sb is not self:
                sb.sync_groups()

    def _sync_model(self):
        self.groups = sidebar_groups(self.win.conf)
        self.group_order = [group['id'] for group in self.groups]
        self.place_order = place_order(self.win.conf)
        self.place_hidden = hidden_places(self.win.conf)
        self.place_group = place_groups(self.win.conf)
        self.fav_order = favorite_order(self.win.conf)
        self.fav_group = favorite_groups(self.win.conf)
        self.device_order = device_order(self.win.conf)
        self.network_order = network_order(self.win.conf)

    def sync_groups(self):
        self._sync_model()
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

    def _build_assigned(self, group_id):
        """Плитки, закреплённые за этой группой (места и избранное)."""
        known = {place_id: (icon, label, path)
                 for place_id, icon, label, path in all_places()}
        for place_id in self.place_order:
            if place_id not in known:
                continue
            if self._place_group_id(place_id) != group_id:
                continue
            icon, label, path = known[place_id]
            if self.editing:
                self._place_row(place_id, icon, label, path, group_id)
            elif place_id not in self.place_hidden:
                self._item(icon, label, path)
        for path, name in self._favorite_entries():
            if self._favorite_group_id(path) != group_id:
                continue
            if self.editing:
                self._fav_row(path, name, group_id)
            else:
                self._item('folder-symbolic', name, path)

    def _placeholder(self, text):
        l = lbl(text)
        l.add_css_class('sz-muted')
        l.set_margin_start(10)
        l.set_ellipsize(Pango.EllipsizeMode.END)
        self.inner.append(l)

    def _group_has_content(self, group):
        gtype = group_type(group)
        if gtype in ('devices', 'network'):
            return True
        group_id = group['id']
        known = {place_id for place_id, _icon, _label, _path in all_places()}
        for place_id in self.place_order:
            if place_id not in known:
                continue
            if self._place_group_id(place_id) != group_id:
                continue
            if self.editing or place_id not in self.place_hidden:
                return True
        for path, _name in self._favorite_entries():
            if self._favorite_group_id(path) == group_id:
                return True
        return False

    def _network_group_active(self):
        return any(group_type(group) == 'network' and not group.get('hidden')
                   for group in self.groups)

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
        if self._group_popup is not None:
            self._group_popup.popdown()
            self._group_popup = None
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

    def _device_handle(self, kind, key):
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
        drag.connect('drag-begin', self._device_drag_begin, kind, key)
        drag.connect('drag-update', self._device_drag_update, kind, key)
        drag.connect('drag-end', self._device_drag_end, kind, key)
        handle.add_controller(drag)
        return handle

    def _device_row(self, icon, text, path, mount=None, volume=None,
                    key=None, kind=None):
        row = hbox(0)
        row.add_css_class('sz-side-device-row')
        if self.editing:
            row.add_css_class('sz-side-device-edit')
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
            button.connect('clicked', lambda x, v=volume:
                           None if self.editing else self._mount_volume(v))
        else:
            button.connect('clicked', lambda x, p=path:
                           None if self.editing else self._go(p))
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
            eject.connect('clicked', lambda x, m=mount:
                          None if self.editing else self._eject_mount(m))
            row.append(eject)
        if self.editing and key and kind:
            row.append(self._device_handle(kind, key))
            self._device_rows_for(kind).append(
                {'key': key, 'row': row, 'kind': kind})
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

    def _device_key(self, path, mount=None, volume=None):
        """Стабильный ключ строки для сохранения пользовательского порядка."""
        if mount is not None:
            uri = self._mount_root_uri(mount)
            if uri:
                return 'uri:' + uri.rstrip('/')
        if volume is not None:
            uri = self._volume_uri(volume)
            if uri:
                return 'uri:' + uri.rstrip('/')
            for name in ('UNIX_DEVICE', 'UUID'):
                ident = getattr(Gio.VolumeIdentifier, name, None)
                if ident is None:
                    continue
                try:
                    value = volume.get_identifier(ident)
                except Exception:
                    value = None
                if value:
                    return 'volume:' + str(value)
            try:
                vname = volume.get_name()
            except Exception:
                vname = None
            if vname:
                return 'volume:' + vname
        if path:
            return 'path:' + os.path.normpath(path)
        return None

    def _build_devices(self):
        entries = [{'key': 'path:/', 'icon': 'drive-harddisk-symbolic',
                    'text': _('File system'), 'path': '/',
                    'mount': None, 'volume': None}]
        monitor = self._monitor
        net_separate = self._network_group_active()
        if monitor is not None:
            mounted_keys = set()
            try:
                for mount in monitor.get_mounts():
                    path = self._mount_local_path(mount)
                    if not path or path == '/' or not os.path.isdir(path):
                        continue
                    path = os.path.normpath(path)
                    key = self._device_key(path, mount, None)
                    if not key or key in mounted_keys:
                        continue
                    mounted_keys.add(key)
                    volume = self._volume_for_mount(mount)
                    if self._is_network_mount(mount):
                        if net_separate:
                            continue
                        name = self._network_label(mount, volume)
                    else:
                        name = (volume.get_name() if volume is not None
                                and volume.get_name() else mount.get_name())
                    entries.append({
                        'key': key,
                        'icon': self._device_icon(volume=volume, mount=mount),
                        'text': name, 'path': path,
                        'mount': mount, 'volume': volume})
            except Exception:
                pass
            try:
                for volume in monitor.get_volumes():
                    if volume.get_mount() is not None:
                        continue
                    if net_separate and self._is_network_volume(volume):
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
                    key = self._device_key(None, None, volume)
                    if not key:
                        continue
                    entries.append({
                        'key': key,
                        'icon': self._device_icon(volume=volume),
                        'text': name, 'path': None,
                        'mount': None, 'volume': volume})
            except Exception:
                pass
        if not net_separate:
            entries.append({'key': 'connect', 'connect': True})
        ordered = self._ordered_device_entries(entries, self.device_order)
        for entry in ordered:
            if entry.get('connect'):
                self._connect_row(entry['key'], 'device')
            else:
                self._device_row(entry['icon'], entry['text'], entry['path'],
                                 mount=entry['mount'], volume=entry['volume'],
                                 key=entry['key'], kind='device')

    def _build_network(self):
        """Сетевые диски: подключённые ресурсы и пункт подключения."""
        entries = []
        monitor = self._monitor
        if monitor is not None:
            seen = set()
            try:
                for mount in monitor.get_mounts():
                    if not self._is_network_mount(mount):
                        continue
                    path = self._mount_local_path(mount)
                    if not path or not os.path.isdir(path):
                        continue
                    path = os.path.normpath(path)
                    key = self._device_key(path, mount, None)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    volume = self._volume_for_mount(mount)
                    entries.append({
                        'key': key,
                        'icon': self._device_icon(volume=volume, mount=mount),
                        'text': self._network_label(mount, volume),
                        'path': path, 'mount': mount, 'volume': volume})
            except Exception:
                pass
            try:
                for volume in monitor.get_volumes():
                    if volume.get_mount() is not None:
                        continue
                    if not self._is_network_volume(volume):
                        continue
                    if not volume.can_mount():
                        continue
                    name = volume.get_name()
                    if not name:
                        continue
                    key = self._device_key(None, None, volume)
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    entries.append({
                        'key': key,
                        'icon': self._device_icon(volume=volume),
                        'text': name, 'path': None,
                        'mount': None, 'volume': volume})
            except Exception:
                pass
        entries.append({'key': 'connect', 'connect': True})
        ordered = self._ordered_device_entries(entries, self.network_order)
        for entry in ordered:
            if entry.get('connect'):
                self._connect_row(entry['key'], 'network')
            else:
                self._device_row(entry['icon'], entry['text'], entry['path'],
                                 mount=entry['mount'], volume=entry['volume'],
                                 key=entry['key'], kind='network')

    def _connect_row(self, key='connect', kind='network'):
        """Пункт «Подключиться к серверу…» в разделе устройств."""
        outer = hbox(0)
        outer.add_css_class('sz-side-connect-row')
        if self.editing:
            outer.add_css_class('sz-side-device-edit')
        button = Gtk.Button()
        button.add_css_class('flat')
        button.add_css_class('sz-side-item')
        button.add_css_class('sz-side-connect')
        button.set_focus_on_click(False)
        button.set_hexpand(True)
        row = hbox(10)
        row.append(Gtk.Image.new_from_icon_name(
            pick_icon('network-server-symbolic', 'network-workgroup-symbolic',
                      'folder-remote-symbolic')))
        label = lbl(_('Connect to server'))
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        row.append(label)
        button.set_child(row)
        button.set_tooltip_text(_('Connect to server'))

        def activate(b):
            if not self.editing:
                self._network_dialog()
        button.connect('clicked', activate)
        outer.append(button)
        if self.editing:
            outer.append(self._device_handle(kind, key))
            self._device_rows_for(kind).append(
                {'key': key, 'row': outer, 'kind': kind})
        self.inner.append(outer)

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
        self.fav_rows = []
        self.device_rows = []
        self.network_rows = []
        favs_present = bool(self._favorite_entries())
        for group in self.groups:
            gtype = group_type(group)
            hidden = bool(group.get('hidden'))
            content = self._group_has_content(group)
            if self.editing:
                self._group_header(group)
            elif not hidden and (content or (gtype == 'favorites' and not favs_present)):
                self._section(group_title(group))
            if hidden:
                continue
            if content:
                self._build_assigned(group['id'])
            if gtype == 'devices':
                self._build_devices()
            elif gtype == 'network':
                self._build_network()
            elif gtype == 'favorites' and not favs_present and not self.editing:
                self._placeholder(_('No favorites yet'))
            elif gtype == 'custom' and not content and self.editing:
                self._placeholder(_('Drag items here'))
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
