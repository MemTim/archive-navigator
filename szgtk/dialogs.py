# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _
from .theme import _theme, style_window
from .utils import handle_text_shortcut


class DlgBase(Gtk.Window):
    """Окно диалога: подхватывает текущую цветовую схему."""

    def __init__(self, **kw):
        super().__init__(**kw)
        style_window(self, _theme.get('scheme', 'midnight'))
        kc = Gtk.EventControllerKey()
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        kc.connect('key-pressed', lambda c, k, _kc, state: handle_text_shortcut(self, k, state))
        self.add_controller(kc)


# ───────────────────────────── вспомогательные виджеты ─────────────────────────────
H, V = Gtk.Orientation.HORIZONTAL, Gtk.Orientation.VERTICAL


def icon_resolves(theme, name):
    """Иконка действительно находится в теме (has_icon() иногда врёт и даёт 'image-missing')."""
    try:
        p = theme.lookup_icon(name, None, 16, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags(0))
        return p.get_icon_name() == name
    except Exception:
        return False


def pick_icon(*names):
    """Первая иконка, которая есть в теме (запасные варианты для разных тем)."""
    try:
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        for n in names:
            if theme.has_icon(n) and icon_resolves(theme, n):
                return n
    except Exception:
        pass
    return names[-1]


def set_margins(w, m):
    w.set_margin_top(m)
    w.set_margin_bottom(m)
    w.set_margin_start(m)
    w.set_margin_end(m)


def vbox(spacing=6, margin=0):
    b = Gtk.Box(orientation=V, spacing=spacing)
    if margin:
        set_margins(b, margin)
    return b


def hbox(spacing=6):
    return Gtk.Box(orientation=H, spacing=spacing)


def lbl(text, xalign=0.0):
    l = Gtk.Label(label=text)
    l.set_xalign(xalign)
    return l


