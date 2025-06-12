from django.db import models

EQUIPMENT_CATEGORIES = [
    ("electronics", "Электроника"),
    ("tool", "Инструмент"),
    ("safety", "Безопасность"),
    ("communication", "Связь"),
    ("other", "Другое")
]

VEHICLE_CATEGORIES = [
    ("car", "Легковой автомобиль"),
    ("truck", "Грузовик"),
    ("bus", "Автобус"),
    ("special", "Спецтехника"),
    ("other", "Другое")
]

class Vehicle(models.Model):
    category = models.CharField(max_length=20, choices=VEHICLE_CATEGORIES, default="other", verbose_name='Категория')
    license_plate = models.CharField(max_length=20, unique=True, verbose_name='Гос. номер')
    model = models.CharField(max_length=50, verbose_name='Модель')
    manufacturer = models.CharField(max_length=50, verbose_name='Производитель')
    year = models.PositiveIntegerField(verbose_name='Год выпуска')
    vin = models.CharField(max_length=50, blank=True, verbose_name='VIN')
    color = models.CharField(max_length=30, blank=True, verbose_name='Цвет')
    note = models.TextField(blank=True, verbose_name='Примечание')
    # Новые поля для статуса исправности
    maintenance_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата технического обслуживания')
    repair_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата ремонта')

    def __str__(self):
        return f"{self.license_plate} ({self.model})"

    def update_operability_status(self):
        from TS_equipment.models import MaintenanceRecord
        active_repair = MaintenanceRecord.objects.filter(vehicle=self, type='repair').exclude(status__in=['done', 'cancelled']).exists()
        active_maintenance = MaintenanceRecord.objects.filter(vehicle=self, type='maintenance').exclude(status__in=['done', 'cancelled']).exists()
        if hasattr(self, 'is_operable'):
            if active_repair:
                self.is_operable = "in_repair"
            elif active_maintenance:
                self.is_operable = "on_maintenance"
            else:
                self.is_operable = "operable"
            self.save()

    class Meta:
        verbose_name = 'Транспортное средство'
        verbose_name_plural = 'Транспортные средства'
        permissions = [
            ("can_assign_responsible", "Может назначать ответственных сотрудников"),
            ("can_set_unplanned_seal", "Может устанавливать внеплановое пломбирование"),
            ("can_set_maintenance_date", "Может устанавливать дату ТО"),
            ("can_set_repair_date", "Может устанавливать дату ремонта"),
        ]

class Equipment(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    serial_number = models.CharField(max_length=50, unique=True, verbose_name='Серийный номер')
    category = models.CharField(max_length=20, choices=EQUIPMENT_CATEGORIES, default="other", verbose_name='Категория')
    description = models.TextField(blank=True, verbose_name='Описание')
    installed_in = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='equipment', blank=True, null=True, verbose_name='Транспортное средство')
    installed_date = models.DateField(verbose_name='Дата установки')
    seal_datetime = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время пломбирования')
    seal_responsible = models.CharField(max_length=100, blank=True, verbose_name='Ответственный за пломбирование')
    unseal_datetime = models.DateTimeField(blank=True, null=True, verbose_name='Дата и время снятия пломбы')
    unseal_reason = models.CharField(max_length=200, blank=True, verbose_name='Причина снятия пломбы')
    unseal_responsible = models.CharField(max_length=100, blank=True, verbose_name='Ответственный за снятие пломбы')
    # Внеплановое пломбирование
    unscheduled_seal_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата внепланового пломбирования')
    unscheduled_seal_reason = models.CharField(max_length=200, blank=True, verbose_name='Причина внепланового пломбирования')
    # Внеплановое ТО
    maintenance_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата технического обслуживания')
    maintenance_reason = models.CharField(max_length=200, blank=True, verbose_name='Причина технического обслуживания')
    # Внеплановый ремонт
    repair_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата ремонта')
    repair_reason = models.CharField(max_length=200, blank=True, verbose_name='Причина ремонта')
    
    OPERABILITY_CHOICES = [
        ("operable", "Исправно"),
        ("in_repair", "В ремонте"),
        ("faulty", "Неисправно"),
        ("on_maintenance", "На ТО"),
        ("unknown", "Не определено"),
    ]
    is_operable = models.CharField(
        max_length=20,
        choices=OPERABILITY_CHOICES,
        default="operable",
        verbose_name="Исправность"
    )

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    def update_operability_status(self):
    
        from TS_equipment.models import MaintenanceRecord
        active_repair = MaintenanceRecord.objects.filter(equipment=self, type='repair').exclude(status__in=['done', 'cancelled']).exists()
        active_maintenance = MaintenanceRecord.objects.filter(equipment=self, type='maintenance').exclude(status__in=['done', 'cancelled']).exists()

        is_explicitly_faulty = bool(self.repair_reason and self.repair_reason.strip())
        if active_repair:
            self.is_operable = "in_repair"
        elif active_maintenance:
            self.is_operable = "on_maintenance"
        elif is_explicitly_faulty:
            self.is_operable = "faulty"
        else:
            self.is_operable = "operable"
        self.save()

    class Meta:
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудование'
        permissions = [
            ("can_assign_responsible", "Может назначать ответственных сотрудников"),
            ("can_set_unplanned_seal", "Может устанавливать внеплановое пломбирование"),
            ("can_set_maintenance_date", "Может устанавливать дату ТО"),
            ("can_set_repair_date", "Может устанавливать дату ремонта"),
        ]

