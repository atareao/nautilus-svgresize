#!/usr/bin/python
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
from threading import Thread
import cairo
import shutil
import os
import subprocess
import threading
from PIL import Image

APPNAME = 'nautilus-iconify'
ICON = 'nautilus-iconify'
VERSION = '$VERSION$'

SIZES = ['ldpi', 'mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']
_ = str


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class DoItInBackground(IdleObject, Thread):
    __gsignals__ = {
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (float,)),
    }

    def __init__(self, elements, options):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.elements = elements
        self.options = options
        self.stopit = False
        self.ok = True
        self.daemon = True
        self.process = None

    def stop(self, *args):
        self.stopit = True

    def create_icon(self, file_in):
        basename = os.path.basename(file_in)
        filename, fileextension = os.path.splitext(basename)
        parent_directory = os.path.join(os.path.dirname(file_in), 'res')
        create_directory(parent_directory)
        if self.options['ldpi']:
            width = self.options['width'] * 0.75
            height = self.options['height'] * 0.75
            if self.options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-ldpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-ldpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if self.options['optimize']:
                optimize_png(png_file)
        if options['mdpi']:
            width = self.options['width'] * 1.0
            height = self.options['height'] * 1.0
            if self.options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-mdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-mdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if self.options['optimize']:
                optimize_png(png_file)
        if self.options['hdpi']:
            width = self.options['width'] * 1.5
            height = self.options['height'] * 1.5
            if self.options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-hdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-hdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if self.options['optimize']:
                optimize_png(png_file)
        if self.options['xhdpi']:
            width = self.options['width'] * 2.0
            height = self.options['height'] * 2.0
            if self.options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-xhdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-xhdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if self.options['optimize']:
                optimize_png(png_file)
        if self.options['xxhdpi']:
            width = self.options['width'] * 3.0
            height = self.options['height'] * 3.0
            if self.options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-xxhdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-xxhdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if self.options['optimize']:
                optimize_png(png_file)
        if self.options['xxxhdpi']:
            width = self.options['width'] * 4.0
            height = self.options['height'] * 4.0
            if self.options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-xxxhdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-xxxhdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if self.options['optimize']:
                optimize_png(png_file)

    def run(self):
        total = 0
        for element in self.elements:
            total += get_duration(element)
        self.emit('started', total)
        try:
            total = 0
            for element in self.elements:
                if self.stopit is True:
                    self.ok = False
                    break
                self.emit('start_one', element)
                self.create_icon(element)
                self.emit('end_one', get_duration(element))
        except Exception as e:
            self.ok = False
        try:
            if self.process is not None:
                self.process.terminate()
                self.process = None
        except Exception as e:
            print(e)
        self.emit('ended', self.ok)


class Progreso(Gtk.Dialog, IdleObject):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent):
        Gtk.Dialog.__init__(self, title, parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT)
        IdleObject.__init__(self)
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
        self.max_value = float(max_value)
        self.value = 0.0

    def set_max_value(self, anobject, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def increase(self, anobject, value):
        self.value += float(value)
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value >= self.max_value:
            self.hide()

    def set_element(self, anobject, element):
        self.label.set_text(_('Converting: %s') % element)


def create_png(svg_file, png_file, width, height):
    svgsurface = Rsvg.Handle.new_from_file(svg_file)
    dimensions = svgsurface.get_dimensions()
    zw = width / dimensions.width
    zh = height / dimensions.height
    pngsurface = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                    int(width),
                                    int(height))
    context = cairo.Context(pngsurface)
    context.save()
    context.scale(zw, zh)
    svgsurface.render_cairo(context)
    context.restore()
    pngsurface.flush()
    pngsurface.write_to_png(png_file)
    pngsurface.finish()
    image = Image.open(png_file)
    image.save(png_file, optimize=True)


def optimize_png(file_in):
    rutine = 'pngnq -f -e "-reduced.png" -n 256 "%s"' % (file_in)
    args = shlex.split(rutine)
    self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = self.process.communicate()


def create_directory(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)


