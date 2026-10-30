# -*- coding: utf-8 -*-
import warnings
from .imports import *  # noqa: F401,F403
from .icons import clear_icon_cache, set_badge_theme

# ───────────────────────────── тема оформления ─────────────────────────────
PAL = dict(bg='#08071F', surface='#211F35', border='#302D45', text='#EEEBFA',
           muted='#8B879C', accent='#458BDF', focus='#FFF59B', soft='#D0CED1')

BASE_CSS = """
.sz-toolbar { padding: 3px 6px; }
.sz-toolbar button { padding: 3px 10px; border-radius: 6px; min-height: 0; min-width: 0; }
.sz-toolbar-h button { padding: 6px 12px; }
.sz-primary label { font-weight: 700; }
.sz-panels-btn { padding: 4px 10px; border-radius: 8px; min-height: 0; min-width: 0; }
.sz-panels-btn label { font-weight: 600; }
.sz-panels-pop { padding: 6px; }
.sz-panels-head { padding: 8px 10px 4px 10px; }
.sz-panels-title { font-weight: 700; font-size: 105%; }
.sz-panels-sub { font-size: 90%; opacity: 0.6; }
.sz-panels-row { padding: 8px 10px; border-radius: 8px; min-height: 0; }
.sz-panels-row-title { font-weight: 600; }
.sz-panels-note { font-size: 88%; opacity: 0.55; }
.sz-panels-check { color: @theme_selected_bg_color; }
.sz-panels-uncheck { opacity: 0.55; }
.sz-panels-sep { margin: 4px 8px; min-height: 1px; }
.sz-panels-preview { padding: 4px 10px; border-radius: 8px;
  background: alpha(currentColor, 0.06); border: 1px solid alpha(currentColor, 0.16); }
.sz-panels-preview label { font-weight: 600; }
.sz-top-panels { padding: 2px 0 4px 0; }
.sz-radio-card { padding: 12px 14px; border-radius: 12px;
  border: 1px solid alpha(currentColor, 0.16); background: alpha(currentColor, 0.03); }
.sz-radio-card:hover { background: alpha(currentColor, 0.06); }
.sz-radio-card:checked { border-color: @theme_selected_bg_color;
  background: alpha(@theme_selected_bg_color, 0.08); }
.sz-radio-card-title { font-weight: 700; }
.sz-radio-card-desc { font-size: 90%; opacity: 0.6; }
.sz-info-box { padding: 10px; border-radius: 12px; background: alpha(currentColor, 0.05);
  border: 1px solid alpha(currentColor, 0.14); }
.sz-muted { opacity: 0.6; }
.sz-st-main { font-weight: 600; }
.sz-statusbar { padding: 5px 12px; font-size: 90%; }
.sz-st-progress { min-width: 140px; min-height: 6px; margin: 0 4px; }
.sz-section { font-size: 78%; font-weight: 700; opacity: 0.55; margin: 12px 8px 4px 8px; }
.sz-side-item { padding: 7px 10px; border-radius: 6px; min-height: 0; }
.sz-side-device-row { padding: 0; border-radius: 6px; }
.sz-side-eject { padding: 4px; min-width: 26px; min-height: 26px; border-radius: 6px; }
.sz-side-unmounted { opacity: 0.72; }
.sz-side-paned > separator { background: transparent; min-width: 5px; min-height: 1px; }
.sz-side-paned > separator:hover { background: alpha(currentColor, 0.16); }
.sz-side-group-label { font-size: 78%; font-weight: 700; opacity: 0.55; }
.sz-side-edit { padding: 4px; min-width: 28px; min-height: 28px; border-radius: 6px;
  background: transparent; border: none; box-shadow: none; }
.sz-side-edit:hover { background: alpha(currentColor, 0.10); }
.sz-side-edit.sz-side-edit-on { background: alpha(currentColor, 0.16); }
.sz-menu-hidden .sz-side-group-label { opacity: 0.35; }
.sz-usercard { padding: 10px 12px; border-radius: 8px; margin: 8px; }
.sz-hdr { padding: 6px 10px; }
.sz-hdr-role { font-weight: 700; }
.sz-badge { font-size: 78%; opacity: 0.6; letter-spacing: 0.5px; }
.sz-title { font-weight: 700; font-size: 115%; }
.sz-prop-icon { background: alpha(currentColor, 0.07); border: 1px solid alpha(currentColor, 0.14);
  border-radius: 10px; padding: 8px; }
.sz-prop-name { font-weight: 500; }
.sz-prop-key { opacity: 0.58; }
.sz-prop-col { opacity: 0.58; font-weight: 600; }
.sz-prop-sep { background: alpha(currentColor, 0.16); min-height: 1px; }
.sz-prop-section { font-weight: 700; font-size: 92%; opacity: 0.62; letter-spacing: 0.3px; }
.sz-prop-note { opacity: 0.55; font-size: 90%; }
.sz-tab-text { color: inherit; }
.sz-prop-tab { background: transparent; background-image: none; border: none; box-shadow: none;
  border-radius: 7px 7px 4px 4px; padding: 5px 12px 0 12px; margin: 0 2px; min-height: 0;
  color: alpha(currentColor, 0.6); outline: none; }
.sz-prop-tab:hover { background: transparent; color: currentColor; }
.sz-prop-tab:checked { background: transparent; color: @theme_selected_bg_color; }
.sz-prop-tab:focus, .sz-prop-tab:focus-visible { outline: none; box-shadow: none; }
.sz-prop-tab:hover .sz-tab-line-hover { opacity: 1; }
.sz-prop-tab:checked .sz-tab-line-active { opacity: 1; }
.sz-prop-tab:checked .sz-tab-line-hover { opacity: 0; }
.sz-prop-tabsep { background: alpha(currentColor, 0.14); min-height: 1px; }
.sz-foot { padding: 5px 10px; font-size: 88%; }
.sz-pathbar { padding: 4px 6px; }
.sz-pathbar button { min-height: 0; min-width: 0; padding: 4px 8px; }
.sz-pv { border-radius: 6px; padding: 4px; background: #08071F; border: 1px solid #302D45; }
.sz-pv-menu { background: #302D45; min-height: 5px; border-radius: 2px; }
.sz-pv-tool { background: #211F35; min-height: 12px; border-radius: 3px; }
.sz-pv-addr { background: #211F35; min-height: 8px; border-radius: 3px; border: 1px solid #F2E5A2; }
.sz-pv-row { background: #302D45; min-height: 3px; border-radius: 1px; }
.sz-pv-rowsel { background: #458BDF; min-height: 3px; border-radius: 1px; }
.sz-pv-side { background: #211F35; border-radius: 3px; }
.sz-pv-stat { background: #302D45; min-height: 4px; border-radius: 2px; }
.sz-pv-hdr { background: #211F35; min-height: 7px; border-radius: 2px; }
.sz-card { padding: 8px; border-radius: 10px; border: 2px solid transparent; }
.sz-card-sel { border-color: #458BDF; }
.sz-menubar { padding: 2px 6px; }
.sz-menubar-item { padding: 3px 10px; min-height: 0; min-width: 0; border-radius: 6px; }
.sz-menu { padding: 4px; border-radius: 10px; }
.sz-menu-item { padding: 6px 10px; min-height: 0; min-width: 0; border-radius: 6px; }
.sz-menu-sep { margin: 4px 6px; min-height: 1px; }
.sz-root-banner { background-color: #8B1D1D; color: #FFFFFF; padding: 3px 12px; font-weight: 600; }
.sz-root-banner label { color: #FFFFFF; }
.sz-inline-edit { padding: 1px 6px; min-height: 0; margin: 0; }
.sz-inline-text { border-radius: 8px; padding: 2px 7px; min-height: 0; }
.sz-inline-text text { background: none; }
.sz-fav-row { border-radius: 12px; padding: 6px 10px; }
.sz-fav-num { font-size: 105%; min-width: 30px; }
.sz-fav-field { border-radius: 10px; padding: 0 10px; min-height: 34px; }
.sz-fav-sort { padding: 3px; min-width: 28px; min-height: 28px; border-radius: 6px;
  background: transparent; border: none; box-shadow: none; }
.sz-fav-del { padding: 4px; min-width: 26px; min-height: 26px; border-radius: 6px;
  background: transparent; border: none; box-shadow: none; }
.sz-fav-add { padding: 0; min-height: 48px; border-radius: 12px; }
.sz-menu-row { min-height: 32px; }
.sz-menu-label { font-size: 105%; }
.sz-menu-handle { padding: 3px; min-width: 28px; min-height: 28px; border-radius: 6px; }
.sz-menu-eye { padding: 3px; min-width: 26px; min-height: 26px; border-radius: 6px;
  background: transparent; border: none; box-shadow: none; }
/* Компактные строки боковой панели в режиме редактирования: ручка и «глаз»
   не должны делать плитку выше обычного пункта. */
.sz-side-edit-row { padding: 5px 10px; margin: 0; min-height: 0; }
.sz-side-handle { padding: 3px; min-width: 0; min-height: 0; border-radius: 6px; }
.sz-side-eye { padding: 3px; min-width: 0; min-height: 0; border-radius: 6px;
  background: transparent; border: none; box-shadow: none; }
.sz-menu-more { padding: 3px; min-width: 26px; min-height: 26px; border-radius: 6px;
  background: transparent; border: none; box-shadow: none; }
.sz-menu-row.sz-menu-selected { background-color: alpha(currentColor, 0.10); }
.sz-menu-row.sz-menu-dragging { opacity: 0.55; }
.sz-menu-row.sz-menu-drop { box-shadow: inset 0 0 0 2px alpha(currentColor, 0.55); }
.sz-menu-group { padding: 3px 10px; min-height: 0; border-radius: 8px;
  background: alpha(currentColor, 0.08); border: none; box-shadow: none; }
.sz-menu-group:hover { background: alpha(currentColor, 0.14); }
.sz-menu-group-icon { color: currentColor; }
.sz-menu-hidden .sz-menu-label { opacity: 0.45; }
.sz-menu-hidden .sz-menu-eye { opacity: 0.55; }
gridview:focus, gridview:focus-visible,
gridview > child:focus, gridview > child:focus-visible, gridview > child:focus-within,
treeview.view:focus, treeview.view:focus-visible
  { outline: none; box-shadow: none; border-color: transparent; }
notebook { border: none; box-shadow: none; }
window:drop(active), window :drop(active) { outline: none; box-shadow: none; border-color: transparent; }
/* ── окно прогресса ── */
.sz-prog-header { min-height: 46px; box-shadow: none; }
.sz-prog-title { font-weight: 700; }
.sz-prog-body { padding: 18px 24px 20px 24px; }
.sz-prog-icon { border-radius: 10px; padding: 9px; background: alpha(currentColor, 0.07); }
.sz-prog-name { font-weight: 700; font-size: 150%; }
/* Вторичный текст не уменьшаем: при 92 % хинтинг Adwaita Sans округляет
   верхние перекладины «Б»/«П»/«7» в ноль (буквы выглядят обрезанными). */
.sz-prog-sub { opacity: 0.62; }
.sz-prog-pct { font-weight: 700; font-size: 150%; }
.sz-prog-info { opacity: 0.62; }
.sz-prog-files { opacity: 0.62; }
.sz-prog-bar trough { min-height: 8px; border-radius: 4px; }
.sz-prog-bar progress { min-height: 8px; border-radius: 4px; }
.sz-prog-footer { padding: 13px 20px; border-top: 1px solid alpha(currentColor, 0.14); }
.sz-prog-cancel, .sz-prog-pause { padding: 7px 18px; border-radius: 8px; }
"""

