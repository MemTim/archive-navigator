# -*- coding: utf-8 -*-
from .imports import *  # noqa: F401,F403
from .dialogs import hbox, lbl, vbox
from .ops import groups_from_model, widget_xy

class MenuLayer:
    """Выпадающие меню, нарисованные ВНУТРИ окна приложения (не системные popup-окна):
    поэтому ничего не обрезается и всё выглядит одинаково в любой версии GTK."""

    def __init__(self, win, overlay):
        self.win, self.overlay = win, overlay
        self.levels, self.catcher, self.owner, self.on_close = [], None, None, None

    @property
    def is_open(self):
        return bool(self.levels)

    def _remove_levels(self, keep):
        while len(self.levels) > keep:
            self.overlay.remove_overlay(self.levels.pop()['outer'])

    def close(self):
        if not self.levels and self.catcher is None:
            return
        self._remove_levels(0)
        if self.catcher is not None:
            self.overlay.remove_overlay(self.catcher)
            self.catcher = None
        owner, self.owner = self.owner, None
        if self.on_close:
            self.on_close(owner)

    def open(self, groups, anchor=None, point=None, owner=None, top=0, min_width=0, focus=False):
        self.close()
        self.owner = owner
        c = Gtk.Box()
        c.set_margin_top(int(top))
        g = Gtk.GestureClick()
        g.set_button(0)
        g.connect('pressed', lambda *a: self.close())
        c.add_controller(g)
        self.overlay.add_overlay(c)
        self.overlay.set_measure_overlay(c, False)
        self.catcher = c
        self._add_level(groups, 0, anchor=anchor, point=point, min_width=min_width)
        if focus:
            self.focus_first(0)

    # ---- служебное ----
    def _act(self, e):
        a = e.get('action')
        return self.win.lookup_action(a[4:]) if a and a.startswith('win.') else None

    def _mark(self, e):
        """None — без метки; '✓' / '' — флажок; '●' / '' — переключатель."""
        act = self._act(e)
        st = act.get_state() if act is not None else None
        if st is None:
            return None
        t, tgt = st.get_type_string(), e.get('target')
        if t == 'b' and tgt is None:
            return '✓' if st.get_boolean() else ''
        if t == 's' and tgt is not None and tgt.get_type_string() == 's':
            return '●' if st.get_string() == tgt.get_string() else ''
        return None

    @staticmethod
    def _sub_groups(sub):
        return sub if isinstance(sub, list) else groups_from_model(sub)

    def _row(self, e, level, has_mark):
        act = self._act(e)
        has_sub = e.get('submenu') is not None
        sub_ok = has_sub and bool(self._sub_groups(e['submenu']))
        enabled = sub_ok or (not has_sub and (bool(e.get('callback')) or (act is not None and act.get_enabled())))
        b = Gtk.Button()
        b.add_css_class('flat')
        b.add_css_class('sz-menu-item')
        b.set_focus_on_click(False)
        b.set_sensitive(enabled)
        row = hbox(14)
        if has_mark:
            m = lbl(self._mark(e) or '')
            m.set_size_request(14, -1)
            row.append(m)
        l = lbl(e['label'])
        l.set_hexpand(True)
        row.append(l)
        if has_sub:
            row.append(lbl('›'))
        elif e.get('action') and e.get('target') is None:
            acc = self.win.accel_text(e['action'][4:])
            if acc:
                a = lbl(acc)
                a.add_css_class('sz-muted')
                row.append(a)
        b.set_child(row)
        b.connect('clicked', lambda x: self._activate(e, b, level))
        mc = Gtk.EventControllerMotion()
        mc.connect('enter', lambda c, x, y: self._hover(e, b, level))
        b.add_controller(mc)
        return b

    def _add_level(self, groups, level, anchor=None, point=None, parent=None, row=None, min_width=0):
        self._remove_levels(level)
        has_mark = any(self._mark(e) is not None for grp in groups for e in grp)
        box = vbox(0)
        rows = []
        for gi, grp in enumerate(groups):
            if gi:
                sep = Gtk.Box()
                sep.add_css_class('sz-menu-sep')
                box.append(sep)
            for e in grp:
                b = self._row(e, level, has_mark)
                rows.append((b, e))
                box.append(b)
        outer = Gtk.Box(orientation=V)
        outer.add_css_class('sz-menu')
        outer.append(box)
        outer.set_halign(Gtk.Align.START)
        outer.set_valign(Gtk.Align.START)
        if min_width:
            outer.set_size_request(int(min_width), -1)
        self.overlay.add_overlay(outer)
        self.overlay.set_measure_overlay(outer, False)
        OW, OH = self.overlay.get_width(), self.overlay.get_height()
        nat = outer.get_preferred_size()[1]
        w, h = nat.width, nat.height
        if parent is not None and row is not None:
            rxy = widget_xy(row, self.overlay) or (parent['x'], parent['y'])
            x, y = parent['x'] + parent['w'] - 4, rxy[1] - 6
            if x + w > OW - 2:
                x = parent['x'] - w + 4
        elif anchor is not None:
            axy = widget_xy(anchor, self.overlay, 0, anchor.get_height()) or (0, 0)
            x, y = axy[0], axy[1] + 2
        else:
            x, y = point
            if y + h > OH - 4 and y - h >= 4:
                y -= h
        x = max(2, min(x, OW - w - 2))
        if h > OH - 8:                      # не помещается — прокрутка внутри меню
            sw = Gtk.ScrolledWindow()
            sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            sw.set_propagate_natural_height(True)
            sw.set_max_content_height(max(80, OH - 24))
            outer.remove(box)
            sw.set_child(box)
            outer.append(sw)
            y, h = 4, OH - 8
        else:
            y = max(2, min(y, OH - h - 2))
        outer.set_margin_start(int(x))
        outer.set_margin_top(int(y))
        self.levels.append(dict(outer=outer, box=box, rows=rows, x=x, y=y, w=w, h=h, source=None))

    def _activate(self, e, b, level):
        if e.get('submenu') is not None:
            self._open_sub(e, b, level)
            return
        self.close()
        GLib.idle_add(self._run, e)

    def _run(self, e):
        if e.get('callback'):
            e['callback']()
        else:
            act = self._act(e)
            if act is not None:
                act.activate(e.get('target'))
        return False

    def _hover(self, e, b, level):
        if e.get('submenu') is not None:
            self._open_sub(e, b, level)
        else:
            self._remove_levels(level + 1)

    def _open_sub(self, e, b, level):
        if len(self.levels) > level + 1 and self.levels[level + 1]['source'] is e:
            return
        groups = self._sub_groups(e['submenu'])
        if not groups:
            return
        self._add_level(groups, level + 1, parent=self.levels[level], row=b)
        self.levels[level + 1]['source'] = e

    def focus_first(self, level):
        for b, e in self.levels[level]['rows']:
            if b.get_sensitive():
                b.grab_focus()
                return


