from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.utils import IntegrityError

class Command(BaseCommand):
    help = 'Creates a superuser for the reimbursement system'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@example.com'
        password = 'adminpassword'
        
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully'))
        except IntegrityError:
            self.stdout.write(f'Superuser "{username}" already exists')
            user = User.objects.get(username=username)
            if not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True
                user.save()
                self.stdout.write(self.style.SUCCESS(f'User "{username}" promoted to superuser'))