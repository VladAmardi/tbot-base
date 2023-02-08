from django.core.management.base import BaseCommand
from tbot.models import Order, ExchangesNames
from tbot.exchanges import Fake
from lib import boolean_input


class Command(BaseCommand):
    help = 'Fake order fill'

    def handle(self, *args, **options):
        def get_option(name):
            if name in options and options[name] is not None:
                return float(options[name])
            return None

        order = Order.objects.get(id=int(options['order_id']))
        if order.position.round.bot.exchange_connection.exchange != ExchangesNames.FAKE:
            print("Order is not fake")
            return

        if order.status != Order.Statuses.ACTIVE:
            print("Order is not active")
            return

        price = order.stop_price if order.stop_price is not None else order.price

        result_filled_quantity = get_option('result_filled_quantity')
        result_quote_asset_quantity = get_option('result_quote_asset_quantity')

        if price is None:
            price = get_option('price')
            if price is None:
                if result_filled_quantity is not None and result_quote_asset_quantity is not None:
                    price = result_quote_asset_quantity / result_filled_quantity
                    print('Price is ' + str(price) + ', calculated from input')
                else:
                    exchange = Fake(connection=order.position.round.bot.exchange_connection)
                    price = exchange.get_asset_price(order.position.round.bot.symbol.symbol)
                    print('Price is ' + str(price) + ', gotten from Binance')

        quote_quantity = order.quote_quantity
        if quote_quantity is None and order.quantity is not None:
            quote_quantity = order.quantity * price

        quantity = order.quantity
        if quantity is None and quote_quantity is not None:
            quantity = quote_quantity / price

        if result_filled_quantity is None:
            result_filled_quantity = quantity

        if result_quote_asset_quantity is None:
            result_quote_asset_quantity = quote_quantity

        opts = {
            'result_quote_asset_quantity': result_quote_asset_quantity,
            'result_filled_quantity': result_filled_quantity
        }

        print("Order will be executed with params:")
        for f in opts:
            print('%s: %s' % (f, opts[f]))

        if not boolean_input(question="Are you sure? [yN]", default=False):
            return

        print("Execution with price: " + str(result_quote_asset_quantity/result_filled_quantity))

        Fake.callback_order_filled(order_id=order.id, **opts)
        if order.oco_order:
            Fake.callback_order_canceled(order_id=order.oco_order.id)

    def add_arguments(self, parser):
        parser.add_argument(
            '-o',
            '--order_id',
            action='store',
            default=None,
            help='Order ID',
            required=True,
            dest='order_id'
        )

        parser.add_argument(
            '-p',
            '--price',
            action='store',
            default=None,
            help='Price. If not set - will be gotten from Binance.',
            required=False,
            dest='price'
        )

        parser.add_argument(
            '-r',
            '--result_quote_asset_quantity',
            action='store',
            default=None,
            help='Result quote asset quantity',
            required=False,
            dest='result_quote_asset_quantity'
        )

        parser.add_argument(
            '-f',
            '--result_filled_quantity',
            action='store',
            default=None,
            help='Result filled asset quantity',
            required=False,
            dest='result_filled_quantity'
        )
