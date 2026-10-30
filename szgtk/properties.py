# -*- coding: utf-8 -*-
"""Диалог свойств файла: основные сведения, права доступа и метаданные."""
from .imports import *  # noqa: F401,F403
from .i18n import _
from .dialogs import (DlgBase, _tab_label, alert, confirm, grid_row, hbox,
                      lbl, vbox)
from .utils import TAR_COMPOUND, fmt_num, fmt_time, human, is_archive_name
from .fileicons import icon_for_file
from .convert import kind_of
from . import samba
from . import vfs


# ───────────────────────────── вспомогательные функции ─────────────────────────────
def _clean(value):
    if value is None:
        return ''
    s = str(value).strip()
    return '' if s.lower() in ('', 'n/a', 'unknown', 'none', 'undefined') else s


def _size_text(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ''
    if n < 1024:
        return fmt_num(n) + ' B'
    return fmt_num(n) + ' B (' + human(n) + ')'


def _duration_text(value):
    try:
        sec = int(round(float(value)))
    except (TypeError, ValueError):
        return ''
    h, rem = divmod(max(0, sec), 3600)
    m, s = divmod(rem, 60)
    return '%d:%02d:%02d' % (h, m, s) if h else '%d:%02d' % (m, s)


def _fps_text(value):
    s = _clean(value)
    if not s:
        return ''
    try:
        if '/' in s:
            a, b = s.split('/', 1)
            val = float(a) / float(b)
        else:
            val = float(s)
    except (ValueError, ZeroDivisionError):
        return ''
    if val <= 0:
        return ''
    return ('%.3f' % val).rstrip('0').rstrip('.') + ' fps'


def _bitrate_text(value):
    s = _clean(value)
    if not s:
        return ''
    try:
        bps = float(s)
    except ValueError:
        return ''
    if bps >= 1000000:
        return ('%.2f' % (bps / 1000000.0)).rstrip('0').rstrip('.') + ' Mb/s'
    if bps >= 1000:
        return fmt_num(round(bps / 1000.0)) + ' kb/s'
    return fmt_num(round(bps)) + ' b/s'


def _hz_text(value):
    s = _clean(value)
    if not s:
        return ''
    try:
        hz = float(s)
    except ValueError:
        return ''
    if hz >= 1000:
        return ('%.3f' % (hz / 1000.0)).rstrip('0').rstrip('.') + ' kHz'
    return fmt_num(round(hz)) + ' Hz'


def _channels_text(stream):
    ch = _clean(stream.get('channels'))
    if not ch:
        return ''
    layout = _clean(stream.get('channel_layout'))
    names = {'mono': _('Mono'), 'stereo': _('Stereo'), '5.1': '5.1', '7.1': '7.1'}
    if layout:
        layout = names.get(layout.lower(), layout)
        return '%s (%s)' % (ch, layout)
    return ch


def _mode_text(mode):
    try:
        return '%s (%04o)' % (stat.filemode(mode), mode & 0o7777)
    except (TypeError, ValueError):
        return ''


def _query_info(path):
    try:
        return vfs.gfile(path).query_info(
            'standard::content-type,standard::icon,standard::type', vfs.FOLLOW, None)
    except (GLib.Error, OSError):
        return None


def _content_type(path, info=None):
    ctype = ''
    if info is not None:
        try:
            ctype = info.get_content_type() or ''
        except Exception:
            ctype = ''
    if not ctype:
        try:
            ctype = Gio.content_type_guess(path, None)[0] or ''
        except Exception:
            ctype = ''
    return ctype


def _type_text(path, ctype, is_dir):
    if is_dir:
        return _('Folder')
    desc = ''
    try:
        desc = Gio.content_type_get_description(ctype) if ctype else ''
    except Exception:
        desc = ''
    if desc:
        return desc
    if is_archive_name(vfs.basename(path) or path):
        return _('Archive')
    return ctype or _('File')


def _icon_for(path, info, is_dir):
    if is_dir:
        return Gio.ThemedIcon.new('folder')
    special = icon_for_file(path)
    if special is not None:
        return special
    if info is not None:
        try:
            gicon = info.get_icon()
            if gicon is not None:
                return gicon
        except Exception:
            pass
    ctype = _content_type(path, info)
    try:
        if ctype:
            return Gio.content_type_get_icon(ctype)
    except Exception:
        pass
    return Gio.ThemedIcon.new('text-x-generic')


def _owner_group(path, st):
    uid = gid = None
    try:
        if vfs.is_uri(path):
            info = vfs.gfile(path).query_info('unix::uid,unix::gid', vfs.FOLLOW, None)
            if info.has_attribute('unix::uid'):
                uid = info.get_attribute_uint32('unix::uid')
            if info.has_attribute('unix::gid'):
                gid = info.get_attribute_uint32('unix::gid')
        else:
            uid, gid = st.st_uid, st.st_gid
    except Exception:
        pass
    owner = group = '—'
    try:
        import pwd
        if uid is not None:
            owner = pwd.getpwuid(uid).pw_name
    except Exception:
        if uid is not None:
            owner = str(uid)
    try:
        import grp
        if gid is not None:
            group = grp.getgrgid(gid).gr_name
    except Exception:
        if gid is not None:
            group = str(gid)
    return owner, group


def _apply_mode(path, mode):
    if vfs.is_uri(path):
        info = Gio.FileInfo()
        info.set_attribute_uint32('unix::mode', mode)
        vfs.gfile(path).set_attributes_from_info(info, vfs.FOLLOW, None)
    else:
        os.chmod(path, mode)


def _count_paths(paths, alive):
    """Файлы/папки/размер содержимого выбранных путей."""
    files = dirs = size = 0
    for path in paths:
        if not alive():
            break
        if vfs.is_dir(path) and not vfs.is_link(path):
            stack = [path]
            while stack and alive():
                cur = stack.pop()
                try:
                    children = vfs.listdir(cur)
                except (OSError, GLib.Error):
                    continue
                for e in children:
                    if not alive():
                        break
                    if e.is_dir and not e.is_link:
                        dirs += 1
                        stack.append(e.path)
                    else:
                        files += 1
                        try:
                            size += vfs.stat(e.path).st_size
                        except (OSError, GLib.Error):
                            pass
        else:
            files += 1
            try:
                size += vfs.stat(path).st_size
            except (OSError, GLib.Error):
                pass
    return files, dirs, size


# ───────────────────────────── метаданные ─────────────────────────────
TAG_LABELS = {
    'title': 'Название', 'artist': 'Исполнитель', 'album': 'Альбом',
    'album_artist': 'Исполнитель альбома', 'genre': 'Жанр', 'date': 'Дата',
    'year': 'Год', 'comment': 'Комментарий', 'track': 'Трек', 'disc': 'Диск',
    'composer': 'Композитор', 'performer': 'Исполнитель', 'copyright': 'Авторские права',
    'encoder': 'Кодировщик', 'encoded_by': 'Кодировщик', 'language': 'Язык',
    'lyrics': 'Текст песни', 'description': 'Описание', 'synopsis': 'Описание',
    'author': 'Автор', 'make': 'Производитель', 'model': 'Модель',
    'creation_time': 'Время создания', 'location': 'Местоположение',
    'compatible_brands': 'Совместимые бренды', 'major_brand': 'Основной бренд',
    'minor_version': 'Версия', 'handler_name': 'Обработчик', 'vendor_id': 'Поставщик',
}
EXIF_LABELS = {
    'Make': 'Производитель', 'Model': 'Модель', 'DateTimeOriginal': 'Дата съёмки',
    'DateTime': 'Дата', 'ExposureTime': 'Выдержка', 'FNumber': 'Диафрагма',
    'ISOSpeedRatings': 'ISO', 'PhotographicSensitivity': 'ISO',
    'FocalLength': 'Фокусное расстояние', 'LensModel': 'Объектив',
    'Orientation': 'Ориентация', 'Flash': 'Вспышка', 'GPSLatitude': 'Широта',
    'GPSLongitude': 'Долгота', 'GPSAltitude': 'Высота', 'Software': 'Программа',
    'Artist': 'Автор', 'Copyright': 'Авторские права', 'ImageDescription': 'Описание',
    'UserComment': 'Комментарий',
}
SKIP_TAGS = {'duration', 'bps', 'number_of_frames', 'number_of_bytes', 'stream_size',
             'filename', 'mimetype'}


def _run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout)
        return p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except Exception as e:  # noqa: BLE001
        return -1, '', str(e)


