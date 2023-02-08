from binance.exceptions import BinanceAPIException
from .exchanges import Exchange
from binance.client import Client as BinanceClient
from binance import AsyncClient as BinanceAsyncClient, BinanceSocketManager
from asgiref.sync import sync_to_async
import asyncio
from tbot.models import ExchangeConnection, ExchangesNames, Order
from lib import catch_and_print_exceptions
from datetime import datetime
from django.utils import timezone


class Binance(Exchange):
    exchange = ExchangesNames.BINANCE

    def __init__(self, connection: ExchangeConnection):
        super().__init__(connection=connection)
        self.client = BinanceClient(connection.API_key, connection.API_secret)
        self._async_client: BinanceAsyncClient | type(None) = None

    def get_asset_balance(self, asset: str, calc_free=True, calc_locked=False):
        info = self.client.get_asset_balance(asset=asset)
        result = 0
        if calc_free:
            result += float(info['free'])
        if calc_locked:
            result += float(info['locked'])
        return result

    def get_asset_price(self, symbol: str):
        result = self.client.get_avg_price(symbol=symbol)
        return float(result['price'])

    def _cancel_order(self, symbol: str, client_id: str):
        try:
            self.client.cancel_order(symbol=symbol, origClientOrderId=client_id)
        except BinanceAPIException as e:
            if e.code != -2011:
                raise e

    def _sync_symbol_history(self, symbol: str, verbose: bool = False):
        time_start = datetime.now(tz=timezone.utc)
        if verbose:
            print('Sync: ' + symbol + ' ')
        # https://binance-docs.github.io/apidocs/spot/en/#all-orders-user_data
        # 500 last orders by default
        orders = self.client.get_all_orders(symbol=symbol)
        for exchange_order_data in orders:
            order_id = Exchange.order_parse_id(exchange_order_data['clientOrderId'])
            if order_id is None:
                if verbose:
                    print("-", end='')
                continue
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                if verbose:
                    print("?", end='')
                continue

            updated = False
            match exchange_order_data['status']:
                case 'NEW':  # The order has been accepted by the engine.
                    if order.status != Order.Statuses.ACTIVE:
                        Exchange.callback_order_new(order_id=order.id, updated_at=time_start)
                        updated = True
                case 'FILLED':  # The order has been completed.
                    if order.status != Order.Statuses.FILLED:
                        Exchange.callback_order_filled(
                            order_id=order_id,
                            result_quote_asset_quantity=float(exchange_order_data['cummulativeQuoteQty']),
                            result_filled_quantity=float(exchange_order_data['executedQty']),
                            updated_at=time_start
                        )
                        updated = True
                case 'CANCELED':  # The order has been canceled by the user
                    if order.status != Order.Statuses.CANCELED:
                        Exchange.callback_order_canceled(order_id=order.id, updated_at=time_start)
                        updated = True
                case 'PENDING_CANCEL':  # Currently unused
                    pass
                case 'REJECTED':  # The order was not accepted by the engine and not processed.
                    pass
                case 'EXPIRED':
                    # The order was canceled according to the order type's rules
                    # (e.g. LIMIT FOK orders with no fill, LIMIT IOC or MARKET orders
                    # that partially fill) or by the exchange, (e.g. orders canceled
                    # during liquidation, orders canceled during maintenance)
                    if order.status != Order.Statuses.EXPIRED:
                        Exchange.callback_order_expired(order_id=order.id, updated_at=time_start)
                        updated = True

            if verbose:
                print("!" if updated else '.', end='')

    class UserDataStream:
        def __init__(self, api_key: str, api_secret: str, verbose: bool, sync_func):
            self.verbose = verbose
            self._async_client = None
            self.api_key = api_key
            self.api_secret = api_secret
            self.sync_func = sync_func
            self._run_loop()

        def _run_loop(self):
            _self = self

            # noinspection PyShadowingNames
            # noinspection PyUnusedLocal
            def exception_handler(self, context):
                _self.loop.stop()

            self.loop = asyncio.new_event_loop()
            self.loop.set_exception_handler(exception_handler)
            self.loop.create_task(self.start())
            self.loop.run_forever()

        async def task_wait_and_stop(self):
            await asyncio.sleep(23 * 60 * 60)  # 23H
            if self.verbose:
                print("<<STOP BY TIMER>> (Will be started automatically)")
            self.loop.stop()  # process will be started by parent process manager

        async def task_sync_history(self):
            await sync_to_async(
                self.sync_func,
                thread_sensitive=True
            )()

        async def task_ping(self):
            while True:
                await asyncio.sleep(30 * 60)
                # Ping every 30 minutes
                if self.verbose:
                    print("<ping>")
                await self._async_client.ping()

        async def task_listen(self):
            bm = BinanceSocketManager(self._async_client)
            # start any sockets here, i.e a trade socket
            user_socket = bm.user_socket()
            if self.verbose:
                print("Socket created")
            # then start receiving messages
            async with user_socket as user_socket_cm:
                if self.verbose:
                    print("Socket receiving")
                self.loop.create_task(self.task_sync_history())
                while True:
                    res = await user_socket_cm.recv()
                    if self.verbose:
                        print(res)
                    if type({}) != type(res):
                        if self.verbose:
                            print("is not dict")
                        continue
                    if 'e' not in res:
                        if self.verbose:
                            print("'e' is not in dict")
                        continue
                    match res['e']:
                        case 'executionReport':
                            # print("executionReport: start")
                            await sync_to_async(
                                self.execution_report,
                                thread_sensitive=True
                            )(res)
                            # print("executionReport: end")

        async def start(self):
            self._async_client = BinanceAsyncClient(
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            self.loop.create_task(self.task_listen())
            self.loop.create_task(self.task_ping())
            self.loop.create_task(self.task_wait_and_stop())

        def read_res(self, res: {}, i):
            if i not in res:
                if self.verbose:
                    print("Can't read '" + i + "'")
                return None
            return res[i]

        def read_res_float(self, res: {}, i):
            result = self.read_res(res=res, i=i)
            return 0 if result is None else float(result)

        def execution_report(self, res: {}):
            # noinspection PyShadowingNames
            def exception_handler():
                self.loop.stop()

            @catch_and_print_exceptions(callback_after=exception_handler)
            def execution():
                if self.verbose:
                    print('[' + res['X'] + ']')
                match res['X']:
                    case 'NEW':
                        # print('[[' + res['c'] + ']]')
                        client_id = self.read_res(res, 'c')
                        if not client_id:
                            return
                        order_id = Exchange.order_parse_id(client_id)
                        if not order_id:
                            return
                        # print('[[[' + str(order_id) + ']]]')
                        Exchange.callback_order_new(order_id=order_id)
                    case 'CANCELED':
                        client_id = self.read_res(res, 'C')
                        if not client_id:
                            return
                        order_id = Exchange.order_parse_id(client_id)
                        if not order_id:
                            return
                        Exchange.callback_order_canceled(order_id=order_id)
                    case 'FILLED':
                        client_id = self.read_res(res, 'c')
                        if not client_id:
                            return
                        order_id = Exchange.order_parse_id(client_id)
                        if not order_id:
                            return
                        result_quote_asset_quantity = self.read_res_float(res, 'Z')
                        result_filled_quantity = self.read_res_float(res, 'z')
                        if self.verbose:
                            print('[' + str(result_quote_asset_quantity) + ', ' + str(result_filled_quantity) + ']')
                        Exchange.callback_order_filled(
                            order_id=order_id,
                            result_quote_asset_quantity=result_quote_asset_quantity,
                            result_filled_quantity=result_filled_quantity
                        )
                    case 'EXPIRED':
                        # TODO: check is it works
                        client_id = self.read_res(res, 'C')
                        if not client_id:
                            return
                        order_id = Exchange.order_parse_id(client_id)
                        if not order_id:
                            return
                        Exchange.callback_order_expired(order_id=order_id)

            execution()

    def _sync_history(self):
        import tbot.services as services
        symbols = []
        for bot in services.get_bots_by_connection_id(exchange_connection_id=self.exchange_connection.id):
            if bot.symbol not in symbols:
                symbols.append(bot.symbol)
        for symbol in symbols:
            self._sync_symbol_history(symbol=symbol.symbol, verbose=True)

    def user_data_stream_execution(self):
        self.UserDataStream(
            api_key=self.exchange_connection.API_key,
            api_secret=self.exchange_connection.API_secret,
            verbose=True,
            sync_func=self._sync_history
        )

    def _round_price(self, symbol: str, price: float) -> float:
        # PRICE_FILTER
        # price % tickSize == 0
        tick_size = self.get_symbol(symbol=symbol).tick_size
        return self.to_float(round(price / tick_size) * tick_size)

    def _round_lot(self, symbol: str, quantity: float) -> float:
        # LOT_SIZE
        # (quantity-minQty) % stepSize == 0
        _symbol = self.get_symbol(symbol=symbol)
        # TODO Someday this assertion should be removed, and logic updated, but it will be someday, not now
        assert _symbol.min_qty == _symbol.step_size
        return self.to_float(round(quantity / _symbol.step_size) * _symbol.step_size)

    def _round_quote_qty(self, symbol: str, quote_quantity: float) -> float:
        _symbol = self.get_symbol(symbol=symbol)
        d = _symbol.step_size * _symbol.tick_size
        return self.to_float(round(quote_quantity / d) * d)

    def _new_order_limit_buy(self, symbol: str, quantity: float, price: float, client_id: str):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_BUY,
            type=BinanceClient.ORDER_TYPE_LIMIT,
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            newClientOrderId=client_id
        )

    def _new_order_limit_sell(self, symbol: str, quantity: float, price: float, client_id: str):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_SELL,
            type=BinanceClient.ORDER_TYPE_LIMIT,
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            newClientOrderId=client_id
        )

    def _new_order_market_buy(self, symbol: str, quote_quantity: float, client_id: str):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_BUY,
            type=BinanceClient.ORDER_TYPE_MARKET,
            quoteOrderQty=self._round_quote_qty(symbol=symbol, quote_quantity=quote_quantity),
            newClientOrderId=client_id
        )

    def _new_order_market_sell(self, symbol: str, quantity: float, client_id: str):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_SELL,
            type=BinanceClient.ORDER_TYPE_MARKET,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            newClientOrderId=client_id
        )

    def _new_order_oco_buy(
            self,
            symbol: str,
            quantity: float,
            price: float,
            stop_price: float,
            limit_client_id: str,
            stop_limit_client_id: str,
            stop_limit_price: float | None = None,
    ):
        self.client.create_oco_order(
            symbol=symbol,
            side=BinanceClient.SIDE_BUY,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            stopPrice=self._round_price(symbol=symbol, price=stop_price),
            stopLimitPrice=self._round_price(symbol=symbol, price=stop_limit_price),
            stopLimitTimeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            limitClientOrderId=limit_client_id,
            stopClientOrderId=stop_limit_client_id,
        )

    def _new_order_oco_sell(
            self,
            symbol: str,
            quantity: float,
            price: float,
            stop_price: float,
            limit_client_id: str,
            stop_limit_client_id: str,
            stop_limit_price: float | None = None,
    ):
        self.client.create_oco_order(
            symbol=symbol,
            side=BinanceClient.SIDE_SELL,
            stopPrice=self._round_price(symbol=symbol, price=stop_price),
            stopLimitPrice=self._round_price(symbol=symbol, price=stop_limit_price),
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            stopLimitTimeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            limitClientOrderId=limit_client_id,
            stopClientOrderId=stop_limit_client_id,
        )

    # STOP_LOSS_LIMIT
    def _new_order_stop_up_limit_buy(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_BUY,
            type=BinanceClient.ORDER_TYPE_STOP_LOSS_LIMIT,
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            stopPrice=self._round_price(symbol=symbol, price=stop_price),
            newClientOrderId=client_id
        )

    # TAKE_PROFIT_LIMIT
    def _new_order_stop_down_limit_buy(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_BUY,
            type=BinanceClient.ORDER_TYPE_TAKE_PROFIT_LIMIT,
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            stopPrice=self._round_price(symbol=symbol, price=stop_price),
            newClientOrderId=client_id
        )

    # STOP LOSS LIMIT
    def _new_order_stop_down_limit_sell(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        self.client.create_order(
            symbol=symbol,
            side=BinanceClient.SIDE_SELL,
            type=BinanceClient.ORDER_TYPE_STOP_LOSS_LIMIT,
            timeInForce=BinanceClient.TIME_IN_FORCE_GTC,
            quantity=self._round_lot(symbol=symbol, quantity=quantity),
            price=self._round_price(symbol=symbol, price=price),
            stopPrice=self._round_price(symbol=symbol, price=stop_price),
            newClientOrderId=client_id
        )