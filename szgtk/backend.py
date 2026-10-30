# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from . import diagnostics
from .utils import parse_time

# ───────────────────────────── бэкенд 7z ─────────────────────────────
RE_PROGRESS = re.compile(r'^\s*(\d+)%\s*(.*)$')
RE_FILEOP = re.compile(r'^[-+U=.] (.+)$')
PW_RE = re.compile(r'wrong password|enter password|encrypted archive|'
                   r'data error in encrypted|crc failed in encrypted', re.I)


class Result:
    def __init__(self, rc, out, cancelled=False):
        self.rc, self.out, self.cancelled = rc, out, cancelled

    @property
    def ok(self):
        return self.rc == 0

    def text(self, limit=300):
        lines = [l for l in self.out.splitlines() if l.strip()]
        return '\n'.join(lines[-limit:])


def needs_password(res):
    return res is not None and res.rc != 0 and not res.cancelled and bool(PW_RE.search(res.out))


class Entry:
    __slots__ = ('path', 'is_dir', 'size', 'packed', 'mtime', 'attrs', 'crc', 'method', 'enc')

    def __init__(self, d):
        self.path = d.get('Path', '').rstrip('/')
        self.attrs = d.get('Attributes', '')
        self.is_dir = d.get('Folder') == '+' or self.attrs.startswith('D')
        self.size = int(d['Size']) if d.get('Size', '').isdigit() else 0
        self.packed = int(d['Packed Size']) if d.get('Packed Size', '').isdigit() else 0
        self.mtime = parse_time(d.get('Modified', ''))
        self.crc = d.get('CRC', '')
        self.method = d.get('Method', '')
        self.enc = d.get('Encrypted') == '+'


def parse_slt(text):
    header, entries, cur = {}, [], {}
    in_entries = False
    for line in text.splitlines():
        if not in_entries:
            if line.strip() == '----------':
                in_entries = True
            elif ' = ' in line:
                k, v = line.split(' = ', 1)
                header.setdefault(k, v)
            continue
        if not line.strip():
            if cur:
                entries.append(cur)
                cur = {}
        elif ' = ' in line:
            k, v = line.split(' = ', 1)
            cur[k] = v
        elif line.endswith(' ='):
            cur[line[:-2]] = ''
    if cur:
        entries.append(cur)
    return header, [e for e in map(Entry, entries) if e.path]


def _cmdline(cmd, limit=2000):
    """Командная строка для журнала — без пароля и без длинного хвоста имён."""
    out = []
    for a in cmd:
        if isinstance(a, str) and a.startswith('-p') and len(a) > 2:
            out.append('-p***')
        else:
            out.append(a)
    text = ' '.join(shlex.quote(str(a)) for a in out)
    if len(text) > limit:
        text = text[:limit] + ' … (%d аргументов)' % len(out)
    return text


class Job:
    """Состояние фоновой операции (читается диалогом прогресса)."""

    def __init__(self):
        self.cancelled = False
        self.procs = []
        self.fraction = None
        self.text = ''
        # общий токен отмены для операций без внешнего процесса (копирование)
        self.cancellable = Gio.Cancellable()

    def register(self, proc):
        self.procs.append(proc)
        if self.cancelled:
            self._kill(proc)

    def cancel(self):
        self.cancelled = True
        try:
            self.cancellable.cancel()
        except Exception:
            pass
        for p in self.procs:
            self._kill(p)

    @staticmethod
    def _kill(p):
        try:
            if p.poll() is None:
                p.terminate()
        except OSError:
            pass