def _tab_line_draw(factor):
    """Линия под вкладкой: скруглённая, длиной factor от ширины текста."""
    def draw(area, cr, w, h):
        c = area.get_color()
        cr.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        line_w = max(0.0, w * factor)
        x = (w - line_w) / 2
        r = min(h / 2, line_w / 2)
        if r <= 0:
            return
        cr.new_sub_path()
        cr.arc(x + line_w - r, r, r, -math.pi / 2, 0)
        cr.arc(x + line_w - r, h - r, r, 0, math.pi / 2)
        cr.arc(x + r, h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.fill()
    return draw


def _tab_label(text):
    """Подпись вкладки с отдельной линией по ширине текста."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.add_css_class('sz-tab-label')
    label = lbl(text, 0.5)
    label.add_css_class('sz-tab-text')
    box.append(label)
    lines = Gtk.Overlay()
    lines.set_hexpand(True)
    lines.set_margin_bottom(2)
    active = Gtk.DrawingArea()
    active.set_content_height(4)
    active.set_hexpand(True)
    active.set_can_target(False)
    active.add_css_class('sz-tab-line-active')
    active.set_draw_func(_tab_line_draw(1.0))
    hover = Gtk.DrawingArea()
    hover.set_content_height(4)
    hover.set_hexpand(True)
    hover.set_can_target(False)
    hover.add_css_class('sz-tab-line-hover')
    hover.set_draw_func(_tab_line_draw(0.75))
    lines.set_child(active)
    lines.add_overlay(hover)
    box.append(lines)
    return box


def make_dd(labels, sel=0):
    d = Gtk.DropDown.new_from_strings(list(labels))
    d.set_selected(sel)
    return d


def set_dd(d, labels, sel=0):
    d.set_model(Gtk.StringList.new(list(labels)))
    d.set_selected(sel)


def grid_row(grid, row, text, widget):
    l = lbl(text)
    grid.attach(l, 0, row, 1, 1)
    grid.attach(widget, 1, row, 1, 1)
    return l


def new_dialog(parent, title, width=0, height=0, modal=True):
    w = DlgBase(title=title, modal=modal, destroy_with_parent=True)
    if parent is not None:
        w.set_transient_for(parent)
    if width or height:
        w.set_default_size(width, height)
    k = Gtk.EventControllerKey()

    def on_key(c, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            w.close()
            return True
        return False
    k.connect('key-pressed', on_key)
    w.add_controller(k)
    return w


def button_row(win, ok_text, on_ok):
    row = hbox(6)
    row.set_halign(Gtk.Align.END)
    cancel = Gtk.Button(label=_('Cancel'))
    cancel.add_css_class('sz-dlg-cancel')
    cancel.connect('clicked', lambda b: win.close())
    ok = Gtk.Button(label=ok_text)
    ok.add_css_class('sz-dlg-ok')
    ok.add_css_class('suggested-action')
    ok.connect('clicked', lambda b: on_ok())
    row.append(cancel)
    row.append(ok)
    win.set_default_widget(ok)
    return row, ok


def alert(parent, message, detail=None):
    d = Gtk.AlertDialog()
    d.set_message(message)
    if detail:
        d.set_detail(detail)
    d.set_buttons([_('OK')])
    d.set_default_button(0)
    d.set_cancel_button(0)
    d.show(parent)


def choose(parent, message, buttons, cb, detail=None, default=0, cancel=0):
    """AlertDialog с несколькими кнопками; cb(index) (-1 — закрыто)."""
    d = Gtk.AlertDialog()
    d.set_message(message)
    if detail:
        d.set_detail(detail)
    d.set_buttons(buttons)
    d.set_default_button(default)
    d.set_cancel_button(cancel)

    def done(dlg, res):
        try:
            idx = dlg.choose_finish(res)
        except GLib.Error:
            idx = -1
        cb(idx)
    d.choose(parent, None, done)


def confirm(parent, message, detail, ok_label, on_yes):
    choose(parent, message, [_('Cancel'), ok_label],
           lambda i: on_yes() if i == 1 else None, detail=detail, default=1, cancel=0)


def text_dialog(parent, title, text, w=680, h=420):
    d = new_dialog(parent, title, w, h, modal=False)
    root = vbox(8, 10)
    d.set_child(root)
    tv = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
    tv.get_buffer().set_text(text)
    sw = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
    sw.set_child(tv)
    root.append(sw)
    row = hbox(6)
    row.set_halign(Gtk.Align.END)
    cp = Gtk.Button(label=_('Copy'))
    cp.connect('clicked', lambda b: d.get_clipboard().set_text(text))
    cl = Gtk.Button(label=_('Close'))
    cl.connect('clicked', lambda b: d.close())
    row.append(cp)
    row.append(cl)
    root.append(row)
    d.present()
    return d


def pick(parent, kind, title, cb, initial=None, name=None):
    """Обёртка над Gtk.FileDialog. kind: open | multi | folder | save. cb(list[str])."""
    d = Gtk.FileDialog()
    d.set_title(title)
    if initial and os.path.isdir(initial):
        d.set_initial_folder(Gio.File.new_for_path(initial))
    if name:
        d.set_initial_name(name)

    def done(dlg, res):
        try:
            if kind == 'folder':
                files = [dlg.select_folder_finish(res)]
            elif kind == 'multi':
                lst = dlg.open_multiple_finish(res)
                files = [lst.get_item(i) for i in range(lst.get_n_items())]
            elif kind == 'save':
                files = [dlg.save_finish(res)]
            else:
                files = [dlg.open_finish(res)]
        except GLib.Error:
            return
        paths = [f.get_path() for f in files if f is not None and f.get_path()]
        if paths:
            cb(paths)
    {'folder': d.select_folder, 'multi': d.open_multiple, 'save': d.save}.get(kind, d.open)(parent, None, done)


# ───────────────────────────── прогресс ─────────────────────────────
class ProgressDialog(DlgBase):
    def __init__(self, parent, title, job):
        super().__init__(title=title, modal=True, transient_for=parent,
                         resizable=False, destroy_with_parent=True)
        self.job = job
        self._alive = True
        self.set_default_size(440, -1)
        root = vbox(10, 16)
        self.set_child(root)
        root.append(lbl(title))
        self.bar = Gtk.ProgressBar()
        root.append(self.bar)
        self.lab = lbl('')
        self.lab.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.lab.set_max_width_chars(60)
        root.append(self.lab)
        cancel = Gtk.Button(label=_('Cancel'))
        cancel.set_halign(Gtk.Align.END)
        cancel.connect('clicked', lambda b: job.cancel())
        root.append(cancel)
        self.connect('close-request', self._on_close)
        GLib.timeout_add(100, self._tick)
        GLib.timeout_add(250, self._delayed_present)

    def _on_close(self, w):
        self.job.cancel()
        return True

    def _delayed_present(self):
        if self._alive:
            self.present()
        return False

    def _tick(self):
        if not self._alive:
            return False
        if self.job.fraction is None:
            self.bar.pulse()
        else:
            self.bar.set_fraction(min(1.0, self.job.fraction))
        self.lab.set_text(self.job.text)
        return True

    def finish(self):
        self._alive = False
        self.destroy()


# ───────────────────────────── простые диалоги ─────────────────────────────
class PasswordDialog(DlgBase):
    def __init__(self, parent, name, cb):
        super().__init__(title=_('Enter password'), modal=True, transient_for=parent,
                         destroy_with_parent=True)
        self.cb, self.sent = cb, False
        root = vbox(10, 14)
        self.set_child(root)
        root.append(lbl(_('Password is required for:') + '\n' + name))
        self.e = Gtk.PasswordEntry(show_peek_icon=True, activates_default=True)
        self.e.set_size_request(340, -1)
        root.append(self.e)
        row, ok = button_row(self, _('OK'), self._ok)
        root.append(row)
        self.connect('close-request', self._closing)

    def _ok(self):
        self.sent = True
        pw = self.e.get_text()
        self.close()
        self.cb(pw)

    def _closing(self, w):
        if not self.sent:
            self.sent = True
            GLib.idle_add(self.cb, None)
        return False


class PromptDialog(DlgBase):
    """Одна строка ввода (+ опционально выбор папки)."""

    def __init__(self, parent, title, label, default, ok_text, on_ok, folder_browse=False):
        super().__init__(title=title, modal=True, transient_for=parent, destroy_with_parent=True)
        self.on_ok = on_ok
        root = vbox(8, 14)
        self.set_child(root)
        root.append(lbl(label))
        row = hbox(6)
        self.e = Gtk.Entry(hexpand=True, text=default, activates_default=True)
        self.e.set_size_request(460, -1)
        row.append(self.e)
        if folder_browse:
            b = Gtk.Button(label='…')
            b.connect('clicked', lambda x: pick(self, 'folder', title,
                                                lambda p: self.e.set_text(p[0]),
                                                initial=self.e.get_text()))
            row.append(b)
        root.append(row)
        brow, ok = button_row(self, ok_text, self._ok)
        root.append(brow)
        self.e.grab_focus()
        if not folder_browse:
            stem = os.path.splitext(default)[0]
            GLib.idle_add(lambda: self.e.select_region(0, len(stem)) or False)

    def _ok(self):
        v = self.e.get_text().strip()
        if not v:
            return
        self.close()
        self.on_ok(v)


class HistoryDialog(DlgBase):
    def __init__(self, parent, items, on_pick):
        super().__init__(title=_('Folders history'), modal=True, transient_for=parent,
                         destroy_with_parent=True)
        self.set_default_size(560, 320)
        root = vbox(8, 10)
        self.set_child(root)
        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for it in reversed(items):
            l = lbl(it)
            set_margins(l, 4)
            lb.append(l)

        def act(box, row):
            self.close()
            on_pick(row.get_child().get_label())
        lb.connect('row-activated', act)
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(lb)
        root.append(sw)


class OpenWithDialog(DlgBase):
    """Выбор программы для файла с возможностью запомнить выбор."""

    def __init__(self, parent, path, on_pick=None):
        super().__init__(title=_('Open with…'), modal=True, transient_for=parent,
                         destroy_with_parent=True)
        self.set_default_size(480, 440)
        self.path = path
        self.gfile = Gio.File.new_for_path(path)
        self.ctype = None
        try:
            info = self.gfile.query_info('standard::content-type',
                                         Gio.FileQueryInfoFlags.NONE, None)
            self.ctype = info.get_content_type()
        except GLib.Error:
            pass
        root = vbox(8, 12)
        self.set_child(root)
        root.append(lbl(_('Choose an application to open the file:')))
        self.chooser = (Gtk.AppChooserWidget(content_type=self.ctype, vexpand=True, hexpand=True)
                        if self.ctype else Gtk.AppChooserWidget(vexpand=True, hexpand=True))
        self.chooser.set_show_all(True)
        self.chooser.set_show_other(True)
        root.append(self.chooser)
        self.chk = Gtk.CheckButton(label=_('Always open with this application'))
        root.append(self.chk)
        row, ok = button_row(self, _('Open'), self._ok)
        root.append(row)
        self.on_pick = on_pick

    def _remember(self, app):
        ok = False
        if self.ctype:
            try:
                app.set_as_default_for_type(self.ctype)
                ok = True
            except GLib.Error:
                pass
        if not ok:
            ext = os.path.splitext(self.path)[1]
            if ext:
                try:
                    app.set_as_default_for_extension(ext)
                    ok = True
                except GLib.Error:
                    pass
        if not ok:
            alert(self, _('Cannot set the default application'))

    def _ok(self):
        app = self.chooser.get_app_info()
        if app is None:
            return
        if self.chk.get_active():
            self._remember(app)
        self.close()
        if self.on_pick is not None:
            self.on_pick(app, self.gfile)
            return
        try:
            app.launch([self.gfile], None)
        except GLib.Error as e:
            alert(self, _('Cannot open file'), e.message)
