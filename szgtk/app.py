# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .i18n import _
from .config import Config
from .backend import SevenZip
from .dialogs import alert
from .window import MainWindow

# ───────────────────────────── приложение ─────────────────────────────
class App(Gtk.Application):
    def __init__(self):
        # У root-экземпляра свой id: он не должен перехватывать команды обычного окна.
        # При наличии сессионной шины он остаётся единственным, а повторные запуски
        # открывают новое окно.
        app_id = APP_ID + '.root' if IS_ROOT else APP_ID
        flags = Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        if IS_ROOT and not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
            flags |= Gio.ApplicationFlags.NON_UNIQUE
        super().__init__(application_id=app_id, flags=flags)
        self.wins = []
        self.win = None          # последнее открытое окно
        self.conf = None
        self.sz = None

    def _backend(self):
        if self.conf is None:
            self.conf, self.sz = Config(), SevenZip()
        return self.conf, self.sz

    def new_window(self, restore=None):
        """Открыть ещё одно окно проводника."""
        conf, sz = self._backend()
        win = MainWindow(self, sz, conf, restore=restore)
        self.wins.append(win)
        self.win = win
        win.connect('close-request', self._on_window_closing)
        win.connect('destroy', self._on_window_destroy)
        if not sz.bin:
            GLib.idle_add(lambda w=win: alert(w, _('7z not found'),
                                              _('Install it:') + ' sudo pacman -S 7zip') and False)
        win.present()
        return win

    def _forget_window(self, win):
        if win in self.wins:
            self.wins.remove(win)
        if self.win is win:
            self.win = self.wins[-1] if self.wins else None

    def _on_window_closing(self, win):
        # close-request приходит при закрытии; destroy в GTK4 — только при уничтожении
        self._forget_window(win)
        return False

    def _on_window_destroy(self, win):
        self._forget_window(win)

    def do_activate(self):
        if not self.wins:
            self.new_window()

    def rebuild(self):
        """Пересоздать все окна (смена дизайна / языка) с сохранением расположений панелей."""
        olds = list(self.wins)
        if not olds:
            return
        self.conf.save()
        states = []
        for old in olds:
            states.append((old, dict(
                p1=old.p1.location_text(), p2=old.p2.location_text(),
                active=0 if old.active is old.p1 else 1, passwords=old.passwords,
                temp=old.temp_dirs)))
            old.rebuilding = True
        for old, state in states:
            # временные каталоги переходят новому окну, старое их не удаляет
            old.temp_dirs = []
            self.new_window(restore=state)
        for old, _state in states:
            old.close()

    def do_command_line(self, cl):
        args = cl.get_arguments()[1:]
        cwd = cl.get_cwd() or os.getcwd()
        win = self.new_window()
        mode, paths = None, []
        for a in args:
            if a in ('--add', '--extract', '--extract-here'):
                mode = a
            else:
                paths.append(os.path.abspath(os.path.join(cwd, a)))
        if mode == '--add':
            win.cli_add(paths)
        elif mode in ('--extract', '--extract-here'):
            win.cli_extract(paths, here=(mode == '--extract-here'))
        elif paths:
            win.cli_open(paths[0])
        win.present()
        return 0


def main():
    sys.exit(App().run(sys.argv))


if __name__ == '__main__':
    main()
