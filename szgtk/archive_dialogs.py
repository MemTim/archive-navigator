# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _, N_
from .display import parse_size, pretty_size_token
from .dialogs import (DlgBase, alert, button_row, grid_row, hbox, lbl,
                      make_dd, pick, set_dd, vbox)

# ───────────────────────────── «Добавить в архив» ─────────────────────────────
FORMATS = ['7z', 'zip', 'tar', 'gzip', 'bzip2', 'xz', 'wim']
FMT = {
    '7z':    dict(ext='7z',  methods=['LZMA2', 'LZMA', 'PPMd', 'BZip2', 'Deflate', 'Copy'],
                  level=True, solid=True, enc=True, hdr=True, mt=True, sfx=True),
    'zip':   dict(ext='zip', methods=['Deflate', 'Deflate64', 'BZip2', 'LZMA', 'PPMd', 'Copy'],
                  level=True, solid=False, enc=True, hdr=False, mt=True, sfx=False),
    'tar':   dict(ext='tar', methods=[], level=False, solid=False, enc=False, hdr=False, mt=False, sfx=False),
    'gzip':  dict(ext='gz',  methods=['Deflate'], level=True, solid=False, enc=False, hdr=False, mt=False, sfx=False),
    'bzip2': dict(ext='bz2', methods=['BZip2'], level=True, solid=False, enc=False, hdr=False, mt=True, sfx=False),
    'xz':    dict(ext='xz',  methods=['LZMA2'], level=True, solid=False, enc=False, hdr=False, mt=True, sfx=False),
    'wim':   dict(ext='wim', methods=[], level=False, solid=False, enc=False, hdr=False, mt=False, sfx=False),
}
LEVELS = [(0, N_('Store')), (1, N_('Fastest')), (3, N_('Fast')), (5, N_('Normal')),
          (7, N_('Maximum')), (9, N_('Ultra'))]
UPDATE_MODES = [('add', N_('Add and replace files')), ('update', N_('Update and add files')),
                ('fresh', N_('Freshen existing files')), ('sync', N_('Synchronize files'))]
PATH_MODES = [('relative', N_('Relative pathnames')), ('full', N_('Full pathnames')),
              ('abs', N_('Absolute pathnames'))]
DICT_LZMA = ['64k', '256k', '1m', '2m', '4m', '8m', '16m', '32m', '64m', '128m', '256m',
             '512m', '1024m', '1536m']
DICT_PPMD = ['1m', '2m', '4m', '8m', '16m', '32m', '64m', '128m', '256m', '512m', '1024m']
DICT_BZ = ['100k', '200k', '300k', '400k', '500k', '600k', '700k', '800k', '900k']
WORD_LZMA = ['5', '6', '8', '12', '16', '24', '32', '48', '64', '96', '128', '192', '256', '273']
WORD_PPMD = ['2', '3', '4', '5', '6', '7', '8', '10', '12', '16', '20', '24', '32']
WORD_DEFL = ['8', '12', '16', '24', '32', '48', '64', '96', '128', '192', '256', '258']
SOLID = ['off', '1m', '2m', '4m', '8m', '16m', '32m', '64m', '128m', '256m', '512m',
         '1g', '2g', '4g', '8g', '16g', '32g', '64g', 'on']
MEM_CHOICES = ['p25', 'p50', 'p75', 'p100']


def method_params(method):
    if method in ('LZMA2', 'LZMA'):
        return DICT_LZMA, WORD_LZMA
    if method == 'PPMd':
        return DICT_PPMD, WORD_PPMD
    if method == 'BZip2':
        return DICT_BZ, None
    if method in ('Deflate', 'Deflate64'):
        return None, WORD_DEFL
    return None, None


def default_add_opts(fmt, archive):
    return dict(archive=archive, fmt=fmt, level=5, method=None, dict=None, word=None,
                solid=None, threads=None, mem=None, update='add', pathmode='relative',
                sfx=False, shared=False, delete=False, symlinks=False, password='',
                enc_names=False, enc_method='AES256', volumes='', params='')


