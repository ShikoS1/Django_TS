from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from datetime import date, timedelta

from .models import MaintenanceRecord

def send_notification_email(subject, message, recipient_list, html_message=None):
    """
    Send a notification email using Django's send_mail.
    """
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipient_list,
        fail_silently=False,
        html_message=html_message,
    )

def get_upcoming_maintenance(days_ahead=7):
    today = date.today()
    upcoming = MaintenanceRecord.objects.filter(
        date__gte=today,
        date__lte=today + timedelta(days=days_ahead),
        status__in=['planned', 'in_progress']
    )
    return upcoming

def setup_user_roles():
    # Администратор
    admin_group, _ = Group.objects.get_or_create(name='Администратор')
    admin_permissions = Permission.objects.all()
    admin_group.permissions.set(admin_permissions)

    # Специалист транспортного отдела
    specialist_group, _ = Group.objects.get_or_create(name='Специалист транспортного отдела')
    # Доступ: просмотр/редактирование данных, отчеты, назначение ответственных, установка дат внепланового пломбирования, ТО и ремонта
    specialist_perms = Permission.objects.filter(
        content_type__app_label='TS_equipment',
        codename__in=[
            'add_equipment', 'change_equipment', 'view_equipment',
            'add_vehicle', 'change_vehicle', 'view_vehicle',
            'add_maintenancerecord', 'change_maintenancerecord', 'view_maintenancerecord',
            'add_equipmentlog', 'change_equipmentlog', 'view_equipmentlog',
            'add_vehiclelog', 'change_vehiclelog', 'view_vehiclelog',
            'add_repairhistory', 'change_repairhistory', 'view_repairhistory',
        ]
    )
    specialist_group.permissions.set(specialist_perms)

    # Сотрудник
    staff_group, _ = Group.objects.get_or_create(name='Сотрудник')
    # Доступ: внесение информации по пломбированию и ТОиР, получение уведомлений
    staff_perms = Permission.objects.filter(
        content_type__app_label='TS_equipment',
        codename__in=[
            'add_equipmentlog', 'change_equipmentlog', 'view_equipmentlog',
            'add_maintenancerecord', 'change_maintenancerecord', 'view_maintenancerecord',
            'change_equipment', 
            'can_set_unplanned_seal', 
        ]
    )
    staff_group.permissions.set(staff_perms)
