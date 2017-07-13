#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-iconify
#
# Copyright (C) 2016 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('GLib', '2.0')
    gi.require_version('Nautilus', '3.0')
    gi.require_version('Rsvg', '2.0')
except Exception as e:
    print(e)
    exit(-1)
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Rsvg
from gi.repository import Nautilus as FileManager
from PIL import Image
from urllib import unquote_plus
import cairo
import shutil
import threading
import os


APPNAME = '$APP$'
ICON = '$APP$'
VERSION = '$VERSION$'

_ = str


class Progreso(Gtk.Dialog):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent):
        Gtk.Dialog.__init__(self, title, parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 30)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        self.set_modal(True)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)
        #
        frame1 = Gtk.Frame()
        vbox.pack_start(frame1, True, True, 0)
        table = Gtk.Table(2, 2, False)
        frame1.add(table)
        #
        self.label = Gtk.Label()
        table.attach(self.label, 0, 2, 0, 1,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        #
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        table.attach(self.progressbar, 0, 1, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        table.attach(button_stop, 1, 2, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK)
        self.stop = False
        self.value = 0.0
        self.show_all()

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def set_max_value(self, widget, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self, widget, value):
        self.value += float(value)
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if int(self.value) >= int(self.max_value):
            self.destroy()

    def set_element(self, widget, element):
        self.label.set_text(_('Resizing: %s') % element)


def resize_svg(svg_file, svg_file_resized, width, height, png):
    if os.path.exists(svg_file):
        if png is True:
            png_file = os.path.splitext(svg_file_resized)[0] + '.png'
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                         int(width),
                                         int(height))
            ctx = cairo.Context(surface)
            svg = Rsvg.Handle.new_from_file(svg_file)
            dimensions = svg.get_dimensions()
            zw = float(width) / float(dimensions.width)
            zh = float(height) / float(dimensions.height)
            if zw > zh:
                z = zh
            else:
                z = zw
            print(zw, zh, z)
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
            fo = open(svg_file_resized, 'w')
            print('---', width, height, '---')
            surface = cairo.SVGSurface(fo, width, height)
            ctx = cairo.Context(surface)
            svg = Rsvg.Handle.new_from_file(svg_file)
            dimensions = svg.get_dimensions()
            zw = float(width) / float(dimensions.width)
            zh = float(height) / float(dimensions.height)
            if zw > zh:
                z = zh
            else:
                z = zw
            print(zw, zh, z)
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
    else:
        raise(Exception)


class DoItInBackground(GObject.GObject, threading.Thread):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, files, options):
        GObject.GObject.__init__(self)
        threading.Thread.__init__(self)
        self.files = files
        self.options = options
        self.stopit = False
        self.ok = True
        self.daemon = True

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)

    def stop(self, *args):
        self.stopit = True

    def run(self):
        self.emit('started', len(self.files))
        try:
            width = self.options['width']
            height = self.options['height']
            png = self.options['png']
            dirname = os.path.join(os.path.dirname(self.files[0]),
                                   '{0}x{1}'.format(width, height))
            create_directory(dirname)
            for svg_file in self.files:
                print(svg_file)
                if self.stopit is True:
                    self.ok = False
                    break
                filename = os.path.basename(svg_file)
                self.emit('start_one', filename)
                svg_file_resized = os.path.join(dirname, filename)
                resize_svg(svg_file, svg_file_resized, width, height, png)
                self.emit('end_one', 1.0)
        except Exception as e:
            self.ok = False
            print(e)
        self.emit('ended', self.ok)


def create_directory(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def remove_directory(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)


def get_duration(file_in):
    return os.path.getsize(file_in)


def get_files(files_in):
    files = []
    for file_in in files_in:
        print(file_in)
        file_in = unquote_plus(file_in.get_uri()[7:])
        if os.path.isfile(file_in):
            files.append(file_in)
    return files


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
        pass

    def all_files_are_svg(self, items):
        for item in items:
            fileName, fileExtension = os.path.splitext(unquote_plus(
                item.get_uri()[7:]))
            if fileExtension.lower() != '.svg':
                return False
        return True

    def resize(self, menu, selected, window):
        rd = ResizeDialog(window)
        if rd.run() == Gtk.ResponseType.ACCEPT:
            rd.hide()
            options = {}
            options['width'] = int(rd.options['width'].get_text())
            options['height'] = int(rd.options['height'].get_text())
            options['png'] = rd.options['png'].get_active()
            files = get_files(selected)
            diib = DoItInBackground(files, options)
            progreso = Progreso(_('Resize svg images'), window)
            diib.connect('started', progreso.set_max_value)
            diib.connect('start_one', progreso.set_element)
            diib.connect('end_one', progreso.increase)
            diib.connect('ended', progreso.close)
            progreso.connect('i-want-stop', diib.stop)
            diib.start()
            progreso.run()
        rd.destroy()

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the File Manager\
        right-click menu, connects its 'activate' signal to the 'run'\
        method passing the selected Directory/File
        """
        if self.all_files_are_svg(sel_items):
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
                                    sel_items,
                                    window)
            submenu.append_item(sub_menuitem_00)
            sub_menuitem_01 = FileManager.MenuItem(
                name='SVGResizeMenuProvider::Gtk-svgresize-sub-02',
                label=_('About'),
                tip=_('About'))
            sub_menuitem_01.connect('activate', self.about, window)
            submenu.append_item(sub_menuitem_01)
            #
            return top_menuitem,
        return

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APPNAME)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2017\nLorenzo Carbonell')
        ad.set_comments(APPNAME)
        ad.set_license('''
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_documenters([
            'Lorenzo Carbonell <lorenzo.carbonell.cerezo@gmail.com>'])
        ad.set_icon_name(ICON)
        ad.set_logo_icon_name(APPNAME)
        ad.run()
        ad.destroy()


if __name__ == '__main__':

    files = ['/home/lorenzo/Escritorio/raspberry_resized0.svg',
             '/home/lorenzo/Escritorio/raspberry_resized1.svg',
             '/home/lorenzo/Escritorio/raspberry_resized2.svg',
             '/home/lorenzo/Escritorio/raspberry_resized3.svg',
             '/home/lorenzo/Escritorio/raspberry_resized4.svg',
             '/home/lorenzo/Escritorio/raspberry_resized5.svg',
             '/home/lorenzo/Escritorio/raspberry_resized6.svg']
    files2 = ['/home/lorenzo/Escritorio/raspberry_resized10.svg',
              '/home/lorenzo/Escritorio/raspberry_resized11.svg',
              '/home/lorenzo/Escritorio/raspberry_resized12.svg',
              '/home/lorenzo/Escritorio/raspberry_resized13.svg',
              '/home/lorenzo/Escritorio/raspberry_resized14.svg',
              '/home/lorenzo/Escritorio/raspberry_resized15.svg',
              '/home/lorenzo/Escritorio/raspberry_resized16.svg']
    for index, afile in enumerate(files):
        resize_svg(afile, files2[index], 500, 500, True)
    exit(0)
