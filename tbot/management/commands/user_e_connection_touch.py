from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tbot.models import ExchangesNames, ExchangeConnection
from lib import is_percent, percent_to_float


# https://habr.com/ru/post/415049/
class Command(BaseCommand):
    help = 'User management - user\'s connections with exchanges'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            print("User does not exist")
            return

        if options['exchange'] not in ExchangesNames.labels:
            print("Exchange does not exist. Available options are: " + (', '.join(ExchangesNames.labels)))
            return

        commission = False

        if is_percent(options['commission']):
            commission = percent_to_float(options['commission'])

        if commission is False or commission == 0:
            print("Incorrect value of -c/--commission - is should be percent")
            return

        connection, created = ExchangeConnection.objects.update_or_create(owner=user, exchange=options['exchange'])

        connection.API_key = options['key']
        connection.API_secret = options['secret']
        connection.commission = commission
        connection.save()

        if created:
            print("Created")
        else:
            print("Updated")

    def add_arguments(self, parser):
        parser.add_argument(
            '-u',
            '--username',
            action='store',
            default=False,
            help='User name',
            required=True,
            dest='username'
        )

        parser.add_argument(
            '-e',
            '--exchange',
            action='store',
            default=False,
            help='Exchange name, available options are: ' + (', '.join(ExchangesNames.labels)),
            required=True,
            dest='exchange'
        )

        parser.add_argument(
            '-k',
            '--key',
            action='store',
            default=False,
            help='API_key',
            required=True,
            dest='key'
        )

        parser.add_argument(
            '-s',
            '--secret',
            action='store',
            default=False,
            help='API_secret',
            required=True,
            dest='secret'
        )

        parser.add_argument(
            '-c',
            '--commission',
            action='store',
            default='0.1%',
            help='Commission (in percent), default = 0.1%%',
            required=False,
            dest='commission'
        )
