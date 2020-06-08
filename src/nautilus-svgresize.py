#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-iconify
#
# Copyright (c) 2016 Lorenzo Carbonell Cerezo <a.k.a. atareao>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('GObject', '2.0')
    gi.require_version('Nautilus', '3.0')
    gi.require_version('Rsvg', '2.0')
except Exception as e:
    print(e)
    exit(-1)
from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import Nautilus as FileManager
from gi.repository import Rsvg
import sys
import os
import locale
import gettext
from PIL import Image
import cairo
try:
    sys.path.insert(1, '/usr/share/nanecalib')
    from nanecalib import DoItInBackground
except Exception as nanecalib_error:
    print(nanecalib_error)
    sys.exit(-1)

APP = '$APP$'
ICON = '$APP$'
VERSION = '$VERSION$'
LANGDIR = os.path.join('usr', 'share', 'locale-langpack')

current_locale, encoding = locale.getdefaultlocale()
language = gettext.translation(APP, LANGDIR, [current_locale])
language.install()
try:
    _ = language.gettext
except Exception:
    _ = str


class ConvertDIIB(DoItInBackground):
    def __init__(self, title, parent, files, width, height, png):
        self._width = width
        self._height = height
        self._png = png
        DoItInBackground.__init__(self, title, parent, files, ICON)

    def process_item(self, file_in):
        width = self._width
        height = self._height
        png = self._png
        head, tail = os.path.split(file_in)
        root, ext = os.path.splitext(tail)
        if png is True:
            png_file = os.path.join(head, root + '.png')
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         int(width),
                                         int(height))
            ctx = cairo.Context(surface)
            svg = Rsvg.Handle.new_from_file(file_in)
            dimensions = svg.get_dimensions()
            zw = float(width) / float(dimensions.width)
            zh = float(height) / float(dimensions.height)
            z = zh if zw > zh else zw
            if z <= 0:
                raise(Exception)
            if width != height:
                if width < height:
                    ctx.translate(0, (float(height)-float(width))/2.0)
                else:
                    ctx.translate((float(width)-float(height))/2.0, 0)
            ctx.scale(z, z)
            svg.render_cairo(ctx)
            surface.flush()
            surface.write_to_png(png_file)
            surface.finish()
            image = Image.open(png_file)
            image.save(png_file, optimize=True)
        else:
            width = round(0.8 * width, 0)
            height = round(0.8 * height, 0)
            svg_file_resized = os.path.join(head, root + '_resized.svg')
            with open(svg_file_resized, 'w') as fo:
                surface = cairo.SVGSurface(fo, width, height)
                ctx = cairo.Context(surface)
                svg = Rsvg.Handle.new_from_file(file_in)
                dimensions = svg.get_dimensions()
                zw = float(width) / float(dimensions.width)
                zh = float(height) / float(dimensions.height)
                z = zh if zw > zh else zw
                if z <= 0:
                    raise(Exception)
                if width != height:
                    if width < height:
                        ctx.translate(0, (float(height)-float(width))/2.0)
                    else:
                        ctx.translate((float(width)-float(height))/2.0, 0)
                ctx.scale(z, z)
                svg.render_cairo(ctx)
                surface.flush()
                surface.finish()


class ResizeDialog(Gtk.Dialog):
    def __init__(self, window):
        Gtk.Dialog.__init__(self, 'Resize SVG', window, Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                             Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        self.options = {}
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        # self.set_size_request(400, 300)

        frame = Gtk.Frame.new(_('New dimensions') + ':')
        frame.set_margin_left(10)
        frame.set_margin_right(10)
        frame.set_margin_top(10)
        frame.set_margin_bottom(10)

        self.get_content_area().add(frame)

        grid = Gtk.Grid.new()
        grid.set_margin_left(10)
        grid.set_margin_right(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_row_spacing(10)
        grid.set_column_spacing(10)
        frame.add(grid)

        label00 = Gtk.Label.new(_('Width') + ':')
        label00.set_alignment(0, 0.5)
        grid.attach(label00, 0, 0, 1, 1)

        self.options['width'] = Gtk.Entry()
        grid.attach(self.options['width'], 1, 0, 1, 1)

        label01 = Gtk.Label.new(_('Height') + ':')
        label01.set_alignment(0, 0.5)
        grid.attach(label01, 0, 1, 1, 1)

        self.options['height'] = Gtk.Entry()
        grid.attach(self.options['height'], 1, 1, 1, 1)

        label02 = Gtk.Label.new(_('Save as PNG?') + ':')
        label02.set_alignment(0, 0.5)
        grid.attach(label02, 0, 2, 1, 1)

        self.options['png'] = Gtk.CheckButton()
        grid.attach(self.options['png'], 1, 2, 1, 1)

        self.show_all()


class SVGResizeMenuProvider(GObject.GObject, FileManager.MenuProvider):

    def __init__(self):
        GObject.GObject.__init__(self)

    def process(self, menu, files, window):
        rd = ResizeDialog(window)
        if rd.run() == Gtk.ResponseType.ACCEPT:
            rd.hide()
            width = int(rd.options['width'].get_text())
            height = int(rd.options['height'].get_text())
            png = rd.options['png'].get_active()
            diib = ConvertDIIB(_('Resize svg images'), window, files, width,
                               height, png)
            diib.run()
        rd.destroy()

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the File Manager\
        right-click menu, connects its 'activate' signal to the 'run'\
        method passing the selected Directory/File
        """
        files = []
        for file_in in sel_items:
            if not file_in.is_directory():
                afile = file_in.get_location().get_path()
                filename, fileextension = os.path.splitext(afile)
                if fileextension.lower() == '.svg':
                    files.append(afile)
        if files:
            top_menuitem = FileManager.MenuItem(
                name='SVGResizeMenuProvider::Gtk-svgresize-top',
                label=_('Resize svg files...'),
                tip=_('Resize svg files'))
            submenu = FileManager.Menu()
            top_menuitem.set_submenu(submenu)

            sub_menuitem_00 = FileManager.MenuItem(
                name='SVGResizeMenuProvider::Gtk-svgresize-sub-01',
                label=_('Resize svg files'),
                tip=_('Resize svg files'))
            sub_menuitem_00.connect('activate',
                                    self.resize,
                                    files,
                                    window)
            submenu.append_item(sub_menuitem_00)
            sub_menuitem_01 = FileManager.MenuItem(
                name='SVGResizeMenuProvider::Gtk-svgresize-sub-02',
                label=_('About'),
                tip=_('About'))
            sub_menuitem_01.connect('activate', self.about, window)
            submenu.append_item(sub_menuitem_01)

            return top_menuitem,
        return

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APP)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2017\nLorenzo Carbonell')
        ad.set_comments(APP)
        ad.set_license('''
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')
        ad.set_website('https://www.atareao.es')
        ad.set_website_label('atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <a.k.a. atareao>'])
        ad.set_documenters([
            'Lorenzo Carbonell <a.k.a. atareao>'])
        ad.set_icon_name(ICON)
        ad.set_logo_icon_name(APP)
        ad.run()
        ad.destroy()