def _ffprobe_rows(path):
    exe = shutil.which('ffprobe')
    if not exe:
        return []
    rc, out, _err = _run([exe, '-v', 'error', '-print_format', 'json',
                          '-show_format', '-show_streams', '-i', path])
    if rc != 0 or not out.strip():
        return []
    return _ffprobe_parse(out)


def _ffprobe_parse(out):
    try:
        data = json.loads(out)
    except ValueError:
        return []
    rows = []

    def add(section, key, value):
        value = _clean(value)
        if value:
            rows.append((section, key, value))

    fmt = data.get('format') or {}
    add(_('Format'), _('Container'), fmt.get('format_long_name') or fmt.get('format_name'))
    add(_('Format'), _('Duration'), _duration_text(fmt.get('duration')))
    add(_('Format'), _('Bitrate'), _bitrate_text(fmt.get('bit_rate')))
    if _clean(fmt.get('size')):
        add(_('Format'), _('Size'), _size_text(fmt.get('size')))

    for i, st in enumerate(data.get('streams') or [], 1):
        typ = st.get('codec_type') or ''
        labels = {'video': _('Video'), 'audio': _('Audio'), 'subtitle': _('Subtitles'),
                  'data': _('Data'), 'attachment': _('Attachment')}
        section = _('Stream {0}: {1}').format(i, labels.get(typ, typ or _('Stream')))
        add(section, _('Codec'), st.get('codec_long_name') or st.get('codec_name'))
        if typ == 'video':
            w, h = st.get('width'), st.get('height')
            if w and h:
                add(section, _('Resolution'), '%s × %s' % (w, h))
            add(section, _('Frame rate'), _fps_text(st.get('avg_frame_rate') or st.get('r_frame_rate')))
            add(section, _('Bitrate'), _bitrate_text(st.get('bit_rate')))
            add(section, _('Color space'), st.get('pix_fmt'))
            add(section, _('Profile'), st.get('profile'))
        elif typ == 'audio':
            add(section, _('Sample rate'), _hz_text(st.get('sample_rate')))
            add(section, _('Channels'), _channels_text(st))
            add(section, _('Bitrate'), _bitrate_text(st.get('bit_rate')))
            add(section, _('Profile'), st.get('profile'))
        elif typ == 'subtitle':
            add(section, _('Language'), (st.get('tags') or {}).get('language'))
        for key, value in (st.get('tags') or {}).items():
            low = key.lower()
            if low in SKIP_TAGS:
                continue
            add(section, TAG_LABELS.get(low, key), value)

    for key, value in (fmt.get('tags') or {}).items():
        low = key.lower()
        if low in SKIP_TAGS:
            continue
        add(_('Tags'), TAG_LABELS.get(low, key), value)
    return rows


