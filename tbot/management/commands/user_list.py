from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'User management - users list'

    def handle(self, *args, **options):
        for user in User.objects.all():
            print(str(user) + ": " + ("Active" if user.is_active else "Deactivated"))


