from django.core.management.base import BaseCommand
from tbot.models import Order, ExchangesNames
from tbot.exchanges import Fake


class Command(BaseCommand):
    help = 'Fake order expired'

    def handle(self, *args, **options):
        order = Order.objects.get(id=int(options['order_id']))
        if order.position.round.bot.exchange_connection.exchange != ExchangesNames.FAKE:
            print("Order is not fake")
            return

        if order.status != Order.Statuses.ACTIVE:
            print("Order is not active")
            return

        Fake.callback_order_expired(order_id=order.id)

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