class MenuBar(Gtk.Box):
    def __init__(self, win, model):
        super().__init__(orientation=H, spacing=0)
        self.add_css_class('sz-menubar')
        self.win, self.items = win, []
        for i in range(model.get_n_items()):
            lab = model.get_item_attribute_value(i, 'label', None).get_string().replace('__', '_')
            b = Gtk.Button()
            b.add_css_class('flat')
            b.add_css_class('sz-menubar-item')
            b.set_focus_on_click(False)
            b.set_child(Gtk.Label(label=lab))
            b.connect('clicked', lambda x, i=i: self.toggle(i))
            mc = Gtk.EventControllerMotion()
            mc.connect('enter', lambda c, x, y, i=i: self.hover(i))
            b.add_controller(mc)
            self.append(b)
            self.items.append((b, model.get_item_link(i, 'submenu')))

    def open_index(self, i, focus=False):
        b, sub = self.items[i]
        top = (widget_xy(self, self.win.overlay, 0, self.get_height()) or (0, self.get_height()))[1]
        self.win.menus.open(groups_from_model(sub), anchor=b, owner=('bar', i), top=top, focus=focus)
        self._mark(i)

    def toggle(self, i):
        if self.win.menus.owner == ('bar', i):
            self.win.menus.close()
        else:
            self.open_index(i)

    def hover(self, i):
        o = self.win.menus.owner
        if o and o[0] == 'bar' and o[1] != i:
            self.open_index(i)

    def _mark(self, active):
        for j, (b, sub) in enumerate(self.items):
            (b.add_css_class if j == active else b.remove_css_class)('sz-menubar-open')

    def clear_marks(self):
        self._mark(-1)
