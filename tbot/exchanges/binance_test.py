from . import Exchange
from .binance import Binance
from tbot.models import ExchangesNames, ExchangeConnection
from binance.client import Client as BinanceClient
from binance import AsyncClient as BinanceAsyncClient


class BinanceTest(Binance):
    exchange = ExchangesNames.BINANCETEST

    def __init__(self, connection: ExchangeConnection):
        Exchange.__init__(self=self, connection=connection)
        self.client = BinanceClient(
            api_key=connection.API_key,
            api_secret=connection.API_secret,
            testnet=True
        )
        self._async_client: BinanceAsyncClient | type(None) = None
