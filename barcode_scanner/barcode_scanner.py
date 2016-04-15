#!/usr/bin/env python

import os
import sys
import logging
import argparse
import json

import cv2
from PIL import Image
import zbar
import pygtk
import gtk
import gobject

from version import getVersion

# Setup Logging
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
log_handler = logging.StreamHandler()
log_formatter = logging.Formatter(
                    fmt='[%(name)s](%(levelname)s) %(message)s',
                    datefmt='%H:%M:%S'
                )
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)

class BarcodeScanner(object):
    """ 
    Args
    ----

        camera (int) : Camera address.
        width (int) : camera width in pixels
        height (int) : camera height in pixels
        standalone (bool) : If True, starts own gtk window,
                            otherwise returns window instance to reparent.
        plugin (bool) : If True, starts plugin interface.
    """
    def __init__(self, camera=None, width=None, height=None,
                 standalone=True, plugin=None):
                 
        camera = 0 if camera is None else camera
        width = 1280 if width is None else width
        height = 1024 if height is None else height
        plugin = False if plugin is None else plugin
            
        self.camera_dim = (width, height)
        self.plugin = plugin
        
        self.builder = gtk.Builder()
        self.builder.add_from_file('barcode_window.glade')
        self.builder.connect_signals(self)
        
        self.window = self.builder.get_object('window1')
        self.window.connect('destroy', gtk.main_quit)
        self.video_image = self.builder.get_object('video_image')
        self.status_image = self.builder.get_object('status_image')
        
        self.camera_entry = self.builder.get_object('camera_entry')
        self.camera_entry.set_text(str(camera))
        
        entry_list = ['pid_entry', 'did_entry', 'bid_entry']
        self.entries = {}
        for i in entry_list:
            self.entries[i] = self.builder.get_object(i)
            
        self._ids = {}
        for i in entry_list:
            self._ids[i] = '0'
        
        self.scan_toggle = self.builder.get_object('scan_toggle')
        self.scan_toggle.connect('toggled', self.on_scan_toggle_toggled)
        
        self.ok_button = self.builder.get_object('ok_button')
        
        self.scan_proc_id = None
        gtk.quit_add(0, self.quit)
        
        # Set Version Strings
        try:
            ver = getVersion()
        except ValueError:
            ver = "1.x"
            logger.warning("Could not fetch version number")
        self.window.set_title("Barcode Scanner %s" % ver)
        
        if plugin:
            logger.info("Starting in plugin mode.")
            
            self.ok_button.set_visible(True)
            self.scan_toggle.set_active(True)
            self.ok_button.connect('clicked', gtk.main_quit)
        
        if standalone:
            self.window.show()
            return None
        else:
            return self.window
            
    def quit(self, *args):
        self.scan_stop()
        if self.plugin:
            self.dump_data()
    
    def on_scan_toggle_toggled(self, control):
        """Starts and stops barcode scanning"""
        if control.get_active():
            self.scan_start()
        else:
            self.scan_stop()
        
    def dump_data(self):
        """Dumps ids to stdout as JSON"""
        os.dup2(self.oldstdout_fno, 1)
        print json.dumps(self.ids)
    
    def scan_start(self):
        """Starts scanning"""
        # Redirect c extensions print statements to null
        devnull = open(os.devnull, 'w')
        self.oldstdout_fno = os.dup(sys.stdout.fileno())
        os.dup2(devnull.fileno(), 1)
        
        self.vc = cv2.VideoCapture(int(self.camera_entry.get_text()))
        self.scanner = zbar.ImageScanner()
        self.scanner.parse_config('enable=0')
        self.scanner.parse_config('qrcode.enable=1')
        self.scanner.parse_config('code128.enable=1')
        self.scanner.parse_config('code128.ascii=1')
        self.scanner.parse_config('code128.min=3')
        self.scanner.parse_config('code128.max=8')
        
        self.vc.open(0)
        self.vc.set(3, self.camera_dim[0])
        self.vc.set(4, self.camera_dim[1])
        
        self.scan_proc_id = gobject.timeout_add(150, self._scan_proc)
    
    def scan_stop(self):
        """Stops ongoing scan."""
        if self.scan_proc_id != None:
            gobject.source_remove(self.scan_proc_id)
            self.vc.release()
            self.scan_proc_id = None
        
        os.dup2(self.oldstdout_fno, 1)
    
    def _scan_proc(self):
        output, img = self.scan_once()
        result = {}
        
        pixbuf = gtk.gdk.pixbuf_new_from_data(img,
                                              gtk.gdk.COLORSPACE_RGB,
                                              has_alpha=False,
                                              bits_per_sample=8,
                                              width=self.camera_dim[0],
                                              height=self.camera_dim[1],
                                              rowstride=self.camera_dim[0]*3)
        
        self.video_image.set_from_pixbuf(
            pixbuf.scale_simple(dest_width=self.camera_dim[0]/4,
                                dest_height=self.camera_dim[1]/4,
                                interp_type=gtk.gdk.INTERP_BILINEAR
                                ).flip(True)
        )
        
        
        for i in output:
            symbol, data = i

            symbol = str(symbol)
            data = str(data)
            
            self.status_image.set_from_stock(gtk.STOCK_YES,
                                             gtk.ICON_SIZE_BUTTON)
            gobject.timeout_add(1000, self._status_icon_reset)
            
            if symbol == 'CODE128':
                result['pid_entry'] = data
            elif symbol == 'QRCODE':
                d_index = data.find('#')
                b_index = data.find('%')
                
                result['did_entry'] = data[d_index+1:b_index]
                result['bid_entry'] = data[b_index+1:]
        
        self.ids = result
        return True
      
    def scan_once(self):
        img_array = cv2.cvtColor( # Convert from BGR to RGB
                                 self.vc.read()[1],
                                 cv2.COLOR_BGR2RGB
                                 )
        pil = Image.fromarray(img_array)
        width, height = pil.size
        raw = pil.convert(mode='L').tobytes()
        
        # wrap image data
        image = zbar.Image(width, height, 'Y800', raw)

        # scan the image for barcodes
        self.scanner.scan(image)

        output = []

        # extract results
        for symbol in image:
            output.append((symbol.type, symbol.data))
        
        return output, img_array
    
    def _status_icon_reset(self):
        self.status_image.set_from_stock(gtk.STOCK_NO, gtk.ICON_SIZE_BUTTON)
        return False
     
    @property
    def ids(self):
        """Stores dict of all ids"""
        for i in self.entries:
            self._ids[i] = self.entries[i].get_text()
        return self._ids
    
    @ids.setter
    def ids(self, id_dict):
        self._ids.update(id_dict)
        for i in self.entries:
            self.entries[i].set_text(self._ids[i])
        
    def destroy(self, widget, data=None):
        gtk.main_quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--plugin", help="Starts 0MQ plugin interface",
                        action="store_true")
    parser.add_argument("-c", "--camera", type=int, help="Camera number")
    parser.add_argument("--width", type=int, help="Camera width (pixels)")
    parser.add_argument("--height", type=int, help="Camera height (pixels)")
    args = parser.parse_args()
    
    MAIN = BarcodeScanner(**vars(args))
    gtk.main()