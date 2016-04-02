#!/usr/bin/env python3
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

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Rsvg
from gi.repository import Nautilus as FileManager
from urllib import unquote_plus
from Queue import Queue
import cairo
import shutil
import os
import subprocess
import threading
from PIL import Image

SIZES = ['ldpi', 'mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']
NUM_THREADS = 4


def increase(worker, image, progreso):
    GLib.idle_add(progreso.increase)
    return False


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


def optimize_png(file_in, level):
    level = '-o'+str(int(level))
    subprocess.check_call(['optipng', level, file_in])


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


class Manager(GObject.GObject):

    def __init__(self, elements, options, backcall):
        self.elements = elements
        self.backcall = backcall
        self.options = options

    def process(self):
        total = len(self.elements)
        if total > 0:
            print(self.elements)
            workers = []
            print('1.- Starting process creating workers')
            cua = Queue(maxsize=total + 1)
            progreso = Progreso('Converting files...', None, total)
            total_workers = total if NUM_THREADS > total else NUM_THREADS
            for i in range(total_workers):
                worker = Worker(cua, self.backcall, self.options)
                # worker.connect('converted', GLib.idle_add, progreso.increase)
                # worker.connect('converted', progreso.increase)
                worker.connect('executed', increase, progreso)
                worker.start()
                workers.append(worker)
            print('2.- Puting task in the queue')
            for element in self.elements:
                cua.put(element)
            print('3.- Block until all tasks are done')
            cua.join()
            print('4.- Stopping workers')
            for i in range(total_workers):
                cua.put(None)
            for worker in workers:
                worker.join()
                while Gtk.events_pending():
                    Gtk.main_iteration()
            print('5.- The End')


class Worker(GObject.GObject, threading.Thread):
    __gsignals__ = {
        'executed': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object, ))
        }

    def __init__(self, cua, backcall, options):
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self.setDaemon(True)
        self.cua = cua
        self.backcall = backcall
        self.options = options

    def run(self):
        while True:
            element = self.cua.get()
            if element is None:
                break
            try:
                self.backcall(element, self.options)
            except Exception as e:
                print(e)
            self.emit('executed', element)
            self.cua.task_done()


class Progreso(Gtk.Dialog):
    def __init__(self, title, parent, max_value):
        #
        Gtk.Dialog.__init__(self, title, parent)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 40)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        #
        vbox1 = Gtk.VBox(spacing=5)
        vbox1.set_border_width(5)
        self.get_content_area().add(vbox1)
        #
        self.progressbar = Gtk.ProgressBar()
        vbox1.pack_start(self.progressbar, True, True, 0)
        #
        self.show_all()
        #
        self.max_value = max_value
        self.value = 0.0

    def close(self, widget=None):
        self.destroy()

    def increase(self):
        self.value += 1.0
        fraction = self.value / self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value == self.max_value:
            self.hide()


class ResizeDialog(Gtk.Dialog):

    def __init__(self):
        Gtk.Dialog.__init__(self, 'Iconify', None, Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT,
                             Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        self.options = {}
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(200, 300)
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
        label = Gtk.Label.new('Optimization level'+':')
        label.set_alignment(0, 0.5)
        table02.attach(label, 0, 1, 2, 3,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
        adjustment1 = Gtk.Adjustment(0, 0, 8, 1, 1, 1)
        self.options['optimization-level'] = Gtk.Scale()
        self.options['optimization-level'].set_digits(0)
        self.options['optimization-level'].set_size_request(200, 10)
        self.options['optimization-level'].set_adjustment(adjustment1)
        self.options['optimization-level'].set_sensitive(False)
        table02.attach(self.options['optimization-level'], 1, 2, 2, 3,
                       xoptions=Gtk.AttachOptions.FILL,
                       yoptions=Gtk.AttachOptions.FILL,
                       xpadding=5,
                       ypadding=5)
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

    def iconify(self, menu, selected):
        rd = ResizeDialog()
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
            options['optimization-level'] =\
                rd.options['optimization-level'].get_value()
            files = get_files(selected)
            manager = Manager(files, options, self.backcall)
            manager.process()

    def backcall(self, element, options):
        basename = os.path.basename(element)
        filename, fileextension = os.path.splitext(basename)
        parent_directory = os.path.join(os.path.dirname(element), 'res')
        create_directory(parent_directory)
        if options['ldpi']:
            width = options['width'] * 0.75
            height = options['height'] * 0.75
            if options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-ldpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-ldpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if options['optimize']:
                optimize_png(png_file, options['optimization-level'])
        if options['mdpi']:
            width = options['width'] * 1.0
            height = options['height'] * 1.0
            if options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-mdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-mdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if options['optimize']:
                optimize_png(png_file, options['optimization-level'])
        if options['hdpi']:
            width = options['width'] * 1.5
            height = options['height'] * 1.5
            if options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-hdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-hdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if options['optimize']:
                optimize_png(png_file, options['optimization-level'])
        if options['xhdpi']:
            width = options['width'] * 2.0
            height = options['height'] * 2.0
            if options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-xhdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-xhdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if options['optimize']:
                optimize_png(png_file, options['optimization-level'])
        if options['xxhdpi']:
            width = options['width'] * 3.0
            height = options['height'] * 3.0
            if options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-xxhdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-xxhdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if options['optimize']:
                optimize_png(png_file, options['optimization-level'])
        if options['xxxhdpi']:
            width = options['width'] * 4.0
            height = options['height'] * 4.0
            if options['is-launcher']:
                directory = os.path.join(parent_directory, 'mipmap-xxxhdpi')
            else:
                directory = os.path.join(parent_directory, 'drawable-xxxhdpi')
            create_directory(directory)
            png_file = os.path.join(directory, filename + '.png')
            create_png(element, png_file, width, height)
            if options['optimize']:
                optimize_png(png_file, options['optimization-level'])

    def get_file_items(self, window, sel_items):
        if self.all_files_are_svg(sel_items):
            top_menuitem = FileManager.MenuItem(
                name='IconifyMenuProvider::Gtk-iconify-tools',
                label='Iconify for Android',
                tip='Create icons for Android')
            top_menuitem.connect('activate', self.iconify, sel_items)
            #
            return top_menuitem,
        return

if __name__ == '__main__':
    rd = ResizeDialog()
    rd.run()
