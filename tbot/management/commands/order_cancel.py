from django.core.management.base import BaseCommand
from tbot.models import Order
from tbot.exchanges import Exchange


class Command(BaseCommand):
    help = 'Order cancel command'

    def handle(self, *args, **options):
        order = Order.objects.get(id=int(options['order_id']))
        connection = order.position.round.bot.exchange_connection
        exchange = Exchange.get_exchange(exchange=connection.exchange)(connection=connection)
        exchange.cancel_order(order=order)
        print("Done")

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