def remove_directory(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)


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
        Gtk.Dialog.__init__(self, 'Iconify', window, Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                             Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        self.options = {}
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(400, 300)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)
        frame00 = Gtk.Frame.new('Dimensions for mdpi')
        vbox.pack_start(frame00, True, True, 0)
        table00 = Gtk.Table(rows=2, columns=2)
        frame00.add(table00)
        label = Gtk.Label.new('width'+':')
        label.set_alignment(0, 0.5)
        table00.attach(label, 0, 1, 0, 1,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        self.options['width'] = Gtk.Entry()
        self.options['width'].set_text('48')
        table00.attach(self.options['width'], 1, 2, 0, 1,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        label = Gtk.Label.new('height'+':')
        label.set_alignment(0, 0.5)
        table00.attach(label, 0, 1, 1, 2,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        self.options['height'] = Gtk.Entry()
        self.options['height'].set_text('48')
        table00.attach(self.options['height'], 1, 2, 1, 2,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        frame01 = Gtk.Frame.new('Density')
        vbox.pack_start(frame01, True, True, 0)
        table01 = Gtk.Table(rows=6, columns=2)
        frame01.add(table01)
        for index, asize in enumerate(SIZES):
            label = Gtk.Label.new(asize+':')
            label.set_alignment(0, 0.5)
            table01.attach(label, 0, 1, 0 + index, 1 + index,
                           xoptions=Gtk.AttachOptions.FILL,
                           yoptions=Gtk.AttachOptions.FILL,
                           xpadding=5,
                           ypadding=5)
            self.options[asize] = Gtk.Switch()
            self.options[asize].set_active(True)
            table01.attach(self.options[asize], 1, 2, 0 + index, 1 + index,
                           xoptions=Gtk.AttachOptions.FILL,
                           yoptions=Gtk.AttachOptions.FILL,
                           xpadding=5,
                           ypadding=5)
        frame02 = Gtk.Frame.new('Options')
        vbox.pack_start(frame02, True, True, 0)
        table02 = Gtk.Table(rows=3, columns=2)
        frame02.add(table02)
        label = Gtk.Label.new('Is launcher'+'?:')
        label.set_alignment(0, 0.5)
        table02.attach(label, 0, 1, 0, 1,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        self.options['is-launcher'] = Gtk.Switch()
        self.options['is-launcher'].set_active(False)
        table02.attach(self.options['is-launcher'], 1, 2, 0, 1,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        label = Gtk.Label.new('Optimize' + '?:')
        label.set_alignment(0, 0.5)
        table02.attach(label, 0, 1, 1, 2,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        self.options['optimize'] = Gtk.Switch()
        self.options['optimize'].set_active(False)
        table02.attach(self.options['optimize'], 1, 2, 1, 2,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        self.options['optimize'].connect('activate', self.on_optimize_changed)
        self.options['optimize'].connect('button-press-event',
                                         self.on_optimize_changed)
        self.show_all()

    def on_optimize_changed(self, widget, data=None):
        active = not self.options['optimize'].get_active()
        self.options['optimization-level'].set_sensitive(active)
        if not active:
            self.options['optimization-level'].set_value(0)


class IconifyMenuProvider(GObject.GObject, FileManager.MenuProvider):

    def __init__(self):
        pass

    def all_files_are_svg(self, items):
        for item in items:
            fileName, fileExtension = os.path.splitext(unquote_plus(
                item.get_uri()[7:]))
            if fileExtension.lower() != '.svg':
                return False
        return True

    def iconify(self, menu, selected, window):
        rd = ResizeDialog(window)
        if rd.run() == Gtk.ResponseType.ACCEPT:
            rd.hide()
            options = {}
            options['width'] = int(rd.options['width'].get_text())
            options['height'] = int(rd.options['height'].get_text())
            options['ldpi'] = rd.options['ldpi'].get_active()
            options['ldpi'] = rd.options['ldpi'].get_active()
            options['mdpi'] = rd.options['mdpi'].get_active()
            options['hdpi'] = rd.options['hdpi'].get_active()
            options['xhdpi'] = rd.options['xhdpi'].get_active()
            options['xxhdpi'] = rd.options['xxhdpi'].get_active()
            options['xxxhdpi'] = rd.options['xxxhdpi'].get_active()
            options['is-launcher'] = rd.options['is-launcher'].get_active()
            options['optimize'] = rd.options['optimize'].get_active()
            files = get_files(selected)
            manager = Manager(files, options, self.backcall)
            manager.process()

    def backcall(self, element, options):
        pass

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the File Manager\
        right-click menu, connects its 'activate' signal to the 'run'\
        method passing the selected Directory/File
        """
        if self.all_files_are_svg(sel_items):
            top_menuitem = FileManager.MenuItem(
                name='IconifyMenuProvider::Gtk-iconify-top',
                label=_('Iconify for Android...'),
                tip=_('Create icons for Android'))
            submenu = FileManager.Menu()
            top_menuitem.set_submenu(submenu)

            sub_menuitem_00 = FileManager.MenuItem(
                name='IconifyMenuProvider::Gtk-iconify-sub-01',
                label=_('Iconify'),
                tip=_('Create icons for Android'))
            sub_menuitem_00.connect('activate',
                                    self.iconify,
                                    sel_items,
                                    window)
            submenu.append_item(sub_menuitem_00)
            sub_menuitem_01 = FileManager.MenuItem(
                name='IconifyMenuProvider::Gtk-iconify-sub-02',
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
        ad.set_copyright('Copyrignt (c) 2016\nLorenzo Carbonell')
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
    rd = ResizeDialog(None)
    rd.run()
