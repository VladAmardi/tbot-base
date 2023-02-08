from django.conf import settings
import pika
import pickle

_connection = {}


def get_connection(host=None):
    if host is None:
        host = settings.RABBITMQ_HOST

    if host not in _connection:
        _connection[host] = pika.BlockingConnection(pika.ConnectionParameters(host))
        pass

    return _connection[host]


def send(queue, routing_key, body, channel_number=None, exchange='', host=None):
    channel = get_connection(host).channel(channel_number=channel_number)
    channel.queue_declare(queue=queue)
    channel.basic_publish(exchange=exchange,
                          routing_key=routing_key,
                          body=pickle.dumps(body))


def listen(queue, callback, channel_number=None, host=None):
    """
    Starts listener

    :param str queue: The queue from which to consume
    :param callable callback: Required function for dispatching messages
        to user, having the signature:
        callback(channel, method, properties, body)
         - channel: BlockingChannel
         - method: spec.Basic.Deliver
         - properties: spec.BasicProperties
         - body: bytes
    :param int channel_number: The channel number to use, defaults to the
        next available.
    :param str host: You may specify host name.
        Defaults will be taken from settings.RABBITMQ_HOST
    """
    _channel = get_connection(host).channel(channel_number=channel_number)
    _channel.queue_declare(queue=queue)

    def callback_wrapper(channel, method, properties, body):
        callback(channel=channel, method=method, properties=properties, body=pickle.loads(body))

    _channel.basic_consume(queue=queue,
                           auto_ack=True,
                           on_message_callback=callback_wrapper)
    _channel.start_consuming()
