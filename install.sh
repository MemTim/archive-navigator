#!/usr/bin/env bash
# Archive Navigator — установка в домашний каталог пользователя.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
prefix="${PREFIX:-$HOME/.local/share/sevenzip-gtk}"
bindir="${BINDIR:-$HOME/.local/bin}"
appdir="${APPDIR:-$HOME/.local/share/applications}"
desktop="$appdir/io.sevenzipgtk.App.desktop"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$bindir/sevenzip-gtk" "$desktop"
    rm -rf "$prefix"
    icondir="${ICONDIR:-$HOME/.local/share/icons}"
    rm -f "$icondir/hicolor/scalable/apps/io.sevenzipgtk.App.svg" \
          "$icondir/hicolor/256x256/apps/io.sevenzipgtk.App.png"
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$icondir/hicolor" 2>/dev/null || true
    command -v update-desktop-database >/dev/null && update-desktop-database "$appdir" 2>/dev/null || true
    echo "Удалено: $prefix, $bindir/sevenzip-gtk, $desktop, значки приложения"
    exit 0
fi

echo "== Проверка зависимостей =="
python3 - <<'PY' || { echo "Нужен GTK4 + PyGObject: sudo pacman -S gtk4 python-gobject"; exit 1; }
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
print('GTK', Gtk.get_major_version(), '.', Gtk.get_minor_version(), '.', Gtk.get_micro_version(), sep='')
PY
if ! command -v 7z >/dev/null && ! command -v 7zz >/dev/null; then
    echo "Внимание: не найден 7z/7zz. Установите: sudo pacman -S 7zip" >&2
fi

install -d "$bindir" "$appdir"

if [[ "$(realpath -m "$prefix")" == "$(realpath -m "$here")" ]]; then
    echo "== Каталог установки совпадает с исходниками — копирование не нужно =="
else
    echo "== Установка в $prefix =="
    install -d "$prefix"
    rm -rf "$prefix/szgtk"
    cp -a "$here/szgtk" "$prefix/"
    cp -a "$here/sevenzip-gtk.py" "$prefix/"
    chmod +x "$prefix/sevenzip-gtk.py"
fi

# прогреваем байткод: иначе первый запуск тратит время на компиляцию всех модулей
python3 -m compileall -q "$prefix/szgtk" "$prefix/sevenzip-gtk.py" 2>/dev/null || true

ln -sf "$prefix/sevenzip-gtk.py" "$bindir/sevenzip-gtk"

sed "s|@EXEC@|$bindir/sevenzip-gtk|g" "$here/data/io.sevenzipgtk.App.desktop" > "$desktop"
chmod 644 "$desktop"

# значки приложения (scalable + растровый запасной вариант)
icondir="${ICONDIR:-$HOME/.local/share/icons}"
if [[ -d "$here/data/icons/hicolor" ]]; then
    install -d "$icondir/hicolor"
    cp -a "$here/data/icons/hicolor/." "$icondir/hicolor/"
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -f -t "$icondir/hicolor" 2>/dev/null || true
fi

command -v update-desktop-database >/dev/null && update-desktop-database "$appdir" 2>/dev/null || true

echo
echo "Готово. Запуск: sevenzip-gtk  (или из меню приложений)"
echo "Удаление:    $here/install.sh --uninstall"
