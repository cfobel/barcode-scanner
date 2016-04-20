from datetime import datetime
import logging

from pygtkhelpers.utils import gsignal
import gobject
import zbar

logger = logging.getLogger(__name__)


class BarcodeScanner(gobject.GObject):
    gsignal('frame-update', object)
    gsignal('symbols-found', object, object)

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

    def reset(self):
        self.status = {'processing_frame': False,
                       'processing_scan': False}

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

    def enable_scan(self):
        self.scan_id = self.connect('frame-update', self.process_frame)

    def disable_scan(self):
        if self.scan_id is not None:
            self.disconnect(self.scan_id)
            self.scan_id = None
        self.reset()

    def start(self, pipeline_command=None, enable_scan=False):
        import gst

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

    def pause(self):
        import gst

        if self.pipeline is not None:
            self.pipeline.set_state(gst.STATE_PAUSED)

    def stop(self):
        import gst

        self.pause()
        if self.pipeline is not None:
            self.pipeline.set_state(gst.STATE_NULL)
            del self.pipeline
            self.pipeline = None

    def __dealloc__(self):
        self.stop()

