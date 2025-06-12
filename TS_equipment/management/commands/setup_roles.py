from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, ContentType
from TS_equipment.models import Equipment, Vehicle

class Command(BaseCommand):
    help = 'Создаёт группы пользователей и назначает права для ролей: Администратор, Специалист транспортного отдела, Сотрудник.'

    def handle(self, *args, **options):
        # Администратор: все права
        admin_group, _ = Group.objects.get_or_create(name='Администратор')
        all_perms = Permission.objects.all()
        admin_group.permissions.set(all_perms)

        # Специалист транспортного отдела
        specialist_group, _ = Group.objects.get_or_create(name='Специалист транспортного отдела')
        specialist_perms = set()
        for model in [Equipment, Vehicle]:
            ct = ContentType.objects.get_for_model(model)
            for codename in [
                'view_' + model._meta.model_name,
                'change_' + model._meta.model_name,
                'add_' + model._meta.model_name,
                'can_assign_responsible',
                'can_set_unplanned_seal',
                'can_set_maintenance_date',
                'can_set_repair_date']:
                perms = Permission.objects.filter(codename=codename, content_type=ct)
                specialist_perms.update(perms)
        specialist_group.permissions.set(specialist_perms)

        # Сотрудник
        employee_group, _ = Group.objects.get_or_create(name='Сотрудник')
        employee_perms = set()
        for model in [Equipment, Vehicle]:
            ct = ContentType.objects.get_for_model(model)
            for codename in [
                'view_' + model._meta.model_name,
                'add_' + model._meta.model_name,
                'can_set_unplanned_seal',
                'can_set_maintenance_date',
                'can_set_repair_date']:
                perms = Permission.objects.filter(codename=codename, content_type=ct)
                employee_perms.update(perms)
        employee_group.permissions.set(employee_perms)

        self.stdout.write(self.style.SUCCESS('Группы и права успешно созданы!'))
