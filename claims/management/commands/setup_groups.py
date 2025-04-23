from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Creates the required user groups for the reimbursement system'

    def handle(self, *args, **options):
        # Define the groups
        groups = [
            'Society Members',
            'Committee Members',
            'SU Staff'
        ]
        
        # Create the groups if they don't exist
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created group "{group_name}"'))
            else:
                self.stdout.write(f'Group "{group_name}" already exists')
        
        self.stdout.write(self.style.SUCCESS('User groups setup complete'))