MIDNIGHT_CSS = """
window.sz-midnight { background-color: $bg; color: $text; }
.sz-midnight label { color: $text; }
.sz-midnight headerbar, .sz-midnight .titlebar
  { background: $bg; color: $text; border-bottom: 1px solid $border; box-shadow: none; }
.sz-midnight headerbar button { color: $text; background: transparent; }
.sz-midnight popovermenubar { background: $bg; border-bottom: 1px solid $border; }
.sz-midnight popovermenubar > item { color: $text; padding: 5px 11px; border-radius: 5px; }
.sz-midnight popovermenubar > item:hover, .sz-midnight popovermenubar > item:checked
  { background: $surface; }
.sz-midnight popover, .sz-midnight popover.background
  { background: none; background-color: transparent; border: none; box-shadow: none; }
.sz-midnight popover > contents { background-color: $surface; color: $text; border: 1px solid $border;
  border-radius: 10px; box-shadow: 0 6px 22px alpha(black, 0.5); }
.sz-midnight popover > arrow { background-color: $surface; border: 1px solid $border; }
.sz-midnight popover modelbutton { color: $text; }
.sz-midnight popover modelbutton:hover { background: $border; }
.sz-midnight popover separator { background: $border; }
.sz-midnight button { background: transparent; background-image: none; color: $text;
  border: 1px solid transparent; box-shadow: none; text-shadow: none; }
.sz-midnight button:hover { background: $surface; }
.sz-midnight button:active, .sz-midnight button:checked { background: $border; }
.sz-midnight button:disabled { opacity: 0.4; }
.sz-midnight .sz-primary { background: $surface; }
.sz-midnight button.suggested-action { background: $accent; color: #ffffff; }
.sz-midnight button.suggested-action label { color: #ffffff; }
.sz-midnight dialog button, .sz-midnight .sz-framed button { border-color: $border; }
.sz-midnight .sz-dlg-cancel { background: $border; border: 1px solid $border; border-radius: 8px; padding: 6px 16px; }
.sz-midnight button.sz-dlg-ok { background: $focus; border: 1px solid $focus; border-radius: 8px; padding: 6px 16px; color: #0E0E43; }
.sz-midnight button.sz-dlg-ok label { color: #0E0E43; }
.sz-midnight button.sz-dlg-ok:hover { background: #FFF59B; border-color: #FFF59B; }
.sz-midnight entry { background: $surface; color: $text; border: 1px solid $border;
  border-radius: 6px; box-shadow: none; caret-color: $text; }
.sz-midnight entry:focus-within { border-color: $focus; }
.sz-midnight entry selection, .sz-midnight text selection { background: $accent; color: #ffffff; }
.sz-midnight treeview.view { background-color: $bg; color: $text; }
.sz-midnight treeview.view:selected { background-color: $surface; color: $text; }
.sz-midnight treeview.view:hover { background-color: alpha($surface, 0.6); }
.sz-midnight treeview.view:focus:selected { background-color: $border; }
.sz-midnight treeview header button { background: $bg; color: $muted; border-radius: 0;
  border-bottom: 1px solid $border; font-weight: 600; }
.sz-midnight treeview header button label { color: $muted; font-weight: 500; }
.sz-midnight treeview header button:hover label { color: $text; }
.sz-midnight scrollbar, .sz-midnight scrollbar trough, .sz-midnight scrollbar.overlay-indicator trough
  { background: none; background-color: transparent; border: none; box-shadow: none; outline: none; }
.sz-midnight scrollbar slider,
.sz-midnight scrollbar.overlay-indicator slider,
.sz-midnight scrollbar.overlay-indicator:not(.dragging):not(.hovering) slider,
.sz-midnight scrollbar.overlay-indicator.hovering slider,
.sz-midnight scrollbar.overlay-indicator.dragging slider
  { background-color: alpha($muted, 0.5); background-image: none; background-clip: padding-box;
    border: 1px solid transparent; border-radius: 999px; box-shadow: none; outline: none; outline-offset: 0; }
.sz-midnight scrollbar slider:hover,
.sz-midnight scrollbar.overlay-indicator.hovering slider { background-color: $muted; }
.sz-midnight gridview, .sz-midnight gridview.view { background-color: $bg; color: $text; }
.sz-midnight gridview > child { border-radius: 8px; }
.sz-midnight gridview > child:hover { background-color: alpha($surface, 0.6); }
.sz-midnight gridview > child:selected, .sz-midnight gridview > child:selected:hover
  { background-color: alpha($accent, 0.30); color: $text; }
.sz-midnight gridview > child label { color: $text; }
.sz-midnight .sz-drop-ring
  { border: 2px solid alpha($accent, 0.65); background-color: alpha($accent, 0.05); border-radius: 8px; }
.sz-midnight iconview, .sz-midnight iconview.view { background-color: $bg; color: $text; }
.sz-midnight iconview:selected, .sz-midnight iconview.view:selected, .sz-midnight iconview .cell:selected
  { background-color: alpha($accent, 0.30); color: $text; border-radius: 8px; }
.sz-midnight iconview:hover { background-color: alpha($surface, 0.5); }
.sz-midnight scrollbar slider:active,
.sz-midnight scrollbar.overlay-indicator.dragging slider { background-color: $accent; }
.sz-midnight undershoot.top, .sz-midnight undershoot.bottom, .sz-midnight undershoot.left, .sz-midnight undershoot.right
  { background: none; }
.sz-midnight separator { background: $border; }
.sz-midnight check, .sz-midnight radio { background: $surface; border: 1px solid $border; color: $text; }
.sz-midnight check:checked, .sz-midnight check:indeterminate,
.sz-midnight radio:checked, .sz-midnight radio:indeterminate
  { background: $focus; border-color: $focus; color: #0E0E43; }
.sz-midnight frame > border { border-color: $border; }
.sz-midnight notebook > header, .sz-midnight notebook > header > tabs
  { background: $bg; border: none; box-shadow: none; }
.sz-midnight notebook > header { padding: 6px 6px 0 6px; }
.sz-midnight notebook > header > tabs > tab { color: $muted; background: transparent;
  border: none; box-shadow: none; border-radius: 7px 7px 4px 4px;
  padding: 5px 12px 0 12px; margin: 0 2px; min-height: 0; }
.sz-midnight notebook > header > tabs > tab:hover { color: $text; background: transparent; }
.sz-midnight notebook > header > tabs > tab:checked { color: $focus; background: transparent; }
.sz-midnight .sz-tab-line-active { color: $focus; opacity: 0;
  transition: opacity 180ms ease; }
.sz-midnight .sz-tab-line-hover { color: #FFFFFF; opacity: 0;
  transition: opacity 180ms ease; }
.sz-midnight notebook > header > tabs > tab:hover .sz-tab-line-hover { opacity: 1; }
.sz-midnight notebook > header > tabs > tab:checked .sz-tab-line-active { opacity: 1; }
.sz-midnight notebook > header > tabs > tab:checked .sz-tab-line-hover { opacity: 0; }
.sz-midnight notebook > stack { background: $bg; border: none; }
.sz-midnight .sz-prop-icon { background: $surface; border: 1px solid $border; }
.sz-midnight .sz-prop-key, .sz-midnight .sz-prop-col,
.sz-midnight .sz-prop-section, .sz-midnight .sz-prop-note { color: $muted; opacity: 1; }
.sz-midnight .sz-prop-sep { background: $border; }
.sz-midnight .sz-prop-name { background: $surface; border: 1px solid $border; }
.sz-midnight .sz-tab-text { color: inherit; }
.sz-midnight .sz-prop-tab { color: $muted; }
.sz-midnight .sz-prop-tab:hover { color: $text; background: transparent; }
.sz-midnight .sz-prop-tab:checked { color: $focus; background: transparent; }
.sz-midnight .sz-prop-tabsep { background: $border; }
.sz-midnight list, .sz-midnight listview { background: $bg; color: $text; }
.sz-midnight row:hover { background: alpha($surface, 0.7); }
.sz-midnight row:selected { background: $surface; color: $text; }
.sz-midnight textview, .sz-midnight textview text { background: $bg; color: $text; }
.sz-midnight progressbar trough { background: $surface; border: none; }
.sz-midnight progressbar progress { background: $focus; border: none; }
.sz-midnight .sz-prog-icon { background: $surface; }
.sz-midnight .sz-prog-sub, .sz-midnight .sz-prog-info,
.sz-midnight .sz-prog-files { color: $soft; opacity: 1; }
.sz-midnight .sz-prog-bar trough { background: $surface; border: none; }
.sz-midnight .sz-prog-bar progress { background: $soft; border: none; }
.sz-midnight .sz-prog-footer { border-top: 1px solid $border; }
.sz-midnight .sz-prog-cancel { background: transparent; border: 1px solid $surface; color: $text; }
.sz-midnight .sz-prog-cancel:hover { background: $surface; }
.sz-midnight .sz-prog-pause { background: $surface; border: 1px solid $surface; color: $text; }
.sz-midnight .sz-prog-pause:hover { background: $border; }
.sz-midnight dropdown > button { background: $surface; border: 1px solid $border; }
.sz-midnight popover.menu listview { background: transparent; }
.sz-midnight .sz-statusbar { background: $surface; border-top: 1px solid $border; }
.sz-midnight .sz-st-progress trough { min-height: 6px; border-radius: 3px; background: $border; }
.sz-midnight .sz-st-progress progress { min-height: 6px; border-radius: 3px; background: $focus; }
.sz-midnight .sz-toolbar { background: $bg; border-bottom: 1px solid $border; }
.sz-midnight .sz-panels-btn { background: $surface; border: 1px solid $border; }
.sz-midnight .sz-panels-btn:hover { background: $border; }
.sz-midnight .sz-panels-row:hover { background: $border; }
.sz-midnight .sz-panels-check { color: $focus; }
.sz-midnight .sz-panels-preview { background: $surface; border-color: $border; }
.sz-midnight .sz-radio-card { background: alpha($surface, 0.55); border-color: $border; }
.sz-midnight .sz-radio-card:hover { background: $surface; }
.sz-midnight .sz-radio-card:checked { border-color: $focus; background: alpha($focus, 0.08); }
.sz-midnight .sz-radio-card check:checked, .sz-midnight .sz-radio-card radio:checked
  { background: $focus; border-color: $focus; color: #0E0E43; }
.sz-midnight switch:checked { background: $focus; border-color: $focus; }
.sz-midnight switch:checked slider { background: #FFFFFF; }
.sz-midnight .sz-info-box { background: $surface; border-color: $border; }
.sz-midnight .sz-sidebar { background: $bg; border-right: 1px solid $border; }
.sz-midnight .sz-usercard { background: $surface; }
.sz-midnight .sz-side-eject:hover { background: $border; }
.sz-midnight .sz-side-active { background: $surface; box-shadow: inset 3px 0 $focus; }
.sz-midnight .sz-side-device-row.sz-side-active { background: $surface; box-shadow: none; }
.sz-midnight .sz-side-device-row.sz-side-active .sz-side-bar { box-shadow: inset 3px 0 $focus; }
.sz-midnight .sz-hdr { background: $bg; border-bottom: 1px solid $border; }
.sz-midnight .sz-foot { background: $bg; border-top: 1px solid $border; }
.sz-midnight paned > separator { background: $border; min-width: 1px; min-height: 1px; }
.sz-midnight tooltip { background: $surface; color: $text; }
.sz-midnight .sz-menubar { background: $bg; border-bottom: 1px solid $border; }
.sz-midnight .sz-menubar-item:hover, .sz-midnight .sz-menubar-open { background-color: $surface; }
.sz-midnight .sz-menu { background-color: $surface; border: 1px solid $border;
  box-shadow: 0 8px 24px alpha(black, 0.55); }
.sz-midnight .sz-menu-item:hover, .sz-midnight .sz-menu-item:focus { background-color: $border; }
.sz-midnight .sz-menu-sep { background-color: alpha($text, 0.22); }
.sz-midnight .sz-inline-text { background-color: $surface; color: $text; border: 1px solid $focus;
  caret-color: $text; }
.sz-midnight .sz-inline-text text { background: transparent; color: $text; }
.sz-midnight .sz-inline-text selection { background-color: $accent; color: #ffffff; }
.sz-midnight .sz-fav-row { background-color: transparent; border: 1px solid alpha($text, 0.62); }
.sz-midnight .sz-fav-row.sz-fav-sel { background-color: #49475F; }
.sz-midnight .sz-fav-num { color: $text; }
.sz-midnight .sz-fav-field { background-color: #302D45; border: 1px solid #3C3958; color: $text; }
.sz-midnight .sz-fav-field:focus-within { border-color: $focus; }
.sz-midnight .sz-fav-field > text > placeholder { color: $muted; }
.sz-midnight .sz-fav-arrow { color: $muted; }
.sz-midnight .sz-fav-sort { color: $text; }
.sz-midnight .sz-fav-del { color: #F20D14; }
.sz-midnight .sz-fav-del:hover { background: alpha(#F20D14, 0.16); }
.sz-midnight .sz-fav-add { background: transparent; border: 1px dashed alpha($muted, 0.9);
  box-shadow: none; color: $text; }
.sz-midnight .sz-fav-add:hover { background: alpha($text, 0.05); }
.sz-midnight .sz-conv-dd > button { background-color: #302D45; border: 1px solid #3C3958;
  border-radius: 10px; min-height: 34px; padding: 0 10px; color: $text; }
.sz-midnight .sz-conv-dd > button:hover { background-color: #3C3958; }
.sz-midnight .sz-conv-dd > button:focus { border-color: $focus; }
.sz-midnight .sz-menu-row.sz-menu-dragging { background-color: #49475F; }
.sz-midnight .sz-menu-row.sz-menu-drop { box-shadow: inset 0 0 0 2px $focus; }
.sz-midnight .sz-menu-row.sz-menu-selected { background-color: alpha($focus, 0.16);
  box-shadow: inset 0 0 0 1px alpha($focus, 0.45); }
.sz-midnight .sz-menu-group { color: $focus; background: alpha($focus, 0.12); }
.sz-midnight .sz-menu-group:hover { background: alpha($focus, 0.20); }
.sz-midnight .sz-menu-handle, .sz-midnight .sz-menu-eye, .sz-midnight .sz-menu-more
  { color: $text; }
.sz-midnight .sz-menu-handle:hover, .sz-midnight .sz-menu-eye:hover,
.sz-midnight .sz-menu-more:hover { background: alpha($text, 0.08); }
.sz-midnight .sz-menu-more.sz-menu-filtered { color: $focus; }
.sz-midnight .sz-menu-hidden .sz-menu-label, .sz-midnight .sz-menu-hidden .sz-menu-eye
  { color: $muted; opacity: 0.55; }
"""

