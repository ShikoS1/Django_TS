from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Создаёт группу "Гость" без прав для демо-доступа'

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name='Гость')
        group.permissions.clear()  # Удаляем все права
        self.stdout.write(self.style.SUCCESS('Группа "Гость" создана и не имеет прав.'))
