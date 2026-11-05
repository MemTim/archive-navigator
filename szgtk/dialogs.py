# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _
from .config import Config
from .display import DISP, format_size
from .openwith import (add_custom, clear_default, command_argv, custom_commands,
                       default_command, remove_custom, set_default_command, spawn)
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
    cp.add_css_class('sz-dlg-cancel')
    cp.connect('clicked', lambda b: d.get_clipboard().set_text(text))
    cl = Gtk.Button(label=_('Close'))
    cl.add_css_class('sz-danger')
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
def _progress_cfg():
    """Настройки размеров для прогресса: всегда удобные единицы."""
    cfg = dict(DISP)
    cfg['size_mode'] = 'adaptive'
    if int(cfg.get('size_decimals') or 0) < 1:
        cfg['size_decimals'] = 1
    return cfg


def _size_text(n):
    return format_size(n, _progress_cfg())


def _rate_text(bps):
    return _('{0}/s').format(_size_text(bps))


def _duration_text(sec):
    sec = max(0, int(round(sec)))
    if sec >= 3600:
        return _('{0} h {1} min').format(sec // 3600, (sec % 3600) // 60)
    if sec >= 60:
        return _('{0} min {1} s').format(sec // 60, sec % 60)
    return _('{0} s').format(sec)


def _niri_session():
    """niri размещает transient-окна относительно родителя, из-за чего окно
    прогресса прыгает. Там его лучше сначала показать обычным плавающим окном
    (niri центрирует его), а transient_for привязать уже после появления."""
    if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
        return False
    if os.environ.get('GDK_BACKEND') in ('x11', 'broadway'):
        return False
    return (bool(os.environ.get('NIRI_SOCKET'))
            or 'niri' in os.environ.get('XDG_CURRENT_DESKTOP', '').lower())


class ProgressDialog(DlgBase):
    def __init__(self, parent, title, job):
        # Не модальный: пока идёт операция, окно проводника должно оставаться
        # рабочим — можно выделять, открывать и перемещать файлы.
        self._parent_win = parent
        self._attach_parent = bool(parent is not None and _niri_session())
        super().__init__(title=title, modal=False,
                         transient_for=None if self._attach_parent else parent,
                         resizable=False,
                         destroy_with_parent=not self._attach_parent)
        header = Gtk.HeaderBar()
        header.add_css_class('sz-prog-header')
        header.set_show_title_buttons(False)
        head = lbl(title, xalign=0.5)
        head.add_css_class('sz-prog-title')
        header.set_title_widget(head)
        self.set_titlebar(header)
        self.job = job
        self._alive = True
        self._hidden_sidebar = False
        self._sidebar_ref = None
        self._parent_destroy_id = 0
        if self._attach_parent:
            try:
                self._parent_destroy_id = parent.connect('destroy', self._on_parent_destroy)
            except Exception:
                self._parent_destroy_id = 0
        self._samples = []
        self._rate = None
        self._eta = None
        self._last_f = None
        self._speed_text = ''
        self._paused_shown = job.paused
        self._icon_name = ''
        # Фиксированный размер: при быстром копировании/перемещении строки
        # появляются и исчезают, и окно не должно прыгать.
        self.set_default_size(520, 392)
        self.set_size_request(520, 392)

        root = vbox(0)
        self.set_child(root)

        body = vbox(16, 24)
        body.add_css_class('sz-prog-body')
        body.set_vexpand(True)
        root.append(body)

        top = hbox(14)
        plate = Gtk.Box()
        plate.add_css_class('sz-prog-icon')
        plate.set_valign(Gtk.Align.START)
        self.icon = Gtk.Image.new_from_icon_name('text-x-generic-symbolic')
        self.icon.set_pixel_size(26)
        plate.append(self.icon)
        top.append(plate)
        names = vbox(2)
        names.set_valign(Gtk.Align.CENTER)
        names.set_hexpand(True)
        self.name = lbl(job.text or title)
        self.name.add_css_class('sz-prog-name')
        self.name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.sub = lbl(job.subtitle or (title + '…'))
        self.sub.add_css_class('sz-prog-sub')
        names.append(self.name)
        names.append(self.sub)
        top.append(names)
        body.append(top)

        pctrow = hbox(12)
        self.pct = lbl('')
        self.pct.add_css_class('sz-prog-pct')
        self.pct.set_hexpand(True)
        self.eta = lbl('', xalign=1.0)
        self.eta.add_css_class('sz-prog-info')
        pctrow.append(self.pct)
        pctrow.append(self.eta)
        body.append(pctrow)

        self.bar = Gtk.ProgressBar()
        self.bar.add_css_class('sz-prog-bar')
        body.append(self.bar)

        self.bytesrow = hbox(12)
        self.bytes = lbl('')
        self.bytes.add_css_class('sz-prog-info')
        self.bytes.set_hexpand(True)
        self.speed = lbl('', xalign=1.0)
        self.speed.add_css_class('sz-prog-info')
        self.bytesrow.append(self.bytes)
        self.bytesrow.append(self.speed)
        body.append(self.bytesrow)

        self.files = lbl('')
        self.files.add_css_class('sz-prog-files')
        body.append(self.files)

        footer = hbox(10)
        footer.add_css_class('sz-prog-footer')
        footer.set_hexpand(True)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        footer.append(spacer)
        self.cancel_btn = Gtk.Button(label=_('Cancel'))
        self.cancel_btn.add_css_class('sz-prog-cancel')
        self.cancel_btn.add_css_class('sz-danger')
        self.cancel_btn.connect('clicked', lambda b: job.cancel())
        footer.append(self.cancel_btn)
        self.pause_btn = Gtk.Button()
        self.pause_btn.add_css_class('sz-prog-pause')
        pb = hbox(6)
        self.pause_img = Gtk.Image.new_from_icon_name('media-playback-pause-symbolic')
        self.pause_lab = lbl(_('Pause'))
        pb.append(self.pause_img)
        pb.append(self.pause_lab)
        self.pause_btn.set_child(pb)
        self.pause_btn.connect('clicked', self._toggle_pause)
        self.pause_btn.set_visible(bool(job.pausable))
        footer.append(self.pause_btn)
        self.hide_btn = Gtk.Button(label=_('Hide'))
        self.hide_btn.add_css_class('sz-prog-hide')
        self.hide_btn.set_tooltip_text(
            _('Hide the window and show progress in the sidebar'))
        self.hide_btn.set_visible(self._sidebar_visible())
        self.hide_btn.connect('clicked', lambda b: self.hide_to_sidebar())
        footer.append(self.hide_btn)
        root.append(footer)

        self.connect('close-request', self._on_close)
        self.connect('destroy', self._on_destroy)
        self._sync_icon()
        GLib.timeout_add(100, self._tick)
        GLib.timeout_add(250, self._delayed_present)

    def _on_destroy(self, *a):
        if self._hidden_sidebar:
            sidebar = self._sidebar()
            if sidebar is not None:
                sidebar.remove_job_dialog(self)
            self._hidden_sidebar = False
        self._sidebar_ref = None
        if self._parent_destroy_id and self._parent_win is not None:
            try:
                self._parent_win.disconnect(self._parent_destroy_id)
            except Exception:
                pass
            self._parent_destroy_id = 0
        self._alive = False

    def _on_parent_destroy(self, *a):
        self._parent_win = None
        self._parent_destroy_id = 0
        if self._alive:
            self.job.cancel()
            GLib.idle_add(self.finish)
        return False

    def _on_close(self, w):
        self.job.cancel()
        return True

    def _delayed_present(self):
        if self._alive and not self._hidden_sidebar:
            self.present()
            if self._attach_parent:
                GLib.timeout_add(80, self._attach_transient)
        return False

    def _attach_transient(self):
        if not self._attach_parent:
            return False
        self._attach_parent = False
        if not self._alive or self._hidden_sidebar or self._parent_win is None:
            return False
        try:
            self.set_transient_for(self._parent_win)
            self.set_destroy_with_parent(True)
        except Exception:
            pass
        return False

    def _sidebar(self):
        ref = getattr(self, '_sidebar_ref', None)
        if ref is not None:
            return ref
        parent = getattr(self, '_parent_win', None) or self.get_transient_for()
        sidebar = getattr(parent, 'sidebar', None)
        return sidebar if hasattr(sidebar, 'add_job_dialog') else None

    def _sidebar_visible(self):
        sidebar = self._sidebar()
        return sidebar is not None and sidebar.get_visible()

    def hide_to_sidebar(self):
        """Скрыть окно и показать круговой индикатор в боковой панели."""
        if not self._alive or self._hidden_sidebar:
            return
        if not self._sidebar_visible():
            return
        sidebar = self._sidebar()
        self._hidden_sidebar = True
        self._sidebar_ref = sidebar
        sidebar.add_job_dialog(self)
        self._detach_transient()
        self.hide()

    def show_full(self):
        """Вернуть скрытое окно прогресса на экран."""
        if not self._alive:
            return
        sidebar = self._sidebar()
        if sidebar is not None:
            sidebar.remove_job_dialog(self)
        self._hidden_sidebar = False
        self._sidebar_ref = None
        self._attach_parent = bool(self._parent_win is not None and _niri_session())
        self.present()
        if self._attach_parent:
            GLib.timeout_add(80, self._attach_transient)

    def _detach_transient(self):
        """Перед скрытием отвязать окно от родителя, чтобы niri снова
        центрировал его при повторном показе, а не сдвигал к родителю."""
        if not self._attach_parent and self.get_transient_for() is None:
            return
        try:
            self.set_destroy_with_parent(False)
            self.set_transient_for(None)
        except Exception:
            pass

    def progress_snapshot(self):
        """Данные для индикатора в боковой панели."""
        return dict(
            alive=self._alive,
            title=self.get_title() or '',
            text=self.name.get_text(),
            sub=self.sub.get_text(),
            pct=self.pct.get_text(),
            eta=self.eta.get_text(),
            bytes=self.bytes.get_text() if self.bytesrow.get_visible() else '',
            speed=self.speed.get_text(),
            files=self.files.get_text() if self.files.get_visible() else '',
            action=self.job.action,
            fraction=self.job.fraction,
            cancelled=self.job.cancelled,
            paused=self.job.paused,
        )

    def _sync_icon(self):
        icon = self.job.icon or 'text-x-generic-symbolic'
        if icon != self._icon_name:
            self._icon_name = icon
            self.icon.set_from_icon_name(icon)

    def _toggle_pause(self, *a):
        self.job.toggle_pause()
        self._show_paused()

    def _show_paused(self):
        self._paused_shown = self.job.paused
        paused = self.job.paused
        self.pause_lab.set_text(_('Resume') if paused else _('Pause'))
        self.pause_img.set_from_icon_name(
            'media-playback-start-symbolic' if paused else 'media-playback-pause-symbolic')
        self.sub.set_text(_('Paused') if paused else (self.job.subtitle or ''))

    def _speed(self, now):
        """Скорость по последней секунде (байт/с), если известны байты."""
        done = self.job.bytes_done
        self._samples.append((now, done))
        while len(self._samples) > 2 and now - self._samples[0][0] > 1.0:
            self._samples.pop(0)
        if len(self._samples) < 2:
            return None
        t0, b0 = self._samples[0]
        dt = now - t0
        if dt < 0.08 or done <= b0:
            return None
        rate = (done - b0) / dt
        self._rate = rate if self._rate is None else (self._rate + rate) / 2
        return self._rate

    def _tick(self):
        if not self._alive:
            return False
        job = self.job
        self.name.set_text(job.text or self.get_title())
        self._sync_icon()
        if job.paused != self._paused_shown:
            self._show_paused()

        f = job.fraction
        if f is None:
            self.bar.pulse()
            self.pct.set_text('…')
            self.eta.set_text('')
        else:
            f = min(1.0, max(0.0, f))
            if self._last_f is not None and f + 0.05 < self._last_f:
                # прогресс начался заново (следующий элемент при перемещении)
                self._eta = None
            self._last_f = f
            self.bar.set_fraction(f)
            self.pct.set_text('%d %%' % round(f * 100))
            if job.paused:
                pass
            elif 0.01 < f < 0.995 and job.elapsed() > 0.3:
                raw = job.elapsed() * (1.0 - f) / f
                self._eta = raw if self._eta is None else self._eta * 0.7 + raw * 0.3
                self.eta.set_text(_('Remaining {0}').format(_duration_text(self._eta)))
            elif f >= 0.995:
                self.eta.set_text('')

        if job.bytes_total:
            self.bytesrow.set_visible(True)
            self.bytes.set_text(_('{0} of {1}').format(
                _size_text(job.bytes_done), _size_text(job.bytes_total)))
            if not job.paused:
                speed = self._speed(time.monotonic())
                if speed and f is not None and f < 1.0:
                    self._speed_text = _rate_text(speed)
                elif f is not None and f >= 1.0:
                    self._speed_text = ''
                self.speed.set_text(self._speed_text)
        else:
            self.bytesrow.set_visible(False)

        if job.files_total and job.files_label:
            self.files.set_visible(True)
            self.files.set_text(job.files_label.format(job.files_done, job.files_total))
        else:
            self.files.set_visible(False)
        return True

    def finish(self):
        if not self._alive:
            return
        self._alive = False
        if self._hidden_sidebar:
            sidebar = self._sidebar()
            if sidebar is not None:
                sidebar.remove_job_dialog(self)
            self._hidden_sidebar = False
        self._sidebar_ref = None
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


class _AppRow(Gtk.ListBoxRow):
    """Строка списка программ: системное приложение или своя команда."""

    def __init__(self, key, name, subtitle, icon, app=None, command='',
                 default=False, on_delete=None):
        super().__init__()
        self.key = key
        self.app = app
        self.command = command
        self.search_text = ' '.join((name, subtitle or '', key)).lower()
        self.add_css_class('sz-app-row')
        box = hbox(10)
        set_margins(box, 6)
        img = icon if isinstance(icon, Gtk.Widget) else Gtk.Image.new_from_icon_name(icon)
        img.set_pixel_size(20)
        box.append(img)
        texts = vbox(2)
        texts.set_hexpand(True)
        title = lbl(name)
        title.add_css_class('sz-app-name')
        title.set_ellipsize(Pango.EllipsizeMode.END)
        texts.append(title)
        if subtitle:
            sub = lbl(subtitle)
            sub.add_css_class('sz-app-sub')
            sub.set_ellipsize(Pango.EllipsizeMode.END)
            texts.append(sub)
        box.append(texts)
        if default:
            mark = Gtk.Image.new_from_icon_name('object-select-symbolic')
            mark.add_css_class('sz-app-default')
            mark.set_tooltip_text(_('Default'))
            box.append(mark)
        if on_delete is not None:
            btn = Gtk.Button.new_from_icon_name('user-trash-symbolic')
            btn.add_css_class('flat')
            btn.add_css_class('sz-app-del')
            btn.set_focus_on_click(False)
            btn.set_tooltip_text(_('Remove custom command'))
            btn.connect('clicked', lambda b: on_delete())
            box.append(btn)
        self.set_child(box)


def _app_key(app):
    try:
        ident = app.get_id()
    except Exception:
        ident = None
    if ident:
        return str(ident)
    try:
        return str(app.get_executable() or '')
    except Exception:
        return ''


def _app_icon(app):
    try:
        icon = app.get_icon()
    except Exception:
        icon = None
    if icon is not None:
        try:
            return Gtk.Image.new_from_gicon(icon)
        except Exception:
            pass
    return Gtk.Image.new_from_icon_name('application-x-executable-symbolic')


def _app_subtitle(app):
    try:
        line = app.get_commandline()
    except Exception:
        line = ''
    if not line:
        try:
            line = app.get_executable() or ''
        except Exception:
            line = ''
    return line


class OpenWithDialog(DlgBase):
    """Выбор программы для файла: поиск, свои команды и значение по умолчанию."""

    def __init__(self, parent, path, on_pick=None):
        super().__init__(title=_('Open with…'), modal=True, transient_for=parent,
                         destroy_with_parent=True)
        self.set_default_size(600, 700)
        self.path = path
        self.gfile = Gio.File.new_for_path(path)
        self.conf = getattr(parent, 'conf', None) or Config()
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

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text(_('Search applications…'))
        self.search.connect('search-changed', lambda e: self._filter())
        self.search.connect('activate', lambda e: self._ok())
        root.append(self.search)

        custom = vbox(6, 10)
        custom.add_css_class('sz-app-custom')
        title = lbl(_('Custom command'))
        title.add_css_class('sz-app-custom-title')
        custom.append(title)
        self.custom_name = Gtk.Entry(hexpand=True,
                                     placeholder_text=_('Name (optional)'))
        custom.append(self.custom_name)
        line = hbox(6)
        self.custom_entry = Gtk.Entry(hexpand=True,
                                      placeholder_text=_('Command, e.g. gimp %f'))
        self.custom_entry.connect('activate', lambda e: self._add_custom())
        line.append(self.custom_entry)
        add = Gtk.Button(label=_('Add'))
        add.add_css_class('sz-dlg-cancel')
        add.connect('clicked', lambda b: self._add_custom())
        line.append(add)
        custom.append(line)
        hint = lbl(_('The file path is appended to the command. '
                     'Use %f where the path should go.'))
        hint.add_css_class('sz-muted')
        hint.set_wrap(True)
        hint.set_xalign(0.0)
        custom.append(hint)
        root.append(custom)

        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list.add_css_class('sz-app-list')
        self.list.connect('row-activated', lambda *a: self._ok())
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_min_content_height(320)
        self.scroll.set_min_content_width(500)
        self.scroll.add_css_class('sz-app-scroll')
        self.scroll.set_child(self.list)
        self.empty = lbl(_('Nothing found'), 0.5)
        self.empty.add_css_class('sz-muted')
        self.empty.set_valign(Gtk.Align.CENTER)
        self.empty.set_vexpand(True)
        self.stack = Gtk.Stack(vexpand=True)
        self.stack.add_named(self.scroll, 'list')
        self.stack.add_named(self.empty, 'empty')
        self.stack.set_visible_child_name('list')
        root.append(self.stack)

        self.chk = Gtk.CheckButton(label=_('Use by default for this file type'))
        root.append(self.chk)
        row, ok = button_row(self, _('Open'), self._ok)
        root.append(row)
        self.on_pick = on_pick
        self.apps = self._load_apps()
        self.rows = []
        self._reload()
        GLib.idle_add(lambda: (self.search.grab_focus(), False)[1])

    def _load_apps(self):
        """Приложения для типа файла, затем все установленные — без дублей."""
        typed, every, seen = [], [], set()

        def add(app, bucket):
            if app is None:
                return
            try:
                if not app.should_show():
                    return
            except Exception:
                pass
            key = _app_key(app)
            if not key or key in seen:
                return
            seen.add(key)
            bucket.append(app)

        if self.ctype:
            try:
                add(Gio.AppInfo.get_default_for_type(self.ctype, False), typed)
            except GLib.Error:
                pass
            try:
                for app in Gio.AppInfo.get_all_for_type(self.ctype):
                    add(app, typed)
            except GLib.Error:
                pass
        try:
            for app in Gio.AppInfo.get_all():
                add(app, every)
        except GLib.Error:
            pass

        def sort_key(app):
            return (app.get_display_name() or app.get_name() or '').casefold()

        every.sort(key=sort_key)
        return typed + every

    def _default_key(self):
        command = default_command(self.conf, self.path, self.ctype)
        if command:
            return 'cmd:' + command
        if self.ctype:
            try:
                app = Gio.AppInfo.get_default_for_type(self.ctype, False)
            except GLib.Error:
                app = None
            if app is not None:
                return 'app:' + _app_key(app)
        return ''

    def _reload(self, select_key=None):
        current = self.list.get_selected_row()
        if select_key is None and isinstance(current, _AppRow):
            select_key = current.key
        child = self.list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list.remove(child)
            child = nxt
        self.rows = []
        default_key = self._default_key()
        for item in custom_commands(self.conf):
            command = item['command']
            row = _AppRow('cmd:' + command, item['name'], command,
                          'utilities-terminal-symbolic', command=command,
                          default=('cmd:' + command) == default_key,
                          on_delete=lambda c=command: self._remove_custom(c))
            self.rows.append(row)
            self.list.append(row)
        for app in self.apps:
            key = 'app:' + _app_key(app)
            if not key[4:]:
                continue
            name = app.get_display_name() or app.get_name() or key[4:]
            row = _AppRow(key, name, _app_subtitle(app), _app_icon(app),
                          app=app, default=key == default_key)
            self.rows.append(row)
            self.list.append(row)
        self._filter(select_key)

    def _filter(self, select_key=None):
        query = self.search.get_text().strip().lower()
        visible = []
        for row in self.rows:
            show = not query or query in row.search_text
            row.set_visible(show)
            if show:
                visible.append(row)
        if not visible:
            self.stack.set_visible_child_name('empty')
            return
        self.stack.set_visible_child_name('list')
        current = self.list.get_selected_row()
        if select_key is None and isinstance(current, _AppRow) and current.get_visible():
            return
        if select_key is None:
            select_key = self._default_key()
        chosen = next((r for r in visible if r.key == select_key), None) or visible[0]
        self.list.select_row(chosen)

    def _add_custom(self, *a):
        command = self.custom_entry.get_text().strip()
        if not command:
            self.custom_entry.grab_focus()
            return None
        try:
            command_argv(command, self.path)
        except ValueError as e:
            alert(self, _('Invalid command'), str(e))
            return None
        name = self.custom_name.get_text().strip()
        add_custom(self.conf, name, command)
        self.conf.save()
        self.custom_entry.set_text('')
        self.custom_name.set_text('')
        self._reload(select_key='cmd:' + command)
        return 'cmd:' + command

    def _remove_custom(self, command):
        remove_custom(self.conf, command)
        self.conf.save()
        self._reload()

    def _remember(self, app):
        ok = False
        if self.ctype:
            try:
                if app.set_as_default_for_type(self.ctype):
                    ok = True
            except GLib.Error:
                pass
        if not ok:
            ext = os.path.splitext(self.path)[1].lower().lstrip('.')
            if ext:
                try:
                    if app.set_as_default_for_extension(ext):
                        ok = True
                except GLib.Error:
                    pass
        if ok:
            clear_default(self.conf, self.path, self.ctype)
            self.conf.save()
        else:
            alert(self, _('Cannot set the default application'))
        return ok

    def _ok(self):
        if self.custom_entry.get_text().strip():
            if self._add_custom() is None:
                return
        row = self.list.get_selected_row()
        if not isinstance(row, _AppRow) or not row.get_visible():
            return
        if self.chk.get_active():
            if row.command:
                set_default_command(self.conf, row.command, self.path, self.ctype)
                self.conf.save()
            elif row.app is not None and not self._remember(row.app):
                return
        self.close()
        if self.on_pick is not None and row.app is not None:
            self.on_pick(row.app, self.gfile)
            return
        if row.command:
            try:
                spawn(row.command, self.path)
            except (OSError, ValueError) as e:
                alert(self, _('Cannot start the program'), str(e))
            return
        if row.app is None:
            return
        try:
            row.app.launch([self.gfile], None)
        except GLib.Error as e:
            alert(self, _('Cannot open file'), e.message)
