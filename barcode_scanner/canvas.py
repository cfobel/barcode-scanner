# -*- coding: utf-8 -*-
import logging

from pygtkhelpers.ui.views.cairo_view import GtkCairoView
import gtk
try:
    import pygst
    pygst.require("0.10")
except:
    pass
finally:
    import gst

logger = logging.getLogger(__name__)


class BarcodeCanvas(GtkCairoView):
    def __init__(self, video_settings):
        self.video_settings = video_settings
        super(BarcodeCanvas, self).__init__()

    def reset(self):
        self.camerabin = gst.element_factory_make("camerabin", "camera-source")
        bus = self.camerabin.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self._on_message)
        bus.connect("sync-message::element", self._on_sync_message)
        self.camerabin.set_property("image-encoder",
                                    gst.element_factory_make("pngenc",
                                                             "png_encoder"))
        self.filename_prefix = ""

    def _on_sync_message(self, bus, message):
        """ _on_sync_message - internal signal handler for bus messages.
        May be useful to extend in a base class to handle messages
        produced from custom behaviors.


        arguments -
        bus: the bus from which the message was sent, typically self.bux
        message: the message sent

        """

        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.window_xid)

    def _on_message(self, bus, message):
        """ _on_message - internal signal handler for bus messages.
        May be useful to extend in a base class to handle messages
        produced from custom behaviors.


        arguments -
        bus: the bus from which the message was sent, typically self.bus
        message: the message sent

        """

        if message is None:
            return

        t = message.type
        #if t == Gst.MessageType.ELEMENT:
        if t == gst.MESSAGE_ELEMENT:
            if message.structure.get_name() == "image-captured":
                #work around to keep the camera working after lots
                #of pictures are taken
                self.camerabin.set_state(gst.STATE_NULL)
                self.camerabin.set_state(gst.STATE_PLAYING)

                self.emit("image-captured", self.filename)

        if t == gst.MESSAGE_EOS:
            self.camerabin.set_state(gst.STATE_NULL)
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug

    def show_and_run(self):
        #def delayed():
            #self.camerabin.set_property("filename", 'test.png')
            #self.camerabin.emit("capture-start")
        #gtk.timeout_add(2000, delayed)

        super(BarcodeCanvas, self).show_and_run()


def source_string(json_source):
    # Import here, since importing `gst` before calling `parse_args` causes
    # command-line help to be overridden by GStreamer help.
    from pygst_utils.video_source import VIDEO_SOURCE_PLUGIN, DEVICE_KEY

    # Set `(red|green|blue)_mask` to ensure RGB channel order for both YUY2
    # and I420 video sources.  If this is not done, red and blue channels
    # might be swapped.
    #
    # See [here][1] for default mask values.
    #
    # [1]: https://www.freedesktop.org/software/gstreamer-sdk/data/docs/latest/gst-plugins-bad-plugins-0.10/gst-plugins-bad-plugins-videoparse.html#GstVideoParse--blue-mask
    caps_str = (u'video/x-yuv,width={width:d},height={height:d},'
                u'red_mask=(int)255,green_mask=(int)65280,'
                u'blue_mask=(int)16711680,'
                u'framerate={framerate_num:d}/{framerate_denom:d}'
                .format(**json_source))
    device_str = u'{} {}="{}"'.format(VIDEO_SOURCE_PLUGIN, DEVICE_KEY,
                                      json_source['device_name'])
    logging.info('[View] video config device string: %s', device_str)
    logging.info('[View] video config caps string: %s', caps_str)

    return ''.join([device_str, ' ! ffmpegcolorspace ! ', caps_str])


if __name__ == '__main__':
    from pygst_utils.video_source import VIDEO_SOURCE_PLUGIN, DEVICE_KEY

    canvas = BarcodeCanvas(None)
    canvas.reset()

    canvas.camerabin.props.video_source = gst.element_factory_make(VIDEO_SOURCE_PLUGIN)
    canvas.camerabin.props.video_source.set_property(DEVICE_KEY, "USB2.0 HD UVC WebCam")
    canvas.camerabin.props.video_source_filter = gst.element_factory_make('ffmpegcolorspace')
    caps_str = "video/x-raw-yuv,width=640,height=480,red_mask=(int)255,green_mask=(int)65280,blue_mask=(int)16711680,framerate=15/1"
    canvas.camerabin.props.filter_caps = gst.caps_from_string(caps_str)
    canvas.camerabin.set_state(gst.STATE_PLAYING)
    #canvas.camerabin.set_state(gst.STATE_NULL)
    canvas.show_and_run()
