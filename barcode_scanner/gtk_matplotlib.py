from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.collections import PatchCollection
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from pygtkhelpers.delegates import SlaveView
import gtk
import matplotlib as mpl


class ScannerView(SlaveView):
    def __init__(self, scanner, width=400, height=300):
        self.scanner = scanner
        self.callback_ids = {}
        self.width = width
        self.height = height
        super(ScannerView, self).__init__()

    def on_button_debug__clicked(self, button):
        import IPython
        import inspect

        # Get parent from stack
        parent_stack = inspect.stack()[1]
        IPython.embed()

    def create_ui(self):
        self.fig = Figure(figsize=(4, 3), frameon=False)
        # Remove padding around axes.
        self.fig.subplots_adjust(bottom=0, top=1, right=1, left=0)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.set_size_request(self.width, self.height)
        self.reset_axis()
        self.button_scan = gtk.Button('Scan')
        self.button_debug = gtk.Button('Debug')

        self.widget.pack_start(self.canvas, True, True, 0)
        for widget_i in (self.button_scan, self.button_debug):
            self.widget.pack_start(widget_i, False, False, 0)

        self.widget.show_all()
        self.button_scan.connect('clicked', lambda *args: self.enable_scan())

    def reset_axis(self):
        self.fig.clf()
        self.axis = self.fig.add_subplot(111)
        self.axis.set_aspect(True)
        self.axis.set_axis_off()

    def cleanup(self):
        for callback_id in ['frame', 'symbol']:
            if callback_id in self.callback_ids:
                self.scanner.disconnect(self.callback_ids[callback_id])
                del self.callback_ids[callback_id]

    def disable_scan(self):
        self.cleanup()
        self.scanner.disable_scan()
        self.button_scan.set_sensitive(True)

    def enable_scan(self):
        self.reset_axis()
        self.scanner.reset()
        self.scanner.enable_scan()
        self.button_scan.set_sensitive(False)
        self.callback_ids['frame'] = self.scanner.connect('frame-update',
                                                          self.on_frame_update)
        self.callback_ids['symbol'] = self.scanner.connect('symbols-found',
                                                           self.on_symbols_found)

    def __dealloc__(self):
        self.cleanup()

    def on_frame_update(self, scanner, np_img):
        self.axis.clear()
        self.axis.set_axis_off()
        self.axis.imshow(np_img)
        self.canvas.draw()

    def on_symbols_found(self, scanner, np_img, symbols):
        patches = []
        if symbols:
            for symbol_record_i in symbols:
                symbol_i = symbol_record_i['symbol']
                location_i = Polygon(symbol_i.location)
                patches.append(location_i)
            patch_collection = PatchCollection(patches, cmap=mpl.cm.jet,
                                               alpha=0.4)
            self.on_frame_update(scanner, np_img)
            self.axis.add_collection(patch_collection)
            self.canvas.draw()
            self.disable_scan()
