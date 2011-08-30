import urllib
import gevent
import anyjson as json


class SocketIOProtocol(object):
    """SocketIO protocol specific functions."""

    def __init__(self, handler):
        self.handler = handler
        self.session = None

    def on_connect(self):
        return self.connected() and self.session.is_new()

    def connected(self):
        if getattr(self, 'session'):
            return self.session.connected
        else:
            return False

    def send(self, message, destination=None):
        if destination is None:
            dst_client = self.session
        else:
            dst_client = self.handler.server.sessions.get(destination)

        self._write(message, dst_client)

    def recv(self):
        """Wait for incoming messages."""

        msg = self.session.get_server_msg()

        if msg is None:
            return []
        else:
            return msg

    def broadcast(self, message, exceptions=None):
        """
        Send messages to all connected clients, except itself and some
        others.
        """

        if exceptions is None:
            exceptions = []

        exceptions.append(self.session.session_id)

        for session_id, session in self.handler.server.sessions.iteritems():
            if session_id not in exceptions:
                self._write(message, session)

    def start_heartbeat(self):
        """Start the heartbeat Greenlet to check connection health."""

        def ping():
            while self.connected():
                gevent.sleep(9.0) # FIXME: make this a setting
                hb_msg = HEARTBEAT_FRAME + str(self.session.heartbeat())
                self._write(hb_msg, self.session)

        return gevent.spawn(ping)

    def check_heartbeat(self, counter):
        """Check for a valid incoming heartbeat."""

        counter = int(counter[len(HEARTBEAT_FRAME):])

        if self.session.valid_heartbeat(counter):
            return
        else:
            self.session.kill()

    def _write(self, message, session=None):
        if session is None:
            raise Exception("No client with that session exists")
        else:
            session.put_client_msg(message)

    def encode(self, message):
        print message

        if isinstance(message, basestring):
            encoded_msg = message
        elif isinstance(message, (object, dict)):
            return self.encode(json.dumps(message))
        else:
            raise ValueError("Can't encode message")

        return MSG_FRAME + str(len(encoded_msg)) + MSG_FRAME + encoded_msg

    def decode(self, data):
        messages = []
        data.encode('utf-8', 'replace')
        msg_type, msg_id, msg_endpoint, data = urllib.unquote_plus(data).split(":", 3)

        print msg_type, data

        if msg_type == 0:
            # Disconnect
            pass
        elif msg_type == 1:
            pass
        elif msg_type == 2:
            # send back heartbeat
            pass
        elif msg_type == 3:
            messages.append(data)
        elif msg_type == 4:
            message.append(json.loads(data))
        elif msg_type == 5:
            # some event
            pass
        elif msg_type == 6:
            # ACK
            pass
        elif msg_type == 7:
            pass
        elif msg_type == 8:
            pass

        return messages



        #if data:
        #    while len(data) != 0:
        #        if data[0:3] == MSG_FRAME:
        #            _, size, data = data.split(MSG_FRAME, 2)
        #            size = int(size)
        #            frame_type = data[0:3]

        #            if frame_type == JSON_FRAME:
        #                messages.append(json.loads(data[3:size]))

        #            elif frame_type == HEARTBEAT_FRAME:
        #                self.check_heartbeat(data[0:size])

        #            else:
        #                messages.append(data[0:size])

        #            data = data[size:]
        #        else:
        #            raise Exception("Unsupported frame type")

        #    return messages
        #else:
        #    return messages