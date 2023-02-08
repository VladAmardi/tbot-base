from django.core.management.base import BaseCommand
from tbot.models import Order


class Command(BaseCommand):
    help = 'Call order callback'

    def handle(self, *args, **options):
        order = Order.objects.get(id=int(options['order_id']))

        from tbot.services import execute_order_callback
        order.callback_status = Order.CallbackStatuses.WAITING
        execute_order_callback(order=order)

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
