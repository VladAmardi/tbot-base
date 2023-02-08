from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


# https://habr.com/ru/post/415049/
class Command(BaseCommand):
    help = 'User management - create/edit'

    def handle(self, *args, **options):
        user, created = User.objects.update_or_create(username=options['username'])

        user.set_password(options['password'])

        user.is_active = True if not options['deactivated'] else False

        user.save()

        if created:
            print("Created")
        else:
            print("Updated")

        if user.is_active:
            print("User is active")
        else:
            print("User is deactivated")

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
            '-p',
            '--password',
            action='store',
            default=False,
            help='Password',
            required=True,
            dest='password'
        )

        parser.add_argument(
            '-d',
            '--deactivated',
            action='store_const',
            default=False,
            help='Is user deactivated',
            required=False,
            const=True,
            dest='deactivated'
        )
