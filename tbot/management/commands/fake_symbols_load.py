from .binance_symbols_load import Command as BinanceCommand
from tbot.models import ExchangesNames


class Command(BinanceCommand):
    help = 'In truth, symbol pairs will be loaded from Binance'

    @classmethod
    def get_exchange_name(cls):
        return ExchangesNames.FAKE
