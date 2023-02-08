from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tbot.models import ExchangesNames, ExchangeConnection


class Command(BaseCommand):
    help = 'User management - lsit user\'s connections with exchanges'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['username'])
        except User.DoesNotExist:
            print("User does not exist")
            return

        for ec in ExchangeConnection.objects.filter(owner=user):
            print(ec.exchange)

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