class SevenZip:
    def __init__(self):
        self.bin = next((p for p in (shutil.which(n) for n in ('7zz', '7z', '7za', '7zr')) if p), None)
        self.version = ''
        self.is_p7zip = False
        if self.bin:
            try:
                out = subprocess.run([self.bin], capture_output=True, text=True, timeout=15,
                                     stdin=subprocess.DEVNULL).stdout
                m = re.search(r'^.*7-Zip.*$', out, re.M)
                self.version = m.group(0).strip() if m else ''
                self.is_p7zip = 'p7zip' in out.lower()
            except Exception:
                pass

    def _handle_line(self, line, out, job):
        if not line.strip():
            return
        m = RE_PROGRESS.match(line)
        if m:
            if job is not None:
                job.fraction = int(m.group(1)) / 100.0
            return
        m = RE_FILEOP.match(line)
        if m:
            if job is not None:
                job.text = m.group(1)
            return
        out.append(line)

    def run(self, command, switches, positional, cwd=None, job=None, password=None):
        """Запуск 7z с разбором прогресса. Возвращает Result."""
        if not self.bin:
            return Result(255, '7z not found')
        cmd = [self.bin, command, '-sccUTF-8', '-scsUTF-8', '-bb1', '-bsp1']
        if password:
            cmd.append('-p' + password)
        cmd += list(switches) + ['--'] + list(positional)
        diagnostics.log('7z %s', _cmdline(cmd))
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError as e:
            diagnostics.log('7z: не удалось запустить: %s', e)
            return Result(255, str(e))
        if job is not None:
            job.register(proc)
        out, buf, fd = [], b'', proc.stdout.fileno()
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            buf += chunk
            parts = re.split(rb'[\r\n\x08]', buf)
            buf = parts.pop()
            for p in parts:
                self._handle_line(p.decode('utf-8', 'replace'), out, job)
        if buf:
            self._handle_line(buf.decode('utf-8', 'replace'), out, job)
        rc = proc.wait()
        cancelled = bool(job and job.cancelled)
        diagnostics.log('7z: rc=%d%s', rc, ' (отменено)' if cancelled else '')
        return Result(255 if cancelled else rc, '\n'.join(out), cancelled)

    def list_archive(self, path, password=None):
        if not self.bin:
            return Result(255, '7z not found'), {}, []
        cmd = [self.bin, 'l', '-slt', '-sccUTF-8', '-scsUTF-8']
        if password:
            cmd.append('-p' + password)
        cmd += ['--', path]
        try:
            p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True)
        except OSError as e:
            return Result(255, str(e)), {}, []
        text = p.stdout.decode('utf-8', 'replace')
        res = Result(p.returncode, text + p.stderr.decode('utf-8', 'replace'))
        header, entries = parse_slt(text)
        return res, header, entries

    def list_tar_compound(self, path, password=None):
        """Содержимое foo.tar.gz (внутренний tar) без записи на диск."""
        c1 = [self.bin, 'x', '-so', '-sccUTF-8']
        if password:
            c1.append('-p' + password)
        c1 += ['--', path]
        c2 = [self.bin, 'l', '-slt', '-si', '-ttar', '-sccUTF-8']
        try:
            p1 = subprocess.Popen(c1, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
            p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL)
        except OSError:
            return {}, []
        p1.stdout.close()
        out = p2.communicate()[0].decode('utf-8', 'replace')
        p1.wait()
        return parse_slt(out)

    def extract_tar_compound(self, archive, dest, overwrite_sw, job, password=None):
        """foo.tar.gz → распаковка за один проход через конвейер 7z | 7z."""
        os.makedirs(dest, exist_ok=True)
        c1 = [self.bin, 'x', '-so', '-sccUTF-8']
        if password:
            c1.append('-p' + password)
        c1 += ['--', archive]
        c2 = [self.bin, 'x', '-si', '-ttar', '-y', '-o' + dest, '-sccUTF-8'] + list(overwrite_sw)
        try:
            p1 = subprocess.Popen(c1, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            p2 = subprocess.Popen(c2, stdin=p1.stdout, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        except OSError as e:
            return Result(255, str(e))
        p1.stdout.close()
        job.register(p1)
        job.register(p2)
        out2 = p2.communicate()[0].decode('utf-8', 'replace')
        err1 = p1.stderr.read().decode('utf-8', 'replace')
        rc1 = p1.wait()
        rc2 = p2.returncode
        cancelled = job.cancelled
        return Result(255 if cancelled else (rc1 or rc2), err1 + '\n' + out2, cancelled)
