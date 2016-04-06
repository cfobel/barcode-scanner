# -*- coding: utf-8 -*-
import logging

from params import get_params, set_params, load_params, save_params
from interface.save import save_text, save_plot
from zmq_plugin.plugin import Plugin as ZmqPlugin
from zmq_plugin.schema import decode_content_data
import gtk
import zmq

logger = logging.getLogger(__name__)


def get_hub_uri(default='tcp://localhost:31000', parent=None):
    message = 'Please enter 0MQ hub URI:'
    d = gtk.MessageDialog(parent=parent, flags=gtk.DIALOG_MODAL |
                          gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK_CANCEL,
                          message_format=message)
    entry = gtk.Entry()
    entry.set_text(default)
    d.vbox.pack_end(entry)
    d.vbox.show_all()
    entry.connect('activate', lambda _: d.response(gtk.RESPONSE_OK))
    d.set_default_response(gtk.RESPONSE_OK)

    r = d.run()
    text = entry.get_text().decode('utf8')
    d.destroy()
    if r == gtk.RESPONSE_OK:
        return text
    else:
        return None


class DstatPlugin(ZmqPlugin):
    '''
    Public 0MQ plugin API.
    '''
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent
        super(DstatPlugin, self).__init__(*args, **kwargs)

    def check_sockets(self):
        '''
        Check for messages on command and subscription sockets and process
        any messages accordingly.
        '''
        try:
            msg_frames = self.command_socket.recv_multipart(zmq.NOBLOCK)
        except zmq.Again:
            pass
        else:
            self.on_command_recv(msg_frames)

        try:
            msg_frames = self.subscribe_socket.recv_multipart(zmq.NOBLOCK)
            source, target, msg_type, msg_json = msg_frames
            self.most_recent = msg_json
        except zmq.Again:
            pass
        except:
            logger.error('Error processing message from subscription '
                         'socket.', exc_info=True)
        return True

    def on_execute__load_params(self, request):
        '''
        Args
        ----

            params_path (str) : Path to file for parameters yaml file.
        '''
        data = decode_content_data(request)
        load_params(self.parent, data['params_path'])

    def on_execute__save_params(self, request):
        '''
        Args
        ----

            params_path (str) : Path to file for parameters yaml file.
        '''
        data = decode_content_data(request)
        save_params(self.parent, data['params_path'])

    def on_execute__set_params(self, request):
        '''
        Args
        ----

            (dict) : Parameters dictionary in format returned by `get_params`.
        '''
        data = decode_content_data(request)
        set_params(self.parent, data['params'])

    def on_execute__get_params(self, request):
        return get_params(self.parent)

    def on_execute__run_active_experiment(self, request):
        self.parent.statusbar.push(self.parent.message_context_id, "µDrop "
                                   "acquisition requested.")
        return self.parent.run_active_experiment()
    
    def on_execute__save_text(self, request):
        '''
        Args
        ----

            save_data_path (str) : Path to file to save text data.
        '''
        data = decode_content_data(request)
        save_text(self.parent.current_exp, data['save_data_path'])

    def on_execute__save_plot(self, request):
        '''
        Args
        ----

            save_plot_path (str) : Path to file to save text data.
        '''
        data = decode_content_data(request)
        save_text(self.parent.current_exp, data['save_plot_path'])

    def on_execute__acquisition_complete(self, request):
        '''
        Args
        ----

        Returns
        -------

            (datetime.datetime or None) : The completion time of the experiment
                corresponding to the specified UUID.
        '''
        data = decode_content_data(request)
        self.parent.statusbar.push(self.parent.message_context_id, "µDrop "
                                   "notified of completed acquisition.")
        if data['experiment_id'] in self.parent.completed_experiment_ids:
            return self.parent.completed_experiment_ids[data['experiment_id']]
        elif data['experiment_id'] == self.parent.active_experiment_id:
            return None
        else:
            raise KeyError('Unknown experiment ID: %s' % data['experiment_id'])
