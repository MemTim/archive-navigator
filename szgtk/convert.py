# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _, N_
from .dialogs import (DlgBase, alert, button_row, grid_row, hbox, lbl, make_dd,
                      pick, vbox)
from .settings import _drawing, _fav_arrow, _fav_plus, _fav_x
from . import vfs

# ───────────────────────────── форматы ─────────────────────────────
AUDIO_FORMATS = [
    ('mp3', 'MP3'), ('m4a', 'M4A (AAC)'), ('aac', 'AAC'), ('ogg', 'OGG Vorbis'),
    ('opus', 'Opus'), ('flac', 'FLAC'), ('wav', 'WAV'), ('aiff', 'AIFF'),
    ('wma', 'WMA'), ('ac3', 'AC-3'), ('mka', 'MKA'),
]
VIDEO_FORMATS = [
    ('mp4', 'MP4'), ('mkv', 'MKV'), ('webm', 'WebM'), ('mov', 'MOV'), ('m4v', 'M4V'),
    ('avi', 'AVI'), ('mpg', 'MPEG'), ('wmv', 'WMV'), ('flv', 'FLV'), ('ts', 'TS'),
    ('ogv', 'OGV'), ('gif', 'GIF (animation)'),
]
IMAGE_FORMATS = [
    ('png', 'PNG'), ('jpg', 'JPEG'), ('webp', 'WebP'), ('avif', 'AVIF'), ('bmp', 'BMP'),
    ('gif', 'GIF'), ('tiff', 'TIFF'), ('ico', 'ICO'), ('pdf', 'PDF'), ('tga', 'TGA'),
    ('ppm', 'PPM'), ('jxl', 'JPEG XL'),
]

AUDIO_EXTS = {'mp3', 'm4a', 'aac', 'ogg', 'oga', 'opus', 'flac', 'wav', 'aiff', 'aif',
              'wma', 'ac3', 'mka', 'ape', 'wv', 'amr', 'mid', 'midi'}
VIDEO_EXTS = {'mp4', 'mkv', 'avi', 'mov', 'webm', 'flv', 'wmv', 'm4v', 'mpg', 'mpeg',
              'ts', 'mts', 'm2ts', 'ogv', '3gp'}
IMAGE_EXTS = {'png', 'jpg', 'jpeg', 'webp', 'avif', 'bmp', 'gif', 'tif', 'tiff', 'ico',
              'pdf', 'tga', 'ppm', 'pgm', 'svg', 'heic', 'heif', 'jxl'}

KIND_LABELS = {'audio': N_('Audio'), 'video': N_('Video'), 'image': N_('Images')}
QUALITIES = [('high', N_('High')), ('normal', N_('Normal')), ('small', N_('Small'))]
AUDIO_BITRATE = {'high': '320k', 'normal': '192k', 'small': '128k'}
VIDEO_CRF = {'high': 18, 'normal': 23, 'small': 28}
IMAGE_QUALITY = {'high': '95', 'normal': '88', 'small': '75'}
# Форматы, которые не хранят несколько кадров: из GIF/TIFF/PDF берём первый кадр.
SINGLE_FRAME_TARGETS = {'jpg', 'jpeg', 'png', 'bmp', 'ppm', 'tga', 'ico', 'avif', 'jxl'}


def ext_of(path):
    name = vfs.basename(path) or path
    return os.path.splitext(name)[1][1:].lower()


def kind_of(path):
    e = ext_of(path)
    if e in IMAGE_EXTS:
        return 'image'
    if e in VIDEO_EXTS:
        return 'video'
    if e in AUDIO_EXTS:
        return 'audio'
    return None


def options_for(kind):
    if kind == 'video':
        return VIDEO_FORMATS + AUDIO_FORMATS
    if kind == 'audio':
        return AUDIO_FORMATS
    return IMAGE_FORMATS


def supports(path, target):
    return target in {e for e, _n in options_for(kind_of(path))}


