from django.core.management.base import BaseCommand
from TS_equipment.models import Equipment

class Command(BaseCommand):
    help = 'Recalculate and update operability status for all equipment.'

    def handle(self, *args, **options):
        updated = 0
        for eq in Equipment.objects.all():
            eq.update_operability_status()
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'Обновлено статусов оборудования: {updated}'))