def build_add_switches(o, exists, p7zip):
    fmt, sw = o['fmt'], []
    f = FMT[fmt]
    if not exists:
        sw.append('-t' + fmt)
    if f['level']:
        sw.append('-mx=%d' % o['level'])
    m = o.get('method')
    if m and o['level'] != 0:
        if fmt in ('7z', 'zip') or len(f['methods']) > 1:
            sw.append(('-m0=' if fmt == '7z' else '-mm=') + m)
        if o.get('dict'):
            sw.append(('-mmem=' if m == 'PPMd' else '-md=') + o['dict'])
        if o.get('word'):
            sw.append(('-mo=' if m == 'PPMd' else '-mfb=') + o['word'])
    if fmt == '7z' and o.get('solid'):
        sw.append('-ms=' + o['solid'])
    if o.get('threads'):
        sw.append('-mmt=' + o['threads'])
    if o.get('mem'):
        sw.append('-mmemuse=' + o['mem'])
    if o.get('password'):
        if fmt == '7z' and o.get('enc_names'):
            sw.append('-mhe=on')
        if fmt == 'zip':
            sw.append('-mem=' + ('ZipCrypto' if o.get('enc_method') == 'ZipCrypto' else 'AES256'))
    if o.get('sfx') and fmt == '7z':
        sw.append('-sfx')
    if o.get('shared'):
        sw.append('-ssw')
    if o.get('delete'):
        sw.append('-sdel')
    if p7zip:
        if not o.get('symlinks'):
            sw.append('-l')
    elif o.get('symlinks'):
        sw.append('-snl')
    if o['pathmode'] == 'full':
        sw.append('-spf')
    elif o['pathmode'] == 'abs':
        sw.append('-spf2')
    if o.get('volumes'):
        sw.append('-v' + o['volumes'])
    if o.get('params'):
        try:
            sw += shlex.split(o['params'])
        except ValueError:
            pass
    if o['update'] == 'fresh':
        sw.append('-up1q1r0x1y2z1w1')
    elif o['update'] == 'sync':
        sw.append('-up1q0r2x1y2z1w1')
    return sw


