# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _
from .dialogs import DlgBase, grid_row, hbox, make_dd, vbox

# ───────────────────────────── Тест производительности ─────────────────────────────
class BenchmarkDialog(DlgBase):
    def __init__(self, win, sz):
        super().__init__(title=_('Benchmark'), transient_for=win, destroy_with_parent=True)
        self.sz, self.proc = sz, None
        self.set_default_size(680, 460)
        root = vbox(8, 12)
        self.set_child(root)
        g = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.dd_dict = make_dd(['%d MB' % (1 << (n - 20)) for n in range(22, 29)], 2)
        cpus = os.cpu_count() or 1
        self.dd_thr = make_dd([str(i) for i in range(1, cpus * 2 + 1)], cpus - 1)
        self.dd_pass = make_dd(['1', '2', '3', '5', '10'], 0)
        grid_row(g, 0, _('Dictionary size:'), self.dd_dict)
        grid_row(g, 1, _('Number of CPU threads:'), self.dd_thr)
        grid_row(g, 2, _('Passes:'), self.dd_pass)
        root.append(g)
        self.tv = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        sw = Gtk.ScrolledWindow(vexpand=True)
        sw.set_child(self.tv)
        root.append(sw)
        row = hbox(6)
        row.set_halign(Gtk.Align.END)
        self.b_start = Gtk.Button(label=_('Start'))
        self.b_start.add_css_class('suggested-action')
        self.b_start.connect('clicked', self._start)
        self.b_stop = Gtk.Button(label=_('Stop'))
        self.b_stop.set_sensitive(False)
        self.b_stop.connect('clicked', lambda b: self._stop())
        cl = Gtk.Button(label=_('Close'))
        cl.connect('clicked', lambda b: self.close())
        for w in (self.b_start, self.b_stop, cl):
            row.append(w)
        root.append(row)
        self.connect('close-request', lambda w: self._stop() or False)

    def _append(self, text):
        buf = self.tv.get_buffer()
        buf.insert(buf.get_end_iter(), text)
        self.tv.scroll_to_mark(buf.get_insert(), 0, False, 0, 0)
        return False

    def _start(self, b):
        self.tv.get_buffer().set_text('')
        bits = 22 + self.dd_dict.get_selected()
        cmd = [self.sz.bin, 'b', '-mmt=%d' % (self.dd_thr.get_selected() + 1),
               '-md=%d' % bits, self.dd_pass.get_selected_item().get_string()]
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
        except OSError as e:
            self._append(str(e))
            return
        self.b_start.set_sensitive(False)
        self.b_stop.set_sensitive(True)
        proc = self.proc

        def reader():
            for raw in iter(proc.stdout.readline, b''):
                GLib.idle_add(self._append, raw.decode('utf-8', 'replace'))
            proc.wait()
            GLib.idle_add(self._finished)
        threading.Thread(target=reader, daemon=True).start()

    def _finished(self):
        self.b_start.set_sensitive(True)
        self.b_stop.set_sensitive(False)
        return False

    def _stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
