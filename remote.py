import tornado.ioloop
import tornado.web
from tornado.locks import Event
from tornado import gen

from ast import literal_eval

## Install
# pip install tornado

## Notes
# (1.) What happens if an attacker deliberately listens on a users public key to
# block them from using the service?
# - This means the that users must be able to listen on the same public key
# simultaneously, but (2.) what will stop an attacker spamming all connections?
class Broker(object):
    def __init__(self):
        self.listeners = {}

    def listen_for_public_key(self, publicKey, event):
        print("subscribe for public key:")
        print(publicKey)
        self.listeners[publicKey] = event

    def remove_listener(self, publicKey):
        print("unsubscribe for public key:")
        print(publicKey)
        event = self.listeners.pop(publicKey)
        event.set()

    def snapshot(self):
        return self.listeners

    def add_transaction(self, publicKey, encryptedPin, transaction):
        if (publicKey in self.listeners):
            self.remove_listener(publicKey)

##
## curl -X POST http://localhost:8888/publish/ -d '{"publicKey":"12345","encryptedPin":"pin","transaction":"bytes?"}'
##
class PublishHandler(tornado.web.RequestHandler):

    def initialize(self, broker):
        self.broker = broker

    async def post(self):
        requestBody = self.__decodeJson(self.request.body)
        validation = self.__validateBody(requestBody)
        if ("error" in validation):
            self.set_status(400)
            self.write(tornado.escape.json_encode(validation))
            self.finish()
        else:
            print ("signing request sent with: ")
            print (requestBody)
            self.broker.add_transaction(requestBody["publicKey"], requestBody["encryptedPin"], requestBody["transaction"])
            self.set_status(200)
            self.finish()

    def __validateBody(self, body):
        if ("publicKey" not in body):
            return {'error':'You must include a publicKey to pubish to.'}
        elif ("encryptedPin" not in body):
            return {'error':'You must include a 6 character secret encrypted with the publicKey.'}
        elif ("transaction" not in body):
            return {'error':'You must include a transaction to be signed.'}
        else:
            return {}

    def __decodeJson(self, requestBody):
        try:
            return tornado.escape.json_decode(requestBody)
        except Exception:
            return {}

class SubscribeHandler(tornado.web.RequestHandler):

    def initialize(self, broker):
        self.event = Event()
        self.broker = broker

    async def get(self, publicKey):
        self.publicKey = publicKey
        self.broker.listen_for_public_key(publicKey, self.event)
        await self.event.wait()
        self.write(publicKey)
        self.finish()

    def on_connection_close(self):
        self.broker.remove_listener(self.publicKey)

class SnapshotHandler(tornado.web.RequestHandler):

    def initialize(self, broker):
        self.broker = broker

    async def get(self):
        print(self.broker.snapshot())
        self.finish()

if __name__ == "__main__":
    broker = Broker()
    app = tornado.web.Application([
        (r"/publish/", PublishHandler, dict(broker=broker)),
        (r"/subscribe/([^/]+)/", SubscribeHandler, dict(broker=broker)),
        (r"/snapshot/", SnapshotHandler, dict(broker=broker))
    ])
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
