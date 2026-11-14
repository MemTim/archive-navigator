#!/bin/sh
# Экспорт интерфейса sevenzip-gtk в SVG (docs/design).
# Запускает приложение в отдельном X-сервере, чтобы не мешать рабочему окну.
set -eu
cd "$(dirname "$0")/.."

if [ "${SZ_DESIGN_DISPLAY:-}" = "1" ]; then
    exec python3 tools/export_design.py "$@"
fi

if ! command -v xvfb-run >/dev/null 2>&1; then
    echo "Нужен xvfb-run (пакет xorg-server-xvfb) или запуск с SZ_DESIGN_DISPLAY=1" >&2
    exit 1
fi

exec xvfb-run -a -s '-screen 0 1400x1000x24' \
    env GDK_BACKEND=x11 GSK_RENDERER=cairo dbus-run-session -- \
    python3 tools/export_design.py "$@"