LIGHT_EXTRA_CSS = """
.sz-light .sz-side-active, .sz-system .sz-side-active { background: alpha(currentColor, 0.1); }
.sz-light .sz-usercard, .sz-system .sz-usercard { background: alpha(currentColor, 0.06); }
.sz-light .sz-statusbar, .sz-system .sz-statusbar { background: alpha(currentColor, 0.10);
  border-top: 1px solid alpha(currentColor, 0.15); }
.sz-light .sz-sidebar, .sz-system .sz-sidebar { border-right: 1px solid alpha(currentColor, 0.15); }
.sz-light .sz-hdr, .sz-system .sz-hdr { border-bottom: 1px solid alpha(currentColor, 0.15); }
.sz-light .sz-primary, .sz-system .sz-primary { background: alpha(currentColor, 0.08); }
.sz-light .sz-menubar, .sz-system .sz-menubar { border-bottom: 1px solid alpha(currentColor, 0.15); }
.sz-light .sz-menubar-item:hover, .sz-light .sz-menubar-open,
.sz-system .sz-menubar-item:hover, .sz-system .sz-menubar-open { background-color: alpha(currentColor, 0.12); }
.sz-light .sz-menu, .sz-system .sz-menu { background-color: color-mix(in srgb, currentColor 6%, @theme_bg_color);
  border: 1px solid alpha(currentColor, 0.22); box-shadow: 0 6px 20px alpha(black, 0.28); }
.sz-light .sz-menu-item:hover, .sz-light .sz-menu-item:focus,
.sz-system .sz-menu-item:hover, .sz-system .sz-menu-item:focus { background-color: alpha(currentColor, 0.1); }
.sz-light .sz-menu-sep, .sz-system .sz-menu-sep { background-color: alpha(currentColor, 0.28); }
.sz-light .sz-inline-text, .sz-system .sz-inline-text { background-color: @theme_base_color;
  color: @theme_text_color; border: 1px solid alpha(currentColor, 0.45); caret-color: currentColor; }
.sz-light .sz-inline-text text, .sz-system .sz-inline-text text { background: transparent; }
.sz-light .sz-inline-text selection, .sz-system .sz-inline-text selection
  { background-color: @theme_selected_bg_color; color: @theme_selected_fg_color; }
.sz-light .sz-drop-ring, .sz-system .sz-drop-ring
  { border: 2px solid alpha(currentColor, 0.5); background-color: alpha(currentColor, 0.04); border-radius: 8px; }
.sz-light notebook > header, .sz-system notebook > header,
.sz-light notebook > header > tabs, .sz-system notebook > header > tabs
  { background: @theme_bg_color; border: none; box-shadow: none; }
.sz-light notebook > header, .sz-system notebook > header { padding: 6px 6px 0 6px; }
.sz-light notebook > header > tabs > tab, .sz-system notebook > header > tabs > tab
  { color: alpha(currentColor, 0.6); background: transparent; border: none; box-shadow: none;
    border-radius: 7px 7px 4px 4px; padding: 5px 12px 0 12px; margin: 0 2px; min-height: 0; }
.sz-light notebook > header > tabs > tab:hover, .sz-system notebook > header > tabs > tab:hover
  { color: currentColor; background: transparent; }
.sz-light notebook > header > tabs > tab:checked, .sz-system notebook > header > tabs > tab:checked
  { color: @theme_selected_bg_color; background: transparent; }
.sz-light .sz-tab-line-active, .sz-system .sz-tab-line-active
  { color: @theme_selected_bg_color; opacity: 0; transition: opacity 180ms ease; }
.sz-light .sz-tab-line-hover, .sz-system .sz-tab-line-hover
  { color: alpha(@theme_fg_color, 0.55); opacity: 0; transition: opacity 180ms ease; }
.sz-light notebook > header > tabs > tab:hover .sz-tab-line-hover,
.sz-system notebook > header > tabs > tab:hover .sz-tab-line-hover { opacity: 1; }
.sz-light notebook > header > tabs > tab:checked .sz-tab-line-active,
.sz-system notebook > header > tabs > tab:checked .sz-tab-line-active { opacity: 1; }
.sz-light notebook > header > tabs > tab:checked .sz-tab-line-hover,
.sz-system notebook > header > tabs > tab:checked .sz-tab-line-hover { opacity: 0; }
.sz-light notebook > stack, .sz-system notebook > stack
  { background: @theme_bg_color; border: none; }
.sz-light .sz-dlg-cancel, .sz-system .sz-dlg-cancel
  { background: alpha(currentColor, 0.10); border: 1px solid alpha(currentColor, 0.18); border-radius: 8px;
    padding: 6px 16px; }
.sz-light .sz-fav-row, .sz-system .sz-fav-row
  { background-color: transparent; border: 1px solid alpha(currentColor, 0.25); }
.sz-light .sz-fav-row.sz-fav-sel, .sz-system .sz-fav-row.sz-fav-sel
  { background-color: alpha(currentColor, 0.07); }
.sz-light .sz-fav-field, .sz-system .sz-fav-field
  { background-color: alpha(currentColor, 0.10); border: 1px solid alpha(currentColor, 0.18); }
.sz-light .sz-fav-field > text > placeholder, .sz-system .sz-fav-field > text > placeholder
  { color: alpha(currentColor, 0.55); }
.sz-light .sz-fav-arrow, .sz-system .sz-fav-arrow { color: alpha(currentColor, 0.6); }
.sz-light .sz-fav-sort, .sz-system .sz-fav-sort { color: currentColor; }
.sz-light .sz-fav-del, .sz-system .sz-fav-del { color: #E01B24; }
.sz-light .sz-fav-del:hover, .sz-system .sz-fav-del:hover { background: alpha(#E01B24, 0.14); }
.sz-light .sz-fav-add, .sz-system .sz-fav-add
  { background: transparent; border: 1px dashed alpha(currentColor, 0.35); box-shadow: none; color: currentColor; }
.sz-light .sz-fav-add:hover, .sz-system .sz-fav-add:hover { background: alpha(currentColor, 0.05); }
.sz-light .sz-conv-dd > button, .sz-system .sz-conv-dd > button
  { background-color: alpha(currentColor, 0.10); border: 1px solid alpha(currentColor, 0.18);
    border-radius: 10px; min-height: 34px; padding: 0 10px; color: currentColor; }
.sz-light .sz-conv-dd > button:hover, .sz-system .sz-conv-dd > button:hover
  { background-color: alpha(currentColor, 0.16); }
.sz-light .sz-menu-row.sz-menu-dragging, .sz-system .sz-menu-row.sz-menu-dragging
  { background-color: alpha(currentColor, 0.12); }
.sz-light .sz-menu-row.sz-menu-drop, .sz-system .sz-menu-row.sz-menu-drop
  { box-shadow: inset 0 0 0 2px alpha(currentColor, 0.55); }
.sz-light .sz-menu-row.sz-menu-selected, .sz-system .sz-menu-row.sz-menu-selected
  { background-color: alpha(@theme_selected_bg_color, 0.14);
    box-shadow: inset 0 0 0 1px alpha(@theme_selected_bg_color, 0.45); }
.sz-light .sz-menu-group, .sz-system .sz-menu-group
  { color: @theme_selected_bg_color; background: alpha(@theme_selected_bg_color, 0.10); }
.sz-light .sz-menu-group:hover, .sz-system .sz-menu-group:hover
  { background: alpha(@theme_selected_bg_color, 0.18); }
.sz-light .sz-menu-handle, .sz-light .sz-menu-eye, .sz-light .sz-menu-more,
.sz-system .sz-menu-handle, .sz-system .sz-menu-eye, .sz-system .sz-menu-more
  { color: currentColor; }
.sz-light .sz-menu-handle:hover, .sz-light .sz-menu-eye:hover, .sz-light .sz-menu-more:hover,
.sz-system .sz-menu-handle:hover, .sz-system .sz-menu-eye:hover, .sz-system .sz-menu-more:hover
  { background: alpha(currentColor, 0.10); }
.sz-light .sz-menu-more.sz-menu-filtered, .sz-system .sz-menu-more.sz-menu-filtered
  { color: @theme_selected_bg_color; }
.sz-light .sz-menu-hidden .sz-menu-label, .sz-light .sz-menu-hidden .sz-menu-eye,
.sz-system .sz-menu-hidden .sz-menu-label, .sz-system .sz-menu-hidden .sz-menu-eye
  { opacity: 0.45; }
.sz-dark .sz-fav-row { background-color: transparent; border: 1px solid alpha(currentColor, 0.62); }
.sz-dark .sz-fav-row.sz-fav-sel { background-color: #49475F; }
.sz-dark .sz-fav-field { background-color: #302D45; border: 1px solid #3C3958; }
.sz-dark .sz-fav-field > text > placeholder { color: alpha(currentColor, 0.55); }
.sz-dark .sz-fav-arrow { color: alpha(currentColor, 0.55); }
.sz-dark .sz-fav-sort { color: currentColor; }
.sz-dark .sz-fav-del { color: #F20D14; }
.sz-dark .sz-fav-del:hover { background: alpha(#F20D14, 0.16); }
.sz-dark .sz-fav-add { background: transparent; border: 1px dashed alpha(currentColor, 0.45);
  box-shadow: none; color: currentColor; }
.sz-dark .sz-fav-add:hover { background: alpha(currentColor, 0.05); }
.sz-dark .sz-conv-dd > button { background-color: #302D45; border: 1px solid #3C3958;
  border-radius: 10px; min-height: 34px; padding: 0 10px; color: #EEEBFA; }
.sz-dark .sz-conv-dd > button:hover { background-color: #3C3958; }
.sz-dark .sz-menu-sep { background-color: alpha(#EEEBFA, 0.22); }
.sz-dark .sz-menu-row.sz-menu-dragging { background-color: #49475F; }
.sz-dark .sz-menu-row.sz-menu-drop { box-shadow: inset 0 0 0 2px #FFF59B; }
.sz-dark .sz-menu-row.sz-menu-selected { background-color: alpha(#FFF59B, 0.14);
  box-shadow: inset 0 0 0 1px alpha(#FFF59B, 0.40); }
.sz-dark .sz-menu-group { color: #FFF59B; background: alpha(#FFF59B, 0.10); }
.sz-dark .sz-menu-group:hover { background: alpha(#FFF59B, 0.18); }
.sz-dark .sz-menu-handle, .sz-dark .sz-menu-eye, .sz-dark .sz-menu-more
  { color: #EEEBFA; }
.sz-dark .sz-menu-handle:hover, .sz-dark .sz-menu-eye:hover, .sz-dark .sz-menu-more:hover
  { background: alpha(#EEEBFA, 0.08); }
.sz-dark .sz-menu-more.sz-menu-filtered { color: #FFF59B; }
.sz-dark .sz-menu-hidden .sz-menu-label, .sz-dark .sz-menu-hidden .sz-menu-eye
  { color: #8B879C; opacity: 0.55; }
"""

