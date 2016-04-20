from datetime import datetime
import logging

from pygtkhelpers.utils import gsignal
import gobject
import zbar

logger = logging.getLogger(__name__)


class BarcodeScanner(gobject.GObject):
    '''
    GObject barcode scanner class, which can scan frames from a GStreamer
    pipeline for barcodes.

    Usage
    -----

        scanner = BarcodeScanner(<`gst-launch` pipeline command>)

        # Start GStreamer pipeline.
        scanner.start()  # Emits `frame-update` signal for every video frame
        # Start scanning each frame for barcode(s).
        scanner.enable_scan()  # Emits `symbols-found` signal if symbols found

        # Stop scanning frames for barcode(s).
        scanner.disable_scan()
        # Pause GStreamer pipeline, but do not release video source.
        scanner.pause()
        # Stop GStreamer pipeline (e.g., free webcam).
        scanner.stop()

    Signals
    -------

     - `frame-update`: `(scanner, np_img)`
         * `scanner` (`BarcodeScanner`): Scanner object.
         * `np_img` (`numpy.ndarray`): Video frame, with shape of
           `(height, width, channels)`.
     - `symbols-found`: `(scanner, np_img, symbols)`
         * `scanner` (`BarcodeScanner`): Scanner object.
         * `np_img` (`numpy.ndarray`): Video frame containing found symbols,
           with shape of `(height, width, channels)`.
         * `symbols` (`list`): List of symbol record dictionaries.  Each
           record contains the following:
             - `type` (`str`): Type of `zbar` code (e.g., `QRCODE`).
             - `data` (`str`): Data from `zbar` symbol.
             - `symbol` (`zbar.Symbol`): Symbol object.
             - `timestamp` (`str`): UTC timestamp in ISO 8601 format.
    '''
    gsignal('frame-update', object)  # Args: `(scanner, np_img)`
    gsignal('symbols-found', object, object)  # Args: `(scanner, np_img, symbols)`

    def __init__(self, pipeline_command=None):
        super(BarcodeScanner, self).__init__()
        self.pipeline_command = pipeline_command
        self.connect('frame-update', self.process_frame)
        self.scanner = zbar.ImageScanner()
        self.scanner.parse_config('enable=0')
        self.scanner.parse_config('ean8.enable=1')
        self.scanner.parse_config('ean13.enable=1')
        self.scanner.parse_config('upce.enable=1')
        self.scanner.parse_config('isbn10.enable=1')
        self.scanner.parse_config('isbn13.enable=1')
        self.scanner.parse_config('i25.enable=1')
        self.scanner.parse_config('upca.enable=1')
        self.scanner.parse_config('code39.enable=1')
        self.scanner.parse_config('qrcode.enable=1')
        self.scanner.parse_config('code128.enable=1')
        self.scanner.parse_config('code128.ascii=1')
        self.scanner.parse_config('code128.min=3')
        self.scanner.parse_config('code128.max=8')
        self.scan_id = None
        self.pipeline = None

    def __dealloc__(self):
        self.stop()

    ###########################################################################
    # Callback methods
    def process_frame(self, obj, np_img):
        import PIL.Image
        import zbar

        if self.status.get('processing_scan'):
            return True
        self.status['processing_scan'] = True
        pil_image = PIL.Image.fromarray(np_img)
        raw = pil_image.convert(mode='L').tobytes()
        height, width, channels = np_img.shape
        zbar_image = zbar.Image(width, height, 'Y800', raw)
        self.scanner.scan(zbar_image)

        symbols = [{'timestamp': datetime.utcnow().isoformat(), 'type':
                    str(s.type), 'data': str(s.data), 'symbol': s}
                   for s in zbar_image]

        def symbols_equal(a, b):
            key = lambda v: (v['type'], v['data'])
            if len(a) == len(b):
                return all([a_i[k] == b_i[k] for k in ('type', 'data')
                            for a_i, b_i in zip(sorted(a, key=key),
                                                sorted(b, key=key))])
            return False

        if symbols and not symbols_equal(symbols, self.status.get('symbols',
                                                                  [])):
            self.emit('symbols-found', np_img, symbols)
            self.status['symbols'] = symbols
            self.status['np_img'] = np_img

        self.status['np_img'] = np_img
        self.status['processing_scan'] = False

    ###########################################################################
    # Control methods
    def disable_scan(self):
        '''
        Stop scanning frames for barcode(s).
        '''
        if self.scan_id is not None:
            self.disconnect(self.scan_id)
            self.scan_id = None
        self.reset()

    def enable_scan(self):
        '''
        Start scanning each frame for barcode(s).
        '''
        self.scan_id = self.connect('frame-update', self.process_frame)

    def pause(self):
        '''
        Pause GStreamer pipeline, but do not release video source.
        '''
        import gst

        if self.pipeline is not None:
            self.pipeline.set_state(gst.STATE_PAUSED)

    def reset(self):
        self.status = {'processing_frame': False,
                       'processing_scan': False}

    def start(self, pipeline_command=None, enable_scan=False):
        '''
        Start GStreamer pipeline and configure pipeline to trigger
        `frame-update` for every new video frame.
        '''
        import gst

        self.reset()
        if pipeline_command is None:
            if self.pipeline_command is None:
                raise ValueError('No default pipeline command available.  Must'
                                 ' provide `pipeline_command` argument.')
            else:
                pipeline_command = self.pipeline_command

        if self.pipeline is not None:
            self.stop()

        pipeline = gst.parse_launch(unicode(pipeline_command).encode('utf-8'))
        self.pipeline = pipeline
        app = pipeline.get_by_name('app-video')
        self.reset()

        def on_new_buffer(appsink):
            import numpy as np

            self.status['processing_frame'] = True
            buf = appsink.emit('pull-buffer')
            caps = buf.caps[0]
            np_img = (np.frombuffer(buf.data, dtype='uint8', count=buf.size)
                      .reshape(caps['height'], caps['width'], -1))
            self.emit('frame-update', np_img)
            self.status['processing_frame'] = False

        app.connect('new-buffer', on_new_buffer)

        pipeline.set_state(gst.STATE_PAUSED)
        pipeline.set_state(gst.STATE_PLAYING)
        self.pipeline = pipeline
        self.pipeline_command = pipeline_command
        if enable_scan:
            self.enable_scan()
        return pipeline, self.status

    def stop(self):
        '''
        Stop GStreamer pipeline (e.g., free webcam).
        '''
        import gst

        self.pause()
        if self.pipeline is not None:
            self.pipeline.set_state(gst.STATE_NULL)
            del self.pipeline
            self.pipeline = None
