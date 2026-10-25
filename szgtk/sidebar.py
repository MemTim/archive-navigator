# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _, N_
from .dialogs import hbox, lbl, pick_icon, vbox
from .favorites import name as fav_name, path as fav_path

PLACES_SPEC = [
    ('user-desktop-symbolic', N_('Desktop'), GLib.UserDirectory.DIRECTORY_DESKTOP),
    ('folder-download-symbolic', N_('Downloads'), GLib.UserDirectory.DIRECTORY_DOWNLOAD),
    ('folder-documents-symbolic', N_('Documents'), GLib.UserDirectory.DIRECTORY_DOCUMENTS),
    ('folder-pictures-symbolic', N_('Pictures'), GLib.UserDirectory.DIRECTORY_PICTURES),
    ('folder-music-symbolic', N_('Music'), GLib.UserDirectory.DIRECTORY_MUSIC),
    ('folder-videos-symbolic', N_('Videos'), GLib.UserDirectory.DIRECTORY_VIDEOS),
]


def special_places():
    home = os.path.normpath(os.path.expanduser('~'))
    out = [('user-home-symbolic', _('Home folder'), home)]
    for icon, label, d in PLACES_SPEC:
        p = GLib.get_user_special_dir(d)
        if p and os.path.isdir(p) and os.path.normpath(p) != home:
            out.append((icon, _(label), os.path.normpath(p)))
    return out


class Sidebar(Gtk.Box):
    """Боковая панель дизайна «Навигационный»: Места / Избранное / Устройства."""

    def __init__(self, win):
        super().__init__(orientation=V)
        self.win, self.items = win, []
        self.add_css_class('sz-sidebar')
        self.set_size_request(220, -1)
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.inner = vbox(2)
        self.inner.set_margin_start(8)
        self.inner.set_margin_end(8)
        sw.set_child(self.inner)
        self.append(sw)
        card = vbox(2)
        card.add_css_class('sz-usercard')
        name = GLib.get_real_name()
        if not name or name == 'Unknown':
            name = GLib.get_user_name()
        n = lbl(name)
        n.add_css_class('sz-hdr-role')
        p = lbl(os.path.expanduser('~'))
        p.add_css_class('sz-muted')
        p.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        card.append(n)
        card.append(p)
        self.append(card)
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

    def rebuild(self):
        child = self.inner.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.inner.remove(child)
            child = nxt
        self.items = []
        self._section(_('PLACES'))
        for icon, label, path in special_places():
            self._item(icon, label, path)
        self._section(_('FAVORITES'))
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
        self._section(_('DEVICES'))
        self._item('drive-harddisk-symbolic', _('File system'), '/')
        try:
            for m in Gio.VolumeMonitor.get().get_mounts():
                root = m.get_root()
                pth = root.get_path() if root is not None else None
                if pth and pth != '/':
                    self._item(pick_icon('media-removable-symbolic', 'drive-removable-media-symbolic', 'drive-harddisk-symbolic'), m.get_name(), pth)
        except Exception:
            pass
        self.set_active(self.win.active.current_dir() if self.win.active is not None
                        and self.win.active.mode == 'fs' else None)

    def set_active(self, path):
        norm = os.path.normpath(path) if path else None
        for p, b in self.items:
            (b.add_css_class if p == norm else b.remove_css_class)('sz-side-active')