def _identify_rows(path):
    exe = shutil.which('identify')
    if not exe:
        return []
    rc, out, _err = _run([exe, '-verbose', path])
    if rc != 0 or not out.strip():
        return []
    return _identify_parse(out)


def _identify_parse(out):
    rows = []
    seen = set()
    started = False

    def add(section, key, value):
        value = _clean(value).replace('\n', ' ')
        if value and (section, key, value) not in seen:
            seen.add((section, key, value))
            rows.append((section, key, value))

    for line in out.splitlines():
        s = line.strip()
        if s.startswith('Image:'):
            if started:
                break
            started = True
            continue
        if s.startswith('Format: '):
            add(_('Image'), _('Format'), s[8:])
        elif s.startswith('Geometry: '):
            geom = s[10:].split('+', 1)[0]
            if 'x' in geom:
                w, h = geom.split('x', 1)
                add(_('Image'), _('Resolution'), '%s × %s' % (w, h))
            else:
                add(_('Image'), _('Geometry'), geom)
        elif s.startswith('Colorspace: '):
            add(_('Image'), _('Color space'), s[12:])
        elif s.startswith('Depth: '):
            add(_('Image'), _('Color depth'), s[7:])
        elif s.startswith('Resolution: '):
            add(_('Image'), _('Print resolution'), s[12:])
        elif s.startswith('Units: '):
            add(_('Image'), _('Units'), s[7:])
        elif s.startswith('exif:'):
            key, _sep, value = s[5:].partition(': ')
            add(_('EXIF'), EXIF_LABELS.get(key, key), value)
    return rows


def _read_metadata(path, kind):
    local = path
    tmp = None
    try:
        if vfs.is_uri(path):
            tmp, local = vfs.copy_to_temp(path)
        if kind == 'image':
            rows = _identify_rows(local)
            if rows:
                return rows, None
        return _ffprobe_rows(local), None
    except Exception as e:  # noqa: BLE001
        return [], str(e)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def _popen_entry_stream(sevenzip_bin, archive_path, entry_path, password=None):
    """Запустить 7z, выводящий содержимое записи архива в stdout.

    Для составных .tar.gz/.tgz нужен конвейер из двух 7z: сначала
    распаковывается внешний контейнер, затем из потока tar читается запись.
    Возвращает (процесс с данными в stdout, процессы-предшественники, ошибка).
    """
    if not sevenzip_bin:
        return None, [], _('7z not found')
    switches = ['-so', '-sccUTF-8', '-scsUTF-8', '-bsp0', '-bb0']
    if password:
        switches.append('-p' + password)

    def spawn(args, stdin=subprocess.DEVNULL):
        return subprocess.Popen(args, stdin=stdin, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)

    try:
        if TAR_COMPOUND.search(archive_path):
            p1 = spawn([sevenzip_bin, 'x'] + switches + ['--', archive_path])
            try:
                p2 = spawn([sevenzip_bin, 'x', '-si', '-ttar'] + switches +
                           ['--', entry_path], p1.stdout)
            except OSError:
                p1.kill()
                p1.wait()
                raise
            p1.stdout.close()
            return p2, [p1], None
        return spawn([sevenzip_bin, 'x'] + switches +
                     ['--', archive_path, entry_path]), [], None
    except OSError as e:
        return None, [], str(e)


