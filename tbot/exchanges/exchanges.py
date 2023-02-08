from __future__ import annotations
from abc import ABC, abstractmethod
import re
import sys
from datetime import datetime
from django.utils import timezone
# project level
from django.conf import settings
from lib import rabbitmq, print_object
# application level
from tbot.dto import ExchangeConnectionWorkerCommands, ExchangeConnectionWorkerCommand
from tbot.models import ExchangeConnection, Symbol, ExchangesNames, Order, Position


def _create_order(**kwargs) -> Order:
    order = Order(**kwargs)
    order.save()
    return order


class Exchange(ABC):
    exchange: ExchangesNames
    _instances = {}

    @classmethod
    def get_all(cls):
        result = []
        for child in cls.__subclasses__():
            result = result + child.get_all()
            result = result + [child]
        return result

    @staticmethod
    def get_exchange(exchange: ExchangesNames) -> type(Exchange) | None:
        for i in Exchange.get_all():
            if i.exchange == exchange:
                return i
        return None

    def __new__(cls, connection: ExchangeConnection, *args, **kwargs):
        _id = str(connection.id)
        if _id not in cls._instances:
            cls._instances[_id] = super(Exchange, cls).__new__(cls, *args, **kwargs)
        return cls._instances[_id]

    def __init__(self, connection: ExchangeConnection):
        self.exchange_connection = connection
        self._symbols = {}

    def get_symbol(self, symbol: str, cached=True) -> Symbol:
        if symbol not in self._symbols or not cached:
            self._symbols[symbol] = Symbol.objects.get(exchange=self.exchange_connection.exchange, symbol=symbol)
        return self._symbols[symbol]

    def clear_symbols_cache(self):
        self._symbols = {}

    @abstractmethod
    def get_asset_balance(self, asset: str, calc_free=True, calc_locked=False):
        pass

    def get_base_asset_balance(self, symbol: Symbol):
        return self.get_asset_balance(asset=symbol.base_asset)
        pass

    def get_quote_asset_balance(self, symbol: Symbol):
        return self.get_asset_balance(asset=symbol.quote_asset)
        pass

    @abstractmethod
    def get_asset_price(self, symbol: str):
        pass

    @classmethod
    def on_error_order(cls, order):
        order.status = order.Statuses.ERROR
        order.save()
        print_object(order, file=sys.stderr)

    def new_order_market_buy(
            self,
            symbol: Symbol,
            position: Position,
            quote_quantity: float,
            callback: str = '',
            position_key: str = '',
    ):
        order = _create_order(
            position=position,
            type=Order.Types.MARKET,
            side=Order.Sides.BUY,
            quote_quantity=quote_quantity,
            callback=callback,
            position_key=position_key,
        )

        try:
            self._new_order_market_buy(
                symbol=symbol.symbol,
                quote_quantity=self.to_float(quote_quantity),
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_market_buy(self, symbol: str, quote_quantity: float, client_id: str):
        pass

    def new_order_market_sell(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            callback: str = '',
            position_key: str = '',
    ):
        order = _create_order(
            position=position,
            type=Order.Types.MARKET,
            side=Order.Sides.SELL,
            quantity=quantity,
            callback=callback,
            position_key=position_key,
        )

        try:
            self._new_order_market_sell(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_market_sell(self, symbol: str, quantity: float, client_id: str):
        pass

    def new_order_limit_buy(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            price: float,
            callback: str = '',
            position_key: str = '',
    ):
        order = _create_order(
            position=position,
            type=Order.Types.LIMIT,
            side=Order.Sides.BUY,
            quantity=quantity,
            price=price,
            callback=callback,
            position_key=position_key,
        )

        try:
            self._new_order_limit_buy(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                price=self.to_float(price),
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_limit_buy(self, symbol: str, quantity: float, price: float, client_id: str):
        pass

    def new_order_limit_sell(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            price: float,
            callback: str = '',
            position_key: str = '',
    ):
        order = _create_order(
            position=position,
            quantity=quantity,
            price=price,
            type=Order.Types.LIMIT,
            side=Order.Sides.SELL,
            callback=callback,
            position_key=position_key,
        )

        try:
            self._new_order_limit_sell(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                price=self.to_float(price),
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_limit_sell(self, symbol: str, quantity: float, price: float, client_id: str):
        pass

    def new_order_stop_down_limit_sell(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            stop_price: float,
            callback: str = '',
            price: float | None = None,
            position_key: str = '',
    ):
        if price is None:
            price = self.to_float(stop_price * 0.9)

        order = _create_order(
            position=position,
            type=Order.Types.STOP_LOSS_LIMIT,
            side=Order.Sides.SELL,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            callback=callback,
            position_key=position_key,
        )

        try:
            self._new_order_stop_down_limit_sell(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                price=self.to_float(price),
                stop_price=stop_price,
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_stop_down_limit_sell(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        pass

    # if price will rise to or above [Stop] ...
    def new_order_stop_up_limit_buy(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            stop_price: float,
            callback: str = '',
            price: float | None = None,
            position_key: str = '',
    ):
        if price is None:
            price = self.to_float(stop_price * 1.1)

        order = _create_order(
            position=position,
            type=Order.Types.STOP_LOSS_LIMIT,
            side=Order.Sides.BUY,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            callback=callback,
            position_key=position_key,
        )

        try:
            self._new_order_stop_up_limit_buy(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                price=self.to_float(price),
                stop_price=stop_price,
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_stop_up_limit_buy(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        pass

    # if price will fall to or below [Stop] ...
    def new_order_stop_down_limit_buy(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            stop_price: float,
            callback: str = '',
            price: float | None = None,
            position_key: str = '',
    ):
        if price is None:
            price = self.to_float(stop_price * 1.1)

        order = _create_order(
            position=position,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            callback=callback,
            type=Order.Types.TAKE_PROFIT_LIMIT,
            side=Order.Sides.BUY,
            position_key=position_key,
        )

        try:
            self._new_order_stop_down_limit_buy(
                symbol=symbol.symbol,
                quantity=quantity,
                price=self.to_float(price),
                stop_price=self.to_float(stop_price),
                client_id=self.order_encode_id(order_id=order.id)
            )
        except BaseException as e:
            self.on_error_order(order=order)
            raise e

    @abstractmethod
    def _new_order_stop_down_limit_buy(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        pass

    def cancel_order(self, order: Order):
        # TODO Stop user-stream worker if it not needed

        reloaded_order = Order.objects.get(id=order.id)
        if reloaded_order.status != order.Statuses.ACTIVE:
            return

        if order.oco_order is not None:
            order.oco_order.callback_status = Order.CallbackStatuses.CANCELED
            order.oco_order.save()

        order.callback_status = order.CallbackStatuses.CANCELED
        order.save()

        self._cancel_order(
            symbol=order.position.round.bot.symbol.symbol,
            client_id=self.order_encode_id(order.id)
        )

    @abstractmethod
    def _cancel_order(self, symbol: str, client_id: str):
        pass

    @classmethod
    def to_float(cls, number):
        return float(round(number, 8))

    def new_order_oco_buy(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            price: float,
            stop_price: float,
            callback_limit: str = '',
            callback_stop_limit: str = '',
            stop_limit_price: float | None = None,
            position_key_limit: str = '',
            position_key_stop_limit: str = '',
    ):
        order_limit = Order(
            position=position,
            type=Order.Types.LIMIT_MAKER,
            side=Order.Sides.BUY,
            quantity=quantity,
            price=price,
            callback=callback_limit,
            position_key=position_key_limit,
        )
        order_limit.save()

        if stop_limit_price is None:
            stop_limit_price = self.to_float(stop_price * 1.1)

        order_stop_limit = Order(
            position=position,
            type=Order.Types.STOP_LOSS_LIMIT,
            side=Order.Sides.BUY,
            quantity=self.to_float(quantity),
            price=stop_limit_price,
            stop_price=stop_price,
            callback=callback_stop_limit,
            oco_order=order_limit,
            position_key=position_key_stop_limit,
        )
        order_stop_limit.save()

        order_limit.oco_order = order_stop_limit
        order_limit.save()

        try:
            self._new_order_oco_buy(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                price=self.to_float(price),
                stop_price=self.to_float(stop_price),
                stop_limit_price=self.to_float(stop_limit_price),
                limit_client_id=self.order_encode_id(order_id=order_limit.id),
                stop_limit_client_id=self.order_encode_id(order_id=order_stop_limit.id),
            )
        except BaseException as e:
            self.on_error_order(order=order_limit)
            self.on_error_order(order=order_stop_limit)
            raise e

    @abstractmethod
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
        pass

    def new_order_oco_sell(
            self,
            symbol: Symbol,
            position: Position,
            quantity: float,
            price: float,
            stop_price: float,
            callback_limit: str = '',
            callback_stop_limit: str = '',
            stop_limit_price: float | None = None,
            position_key_limit: str = '',
            position_key_stop_limit: str = '',
    ):
        order_limit = Order(
            position=position,
            quantity=quantity,
            type=Order.Types.LIMIT_MAKER,
            side=Order.Sides.SELL,
            price=price,
            callback=callback_limit,
            position_key=position_key_limit,
        )
        order_limit.save()

        if stop_limit_price is None:
            stop_limit_price = stop_price * 0.9

        order_stop_limit = Order(
            type=Order.Types.STOP_LOSS_LIMIT,
            side=Order.Sides.SELL,
            position=position,
            quantity=quantity,
            price=stop_limit_price,
            stop_price=stop_price,
            callback=callback_stop_limit,
            oco_order=order_limit,
            position_key=position_key_stop_limit,
        )
        order_stop_limit.save()

        order_limit.oco_order = order_stop_limit
        order_limit.save()

        try:
            self._new_order_oco_sell(
                symbol=symbol.symbol,
                quantity=self.to_float(quantity),
                price=self.to_float(price),
                stop_price=self.to_float(stop_price),
                stop_limit_price=self.to_float(stop_limit_price),
                limit_client_id=self.order_encode_id(order_id=order_limit.id),
                stop_limit_client_id=self.order_encode_id(order_id=order_stop_limit.id),
            )
        except BaseException as e:
            self.on_error_order(order=order_limit)
            self.on_error_order(order=order_stop_limit)
            raise e

    @abstractmethod
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
        pass

    def user_data_stream_command(self, command: str):
        command_body = ExchangeConnectionWorkerCommand(
            exchange_connection_id=self.exchange_connection.id,
            command=command
        )

        rabbitmq.send(
            queue=settings.RABBITMQ_USER_DS_CMD_QUEUE,
            routing_key=settings.RABBITMQ_USER_DS_CMD_QUEUE,
            body=command_body)

    def user_data_stream_start(self):
        self.user_data_stream_command(ExchangeConnectionWorkerCommands.START)

    def user_data_stream_stop(self):
        self.user_data_stream_command(ExchangeConnectionWorkerCommands.STOP)

    @abstractmethod
    def user_data_stream_execution(self):
        pass

    @staticmethod
    def order_parse_id(order_id: str) -> int | None:
        r = re.match(r'^(\w{12})-(\d+)$', order_id)
        if r is None:
            return None
        if r.group(1) != settings.EXCHANGE_ORDER_PREFIX:
            return None
        return int(r.group(2))

    @staticmethod
    def order_encode_id(order_id: int) -> str:
        return settings.EXCHANGE_ORDER_PREFIX + "-" + str(order_id)

    @classmethod
    def _callback_order(cls, status: Order.Statuses, order_id: int, updated_at: datetime | None = None, **kwargs):
        order: Order = Order.objects.get(id=order_id)
        order.status = status
        fields = ['status']
        for k in kwargs:
            setattr(order, k, kwargs[k])
            if k not in fields:
                fields.append(k)

        if updated_at is None:
            order.save(update_fields=(fields + ['updated_at']))
            saved = True
        else:
            update = {
                'updated_at': datetime.now(tz=timezone.utc)
            }
            for key in fields:
                update[key] = order._meta.get_field(key).value_from_object(order)
            saved = Order.objects.filter(id=order.id, updated_at__lt=updated_at).update(**update) > 0

        ignore_callback = (status == Order.Statuses.EXPIRED) and order.oco_order_id is not None

        if saved and not ignore_callback:
            bot = order.position.round.bot
            if bot.status == bot.Statuses.ON and status != order.Statuses.ACTIVE:
                from tbot.services import execute_order_callback
                execute_order_callback(order=order)

    @classmethod
    def callback_order_filled(
            cls,
            order_id: int,
            result_quote_asset_quantity: float,
            result_filled_quantity: float,
            updated_at: datetime | None = None
    ):
        cls._callback_order(
            status=Order.Statuses.FILLED,
            order_id=order_id,
            updated_at=updated_at,
            result_quote_asset_quantity=result_quote_asset_quantity,
            result_filled_quantity=result_filled_quantity
        )

    @classmethod
    def callback_order_new(cls, order_id: int, updated_at: datetime | None = None):
        cls._callback_order(status=Order.Statuses.ACTIVE, order_id=order_id, updated_at=updated_at)

    @classmethod
    def callback_order_canceled(cls, order_id: int, updated_at: datetime | None = None):
        cls._callback_order(status=Order.Statuses.CANCELED, order_id=order_id, updated_at=updated_at)

    @classmethod
    def callback_order_expired(cls, order_id: int, updated_at: datetime | None = None):
        cls._callback_order(status=Order.Statuses.EXPIRED, order_id=order_id, updated_at=updated_at)