def build_convert_menu(paths):
    kinds = [k for k in ('audio', 'video', 'image') if any(kind_of(p) == k for p in paths)]
    menu = Gio.Menu()

    def fill(m, opts):
        for ext, label in opts:
            it = Gio.MenuItem.new(_(label), None)
            it.set_action_and_target_value('win.convert-to', GLib.Variant.new_string(ext))
            m.append_item(it)

    if kinds == ['video']:
        v, a = Gio.Menu(), Gio.Menu()
        fill(v, VIDEO_FORMATS)
        fill(a, AUDIO_FORMATS)
        menu.append_submenu(_('Video'), v)
        menu.append_submenu(_('Audio'), a)
    elif len(kinds) == 1:
        fill(menu, options_for(kinds[0]))
    else:
        for kind in kinds:
            sub = Gio.Menu()
            fill(sub, VIDEO_FORMATS if kind == 'video' else options_for(kind))
            menu.append_submenu(_(KIND_LABELS[kind]), sub)
    return menu


# ───────────────────────────── команды преобразования ─────────────────────────────
def _audio_args(ext, quality):
    br = AUDIO_BITRATE[quality]
    if ext == 'mp3':
        return ['-c:a', 'libmp3lame', '-b:a', br]
    if ext in ('m4a', 'aac'):
        return ['-c:a', 'aac', '-b:a', br]
    if ext == 'ogg':
        return ['-c:a', 'libvorbis', '-q:a', {'high': '8', 'normal': '6', 'small': '4'}[quality]]
    if ext == 'opus':
        return ['-c:a', 'libopus', '-b:a', br]
    if ext == 'flac':
        return ['-c:a', 'flac']
    if ext == 'wav':
        return ['-c:a', 'pcm_s16le']
    if ext == 'aiff':
        return ['-c:a', 'pcm_s16be']
    if ext == 'wma':
        return ['-c:a', 'wmav2', '-b:a', br]
    if ext == 'ac3':
        return ['-c:a', 'ac3', '-b:a', {'high': '192k', 'normal': '160k', 'small': '128k'}[quality]]
    if ext == 'mka':
        return ['-c:a', 'flac']
    return ['-c:a', 'copy']


def _video_args(ext, quality):
    crf = VIDEO_CRF[quality]
    br = {'high': '192k', 'normal': '160k', 'small': '128k'}[quality]
    qv = {'high': '2', 'normal': '4', 'small': '6'}[quality]
    if ext in ('mp4', 'm4v', 'mov', 'mkv'):
        a = ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-c:a', 'aac', '-b:a', br]
        if ext != 'mkv':
            a += ['-movflags', '+faststart']
    elif ext == 'webm':
        a = ['-c:v', 'libvpx-vp9', '-crf', str(crf + 8), '-b:v', '0',
             '-c:a', 'libopus', '-b:a', br]
    elif ext == 'avi':
        a = ['-c:v', 'mpeg4', '-vtag', 'XVID', '-q:v', qv, '-c:a', 'libmp3lame', '-b:a', br]
    elif ext == 'mpg':
        a = ['-c:v', 'mpeg2video', '-q:v', qv, '-c:a', 'mp2', '-b:a', br]
    elif ext == 'wmv':
        a = ['-c:v', 'wmv2', '-q:v', qv, '-c:a', 'wmav2', '-b:a', br]
    elif ext == 'flv':
        a = ['-c:v', 'flv', '-q:v', qv, '-c:a', 'libmp3lame', '-b:a', br]
    elif ext == 'ts':
        a = ['-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-c:a', 'aac', '-b:a', br]
    elif ext == 'ogv':
        a = ['-c:v', 'libtheora', '-q:v', {'high': '8', 'normal': '6', 'small': '4'}[quality],
             '-c:a', 'libvorbis', '-q:a', '5']
    elif ext == 'gif':
        fps = {'high': '15', 'normal': '12', 'small': '10'}[quality]
        a = ['-vf', 'fps=' + fps + ',split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
             '-an', '-loop', '0']
    else:
        a = ['-c:v', 'libx264', '-crf', str(crf), '-c:a', 'aac', '-b:a', br]
    return a


