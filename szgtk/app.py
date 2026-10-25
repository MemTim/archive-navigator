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
        # При наличии сессионной шины он остаётся единственным и повторные запуски
        # просто открывают папку в уже существующем root-окне.
        app_id = APP_ID + '.root' if IS_ROOT else APP_ID
        flags = Gio.ApplicationFlags.HANDLES_COMMAND_LINE
        if IS_ROOT and not os.environ.get('DBUS_SESSION_BUS_ADDRESS'):
            flags |= Gio.ApplicationFlags.NON_UNIQUE
        super().__init__(application_id=app_id, flags=flags)
        self.win = None
        self.conf = None
        self.sz = None

    def rebuild(self):
        """Пересоздать окно (смена дизайна / языка) с сохранением расположений панелей."""
        old = self.win
        state = dict(p1=old.p1.location_text(), p2=old.p2.location_text(),
                     active=0 if old.active is old.p1 else 1, passwords=old.passwords,
                     temp=old.temp_dirs)
        old.rebuilding = True
        self.conf.save()
        new = MainWindow(self, self.sz, self.conf, restore=state)
        self.win = new
        new.present()
        old.close()

    def do_command_line(self, cl):
        args = cl.get_arguments()[1:]
        cwd = cl.get_cwd() or os.getcwd()
        if self.win is None:
            self.conf, self.sz = Config(), SevenZip()
            self.win = MainWindow(self, self.sz, self.conf)
            if not self.sz.bin:
                GLib.idle_add(lambda: alert(self.win, _('7z not found'),
                                            _('Install it:') + ' sudo pacman -S 7zip') and False)
        mode, paths = None, []
        for a in args:
            if a in ('--add', '--extract', '--extract-here'):
                mode = a
            else:
                paths.append(os.path.abspath(os.path.join(cwd, a)))
        if mode == '--add':
            self.win.cli_add(paths)
        elif mode in ('--extract', '--extract-here'):
            self.win.cli_extract(paths, here=(mode == '--extract-here'))
        elif paths:
            self.win.cli_open(paths[0])
        self.win.present()
        return 0


def main():
    sys.exit(App().run(sys.argv))


if __name__ == '__main__':
    main()
