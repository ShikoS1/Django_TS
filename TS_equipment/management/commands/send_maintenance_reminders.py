from django.core.management.base import BaseCommand
from TS_equipment.utils import get_upcoming_maintenance, send_notification_email
from TS_equipment.models import MaintenanceRecord

class Command(BaseCommand):
    help = 'Send email reminders for upcoming maintenance (ТОиР) to responsibles.'

    def handle(self, *args, **options):
        upcoming = get_upcoming_maintenance(days_ahead=7)
        count = 0
        for record in upcoming:
            responsible = record.responsible
            email = None
            if '@' in responsible:
                email = responsible
            else:
                fio = responsible.strip().split()
                if len(fio) >= 2:
                    last = fio[0].lower()
                    initials = ''.join([x[0].lower() for x in fio[1:]])
                    email = f"{last}.{initials}@corporate-mail.com"
            if email:
                subject = f'Напоминание о предстоящем ТОиР: {record.get_type_display()} {record.date:%d.%m.%Y}'
                message = f'Уважаемый(ая) {responsible},\n\nВам назначено проведение {record.get_type_display()} для объекта: '
                if record.equipment:
                    message += f'Оборудование {record.equipment}.'
                elif record.vehicle:
                    message += f'ТС {record.vehicle}.'
                message += f'\nДата: {record.date:%d.%m.%Y}\nОписание: {record.description}\n'
                send_notification_email(subject, message, [email])
                count += 1
        self.stdout.write(self.style.SUCCESS(f'Отправлено напоминаний: {count}'))