DENSITY_YPAD = {'compact': 0, 'normal': 2, 'comfortable': 5}
_theme = {'prov': None, 'orig_dark': None}
_probe = [None]


def _theme_color(name):
    """Цвет из текущей темы GTK (например, theme_base_color или accent_color)."""
    if _probe[0] is None:
        _probe[0] = Gtk.Label()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            ok, color = _probe[0].get_style_context().lookup_color(name)
        if ok:
            return '#%02X%02X%02X' % (round(color.red * 255), round(color.green * 255),
                                      round(color.blue * 255))
    except Exception:
        pass
    return None


def style_window(w, scheme):
    for c in ('sz-midnight', 'sz-light', 'sz-system'):
        w.remove_css_class(c)
    w.add_css_class('sz-' + scheme)
    try:
        dark = _theme_is_dark(Gtk.Settings.get_default())
    except Exception:
        dark = scheme == 'midnight'
    if dark:
        w.add_css_class('sz-dark')
    else:
        w.remove_css_class('sz-dark')


def _theme_is_dark(settings):
    """Тёмная ли тема: учитываем флаг, имя темы и принудительный режим для root."""
    forced = os.environ.get('SZ_FORCE_DARK')
    if forced in ('0', '1'):
        return forced == '1'
    if settings.get_property('gtk-application-prefer-dark-theme'):
        return True
    name = (settings.get_property('gtk-theme-name') or '').lower()
    return name.endswith('-dark') or ':dark' in name


