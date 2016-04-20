from argparse import ArgumentParser
import json
import logging
import pprint
import sys

import gtk

from ..io_redirect import nostderr
from ..scanner import BarcodeScanner

logger = logging.getLogger(__name__)


def gui_main(pipeline_command):
    from ..gtk_matplotlib import ScannerView

    gtk.gdk.threads_init()
    scanner = BarcodeScanner()

    with nostderr():
        pipeline, status = scanner.start(pipeline_command)

    def on_exit(*args):
        scanner.stop()
        gtk.main_quit()

    window = gtk.Window()
    scanner_view = ScannerView(scanner)
    window.add(scanner_view.widget)
    window.connect('destroy', on_exit)
    window.show_all()

    gtk.main()


def pipeline_command_from_json(json_source):
    # Import here, since importing `gst` before calling `parse_args` causes
    # command-line help to be overridden by GStreamer help.
    with nostderr():
        from pygst_utils.video_source import VIDEO_SOURCE_PLUGIN, DEVICE_KEY

    # Set `(red|green|blue)_mask` to ensure RGB channel order for both YUY2
    # and I420 video sources.  If this is not done, red and blue channels
    # might be swapped.
    #
    # See [here][1] for default mask values.
    #
    # [1]: https://www.freedesktop.org/software/gstreamer-sdk/data/docs/latest/gst-plugins-bad-plugins-0.10/gst-plugins-bad-plugins-videoparse.html#GstVideoParse--blue-mask
    caps_str = (u'video/x-raw-rgb,width={width:d},height={height:d},'
                u'framerate={framerate_num:d}/{framerate_denom:d}'
                .format(**json_source))
    device_str = u'{} {}="{}"'.format(VIDEO_SOURCE_PLUGIN, DEVICE_KEY,
                                      json_source['device_name'])
    logging.info('[View] video config device string: %s', device_str)
    logging.info('[View] video config caps string: %s', caps_str)

    video_command = ''.join([device_str, ' ! ffmpegcolorspace ! ', caps_str,
                             ' ! appsink name=app-video emit-signals=true'])
    return video_command


def parse_args(args=None):
    """Parses arguments, returns (options, args)."""

    if args is None:
        args = sys.argv

    parser = ArgumentParser(description='Barcode scanner based on GStreamer, '
                            'zbar, and gtk.')
    log_levels = ('critical', 'error', 'warning', 'info', 'debug', 'notset')

    parser_pipeline = ArgumentParser(add_help=False)
    parser_pipeline.add_argument('-i', '--interactive', action='store_true',
                                 help='Do not start main loop.')
    parser_pipeline.add_argument('-l', '--log-level', type=str, choices=log_levels,
                        default='info')

    default_pipeline = [
        'autovideosrc name=video-source', '!',
        'ffmpegcolorspace', '!',
        'video/x-raw-rgb,format=(fourcc)I420,framerate=30/1,'
        'width=640,height=480', '!',
        'videorate', '!',
        'appsink',
            'name=app-video',
            #'enable-last-buffer=true',
            'emit-signals=true',
            #'sync=true',
    ]
    default_pipeline_command = " ".join(default_pipeline)

    subparsers = parser.add_subparsers(help='sub-command help', dest='command')

    parser_launch = subparsers.add_parser('launch', help='Configure pipeline '
                                          'using `gst-launch` syntax.',
                                          parents=[parser_pipeline])
    parser_launch.add_argument('pipeline', nargs='?',
                               default=default_pipeline_command,
                               help='Default: %(default)s')

    parser_json = subparsers.add_parser('fromjson', help='Configure pipeline'
                                        'from json object including: '
                                        'device_name, width, height, '
                                        'framerate_num, framerate_denom',
                                        parents=[parser_pipeline])
    parser_json.add_argument('json', help='JSON object including: '
                             'device_name, width, height, framerate_num, '
                             'framerate_denom')

    subparsers.add_parser('device_list', help='List available device names')

    parser_device_caps = subparsers.add_parser('device_caps', help='List '
                                               'JSON serialized capabilities '
                                               'for device (compatible with '
                                               '`fromjson` subcommand).')
    parser_device_caps.add_argument('device_name')

    args = parser.parse_args()
    if hasattr(args, 'log_level'):
        args.log_level = getattr(logging, args.log_level.upper())
    return args


def main(args=None):
    args = parse_args(args)

    if args.command == 'launch':
        gui_main(args.pipeline)
    elif args.command == 'fromjson':
        json_config = json.loads(args.json)
        pipeline_command = pipeline_command_from_json(json_config)
        gui_main(pipeline_command)
    elif args.command == 'device_list':
        with nostderr():
            from pygst_utils.video_source import get_video_source_names

            print '\n'.join(get_video_source_names())
    elif args.command == 'device_caps':
        with nostderr():
            from pygst_utils.video_source import (expand_allowed_capabilities,
                                                  get_allowed_capabilities)

            df_allowed_caps = get_allowed_capabilities(args.device_name)
            df_source_caps = expand_allowed_capabilities(df_allowed_caps)
            print '\n'.join([c.to_json() for i, c in
                             df_source_caps.iterrows()])


if __name__ == "__main__":
    main()