class AddDialog(DlgBase):
    def __init__(self, win, archive, on_ok, fmt='7z', level=5):
        super().__init__(title=_('Add to Archive'), modal=True, transient_for=win,
                         destroy_with_parent=True)
        self.win, self.on_ok, self._ready = win, on_ok, False
        self.dict_vals, self.word_vals = [None], [None]
        root = vbox(10, 14)
        self.set_child(root)

        row = hbox(6)
        row.append(lbl(_('Archive:')))
        self.e_name = Gtk.Entry(hexpand=True, text=archive)
        self.e_name.set_size_request(520, -1)
        row.append(self.e_name)
        b = Gtk.Button(label='…')
        b.connect('clicked', self._browse)
        row.append(b)
        root.append(row)

        cols = hbox(14)
        root.append(cols)
        left = Gtk.Grid(row_spacing=6, column_spacing=8)
        cols.append(left)
        self.dd_fmt = make_dd(FORMATS, FORMATS.index(fmt) if fmt in FORMATS else 0)
        self.dd_level = make_dd([_(x[1]) for x in LEVELS], [x[0] for x in LEVELS].index(level)
                                if level in [x[0] for x in LEVELS] else 3)
        self.dd_method = make_dd(['-'])
        self.dd_dict = make_dd([_('Auto')])
        self.dd_word = make_dd([_('Auto')])
        self.dd_solid = make_dd([_('Auto')] + [_('Non-solid') if s == 'off' else
                                               _('Solid') if s == 'on' else pretty_size_token(s)
                                               for s in SOLID])
        cpus = os.cpu_count() or 1
        self.dd_threads = make_dd([_('Auto')] + [str(i) for i in range(1, cpus + 1)])
        self.dd_mem = make_dd([_('Auto')] + ['%s%%' % m[1:] for m in MEM_CHOICES])
        grid_row(left, 0, _('Archive format:'), self.dd_fmt)
        grid_row(left, 1, _('Compression level:'), self.dd_level)
        grid_row(left, 2, _('Compression method:'), self.dd_method)
        self.l_dict = grid_row(left, 3, _('Dictionary size:'), self.dd_dict)
        self.l_word = grid_row(left, 4, _('Word size:'), self.dd_word)
        grid_row(left, 5, _('Solid block size:'), self.dd_solid)
        grid_row(left, 6, _('Number of CPU threads:'), self.dd_threads)
        grid_row(left, 7, _('Memory usage:'), self.dd_mem)

        right = vbox(8)
        cols.append(right)
        g2 = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.dd_update = make_dd([_(x[1]) for x in UPDATE_MODES])
        self.dd_path = make_dd([_(x[1]) for x in PATH_MODES])
        grid_row(g2, 0, _('Update mode:'), self.dd_update)
        grid_row(g2, 1, _('Path mode:'), self.dd_path)
        right.append(g2)

        fo = Gtk.Frame(label=_('Options'))
        ob = vbox(4, 8)
        fo.set_child(ob)
        self.c_sfx = Gtk.CheckButton(label=_('Create SFX archive'))
        self.c_shared = Gtk.CheckButton(label=_('Compress shared files'))
        self.c_del = Gtk.CheckButton(label=_('Delete files after compression'))
        self.c_links = Gtk.CheckButton(label=_('Store symbolic links as links'))
        for c in (self.c_sfx, self.c_shared, self.c_del, self.c_links):
            ob.append(c)
        right.append(fo)

        fe = Gtk.Frame(label=_('Encryption'))
        eb = vbox(4, 8)
        fe.set_child(eb)
        self.e_pw1 = Gtk.PasswordEntry(show_peek_icon=True)
        self.e_pw2 = Gtk.PasswordEntry(show_peek_icon=True)
        eb.append(lbl(_('Enter password:')))
        eb.append(self.e_pw1)
        eb.append(lbl(_('Reenter password:')))
        eb.append(self.e_pw2)
        self.dd_enc = make_dd(['AES-256', 'ZipCrypto'])
        eb.append(self.dd_enc)
        self.c_hdr = Gtk.CheckButton(label=_('Encrypt file names'))
        eb.append(self.c_hdr)
        right.append(fe)

        g3 = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.e_vol = Gtk.Entry(hexpand=True, placeholder_text='100m, 700m, 4480m …')
        self.e_par = Gtk.Entry(hexpand=True, placeholder_text='-mqs=on -mf=BCJ2 …')
        grid_row(g3, 0, _('Split to volumes, bytes:'), self.e_vol)
        grid_row(g3, 1, _('Parameters:'), self.e_par)
        root.append(g3)

        brow, ok = button_row(self, _('OK'), self._ok)
        root.append(brow)

        self._ready = True
        GLib.idle_add(self._select_stem)
        self.dd_fmt.connect('notify::selected', self._on_fmt)
        self.dd_level.connect('notify::selected', self._on_method)
        self.dd_method.connect('notify::selected', self._on_method)
        self._on_fmt(refresh_name=False)

    def _select_stem(self):
        t = self.e_name.get_text()
        start = len(os.path.dirname(t)) + 1 if os.path.dirname(t) else 0
        end = len(os.path.splitext(t)[0])
        self.e_name.grab_focus()
        self.e_name.select_region(start, end)
        return False

    # --- реакции на смену формата / метода ---
    def _fkey(self):
        return FORMATS[self.dd_fmt.get_selected()]

    def _cur_method(self):
        ms = FMT[self._fkey()]['methods']
        return ms[self.dd_method.get_selected()] if ms and self.dd_method.get_selected() < len(ms) else None

    def _on_fmt(self, *a, refresh_name=True):
        if not self._ready:
            return
        k = self._fkey()
        f = FMT[k]
        if refresh_name:
            name = self.e_name.get_text()
            for e in [x['ext'] for x in FMT.values()]:
                if name.lower().endswith('.' + e):
                    name = name[:-(len(e) + 1)]
                    break
            self.e_name.set_text(name + '.' + f['ext'])
        self._ready = False
        set_dd(self.dd_method, f['methods'] or ['-'], 0)
        self._ready = True
        self.dd_level.set_sensitive(f['level'])
        self.dd_solid.set_sensitive(f['solid'])
        self.dd_threads.set_sensitive(f['mt'])
        self.dd_mem.set_sensitive(f['mt'])
        self.c_sfx.set_sensitive(f['sfx'])
        self.e_pw1.set_sensitive(f['enc'])
        self.e_pw2.set_sensitive(f['enc'])
        self.dd_enc.set_sensitive(k == 'zip')
        self.c_hdr.set_sensitive(f['hdr'])
        self._on_method()

    def _on_method(self, *a):
        if not self._ready:
            return
        f = FMT[self._fkey()]
        m = self._cur_method()
        store = LEVELS[self.dd_level.get_selected()][0] == 0
        self.dd_method.set_sensitive(len(f['methods']) > 1 and not store)
        dl, wl = (None, None) if (store or m == 'Copy') else method_params(m)
        self.l_dict.set_label(_('Memory size:') if m == 'PPMd' else _('Dictionary size:'))
        self.l_word.set_label(_('Order:') if m == 'PPMd' else _('Word size:'))
        self.dict_vals = [None] + (dl or [])
        self.word_vals = [None] + (wl or [])
        set_dd(self.dd_dict, [_('Auto')] + [pretty_size_token(x) for x in (dl or [])], 0)
        set_dd(self.dd_word, [_('Auto')] + list(wl or []), 0)
        self.dd_dict.set_sensitive(bool(dl))
        self.dd_word.set_sensitive(bool(wl))

    def _browse(self, b):
        cur = self.e_name.get_text()
        pick(self, 'save', _('Archive'), lambda p: self.e_name.set_text(p[0]),
             initial=os.path.dirname(cur), name=os.path.basename(cur))

    def _ok(self):
        name = self.e_name.get_text().strip()
        if not name:
            return
        pw = self.e_pw1.get_text()
        if pw != self.e_pw2.get_text():
            alert(self, _('Passwords do not match'))
            return
        vol = self.e_vol.get_text().strip()
        if vol and not re.fullmatch(r'\d+[bBkKmMgG]?', vol):
            alert(self, _('Invalid volume size'))
            return
        k = self._fkey()
        f = FMT[k]
        sol = self.dd_solid.get_selected()
        thr = self.dd_threads.get_selected()
        mem = self.dd_mem.get_selected()
        o = default_add_opts(k, name)
        o.update(
            level=LEVELS[self.dd_level.get_selected()][0],
            method=self._cur_method(),
            dict=self.dict_vals[self.dd_dict.get_selected()] if self.dict_vals else None,
            word=self.word_vals[self.dd_word.get_selected()] if self.word_vals else None,
            solid=SOLID[sol - 1] if sol > 0 else None,
            threads=str(thr) if thr > 0 else None,
            mem=MEM_CHOICES[mem - 1] if mem > 0 else None,
            update=UPDATE_MODES[self.dd_update.get_selected()][0],
            pathmode=PATH_MODES[self.dd_path.get_selected()][0],
            sfx=self.c_sfx.get_active(), shared=self.c_shared.get_active(),
            delete=self.c_del.get_active(), symlinks=self.c_links.get_active(),
            password=pw, enc_names=self.c_hdr.get_active(),
            enc_method='ZipCrypto' if self.dd_enc.get_selected() == 1 else 'AES256',
            volumes=vol, params=self.e_par.get_text().strip())
        self.close()
        self.on_ok(o)