def apply_theme(conf):
    """Применить цветовую схему (midnight — палитра макетов / system / light)."""
    scheme = conf['scheme'] if conf['scheme'] in ('midnight', 'system', 'light') else 'midnight'
    settings = Gtk.Settings.get_default()
    if _theme['orig_dark'] is None:
        _theme['orig_dark'] = _theme_is_dark(settings)
    want_dark = (_theme['orig_dark'] if scheme == 'system' else scheme == 'midnight')
    # Смена этого свойства перестраивает стили всего приложения даже при том же
    # значении, поэтому выставляем его только когда оно действительно меняется.
    if bool(settings.get_property('gtk-application-prefer-dark-theme')) != bool(want_dark):
        settings.set_property('gtk-application-prefer-dark-theme', bool(want_dark))
    # Фон плашки — фактический фон списка, обводка и значок — акцент текущей темы GTK.
    badge_bg = PAL['bg'] if scheme == 'midnight' else (
        _theme_color('theme_base_color') or _theme_color('theme_bg_color') or '#FAFAFA')
    badge_accent = (_theme_color('accent_color') or _theme_color('theme_selected_bg_color')
                    or PAL['accent'])
    set_badge_theme(badge_bg, badge_accent)
    css = BASE_CSS + (string.Template(MIDNIGHT_CSS).substitute(PAL) if scheme == 'midnight' else LIGHT_EXTRA_CSS)
    display = Gdk.Display.get_default()
    if _theme['prov'] is not None:
        Gtk.StyleContext.remove_provider_for_display(display, _theme['prov'])
    prov = Gtk.CssProvider()
    try:
        prov.load_from_string(css)
    except AttributeError:
        prov.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_display(display, prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    _theme['prov'] = prov
    _theme['scheme'] = scheme
    clear_icon_cache()
    for w in Gtk.Window.list_toplevels():
        style_window(w, scheme)