def _stream_entry(sevenzip_bin, archive_path, entry_path, password, consumer_cmd,
                  timeout=30):
    """Передать содержимое записи архива на stdin внешней программе."""
    producer, upstream, err = _popen_entry_stream(
        sevenzip_bin, archive_path, entry_path, password)
    if producer is None:
        return -1, b'', err, -1
    try:
        consumer = subprocess.Popen(consumer_cmd, stdin=producer.stdout,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        producer.kill()
        for p in upstream:
            p.kill()
        producer.wait()
        for p in upstream:
            p.wait()
        return -1, b'', str(e), -1
    producer.stdout.close()
    try:
        out, errout = consumer.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        consumer.kill()
        out, errout = consumer.communicate()
        errout = (errout or b'') + b'\n' + _('Timed out').encode('utf-8')
    procs = [producer] + upstream
    rc = producer.poll()
    for p in procs:
        if p.poll() is None:
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
    return consumer.returncode, out, errout, rc if rc is not None else producer.returncode


def read_archive_metadata(sevenzip_bin, archive_path, entry_path, kind, password=None):
    """Метаданные медиафайла внутри архива без распаковки на диск."""
    if not sevenzip_bin:
        return [], _('7z not found')
    last_err = ''
    if kind == 'image':
        exe = shutil.which('identify')
        if exe:
            rc, out, err, _rc = _stream_entry(
                sevenzip_bin, archive_path, entry_path, password,
                [exe, '-verbose', '-'])
            if rc == 0 and out.strip():
                rows = _identify_parse(out.decode('utf-8', 'replace'))
                if rows:
                    return rows, None
            last_err = err.decode('utf-8', 'replace').strip()
        else:
            last_err = _('ImageMagick not found')
    exe = shutil.which('ffprobe')
    if not exe:
        return [], last_err or _('ffprobe not found')
    rc, out, err, _rc = _stream_entry(
        sevenzip_bin, archive_path, entry_path, password,
        [exe, '-v', 'error', '-print_format', 'json',
         '-show_format', '-show_streams', '-i', 'pipe:0'])
    if rc == 0 and out.strip():
        rows = _ffprobe_parse(out.decode('utf-8', 'replace'))
        if rows:
            return rows, None
    err_text = err.decode('utf-8', 'replace').strip()
    return [], err_text or last_err or None


# ───────────────────────────── диалог ─────────────────────────────
class PropertiesDialog(DlgBase):
    def __init__(self, parent, paths=None, entry=None, archive_path=None, archive_info=None,
                 entry_meta=None):
        super().__init__(title=_('Properties'), modal=True, transient_for=parent,
                         destroy_with_parent=True)
        self._alive = True
        self._updating_mode = False
        self.mode_path = None
        self.mode_checks = []
        self.mode_label = None
        self.attrs_val = None
        self.files_val = self.folders_val = self.size_val = None
        self.meta_box = None
        self._switching_tabs = False
        self.tab_buttons = []
        # вкладка общего доступа Samba
        self.share_path = None
        self.share_current = None
        self.share_enabled = None
        self.share_name = None
        self.share_comment = None
        self.share_read_only = None
        self.share_guest = None
        self.share_users = None
        self.share_browseable = None
        self.share_apply = None
        self.share_remove = None
        self.share_start = None
        self.share_status = None
        self.share_warn = None
        self._samba_service = 'unknown'
        self._share_helper_warning = ''
        self._share_message = ''
        self._sharing_busy = False
        self.add_css_class('sz-props')
        self.set_default_size(560, 460)
        self.connect('close-request', self._on_close)
        self.connect('unrealize', self._on_close)

        root = vbox(10, 14)
        self.set_child(root)
        tabwrap = vbox(0)
        tabbar = hbox(2)
        tabbar.set_halign(Gtk.Align.START)
        tabbar.set_margin_start(6)
        tabbar.set_margin_end(6)
        tabwrap.append(tabbar)
        tabsep = Gtk.Separator(orientation=H)
        tabsep.add_css_class('sz-prop-tabsep')
        tabwrap.append(tabsep)
        root.append(tabwrap)
        self.tabbar = tabbar
        self.stack = Gtk.Stack(vexpand=True, hexpand=True)
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        root.append(self.stack)

        if paths:
            path = paths[0]
            self._add_tab(self._page_fs(path, archive_info), _('Main'))
            self._add_tab(self._page_permissions(path), _('Permissions'))
            if self._can_share(path):
                self._add_tab(self._page_sharing(path), _('Sharing'))
            kind = kind_of(path) if vfs.is_file(path) else None
            if kind:
                self._add_tab(self._page_metadata(path, kind), _('Metadata'))
        elif entry is not None:
            self._add_tab(self._page_entry(entry, archive_path), _('Main'))
            kind = kind_of(entry.path) if not entry.is_dir else None
            if kind and entry_meta is not None:
                self._add_tab(self._page_entry_metadata(entry, kind, entry_meta),
                              _('Metadata'))
        else:
            self._add_tab(self._page_error(), _('Main'))
        if self.tab_buttons:
            self.tab_buttons[0].set_active(True)

        bottom = hbox(0)
        bottom.set_halign(Gtk.Align.END)
        close = Gtk.Button(label=_('Close'))
        close.add_css_class('sz-dlg-ok')
        close.add_css_class('suggested-action')
        close.connect('clicked', lambda b: self.close())
        bottom.append(close)
        root.append(bottom)
        self.set_default_widget(close)

        key = Gtk.EventControllerKey()

        def on_key(_c, keyval, _code, _state):
            if keyval == Gdk.KEY_Escape:
                self.close()
                return True
            return False
        key.connect('key-pressed', on_key)
        self.add_controller(key)

    def _on_close(self, _w):
        self._alive = False
        return False

    def _add_tab(self, page, label):
        name = 'page%d' % len(self.tab_buttons)
        btn = Gtk.ToggleButton()
        btn.set_has_frame(False)
        btn.add_css_class('sz-prop-tab')
        btn.set_child(_tab_label(label))
        btn.connect('toggled', self._tab_toggled, name)
        self.tab_buttons.append(btn)
        self.tabbar.append(btn)
        self.stack.add_named(page, name)

    def _tab_toggled(self, btn, name):
        if self._switching_tabs:
            return
        if not btn.get_active():
            if self.stack.get_visible_child_name() == name:
                self._switching_tabs = True
                btn.set_active(True)
                self._switching_tabs = False
            return
        self._switching_tabs = True
        for other in self.tab_buttons:
            if other is not btn:
                other.set_active(False)
        self._switching_tabs = False
        self.stack.set_visible_child_name(name)

    # ---------- общие элементы ----------
    def _header(self, gicon, name):
        head = hbox(12)
        head.set_hexpand(True)
        icon = Gtk.Image.new_from_gicon(gicon)
        icon.set_pixel_size(24)
        box = Gtk.Box()
        box.add_css_class('sz-prop-icon')
        box.set_size_request(44, 44)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.append(icon)
        head.append(box)
        field = Gtk.Entry()
        field.set_text(name)
        field.set_editable(False)
        field.set_can_focus(False)
        field.set_hexpand(True)
        field.set_valign(Gtk.Align.CENTER)
        field.add_css_class('sz-prop-name')
        field.set_tooltip_text(name)
        head.append(field)
        return head

    def _grid(self):
        g = Gtk.Grid(column_spacing=24, row_spacing=10)
        g.set_hexpand(True)
        g.set_valign(Gtk.Align.START)
        return g

    def _row(self, grid, row, key, value=''):
        k = lbl(key)
        k.add_css_class('sz-prop-key')
        k.set_xalign(0)
        k.set_valign(Gtk.Align.START)
        k.set_size_request(110, -1)
        v = lbl(value)
        v.add_css_class('sz-prop-val')
        v.set_xalign(0)
        v.set_hexpand(True)
        v.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        v.set_tooltip_text(value)
        grid.attach(k, 0, row, 1, 1)
        grid.attach(v, 1, row, 1, 1)
        return v

    def _sep(self, grid, row):
        sep = Gtk.Separator(orientation=H)
        sep.add_css_class('sz-prop-sep')
        sep.set_margin_top(2)
        sep.set_margin_bottom(2)
        grid.attach(sep, 0, row, 2, 1)

    def _counts_row(self, grid, row, files='1', folders='0'):
        box = hbox(36)
        box.set_hexpand(True)
        vals = []
        for key, value in ((_('Files'), files), (_('Folders'), folders)):
            pair = hbox(10)
            k = lbl(key)
            k.add_css_class('sz-prop-key')
            k.set_xalign(0)
            k.set_size_request(64, -1)
            v = lbl(value)
            v.add_css_class('sz-prop-val')
            v.set_xalign(0)
            pair.append(k)
            pair.append(v)
            box.append(pair)
            vals.append(v)
        grid.attach(box, 0, row, 2, 1)
        return vals

    # ---------- основная вкладка ----------
    def _page_fs(self, path, archive_info):
        page = vbox(12, 6)
        try:
            st = vfs.stat(path)
        except (OSError, GLib.Error) as e:
            page.append(lbl(str(e)))
            return page
        info = _query_info(path)
        ctype = _content_type(path, info)
        is_dir = vfs.is_dir(path)
        real_dir = is_dir and not vfs.is_link(path)
        name = vfs.basename(path) or vfs.display(path)
        page.append(self._header(_icon_for(path, info, is_dir), name))

        grid = self._grid()
        page.append(grid)
        self._row(grid, 0, _('Type'), _type_text(path, ctype, is_dir))
        self._row(grid, 1, _('Location'), vfs.display(vfs.dirname(path) or '/'))
        self.size_val = self._row(grid, 2, _('Size'), '…' if real_dir else _size_text(st.st_size))
        self._sep(grid, 3)
        self._row(grid, 4, _('Modified'), fmt_time(int(st.st_mtime)))
        self.attrs_val = self._row(grid, 5, _('Attributes'), stat.filemode(st.st_mode))
        self._sep(grid, 6)
        self.files_val, self.folders_val = self._counts_row(
            grid, 7, '…' if real_dir else '1', '…' if real_dir else '0')

        if real_dir:
            self._start_fs_count([path], True)
        elif is_archive_name(name):
            self._start_archive_count(path, archive_info)
        return page

    def _start_fs_count(self, paths, update_size):
        def work():
            files, dirs, size = _count_paths(paths, lambda: self._alive)
            if not self._alive:
                return
            GLib.idle_add(lambda: self._set_counts(files, dirs, size if update_size else None))

        threading.Thread(target=work, daemon=True).start()

    def _start_archive_count(self, path, archive_info):
        if archive_info is None:
            return

        def done(result):
            if not self._alive or result is None:
                return
            files, dirs = result
            self._set_counts(files, dirs, None)

        try:
            archive_info(path, done)
        except Exception:
            pass

    def _set_counts(self, files, dirs, size=None):
        if not self._alive:
            return
        if self.files_val is not None:
            self.files_val.set_text(fmt_num(files))
        if self.folders_val is not None:
            self.folders_val.set_text(fmt_num(dirs))
        if size is not None and self.size_val is not None:
            text = _size_text(size)
            self.size_val.set_text(text)
            self.size_val.set_tooltip_text(text)
        return False

    def _page_entry(self, entry, archive_path):
        page = vbox(12, 6)
        name = os.path.basename(entry.path.rstrip('/')) or entry.path
        is_dir = entry.is_dir
        ctype = _content_type(name)
        info = None
        page.append(self._header(_icon_for(name, info, is_dir), name))

        grid = self._grid()
        page.append(grid)
        self._row(grid, 0, _('Type'), _type_text(name, ctype, is_dir))
        self._row(grid, 1, _('Location'), vfs.display(archive_path) if archive_path else '')
        self._row(grid, 2, _('Size'), _size_text(entry.size))
        self._sep(grid, 3)
        self._row(grid, 4, _('Modified'), fmt_time(entry.mtime))
        self._row(grid, 5, _('Attributes'), entry.attrs or '')
        self._sep(grid, 6)
        self._row(grid, 7, _('Packed Size'), _size_text(entry.packed))
        self._row(grid, 8, 'CRC', entry.crc or '')
        self._row(grid, 9, _('Method'), entry.method or '')
        self._row(grid, 10, _('Path'), entry.path)
        return page

    def _page_error(self):
        page = vbox(8, 6)
        page.append(lbl(_('Properties are unavailable.')))
        return page

    # ---------- права доступа ----------
    def _page_permissions(self, path):
        page = vbox(10, 6)
        try:
            st = vfs.stat(path)
        except (OSError, GLib.Error) as e:
            page.append(lbl(str(e)))
            return page
        self.mode_path = path
        owner, group = _owner_group(path, st)
        info_grid = self._grid()
        page.append(info_grid)
        self._row(info_grid, 0, _('Owner'), owner)
        self._row(info_grid, 1, _('Group name'), group)
        self.mode_label = self._row(info_grid, 2, _('Mode'), _mode_text(st.st_mode))

        sep = Gtk.Separator(orientation=H)
        sep.add_css_class('sz-prop-sep')
        page.append(sep)

        grid = Gtk.Grid(column_spacing=24, row_spacing=8)
        grid.set_hexpand(True)
        headers = ('', _('Owner'), _('Group name'), _('Others'))
        for col, text in enumerate(headers):
            l = lbl(text)
            l.add_css_class('sz-prop-key' if col == 0 else 'sz-prop-col')
            l.set_xalign(0)
            if col == 0:
                l.set_size_request(90, -1)
            grid.attach(l, col, 0, 1, 1)
        rows = ((_('Read'), 0o400, 0o040, 0o004),
                (_('Write'), 0o200, 0o020, 0o002),
                (_('Execute'), 0o100, 0o010, 0o001))
        for r, (name, m_owner, m_group, m_other) in enumerate(rows, 1):
            l = lbl(name)
            l.add_css_class('sz-prop-key')
            l.set_xalign(0)
            grid.attach(l, 0, r, 1, 1)
            for c, bit in enumerate((m_owner, m_group, m_other), 1):
                cb = Gtk.CheckButton()
                cb.set_active(bool(st.st_mode & bit))
                cb.set_halign(Gtk.Align.START)
                cb.connect('toggled', self._mode_toggled)
                grid.attach(cb, c, r, 1, 1)
                self.mode_checks.append((bit, cb))
        page.append(grid)
        note = lbl(_('Changes are applied immediately.'))
        note.add_css_class('sz-prop-note')
        page.append(note)
        page.append(Gtk.Box(vexpand=True))
        return page

    def _reload_mode(self):
        if not self.mode_path:
            return
        try:
            st = vfs.stat(self.mode_path)
        except (OSError, GLib.Error):
            return
        self._updating_mode = True
        for bit, cb in self.mode_checks:
            cb.set_active(bool(st.st_mode & bit))
        self._updating_mode = False
        if self.mode_label is not None:
            text = _mode_text(st.st_mode)
            self.mode_label.set_text(text)
            self.mode_label.set_tooltip_text(text)
        if self.attrs_val is not None:
            text = stat.filemode(st.st_mode)
            self.attrs_val.set_text(text)
            self.attrs_val.set_tooltip_text(text)

    def _mode_toggled(self, _cb):
        if self._updating_mode or not self.mode_path:
            return
        mode = 0
        for bit, cb in self.mode_checks:
            if cb.get_active():
                mode |= bit
        try:
            mode |= vfs.stat(self.mode_path).st_mode & 0o7000
        except (OSError, GLib.Error):
            pass
        try:
            _apply_mode(self.mode_path, mode)
        except (OSError, GLib.Error) as e:
            alert(self, _('Cannot change permissions'), str(e))
        self._reload_mode()

    # ---------- общий доступ Samba ----------
    @staticmethod
    def _share_real_path(path):
        real = vfs.display(path) if vfs.is_admin(path) else path
        try:
            return os.path.realpath(real)
        except (OSError, ValueError):
            return None

    def _can_share(self, path):
        try:
            if not vfs.is_dir(path) or vfs.is_link(path):
                return False
        except (OSError, GLib.Error):
            return False
        real = self._share_real_path(path)
        if not real or not os.path.isabs(real) or real == '/':
            return False
        if '/gvfs/' in real:
            return False
        for prefix in ('/proc', '/sys', '/dev'):
            if real == prefix or real.startswith(prefix + os.sep):
                return False
        return True

    def _page_sharing(self, path):
        page = vbox(10, 6)
        real = self._share_real_path(path)
        self.share_path = real
        try:
            self.share_current = samba.share_for_path(real) if real else None
        except Exception:
            self.share_current = None

        if not samba.samba_installed():
            page.append(lbl(_('Samba is not installed.')))
            note = lbl(_('Install Samba (smbd, testparm) with your package manager.'))
            note.add_css_class('sz-prop-note')
            note.set_wrap(True)
            page.append(note)
            return page
        if not samba.can_apply():
            page.append(lbl(_('Administrator privileges are required to configure Samba.')))
            note = lbl(_('Install polkit/pkexec or run the application as root.'))
            note.add_css_class('sz-prop-note')
            note.set_wrap(True)
            page.append(note)
            return page

        title = lbl(_('Shared folder'))
        title.add_css_class('sz-prop-section')
        page.append(title)

        current = self.share_current
        name = current['name'] if current else samba.suggest_name(real)
        self.share_enabled = Gtk.CheckButton(label=_('Share this folder over Samba'))
        self.share_enabled.set_active(current is not None)
        self.share_enabled.connect('toggled', self._share_toggled)
        page.append(self.share_enabled)

        grid = Gtk.Grid(column_spacing=16, row_spacing=8)
        grid.set_hexpand(True)
        page.append(grid)

        self.share_name = Gtk.Entry(hexpand=True, text=name)
        grid_row(grid, 0, _('Share name:'), self.share_name)

        self.share_comment = Gtk.Entry(hexpand=True,
                                       text=(current or {}).get('comment', ''))
        grid_row(grid, 1, _('Comment:'), self.share_comment)

        options = vbox(4)
        self.share_read_only = Gtk.CheckButton(label=_('Read only'))
        self.share_read_only.set_active((current or {}).get('read_only', True))
        self.share_read_only.connect('toggled', self._share_options_changed)
        options.append(self.share_read_only)
        self.share_guest = Gtk.CheckButton(
            label=_('Allow guest access (no password)'))
        self.share_guest.set_active((current or {}).get('guest_ok', False))
        self.share_guest.connect('toggled', self._share_options_changed)
        options.append(self.share_guest)
        self.share_browseable = Gtk.CheckButton(
            label=_('Show in network neighbourhood'))
        self.share_browseable.set_active((current or {}).get('browseable', True))
        options.append(self.share_browseable)
        grid_row(grid, 2, _('Access:'), options)

        self.share_users = Gtk.Entry(hexpand=True)
        if current:
            self.share_users.set_text(', '.join(current.get('users') or []))
        self.share_users.set_placeholder_text(_('All Samba users'))
        grid_row(grid, 3, _('Users:'), self.share_users)
        users_note = lbl(_('Comma-separated list. Empty — all Samba users.'))
        users_note.add_css_class('sz-prop-note')
        users_note.set_wrap(True)
        grid.attach(users_note, 1, 4, 1, 1)

        note = lbl(_('Filesystem permissions also apply. '
                     'Adjust them on the Permissions tab.'))
        note.add_css_class('sz-prop-note')
        note.set_wrap(True)
        page.append(note)

        self.share_warn = lbl('')
        self.share_warn.add_css_class('sz-prop-note')
        self.share_warn.set_wrap(True)
        page.append(self.share_warn)

        self.share_status = lbl('')
        self.share_status.add_css_class('sz-prop-note')
        self.share_status.set_wrap(True)
        page.append(self.share_status)

        buttons = hbox(8)
        buttons.set_halign(Gtk.Align.START)
        self.share_apply = Gtk.Button(label=_('Apply'))
        self.share_apply.add_css_class('suggested-action')
        self.share_apply.connect('clicked', lambda b: self._apply_sharing())
        buttons.append(self.share_apply)
        self.share_remove = Gtk.Button(label=_('Stop sharing'))
        self.share_remove.add_css_class('destructive-action')
        self.share_remove.connect('clicked', lambda b: self._remove_sharing())
        self.share_remove.set_visible(current is not None)
        buttons.append(self.share_remove)
        self.share_start = Gtk.Button(label=_('Start Samba service'))
        self.share_start.connect('clicked', lambda b: self._start_samba())
        self.share_start.set_visible(False)
        buttons.append(self.share_start)
        page.append(buttons)
        page.append(Gtk.Box(vexpand=True))

        self._share_toggled(self.share_enabled)
        self._update_share_status()
        self._load_service_state()
        return page

    def _share_options_changed(self, _w=None):
        if self.share_users is None or self.share_guest is None:
            return
        on = (self.share_enabled is not None and
              self.share_enabled.get_active() and
              not self._sharing_busy)
        self.share_users.set_sensitive(on and not self.share_guest.get_active())
        self._update_share_warning()

    def _share_toggled(self, _w=None):
        if self.share_enabled is None:
            return
        on = self.share_enabled.get_active() and not self._sharing_busy
        for widget in (self.share_name, self.share_comment,
                       self.share_read_only, self.share_guest,
                       self.share_browseable):
            if widget is not None:
                widget.set_sensitive(on)
        self._share_options_changed()
        if self.share_apply is not None:
            self.share_apply.set_sensitive(on)
        if self.share_remove is not None:
            self.share_remove.set_visible(self.share_current is not None)
        self._update_share_warning()

    def _update_share_warning(self):
        if self.share_warn is None:
            return
        parts = []
        if (self.share_enabled is not None and
                self.share_enabled.get_active() and
                self.share_guest is not None and
                self.share_guest.get_active()):
            read_only = self.share_read_only.get_active()
            try:
                mode = os.stat(self.share_path).st_mode
            except (OSError, TypeError):
                mode = 0
            if not (mode & 0o005):
                parts.append(_('Guests may not be able to read this folder: '
                               'other users have no read/execute permission.'))
            if not read_only and not (mode & 0o002):
                parts.append(_('Guests may not be able to write to this folder: '
                               'other users have no write permission.'))
        if self._share_helper_warning:
            parts.append(self._share_helper_warning)
        self.share_warn.set_text('\n'.join(parts))
        self.share_warn.set_visible(bool(parts))

    def _update_share_status(self):
        if self.share_status is None or self._sharing_busy:
            return
        parts = []
        if self.share_current:
            parts.append(_('Shared as {0}').format(
                samba.unc_path(self.share_current['name'])))
        else:
            parts.append(_('Not shared'))
        state = self._samba_service
        if state == 'active':
            parts.append(_('Samba service is running'))
        elif state == 'inactive':
            parts.append(_('Samba service is not running; '
                           'it will be started when you apply.'))
        elif state == 'started':
            parts.append(_('Samba service started'))
        elif state == 'reloaded':
            parts.append(_('Samba service reloaded'))
        try:
            if not samba.include_present():
                parts.append(_('Samba will be configured automatically on first apply.'))
        except Exception:
            pass
        if self._share_message:
            parts.append(self._share_message)
        self.share_status.set_text(' · '.join(parts))
        if self.share_start is not None:
            self.share_start.set_visible(state == 'inactive')

    def _load_service_state(self):
        def work():
            state = samba.service_status()
            GLib.idle_add(lambda: self._set_service_state(state))

        threading.Thread(target=work, daemon=True).start()

    def _set_service_state(self, state):
        if not self._alive:
            return False
        self._samba_service = state
        self._update_share_status()
        return False

    def _share_busy(self, busy):
        self._sharing_busy = busy
        if busy:
            for widget in (self.share_enabled, self.share_name, self.share_comment,
                           self.share_read_only, self.share_guest, self.share_users,
                           self.share_browseable, self.share_apply, self.share_remove,
                           self.share_start):
                if widget is not None:
                    widget.set_sensitive(False)
            self.share_status.set_text(_('Applying sharing settings…'))
        else:
            for widget in (self.share_enabled, self.share_remove, self.share_start):
                if widget is not None:
                    widget.set_sensitive(True)
            self._share_toggled(self.share_enabled)
            self._update_share_status()
            self._update_share_warning()

    def _apply_sharing(self):
        if self._sharing_busy or self.share_enabled is None:
            return
        if not self.share_enabled.get_active():
            return
        data = {
            'path': self.share_path,
            'name': self.share_name.get_text().strip(),
            'comment': self.share_comment.get_text().strip(),
            'read_only': self.share_read_only.get_active(),
            'guest_ok': self.share_guest.get_active(),
            'users': self.share_users.get_text(),
            'browseable': self.share_browseable.get_active(),
        }
        try:
            data = samba.normalize_share(data)
        except samba.ShareError as e:
            alert(self, _('Cannot configure sharing'), _(str(e)))
            return
        self._share_helper_warning = ''
        self._share_message = ''
        self._share_busy(True)

        def work():
            result = samba.apply_share(data)
            GLib.idle_add(lambda: self._share_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _share_done(self, result):
        if not self._alive:
            return False
        self._share_busy(False)
        if not result:
            result = {'ok': False, 'error': _('Unknown error')}
        if not result.get('ok'):
            if result.get('cancelled'):
                self._share_message = _('Sharing settings were not changed.')
                self._update_share_status()
                return False
            error = result.get('error') or _('Unknown error')
            detail = result.get('detail') or ''
            text = _(str(error))
            if detail:
                text += '\n\n' + detail[:2000]
            alert(self, _('Cannot configure sharing'), text)
            return False
        action = result.get('action')
        self._samba_service = result.get('service', self._samba_service)
        self._share_helper_warning = result.get('warning', '')
        if action == 'remove':
            self.share_current = None
            self.share_enabled.set_active(False)
            self._share_message = _('Sharing disabled')
        else:
            try:
                self.share_current = samba.share_for_path(self.share_path)
            except Exception:
                self.share_current = None
            if self.share_current is None:
                self.share_current = {
                    'name': result.get('name', ''),
                    'path': self.share_path,
                    'comment': '',
                    'browseable': True,
                    'read_only': True,
                    'guest_ok': False,
                    'users': [],
                }
            self.share_enabled.set_active(True)
            if result.get('name'):
                self.share_name.set_text(result['name'])
            self._share_message = _('Sharing settings applied')
        self._share_toggled(self.share_enabled)
        self._update_share_status()
        self._update_share_warning()
        return False

    def _remove_sharing(self):
        if self._sharing_busy or not self.share_current:
            return
        name = self.share_current.get('name')

        def do_remove():
            self._share_helper_warning = ''
            self._share_message = ''
            self._share_busy(True)

            def work():
                result = samba.remove_share(name=name, path=self.share_path)
                GLib.idle_add(lambda: self._share_done(result))

            threading.Thread(target=work, daemon=True).start()

        confirm(self, _('Stop sharing this folder?'),
                _('The Samba share will be removed. '
                  'The folder itself will not be changed.'),
                _('Stop sharing'), do_remove)

    def _start_samba(self):
        if self._sharing_busy:
            return
        self._share_busy(True)
        self.share_status.set_text(_('Starting Samba service…'))

        def work():
            result = samba.start_service()
            GLib.idle_add(lambda: self._start_done(result))

        threading.Thread(target=work, daemon=True).start()

    def _start_done(self, result):
        if not self._alive:
            return False
        self._share_busy(False)
        if result and result.get('ok'):
            self._samba_service = result.get('service', 'started')
            self._share_message = _('Samba service started')
            self._update_share_status()
            return False
        error = (result or {}).get('error') or _('Unknown error')
        detail = (result or {}).get('detail') or ''
        text = _(str(error))
        if detail:
            text += '\n\n' + detail[:2000]
        alert(self, _('Cannot start Samba service'), text)
        self._update_share_status()
        return False

    # ---------- метаданные ----------
    def _page_metadata(self, path, kind):
        return self._metadata_page(lambda: _read_metadata(path, kind))

    def _page_entry_metadata(self, entry, kind, reader):
        return self._metadata_page(lambda: reader(entry, kind))

    def _metadata_page(self, reader):
        page = vbox(0, 0)
        sw = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.meta_box = vbox(8, 6)
        sw.set_child(self.meta_box)
        page.append(sw)
        note = lbl(_('Reading metadata…'))
        note.add_css_class('sz-prop-note')
        self.meta_box.append(note)

        def work():
            rows, err = reader()
            if not self._alive:
                return
            GLib.idle_add(lambda: self._show_metadata(rows, err))

        threading.Thread(target=work, daemon=True).start()
        return page

    def _show_metadata(self, rows, err):
        if not self._alive or self.meta_box is None:
            return False
        child = self.meta_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.meta_box.remove(child)
            child = nxt
        if not rows:
            text = _('Metadata unavailable')
            if err:
                text += ': ' + err
            note = lbl(text)
            note.add_css_class('sz-prop-note')
            note.set_wrap(True)
            self.meta_box.append(note)
            return False

        grid = Gtk.Grid(column_spacing=20, row_spacing=8)
        grid.set_hexpand(True)
        grid.set_valign(Gtk.Align.START)
        row = 0
        last = object()
        for section, key, value in rows:
            if section != last:
                if row:
                    row += 1
                if section:
                    s = lbl(section)
                    s.add_css_class('sz-prop-section')
                    s.set_xalign(0)
                    s.set_margin_top(6)
                    grid.attach(s, 0, row, 2, 1)
                    row += 1
                last = section
            k = lbl(key)
            k.add_css_class('sz-prop-key')
            k.set_xalign(0)
            k.set_valign(Gtk.Align.START)
            k.set_size_request(150, -1)
            v = lbl(value)
            v.add_css_class('sz-prop-val')
            v.set_xalign(0)
            v.set_valign(Gtk.Align.START)
            v.set_wrap(True)
            v.set_selectable(True)
            v.set_hexpand(True)
            grid.attach(k, 0, row, 1, 1)
            grid.attach(v, 1, row, 1, 1)
            row += 1
        self.meta_box.append(grid)
        return False
