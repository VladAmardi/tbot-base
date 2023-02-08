from django.core.management.base import BaseCommand
from binance.client import Client
from tbot.models import Symbol, ExchangesNames
from lib import cached


@cached('binance_exchange_info', 15*60)
def get_binance_exchange_info():
    client = Client()
    return client.get_exchange_info()


def get_filter(symbol_info, filter_name, filter_param):
    if 'filters' in symbol_info:
        for _filter in symbol_info['filters']:
            if _filter['filterType'] == filter_name:
                if filter_param in _filter:
                    return _filter[filter_param]

    return None


# https://habr.com/ru/post/415049/
class Command(BaseCommand):
    help = 'Loading symbol pairs from Binance'

    @classmethod
    def get_exchange_name(cls):
        return ExchangesNames.BINANCE

    def handle(self, *args, **options):

        client = Client()
        info = client.get_exchange_info()
        for symbol_info in info['symbols']:

            symbol, created = Symbol.objects.get_or_create(
                exchange=self.get_exchange_name(),
                base_asset=symbol_info['baseAsset'],
                quote_asset=symbol_info['quoteAsset']
            )

            symbol.symbol = symbol_info['symbol']
            symbol.min_notional = float(get_filter(symbol_info, 'MIN_NOTIONAL', 'minNotional'))

            symbol.min_price = float(get_filter(symbol_info, 'PRICE_FILTER', 'minPrice'))
            symbol.max_price = float(get_filter(symbol_info, 'PRICE_FILTER', 'maxPrice'))
            symbol.tick_size = float(get_filter(symbol_info, 'PRICE_FILTER', 'tickSize'))

            symbol.step_size = float(get_filter(symbol_info, 'LOT_SIZE', 'stepSize'))
            symbol.min_qty = float(get_filter(symbol_info, 'LOT_SIZE', 'minQty'))

            # symbol.multiplier_up = float(get_filter(symbol_info, 'PERCENT_PRICE', 'multiplierUp'))
            # symbol.multiplier_down = float(get_filter(symbol_info, 'PERCENT_PRICE', 'multiplierDown'))
            # symbol.multiplier_avg_price_minutes = float(get_filter(symbol_info, 'PERCENT_PRICE', 'avgPriceMins'))

            enabled = True
            if symbol_info['status'] != 'TRADING':
                enabled = False
            if not symbol_info['ocoAllowed']:
                enabled = False
            if not symbol_info['isSpotTradingAllowed']:
                enabled = False

            symbol.enabled = enabled

            symbol.save()

            print(symbol.symbol + ': ' + ('Created' if created else 'Saved'))
