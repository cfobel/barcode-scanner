from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.collections import PatchCollection
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
import gtk
import matplotlib as mpl


def get_scanner_window(scanner):
    window = gtk.Window()
    vbox = gtk.VBox()
    window.set_default_size(400, 300)
    fig = Figure(figsize=(4, 3))
    axis = fig.add_subplot(111)
    axis.set_aspect(True)
    axis.set_axis_off()
    canvas = FigureCanvas(fig)
    button_scan = gtk.Button('Scan')

    vbox.pack_start(canvas, True, True, 0)
    for widget_i in (button_scan, ):
        vbox.pack_start(widget_i, False, False, 0)

    window.add(vbox)
    window.show_all()

    status = {}

    def disable_scan():
        for callback_id in ['frame_callback_id', 'symbol_callback_id']:
            if callback_id in status:
                scanner.disconnect(status[callback_id])
                del status[callback_id]
        scanner.disable_scan()
        button_scan.set_sensitive(True)

    def enable_scan():
        scanner.reset()
        scanner.enable_scan()
        button_scan.set_sensitive(False)
        status['frame_callback_id'] = scanner.connect('frame-update',
                                                      on_frame_update)
        status['symbol_callback_id'] = scanner.connect('symbols-found',
                                                       on_symbols_found)

    button_scan.connect('clicked', lambda *args: enable_scan())

    def on_frame_update(scanner, np_img):
        axis.clear()
        axis.set_axis_off()
        axis.imshow(np_img)
        canvas.draw()

    def on_symbols_found(scanner, np_img, symbols):
        patches = []
        if symbols:
            for symbol_record_i in symbols:
                symbol_i = symbol_record_i['symbol']
                location_i = Polygon(symbol_i.location)
                patches.append(location_i)
            patch_collection = PatchCollection(patches, cmap=mpl.cm.jet, alpha=0.4)
            on_frame_update(scanner, np_img)
            axis.add_collection(patch_collection)
            canvas.draw()
            disable_scan()

    def on_exit(*args):
        for callback_id in ['frame_callback_id', 'symbol_callback_id']:
            if callback_id in status:
                scanner.disconnect(status[callback_id])
                del status[callback_id]

    window.connect('destroy', on_exit)
    return window