# ───────────────────────────── «Распаковать» ─────────────────────────────
EXTRACT_PATHMODES = [('full', N_('Full pathnames')), ('none', N_('No pathnames')),
                     ('abs', N_('Absolute pathnames'))]
OVERWRITE_MODES = [('ask', N_('Ask before overwrite')), ('overwrite', N_('Overwrite without prompt')),
                   ('skip', N_('Skip existing files')), ('rename', N_('Auto rename')),
                   ('rename_existing', N_('Auto rename existing files'))]


def extract_switches(opts, dest):
    cmd = 'e' if opts['pathmode'] == 'none' else 'x'
    sw = ['-o' + dest, '-y', {'overwrite': '-aoa', 'skip': '-aos', 'rename': '-aou',
                              'rename_existing': '-aot', 'ask': '-aoa'}[opts['overwrite']]]
    if opts['pathmode'] == 'abs':
        sw.append('-spf')
    if opts.get('nodup'):
        sw.append('-spe')
    return cmd, sw


class ExtractDialog(DlgBase):
    def __init__(self, win, title, dest, on_ok, can_nodup=True, pathmode='full', overwrite='ask'):
        super().__init__(title=title, modal=True, transient_for=win, destroy_with_parent=True)
        self.on_ok = on_ok
        root = vbox(10, 14)
        self.set_child(root)
        root.append(lbl(_('Extract to:')))
        row = hbox(6)
        self.e = Gtk.Entry(hexpand=True, text=dest, activates_default=True)
        self.e.set_size_request(520, -1)
        row.append(self.e)
        b = Gtk.Button(label='…')
        b.connect('clicked', lambda x: pick(self, 'folder', _('Extract to:'),
                                            lambda p: self.e.set_text(p[0]),
                                            initial=os.path.dirname(self.e.get_text().rstrip('/'))))
        row.append(b)
        root.append(row)
        g = Gtk.Grid(row_spacing=6, column_spacing=8)
        self.dd_path = make_dd([_(x[1]) for x in EXTRACT_PATHMODES],
                               [x[0] for x in EXTRACT_PATHMODES].index(pathmode) if pathmode in [x[0] for x in EXTRACT_PATHMODES] else 0)
        self.dd_over = make_dd([_(x[1]) for x in OVERWRITE_MODES],
                               [x[0] for x in OVERWRITE_MODES].index(overwrite) if overwrite in [x[0] for x in OVERWRITE_MODES] else 0)
        grid_row(g, 0, _('Path mode:'), self.dd_path)
        grid_row(g, 1, _('Overwrite mode:'), self.dd_over)
        root.append(g)
        self.c_nodup = Gtk.CheckButton(label=_('Eliminate duplication of root folder'))
        self.c_nodup.set_sensitive(can_nodup)
        root.append(self.c_nodup)
        root.append(lbl(_('Password:')))
        self.e_pw = Gtk.PasswordEntry(show_peek_icon=True)
        root.append(self.e_pw)
        brow, ok = button_row(self, _('OK'), self._ok)
        root.append(brow)

    def _ok(self):
        d = self.e.get_text().strip()
        if not d:
            return
        o = dict(pathmode=EXTRACT_PATHMODES[self.dd_path.get_selected()][0],
                 overwrite=OVERWRITE_MODES[self.dd_over.get_selected()][0],
                 nodup=self.c_nodup.get_active(), password=self.e_pw.get_text())
        self.close()
        self.on_ok(os.path.expanduser(d), o)


