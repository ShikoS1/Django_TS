from django.contrib import admin

admin.site.site_header = 'Панель управления оборудованием'
admin.site.site_title = 'Учёт оборудования ТС'
admin.site.index_title = 'Добро пожаловать в админ-панель'
admin.site.verbose_name = 'Учёт оборудования ТС'

from .models import Vehicle, Equipment, EquipmentLog, VehicleLog

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'model', 'manufacturer', 'year')
    search_fields = ('license_plate', 'model', 'manufacturer')

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'serial_number', 'installed_in', 'installed_date')
    search_fields = ('name', 'serial_number')
    list_filter = ('installed_in',)

@admin.register(EquipmentLog)
class EquipmentLogAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'action', 'timestamp', 'user')
    search_fields = ('equipment__name', 'action', 'user', 'details')
    list_filter = ('action', 'timestamp', 'user')

@admin.register(VehicleLog)
class VehicleLogAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'action', 'timestamp', 'user')
    search_fields = ('vehicle__license_plate', 'action', 'user', 'details')
    list_filter = ('action', 'timestamp', 'user')