def _image_cmd(src, dst, target, quality):
    exe = shutil.which('magick') or shutil.which('convert')
    if exe:
        isrc = src + '[0]' if ext_of(src) == 'pdf' or target in SINGLE_FRAME_TARGETS else src
        cmd = [exe, isrc, '-auto-orient']
        if target in ('jpg', 'jpeg', 'webp', 'avif', 'heic', 'jxl'):
            cmd += ['-quality', IMAGE_QUALITY[quality]]
        elif target == 'png':
            cmd += ['-define', 'png:compression-level=9']
        elif target == 'ico':
            cmd += ['-define', 'icon:auto-resize=256,128,64,48,32,16']
        return cmd + [dst]
    ff = shutil.which('ffmpeg')
    if not ff:
        return None
    q = {'high': '2', 'normal': '4', 'small': '6'}[quality]
    cmd = [ff, '-y', '-i', src]
    if target in ('jpg', 'jpeg'):
        cmd += ['-q:v', q]
    elif target == 'webp':
        cmd += ['-quality', IMAGE_QUALITY[quality]]
    elif target == 'png':
        cmd += ['-compression_level', '6']
    return cmd + [dst]


def _duration(path):
    exe = shutil.which('ffprobe')
    if not exe:
        return None
    try:
        out = subprocess.run([exe, '-v', 'error', '-show_entries', 'format=duration',
                              '-of', 'default=nw=1:nk=1', path],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return float(out) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _run(cmd, job, duration=None, index=0, total=1):
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    job.register(proc)
    errors = []
    start = index / float(total or 1)
    span = 1 / float(total or 1)
    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith('out_time_ms=') and duration:
                try:
                    t = int(line.split('=', 1)[1]) / 1000000.0
                    job.fraction = min(1.0, start + span * min(1.0, t / duration))
                except (ValueError, ZeroDivisionError):
                    pass
            elif line and not line.startswith(('frame=', 'fps=', 'stream_0', 'bitrate=',
                                               'total_size=', 'out_time', 'dup_frames',
                                               'drop_frames', 'speed=', 'progress=')):
                errors.append(line)
    finally:
        proc.stdout.close()
    rc = proc.wait()
    if job.cancelled:
        return False
    if rc != 0:
        raise RuntimeError('\n'.join(errors[-8:]) or 'ffmpeg exit code %d' % rc)
    return True


def convert_files(items, job, quality='normal'):
    total = len(items)
    done = []
    for i, (src, dst, target) in enumerate(items):
        if job.cancelled:
            break
        job.fraction = i / float(total or 1)
        job.text = '%d/%d · %s → %s' % (i + 1, total, vfs.basename(src), target.upper())
        tmp_src = tmp_out = None
        local_src, local_dst = src, dst
        src_admin, dst_admin = vfs.is_admin(src), vfs.is_admin(dst)
        try:
            if src_admin:
                tmp_src, local_src = vfs.copy_to_temp(src)
            if dst_admin:
                tmp_out = tempfile.mkdtemp(prefix='7zgtk-conv-')
                local_dst = os.path.join(tmp_out, vfs.basename(dst))
            d = os.path.dirname(local_dst)
            if d:
                os.makedirs(d, exist_ok=True)
            existed = vfs.exists(dst)
            ok = False
            try:
                if kind_of(local_src) == 'image':
                    cmd = _image_cmd(local_src, local_dst, target, quality)
                    if cmd is None:
                        raise RuntimeError(_('ImageMagick not found'))
                    duration = None
                else:
                    ff = shutil.which('ffmpeg')
                    if not ff:
                        raise RuntimeError(_('ffmpeg not found'))
                    duration = _duration(local_src)
                    cmd = [ff, '-y', '-i', local_src, '-progress', 'pipe:1', '-nostats']
                    cmd += (['-vn'] if target in {e for e, _n in AUDIO_FORMATS} else [])
                    cmd += _audio_args(target, quality) if target in {e for e, _n in AUDIO_FORMATS} \
                        else _video_args(target, quality)
                    cmd.append(local_dst)
                ok = _run(cmd, job, duration, i, total)
            finally:
                if not ok and not existed:
                    try:
                        os.remove(local_dst)
                    except OSError:
                        pass
            if not ok:
                break
            if dst_admin:
                vfs.copy_from_temp(local_dst, dst)
            done.append(dst)
        finally:
            if tmp_src:
                shutil.rmtree(tmp_src, ignore_errors=True)
            if tmp_out:
                shutil.rmtree(tmp_out, ignore_errors=True)
    if not job.cancelled:
        job.fraction = 1.0
    return done


# ───────────────────────────── диалог ─────────────────────────────
class ConverterDialog(DlgBase):
    def __init__(self, win, paths, target=None, on_ok=None):
        super().__init__(title=_('Converter'), modal=True, transient_for=win,
                         destroy_with_parent=True)
        self.win, self.on_ok, self.target = win, on_ok, target
        self.add_css_class('sz-settings')
        self.set_default_size(820, 560)
        if target is not None:
            paths = [p for p in paths if supports(p, target)]
        self.files = [p for p in paths if kind_of(p)]
        self.targets = []
        for p in self.files:
            k = kind_of(p)
            opts = [e for e, _n in options_for(k)]
            self.targets.append(target if target in opts else self._default_target(p, k))
        self.sel = 0 if self.files else -1

        root = vbox(10, 14)
        self.set_child(root)
        hint = lbl(_('Convert audio, video and images to another format. The originals are kept.'))
        hint.add_css_class('sz-muted')
        hint.set_wrap(True)
        root.append(hint)

        page = vbox(8)
        self.rows_box = vbox(8)
        page.append(self.rows_box)
        self.add_btn = Gtk.Button()
        self.add_btn.add_css_class('sz-fav-add')
        self.add_btn.set_tooltip_text(_('Add files'))
        self.add_btn.set_child(_drawing(28, 28, _fav_plus, 'sz-fav-plus'))
        self.add_btn.connect('clicked', lambda b: self._add_files())
        page.append(self.add_btn)
        sw = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(page)
        root.append(sw)

        g = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.e_out = Gtk.Entry(hexpand=True, placeholder_text=_('Next to the original file'))
        self.e_out.add_css_class('sz-fav-field')
        browse = Gtk.Button(label='…')
        browse.set_tooltip_text(_('Choose folder'))
        browse.connect('clicked', self._browse_out)
        row = hbox(6)
        row.append(self.e_out)
        row.append(browse)
        grid_row(g, 0, _('Output folder:'), row)
        self.dd_quality = make_dd([_(x[1]) for x in QUALITIES], 1)
        grid_row(g, 1, _('Quality:'), self.dd_quality)
        root.append(g)

        brow, ok = button_row(self, _('Convert'), self._ok)
        ok.set_sensitive(bool(self.files))
        self.ok_btn = ok
        root.append(brow)
        self._rebuild()

    @staticmethod
    def _default_target(path, kind):
        ext = ext_of(path)
        opts = [e for e, _n in options_for(kind)]
        return next((e for e in opts if e != ext), opts[0])

    def _rebuild(self):
        ch = self.rows_box.get_first_child()
        while ch is not None:
            nxt = ch.get_next_sibling()
            self.rows_box.remove(ch)
            ch = nxt
        self.rows = []
        if self.files:
            self.sel = max(0, min(self.sel, len(self.files) - 1))
        else:
            self.sel = -1
        for i in range(len(self.files)):
            self.rows_box.append(self._row(i))
        self.ok_btn.set_sensitive(bool(self.files))

    def _row(self, idx):
        path = self.files[idx]
        kind = kind_of(path)
        row = hbox(8)
        row.add_css_class('sz-fav-row')
        if idx == self.sel:
            row.add_css_class('sz-fav-sel')
        click = Gtk.GestureClick()
        click.connect('pressed', lambda g, n, x, y, i=idx: self._select(i))
        row.add_controller(click)
        num = lbl('%d.' % (idx + 1), 0.5)
        num.add_css_class('sz-fav-num')
        num.set_size_request(30, -1)
        src = Gtk.Entry(hexpand=True, editable=False, text=vfs.display(path))
        src.add_css_class('sz-fav-field')
        src.set_size_request(-1, 34)
        src.set_can_focus(False)
        src.set_tooltip_text(vfs.display(path))
        arrow = _drawing(44, 18, _fav_arrow, 'sz-fav-arrow')
        opts = options_for(kind)
        dd = Gtk.DropDown.new_from_strings([_(n) for _e, n in opts])
        dd.add_css_class('sz-conv-dd')
        dd.set_hexpand(True)
        dd.set_size_request(190, 34)
        cur = [e for e, _n in opts]
        dd.set_selected(cur.index(self.targets[idx]) if self.targets[idx] in cur else 0)
        dd.connect('notify::selected', lambda d, i=idx, c=cur: self._pick(i, c[d.get_selected()]))
        for w in (src, dd):
            fc = Gtk.EventControllerFocus()
            fc.connect('enter', lambda c, i=idx: self._select(i))
            w.add_controller(fc)
        rm = Gtk.Button()
        rm.add_css_class('sz-fav-del')
        rm.set_tooltip_text(_('Remove from list'))
        rm.set_child(_drawing(20, 20, _fav_x, 'sz-fav-x'))
        rm.connect('clicked', lambda b, i=idx: self._remove(i))
        for w in (num, src, arrow, dd, rm):
            if isinstance(w, (Gtk.Label, Gtk.Entry, Gtk.DropDown)):
                w.set_valign(Gtk.Align.CENTER)
            row.append(w)
        self.rows.append({'row': row, 'dd': dd})
        return row

    def _pick(self, idx, ext):
        if 0 <= idx < len(self.targets):
            self.targets[idx] = ext

    def _select(self, idx):
        if idx == self.sel or not (0 <= idx < len(getattr(self, 'rows', ()))):
            return
        self.sel = idx
        for i, r in enumerate(self.rows):
            (r['row'].add_css_class if i == idx else r['row'].remove_css_class)('sz-fav-sel')

    def _remove(self, idx):
        if 0 <= idx < len(self.files):
            del self.files[idx]
            del self.targets[idx]
            if self.sel > idx:
                self.sel -= 1
            elif self.sel == idx:
                self.sel = min(idx, len(self.files) - 1)
            self._rebuild()

    def _add_files(self):
        if self.files:
            d = vfs.dirname(self.files[0])
            initial = os.path.expanduser('~') if vfs.is_admin(d) else vfs.display(d)
        else:
            initial = os.path.expanduser('~')

        def done(paths):
            added = [p for p in paths if kind_of(p)]
            if not added:
                return
            for p in added:
                kind = kind_of(p)
                opts = [e for e, _n in options_for(kind)]
                self.files.append(p)
                self.targets.append(self.target if self.target in opts
                                    else self._default_target(p, kind))
            self.sel = len(self.files) - 1
            self._rebuild()
        pick(self, 'multi', _('Add files'), done, initial=initial)

    def _browse_out(self, b):
        start = self.e_out.get_text().strip()
        if not os.path.isdir(os.path.expanduser(start)):
            if self.files:
                d = vfs.dirname(self.files[0])
                start = os.path.expanduser('~') if vfs.is_admin(d) else vfs.display(d)
            else:
                start = os.path.expanduser('~')

        def done(paths):
            if paths:
                self.e_out.set_text(paths[0])
        pick(self, 'folder', _('Output folder'), done, initial=start)

    def _unique_dst(self, dst, used):
        d, name = vfs.dirname(dst), vfs.basename(dst)
        stem, ext = os.path.splitext(name)
        cand, i = dst, 0
        while cand in used or vfs.exists(cand):
            i += 1
            cand = vfs.join(d, '%s (%d)%s' % (stem, i, ext))
        used.add(cand)
        return cand

    def _ok(self):
        if not self.files:
            alert(self, _('No files to convert'))
            return
        out = self.e_out.get_text().strip()
        out = os.path.abspath(os.path.expanduser(out)) if out else ''
        quality = QUALITIES[self.dd_quality.get_selected()][0]
        items, used = [], set()
        for src, target in zip(self.files, self.targets):
            base = os.path.splitext(vfs.basename(src))[0]
            if target == ext_of(src):
                base += '_converted'
            if out:
                dst = os.path.join(out, base + '.' + target)
            else:
                dst = vfs.join(vfs.dirname(src), base + '.' + target)
            items.append((src, self._unique_dst(dst, used), target))
        self.close()
        if self.on_ok:
            self.on_ok(items, quality)