# ───────────────────────────── Разбить / Склеить ─────────────────────────────
SPLIT_PRESETS = ['10M', '100M', '650M - CD', '700M - CD', '4480M - DVD', '1G', '4G']


def split_worker(src, dest_dir, size, job):
    total = os.path.getsize(src)
    done, n = 0, 1
    base = os.path.join(dest_dir, os.path.basename(src))
    with open(src, 'rb') as f:
        while not job.cancelled:
            part = '%s.%03d' % (base, n)
            written = 0
            with open(part, 'wb') as o:
                while written < size and not job.cancelled:
                    chunk = f.read(min(1 << 20, size - written))
                    if not chunk:
                        break
                    o.write(chunk)
                    written += len(chunk)
                    done += len(chunk)
                    job.fraction = done / total if total else 1.0
                    job.text = os.path.basename(part)
            if written == 0 or job.cancelled:
                os.remove(part)
                break
            n += 1
            if written < size:
                break
    return n - 1


def combine_worker(first_part, out_path, job):
    m = re.match(r'^(.*)\.(\d{3})$', first_part)
    if not m:
        raise ValueError('not a .001 file')
    base, n = m.group(1), int(m.group(2))
    parts = []
    while os.path.exists('%s.%03d' % (base, n)):
        parts.append('%s.%03d' % (base, n))
        n += 1
    total = sum(os.path.getsize(p) for p in parts) or 1
    done = 0
    with open(out_path, 'wb') as o:
        for p in parts:
            job.text = os.path.basename(p)
            with open(p, 'rb') as f:
                while not job.cancelled:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    o.write(chunk)
                    done += len(chunk)
                    job.fraction = done / total
            if job.cancelled:
                break
    if job.cancelled:
        os.remove(out_path)
    return len(parts)


class SplitDialog(DlgBase):
    def __init__(self, win, src, on_ok):
        super().__init__(title=_('Split File'), modal=True, transient_for=win,
                         destroy_with_parent=True)
        self.on_ok = on_ok
        root = vbox(8, 14)
        self.set_child(root)
        root.append(lbl(_('Split') + ': ' + src))
        root.append(lbl(_('Split to:')))
        row = hbox(6)
        self.e_dest = Gtk.Entry(hexpand=True, text=os.path.dirname(src))
        self.e_dest.set_size_request(480, -1)
        b = Gtk.Button(label='…')
        b.connect('clicked', lambda x: pick(self, 'folder', _('Split to:'),
                                            lambda p: self.e_dest.set_text(p[0]),
                                            initial=self.e_dest.get_text()))
        row.append(self.e_dest)
        row.append(b)
        root.append(row)
        root.append(lbl(_('Split to volumes, bytes:')))
        row2 = hbox(6)
        self.e_size = Gtk.Entry(hexpand=True, text='100M', activates_default=True)
        self.dd = make_dd(SPLIT_PRESETS, 1)
        self.dd.connect('notify::selected', lambda d, p: self.e_size.set_text(
            SPLIT_PRESETS[d.get_selected()].split()[0]))
        row2.append(self.e_size)
        row2.append(self.dd)
        root.append(row2)
        brow, ok = button_row(self, _('OK'), self._ok)
        root.append(brow)

    def _ok(self):
        size = parse_size(self.e_size.get_text())
        if size <= 0:
            alert(self, _('Invalid volume size'))
            return
        dest = self.e_dest.get_text().strip()
        self.close()
        self.on_ok(dest, size)
