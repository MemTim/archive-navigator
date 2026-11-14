# Макеты интерфейса (SVG)

Каждое окно, страница настроек и меню приложения выгружены в отдельный
редактируемый SVG. Начните с [`index.svg`](index.svg) — там все экраны
сеткой, с ссылками на файлы. Для браузера есть та же галерея в
[`index.html`](index.html).

SVG содержат настоящие векторные фигуры, градиенты, значки и текст
(не скриншоты). Исключение — миниатюры и растровые изображения: они
встроены как PNG.

> Правка этих файлов **не меняет приложение**. Это снимки текущего
> оформления для обсуждения и перерисовки макета. После изменения кода
> или темы файлы нужно сгенерировать заново.

## Как перегенерировать

```sh
tools/export-design.sh
```

Скрипт запускает приложение во временном профиле (ваши настройки не
затрагиваются), обходит окна и сохраняет SVG в `docs/design/`.
Нужен X-сервер; на headless-машине используется `xvfb-run`. Для текста
требуется `python3-fonttools` (fontTools).

Для правки в Inkscape/Figma удобнее открывать отдельные файлы: текст
остаётся текстом, палитра и размеры читаются напрямую.

## Главное окно

- [Главное окно — плитки](main/main-tiles.svg)
- [Главное окно — подробный список](main/main-details.svg)
- [Главное окно — поиск](main/main-search.svg)
- [Главное окно — две панели](main/main-two-panels.svg)
- [Главное окно — светлая схема](main/main-tiles-light.svg)
- [Главное окно — двухпанельный дизайн](main/main-dual.svg)
- [Главное окно — навигация с боковой панелью](main/main-nav.svg)

## Меню

- [Меню «Файл»](menus/menubar-file.svg)
- [Меню «Файл» → «Контрольная сумма»](menus/menubar-file-checksum.svg)
- [Меню «Правка»](menus/menubar-edit.svg)
- [Меню «Просмотр»](menus/menubar-view.svg)
- [Меню «Просмотр» → «Колонки»](menus/menubar-view-columns.svg)
- [Меню «Просмотр» → «Сортировка»](menus/menubar-view-sort.svg)
- [Меню «Избранное»](menus/menubar-favorites.svg)
- [Меню «Избранное» → «Добавить папку в избранное как»](menus/menubar-favorites-add-as.svg)
- [Меню «Избранное» → «Убрать из избранного»](menus/menubar-favorites-remove.svg)
- [Меню «Избранное» → «Переименовать избранное»](menus/menubar-favorites-rename.svg)
- [Меню «Сервис»](menus/menubar-tools.svg)
- [Меню «Справка»](menus/menubar-help.svg)
- [Контекстное меню — несколько файлов](menus/context-selection.svg)
- [Контекстное меню → «Конвертировать в»](menus/context-convert-to.svg)
- [Контекстное меню → «Контрольная сумма»](menus/context-checksum.svg)
- [Меню панели](menus/panel-menu.svg)
- [Меню колонок](menus/columns-menu.svg)
- [История папок](menus/history-menu.svg)
- [Поповер «Панели»](menus/top-panels-popover.svg)
- [Избранное — порядок записи](menus/favorites-order.svg)
- [Меню группы боковой панели](menus/sidebar-group-menu.svg)

## Настройки

- [Настройки — Общие](settings/settings-1-general.svg)
- [Настройки — Избранное](settings/settings-2-favorites.svg)
- [Настройки — Оформление](settings/settings-3-appearance.svg)
- [Настройки — Отображение](settings/settings-4-display.svg)
- [Настройки — Язык](settings/settings-5-language.svg)
- [Настройки — Горячие клавиши](settings/settings-6-hotkeys.svg)

## Диалоги

- [Добавить в архив](dialogs/add-archive.svg)
- [Извлечь файлы](dialogs/extract.svg)
- [Разбить файл](dialogs/split.svg)
- [Тест производительности](dialogs/benchmark.svg)
- [Конвертер](dialogs/converter.svg)
- [Свойства файла — Основное](dialogs/properties-file-main.svg)
- [Свойства файла — Права](dialogs/properties-file-permissions.svg)
- [Свойства архива](dialogs/properties-archive.svg)
- [Свойства папки](dialogs/properties-folder.svg)
- [Прогресс — копирование](dialogs/progress-copy.svg)
- [Ввод пароля](dialogs/password.svg)
- [Переименование](dialogs/prompt-rename.svg)
- [Подтверждение удаления](dialogs/confirm-delete.svg)
- [История папок](dialogs/history.svg)
- [Открыть с помощью…](dialogs/open-with.svg)
- [Запись сочетания клавиш](dialogs/key-capture.svg)
- [Результат проверки контрольных сумм](dialogs/text-checksum.svg)
- [О программе](dialogs/about.svg)
- [Системное предупреждение](dialogs/alert.svg)
