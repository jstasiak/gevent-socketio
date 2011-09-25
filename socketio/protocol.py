import gevent
import anyjson as json


class SocketIOProtocol(object):
    """SocketIO protocol specific functions."""

    def __init__(self, handler):
        self.handler = handler
        self.session = None

    def ack(self, msg_id, *args):
        if '+' not in msg_id:
            assert not args

        self._send_raw("6:::%s%s" % (msg_id, json.dumps(args) if '+' in msg_id else ''))

    def send(self, message):
        self._send_raw(self._format_message_frame(message))

    def _format_message_frame(self, message):
        return "3:::{0}".format(message)

    def emit(self, name, *args):
        self._send_raw(self._format_event_frame(name, *args))

    def _format_event_frame(self, name, *args):
        return "5:::" + json.dumps({'name': name, 'args': args})

    def receive(self):
        """Wait for incoming messages."""

        return self.session.get_server_msg()

    def broadcast_send(self, message, **kwargs):
        self._broadcast_raw(self._format_message_frame(message), **kwargs)

    def broadcast_emit(self, name, *args, **kwargs):
        self._broadcast_raw(self._format_event_frame(name, *args), **kwargs)

    def _broadcast_raw(self, message, exceptions = None, include_self = False):
        """
        Send messages to all connected clients, except itself and some
        others.
        """

        if exceptions is None:
            exceptions = []

        if not include_self:
            exceptions.append(self.session.session_id)

        for session_id, session in self.handler.server.sessions.iteritems():
            if session_id not in exceptions:
                self._write(message, session)

    def start_heartbeat(self):
        """Start the heartbeat Greenlet to check connection health."""
        def ping():
            self.session.state = self.session.STATE_CONNECTED

            while self.session.connected:
                gevent.sleep(5.0) # FIXME: make this a setting
                self._send_raw("2::")

        return gevent.spawn(ping)

    def _send_raw(self, message, destination = None):
        if destination is None:
            dst_client = self.session
        else:
            dst_client = self.handler.server.sessions.get(destination)

        self._write(message, dst_client)


    def _write(self, message, session=None):
        if session is None:
            raise Exception("No client with that session exists")
        else:
            print('{0} <= {1!r}'.format(self.session.session_id, message))
            session.put_client_msg(message)

    def encode(self, message):
        if isinstance(message, basestring):
            encoded_msg = message
        elif isinstance(message, (object, dict)):
            return self.encode(json.dumps(message))
        else:
            raise ValueError("Can't encode message")

        return encoded_msg

    def decode(self, data):
        messages = []
        msg_type, msg_id, tail = data.split(":", 2)

        print('{0} => {1!r}'.format(self.session.session_id, data))

        if msg_type == "0":
            self.session.kill()
            return None

        elif msg_type == "1":
            self._send_raw("1::%s" % tail)
            return None

        elif msg_type == "2":
            self.session.heartbeat()
            return None

        msg_endpoint, data = tail.split(":", 1)

        if msg_type == "3":
            message = {
                'type': 'message',
                'data': data,
            }
            messages.append(message)
            self.ack(msg_id)
        elif msg_type == "4":
            raise Exception("TODO")
        elif msg_type == "5":
            message = json.loads(data)

            if "+" in msg_id:
                message['id'] = msg_id
            else:
                pass # TODO send auto ack
            message['type'] = 'event'
            messages.append(message)
        else:
            raise Exception("Unknown message type: %s" % msg_type)

        return messages[0]
