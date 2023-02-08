from .exchanges import Exchange
from tbot.models import ExchangesNames, ExchangeConnection


class Fake(Exchange):
    exchange = ExchangesNames.FAKE

    def __init__(self, connection: ExchangeConnection):
        super().__init__(connection=connection)
        self._binance = None

    def _get_binance(self):
        if self._binance is None:
            try:
                binance_connection = ExchangeConnection.objects.filter(
                    owner=self.exchange_connection.owner,
                    exchange=ExchangesNames.BINANCE
                )[0]
            except IndexError:
                try:
                    binance_connection = ExchangeConnection.objects.filter(
                        owner=self.exchange_connection.owner,
                        exchange=ExchangesNames.BINANCETEST
                    )[0]
                except IndexError:
                    raise BaseException("You should add for current user connection to binance or at least binancetest")
            from tbot.services import get_exchange
            self._binance = get_exchange(exchange_connection=binance_connection)
        return self._binance

    def get_asset_balance(self, asset: str, calc_free=True, calc_locked=False):
        return 1000000

    def get_asset_price(self, symbol: str):
        return self._get_binance().get_asset_price(symbol=symbol)

    def _cancel_order(self, symbol: str, client_id: str):
        order_id = Exchange.order_parse_id(client_id)
        Exchange.callback_order_canceled(order_id=order_id)

    def sync_history(self, symbol: str, verbose: bool = False):
        pass

    def user_data_stream_execution(self):
        pass

    @staticmethod
    def _mark_active(client_id: str):
        order_id = Exchange.order_parse_id(client_id)
        Exchange.callback_order_new(order_id=order_id)

    def _new_order_limit_buy(self, symbol: str, quantity: float, price: float, client_id: str):
        self._mark_active(client_id=client_id)

    def _new_order_market_buy(self, symbol: str, quote_quantity: float, client_id: str):
        self._mark_active(client_id=client_id)

    def _new_order_market_sell(self, symbol: str, quantity: float, client_id: str):
        self._mark_active(client_id=client_id)

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
        self._mark_active(client_id=limit_client_id)
        self._mark_active(client_id=stop_limit_client_id)

    # Disable user-data-stream
    def user_data_stream_command(self, command: str):
        pass

    def _new_order_stop_down_limit_sell(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        self._mark_active(client_id=client_id)

    def _new_order_stop_up_limit_buy(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        self._mark_active(client_id=client_id)

    def _new_order_stop_down_limit_buy(
            self,
            symbol: str,
            quantity: float,
            stop_price: float,
            price: float,
            client_id: str
    ):
        self._mark_active(client_id=client_id)

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
        self._mark_active(client_id=limit_client_id)
        self._mark_active(client_id=stop_limit_client_id)

    def _new_order_limit_sell(self, symbol: str, quantity: float, price: float, client_id: str):
        self._mark_active(client_id=client_id)
