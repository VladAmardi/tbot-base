#!/usr/bin/env python
import os
import django
from lib import rabbitmq, catch_and_print_exceptions
import procname
import time
from multiprocessing import Process  # , current_process
from threading import Thread
from tbot.dto import *

# import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tbot.settings')


def main():
    from django.conf import settings
    from tbot import services

    # def sync_history(exchange_connection_id):
    #     connection = services.get_exchange_connection(id=exchange_connection_id)
    #     exchange = services.get_exchange(exchange_connection=connection)
    #     symbols = []
    #     for bot in services.get_bots_by_connection(exchange_connection=connection):
    #         if bot.symbol not in symbols:
    #             symbols.append(bot.symbol)
    #     for symbol in symbols:
    #         exchange.sync_history(symbol=symbol.symbol, verbose=True)

    def worker_function(exchange_connection_id):
        #     print('proc_name:{0} exchange_connection_id:{1} pid:{2}'
        #           .format(proc_name, exchange_connection_id, pid))
        procname.setprocname("c-" + str(exchange_connection_id))
        connection = services.get_exchange_connection(id=exchange_connection_id)
        exchange = services.get_exchange(exchange_connection=connection)
        exchange.user_data_stream_execution()

    class ProcessWorker(Thread):
        def __init__(self, exchange_connection_id, processes):
            Thread.__init__(self)
            self.exchange_connection_id = exchange_connection_id
            self.processes = processes

        def run(self):
            while True:
                process = Process(target=worker_function, args=(self.exchange_connection_id,))
                process.daemon = True
                self.processes[self.exchange_connection_id] = process
                process.start()
                process.join()
                if self.processes[self.exchange_connection_id] == 'stopped':
                    break
                print("RESTART: " + str(self.exchange_connection_id))

    _processes = {}

    def command_received(channel, method, properties, body: ExchangeConnectionWorkerCommand):
        if body.command == ExchangeConnectionWorkerCommands.START:
            if body.exchange_connection_id not in _processes or \
                    _processes[body.exchange_connection_id] == 'stopped':
                print("START: " + str(body.exchange_connection_id))
                worker = ProcessWorker(body.exchange_connection_id, _processes)
                worker.start()

        if body.command == ExchangeConnectionWorkerCommands.STOP:
            if body.exchange_connection_id in _processes:
                print("STOP: " + str(body.exchange_connection_id))
                worker = _processes[body.exchange_connection_id]
                _processes[body.exchange_connection_id] = 'stopped'
                worker.terminate()

    def exception_handler():
        print('Emergency termination in 3 seconds')
        time.sleep(3)
        for _exchange_connection_id in _processes:
            print("TERMINATE: " + str(_exchange_connection_id))
            worker = _processes[_exchange_connection_id]
            _processes[_exchange_connection_id] = 'stopped'
            worker.terminate()

    @catch_and_print_exceptions(callback_after=exception_handler, exit_after=True)
    def run():
        for exchange_connection in services.get_active_exchange_connections():
            _exchange = services.get_exchange(exchange_connection=exchange_connection)
            _exchange.user_data_stream_start()

        rabbitmq.listen(queue=settings.RABBITMQ_USER_DS_CMD_QUEUE, callback=command_received)

    run()


if __name__ == '__main__':
    django.setup()
    main()
