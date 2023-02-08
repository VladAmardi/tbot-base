# from __future__ import annotations
from django.core.management.base import BaseCommand
from argparse import RawTextHelpFormatter
from tbot.models import Bot, Order, Round, Position
from tbot.exchanges import Exchange
from lib import boolean_input, print_object
from django.db.models import Sum, F


class Command(BaseCommand):
    help = 'Bot stop command'

    types = {
        'freeze': 'Leave current active orders \'as is\'',
        'keep': 'Cancel current active orders',
        'revert': 'Cancel current active orders and sell all base_asset',
    }

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def get_available_types(self):
        return '\'' + str("\n'".join(str(k) + '\': ' + str(self.types[k]) for k in self.types))

    def handle(self, *args, **options):
        type_key = options['type']
        if type_key not in self.types:
            print("Type is not correct. Correct types are: \n" + self.get_available_types())
            return

        bot = Bot.objects.get(id=int(options['bot_id']))

        if bot.status != bot.Statuses.ON:
            print("Bot is not enabled")
            return

        active_orders = Order.objects.filter(position__round__bot_id=bot.id, status=Order.Statuses.ACTIVE)
        sell_qty = 0
        last_round = Round.objects.filter(bot=bot).order_by('-id')[:1][0]

        print("This bot will be stopped:")
        print_object(bot, line_prefix="\t")
        print("")

        def print_orders(orders, key_filter=None):
            if key_filter is None:
                key_filter = []
            for _order in orders:
                print("")
                print_object(model=_order, key_filter=[
                    'id',
                    'type',
                    'side',
                    'created_at',
                    'updated_at',
                    'position',
                    'quote_quantity',
                    'quantity',
                    'price',
                    'stop_price',
                    'oco_order',
                ] + key_filter, line_prefix="\t")
            print("")

        match type_key:
            case 'freeze':
                print("Following order will be leaved 'as is', but will not be placed any new orders:")
                print_orders(orders=active_orders)
            case 'keep':
                print("Following order will be canceled:")
                print_orders(orders=active_orders)
            case 'revert':
                print("Following order will be canceled:")
                print_orders(orders=active_orders)
                print("And bought base asset will be sold:")
                sell_orders = Order.objects.filter(position__round_id=last_round, status=Order.Statuses.FILLED)
                print_orders(orders=sell_orders, key_filter=['result_quote_asset_quantity', 'result_filled_quantity'])
                d = round(1 / bot.symbol.min_qty)
                sell_qty = Order.objects.filter(position__round=last_round)\
                    .aggregate(sum=Sum(F('result_filled_quantity')*d))['sum'] / d
                print("\nTotal will be sold: " + str(sell_qty))

        if not boolean_input(question="Are you sure? [yN]", default=False):
            print("Canceled")
            return

        bot.status = bot.Statuses.OFF
        bot.save()

        exchange = Exchange.get_exchange(exchange=bot.exchange_connection.exchange)(connection=bot.exchange_connection)

        if type_key == 'keep' or type_key == 'revert':
            for order in active_orders:
                exchange.cancel_order(order=order)
                print('.', end='')

        if sell_qty != 0:
            position = Position.objects.filter(round=last_round).order_by('-id')[:1][0]
            exchange.new_order_market_sell(
                symbol=bot.symbol,
                quantity=sell_qty,
                position=position
            )
            print('@', end='')

        print("\nDone")

    def add_arguments(self, parser):
        parser.add_argument(
            '-b',
            '--bot_id',
            action='store',
            default=None,
            help="Bot ID",
            required=True,
            dest='bot_id'
        )
        parser.add_argument(
            '-t',
            '--type',
            action='store',
            default=None,
            help="Actions with assets: \n" + self.get_available_types(),
            required=True,
            dest='type'
        )