class EquipmentLog(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='logs', verbose_name='Оборудование')
    action = models.CharField(max_length=100, verbose_name='Операция')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')
    user = models.CharField(max_length=100, blank=True, verbose_name='Пользователь')
    details = models.TextField(blank=True, verbose_name='Детали изменений')

    class Meta:
        verbose_name = 'Журнал оборудования'
        verbose_name_plural = 'Журналы оборудования'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.equipment} — {self.action} — {self.timestamp:%d.%m.%Y %H:%M}"

class VehicleLog(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='logs', verbose_name='ТС')
    action = models.CharField(max_length=100, verbose_name='Операция')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')
    user = models.CharField(max_length=100, blank=True, verbose_name='Пользователь')
    details = models.TextField(blank=True, verbose_name='Детали изменений')

    class Meta:
        verbose_name = 'Журнал транспорта'
        verbose_name_plural = 'Журналы транспорта'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.vehicle} — {self.action} — {self.timestamp:%d.%m.%Y %H:%M}"

class MaintenanceRecord(models.Model):
    MAINTENANCE_TYPE = [
        ('maintenance', 'ТО'),
        ('repair', 'Ремонт'),
    ]
    STATUS_CHOICES = [
        ('planned', 'Запланировано'),
        ('in_progress', 'В работе'),
        ('done', 'Выполнено'),
        ('cancelled', 'Отменено'),
        ('postponed', 'Отложено'),
    ]
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records', null=True, blank=True, verbose_name='Оборудование')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='maintenance_records', null=True, blank=True, verbose_name='ТС')
    type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE, verbose_name='Тип работ')
    date = models.DateField(verbose_name='Дата работ')
    mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name='Пробег/наработка')
    description = models.TextField(verbose_name='Описание работ')
    responsible = models.CharField(max_length=100, verbose_name='Ответственный')
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Стоимость')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name='Статус')
    file = models.FileField(upload_to='maintenance_docs/', null=True, blank=True, verbose_name='Документ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Запись ТОиР'
        verbose_name_plural = 'ТОиР'
        ordering = ['-date', '-created_at']

    def __str__(self):
        obj = self.equipment or self.vehicle
        return f"{obj} — {self.get_type_display()} — {self.date:%d.%m.%Y}"

class RepairHistory(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='repair_history', null=True, blank=True, verbose_name='Оборудование')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='repair_history', null=True, blank=True, verbose_name='ТС')
    type = models.CharField(max_length=20, choices=MaintenanceRecord.MAINTENANCE_TYPE, verbose_name='Тип работ')
    date = models.DateField(verbose_name='Дата работ')
    mileage = models.PositiveIntegerField(null=True, blank=True, verbose_name='Пробег/наработка')
    description = models.TextField(verbose_name='Описание работ')
    responsible = models.CharField(max_length=100, verbose_name='Ответственный')
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Стоимость')
    status = models.CharField(max_length=20, choices=MaintenanceRecord.STATUS_CHOICES, default='done', verbose_name='Статус')
    file = models.FileField(upload_to='repair_docs/', null=True, blank=True, verbose_name='Документ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'История ремонта'
        verbose_name_plural = 'История ремонтов'
        ordering = ['-date', '-created_at']

    def __str__(self):
        obj = self.equipment or self.vehicle
        return f"{obj} — {self.get_type_display()} — {self.date:%d.%m.%Y}"
