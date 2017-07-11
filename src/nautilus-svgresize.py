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
from urllib import unquote_plus
import cairo
import shutil
import os
import threading
import traceback

APPNAME = 'nautilus-svgresize'
ICON = 'nautilus-svgresize'
VERSION = '$VERSION$'

SIZES = ['ldpi', 'mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']
_ = str


def _async_call(f, args, kwargs, on_done):
    def run(data):
        f, args, kwargs, on_done = data
        error = None
        result = None
        try:
            result = f(*args, **kwargs)
        except Exception as e:
            e.traceback = traceback.format_exc()
            error = 'Unhandled exception in asyn call:\n{}'.format(e.traceback)
        GLib.idle_add(lambda: on_done(result, error))

    data = f, args, kwargs, on_done
    thread = threading.Thread(target=run, args=(data,))
    thread.daemon = True
    thread.start()


def async_function(on_done=None):
    def wrapper(f):
        def run(*args, **kwargs):
            _async_call(f, args, kwargs, on_done)
        return run
    return wrapper


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
        self.show_all()
        self.value = 0.0

    def set_max_value(self, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self):
        self.value += 1.0
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if int(self.value) >= int(self.max_value):
            self.hide()

    def set_element(self, element):
        self.label.set_text(_('Resizing: %s') % element)


def resize_svg(svg_file, svg_file_resized, width, height):
    if os.path.exists(svg_file):
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


def resize_images(files, options, progreso):
    def on_resize_images_done(result, error):
        pass

    @async_function(on_done=on_resize_images_done)
    def do_resize_images_in_thread(files, options, progreso):
        print('resizing files')
        width = options['width']
        height = options['height']
        dirname = os.path.join(os.path.dirname(files[0]),
                               '{0}x{1}'.format(width, height))
        create_directory(dirname)
        progreso.set_max_value(len(files))
        for svg_file in files:
            svg_file_resized = os.path.join(dirname,
                                            os.path.basename(svg_file))
            progreso.set_element(svg_file)
            resize_svg(svg_file, svg_file_resized, width, height)
            if progreso.get_stop() is True:
                break
            progreso.increase()
        progreso.destroy()

    do_resize_images_in_thread(files, options, progreso)


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
            files = get_files(selected)
            progreso = Progreso('Resize svg file', window)
            resize_images(files, options, progreso)

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
    import time
    files = ['/home/lorenzo/Escritorio/raspberry_resized0.svg',
             '/home/lorenzo/Escritorio/raspberry_resized1.svg',
             '/home/lorenzo/Escritorio/raspberry_resized2.svg',
             '/home/lorenzo/Escritorio/raspberry_resized3.svg',
             '/home/lorenzo/Escritorio/raspberry_resized4.svg',
             '/home/lorenzo/Escritorio/raspberry_resized5.svg',
             '/home/lorenzo/Escritorio/raspberry_resized6.svg']
    options = {'width': 256, 'height': 256}
    progreso = Progreso('Resize svg file', None)
    resize_images(files, options, progreso)
    time.sleep(20)
