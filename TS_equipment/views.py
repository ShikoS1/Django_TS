from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
import tablib
from django.template.loader import render_to_string
from django import forms
from django.db.models import Q
from collections import Counter
from django.db.models.functions import TruncMonth
from django.db import models
import json
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.models import Group
from django.views.decorators.csrf import csrf_exempt
import random
import string

from .models import Equipment, Vehicle, EquipmentLog, MaintenanceRecord, RepairHistory
from .forms import VehicleForm, EquipmentForm, EquipmentAssignForm, MaintenanceRecordForm
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.http import require_POST
from .utils import send_notification_email


FIELD_LABELS_RU = {
    'license_plate': 'Гос. номер',
    'model': 'Модель',
    'manufacturer': 'Производитель',
    'year': 'Год выпуска',
    'vin': 'VIN',
    'color': 'Цвет',
    'note': 'Примечание',
    'category': 'Категория',
    'maintenance_date': 'Дата ТО',
    'repair_date': 'Дата ремонта',
    'name': 'Название',
    'serial_number': 'Серийный номер',
    'description': 'Описание',
    'installed_in': 'ТС',
    'installed_date': 'Дата установки',
    'seal_datetime': 'Дата и время пломбирования',
    'seal_responsible': 'Ответственный за пломбирование',
    'unseal_datetime': 'Дата и время снятия пломбы',
    'unseal_reason': 'Причина снятия пломбы',
    'unseal_responsible': 'Ответственный за снятие пломбы',
    'unscheduled_seal_date': 'Дата внепланового пломбирования',
    'unscheduled_seal_reason': 'Причина внепланового пломбирования',
    'maintenance_reason': 'Причина ТО',
    'repair_reason': 'Причина ремонта',
}

def get_field_label(field):
    return FIELD_LABELS_RU.get(field, field)

@login_required
def dashboard(request):
    total_vehicles = Vehicle.objects.count()
    total_equipment = Equipment.objects.count()
    equipment_in_use = total_equipment
    # --- Индивидуальные последние объекты ---
    recent_vehicles_ids = request.session.get('recent_vehicles', [])
    recent_equipment_ids = request.session.get('recent_equipment', [])
    recent_vehicles = list(Vehicle.objects.filter(id__in=recent_vehicles_ids))
    # Сохраняем порядок просмотра
    recent_vehicles.sort(key=lambda v: recent_vehicles_ids.index(v.id))
    recent_equipment = list(Equipment.objects.filter(id__in=recent_equipment_ids))
    recent_equipment.sort(key=lambda e: recent_equipment_ids.index(e.id))
    # --- конец ---
    # Статистика ТОиР по статусам
    if MaintenanceRecord.objects.exists():
        status_counts = dict(Counter(MaintenanceRecord.objects.values_list('status', flat=True)))
        type_counts = dict(Counter(MaintenanceRecord.objects.values_list('type', flat=True)))
        monthly_stats = MaintenanceRecord.objects.annotate(month=TruncMonth('date')).values('month', 'type').order_by('month').annotate(count=models.Count('id'))
        monthly_data = {}
        for row in monthly_stats:
            m = row['month'].strftime('%Y-%m') if row['month'] else '—'
            t = row['type']
            if m not in monthly_data:
                monthly_data[m] = {'maintenance': 0, 'repair': 0}
            monthly_data[m][t] = row['count']
        monthly_labels = json.dumps(list(monthly_data.keys()), ensure_ascii=False)
        monthly_maintenance = json.dumps([v['maintenance'] for v in monthly_data.values()], ensure_ascii=False)
        monthly_repair = json.dumps([v['repair'] for v in monthly_data.values()], ensure_ascii=False)
        status_labels = json.dumps(list(status_counts.keys()), ensure_ascii=False)
        status_data = json.dumps(list(status_counts.values()), ensure_ascii=False)
    else:
        monthly_labels = json.dumps([])
        monthly_maintenance = json.dumps([])
        monthly_repair = json.dumps([])
        status_labels = json.dumps([])
        status_data = json.dumps([])
    return render(request, 'TS_equipment/dashboard.html', {
        'total_vehicles': total_vehicles,
        'total_equipment': total_equipment,
        'equipment_in_use': equipment_in_use,
        'recent_vehicles': recent_vehicles,
        'recent_equipment': recent_equipment,
        'maintenance_stats': type_counts if MaintenanceRecord.objects.exists() else {},
        'status_counts': status_counts if MaintenanceRecord.objects.exists() else {},
        'monthly_labels': monthly_labels,
        'monthly_maintenance': monthly_maintenance,
        'monthly_repair': monthly_repair,
        'status_labels': status_labels,
        'status_data': status_data,
    })

@login_required
def vehicle_list(request):
    vehicles = Vehicle.objects.all()
    is_guest = request.user.groups.filter(name='Гость').exists()
    return render(request, 'TS_equipment/vehicle_list.html', {'vehicles': vehicles, 'is_guest': is_guest})

@login_required
def equipment_list(request):
    equipment = Equipment.objects.all().order_by('-id')
    equipment_list = Equipment.objects.all()  # Для фильтра
    # Фильтры
    vehicle_id = request.GET.get('vehicle')
    equipment_id = request.GET.get('equipment')
    status = request.GET.get('status')
    type_ = request.GET.get('type')
    responsible = request.GET.get('responsible')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    try:
        if vehicle_id:
            equipment = equipment.filter(installed_in_id=vehicle_id)
        if equipment_id:
            equipment = equipment.filter(id=equipment_id)
        if status:
            if status == 'sealed':
                equipment = equipment.filter(seal_datetime__isnull=False, unseal_datetime__isnull=True)
            elif status == 'unsealed':
                equipment = equipment.filter(unseal_datetime__isnull=False)
            elif status == 'none':
                equipment = equipment.filter(seal_datetime__isnull=True, unseal_datetime__isnull=True)
        if type_:
            equipment = equipment.filter(category=type_)
        if responsible:
            equipment = equipment.filter(seal_responsible__icontains=responsible)
        if date_from:
            equipment = equipment.filter(seal_datetime__gte=date_from)
        if date_to:
            equipment = equipment.filter(seal_datetime__lte=date_to)
    except ValueError:
        messages.error(request, "Invalid filter parameters provided.")
        equipment = Equipment.objects.none()

    # Экспорт данных
    export = request.GET.get('export')
    if export == 'excel':
        from datetime import datetime
        dataset = tablib.Dataset()
        dataset.headers = ['Название', 'Серийный номер', 'ТС', 'Статус пломбы']
        for e in equipment:
            if e.seal_datetime and not e.unseal_datetime:
                status = 'Пломбировано'
            elif e.unseal_datetime:
                status = 'Снята пломба'
            else:
                status = 'Без пломбы'
            dataset.append([e.name, e.serial_number, str(e.installed_in) if e.installed_in else '', status])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=equipment_report_{timestamp}.xlsx'
        return response
    elif export == 'html':
        from datetime import datetime
        html = render_to_string('TS_equipment/report_equipment_list_export.html', {'equipment': equipment})
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename=equipment_report_{timestamp}.html'
        return response

    vehicles = Vehicle.objects.all()
    responsibles = Equipment.objects.values_list('seal_responsible', flat=True).distinct()
    return render(request, 'TS_equipment/equipment_list.html', {
        'equipment': equipment,
        'equipment_list': equipment_list,
        'vehicles': vehicles,
        'responsibles': responsibles,
        'filter': {
            'vehicle_id': vehicle_id,
            'equipment_id': equipment_id,
            'status': status,
            'type': type_,
            'responsible': responsible,
            'date_from': date_from,
            'date_to': date_to,
        }
    })

@login_required
def vehicle_add(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save()
            log_vehicle_action(
                vehicle,
                action='Создание',
                user=request.user,
                details=f'ТС создано: {vehicle}'
            )
            messages.success(request, 'Транспортное средство успешно добавлено!')
            return redirect('vehicle_list')
    else:
        form = VehicleForm()
    return render(request, 'TS_equipment/vehicle_add.html', {'form': form})

@login_required
def equipment_add(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save()
            log_equipment_action(
                equipment,
                action='Создание',
                user=request.user,
                details=f'Оборудование создано: {equipment}'
            )
            messages.success(request, 'Оборудование успешно добавлено!')
            return redirect('equipment_list')
    else:
        form = EquipmentForm()
    return render(request, 'TS_equipment/equipment_add.html', {'form': form})

@login_required
def vehicle_edit(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            old_vehicle = Vehicle.objects.get(pk=pk)
            changed_fields = []
            for field in form.changed_data:
                old_val = getattr(old_vehicle, field, None)
                new_val = form.cleaned_data.get(field, None)
                label = get_field_label(field)
                changed_fields.append(f'{label}: {old_val} → {new_val}')
            form.save()
            log_vehicle_action(
                vehicle,
                action='Редактирование',
                user=request.user,
                details='; '.join(changed_fields) if changed_fields else 'Изменения не определены'
            )
            messages.success(request, 'Данные транспортного средства обновлены!')
            return redirect('vehicle_list')
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, 'TS_equipment/vehicle_add.html', {'form': form, 'edit': True, 'vehicle': vehicle})

@login_required
def equipment_edit(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        form = EquipmentForm(request.POST, instance=equipment)
        if form.is_valid():
            old_equipment = Equipment.objects.get(pk=pk)
            changed_fields = []
            for field in form.changed_data:
                old_val = getattr(old_equipment, field, None)
                new_val = form.cleaned_data.get(field, None)
                label = get_field_label(field)
                changed_fields.append(f'{label}: {old_val} → {new_val}')
            equipment = form.save()
            log_equipment_action(
                equipment,
                action='Редактирование',
                user=request.user,
                details='; '.join(changed_fields) if changed_fields else 'Изменения не определены'
            )
            return redirect('equipment_list')
    else:
        form = EquipmentForm(instance=equipment)
    return render(request, 'TS_equipment/equipment_add.html', {'form': form, 'edit': True, 'equipment': equipment})

@login_required
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        log_vehicle_action(
            vehicle,
            action='Удаление',
            user=request.user,
            details=f'ТС удалено: {vehicle}'
        )
        vehicle.delete()
        messages.success(request, 'Транспортное средство удалено!')
        return redirect('vehicle_list')
    return render(request, 'TS_equipment/vehicle_confirm_delete.html', {'vehicle': vehicle})

@login_required
def equipment_delete(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        log_equipment_action(
            equipment,
            action='Удаление',
            user=request.user,
            details=f'Оборудование удалено: {equipment}'
        )
        equipment.delete()
        messages.success(request, 'Оборудование удалено!')
        return redirect('equipment_list')
    return render(request, 'TS_equipment/equipment_confirm_delete.html', {'equipment': equipment})

@login_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    # Исправлено: сортировка по timestamp, а не по date
    logs = vehicle.logs.order_by('-timestamp')
    # --- Сохраняем просмотренное ТС в сессию ---
    recent_vehicles = request.session.get('recent_vehicles', [])
    if pk in recent_vehicles:
        recent_vehicles.remove(pk)
    recent_vehicles.insert(0, pk)
    request.session['recent_vehicles'] = recent_vehicles[:5]  # только 5 последних
    # --- конец ---
    return render(request, 'TS_equipment/vehicle_detail.html', {'vehicle': vehicle, 'logs': logs})

@login_required
def equipment_detail(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    # --- Сохраняем просмотренное оборудование в сессию ---
    recent_equipment = request.session.get('recent_equipment', [])
    if pk in recent_equipment:
        recent_equipment.remove(pk)
    recent_equipment.insert(0, pk)
    request.session['recent_equipment'] = recent_equipment[:5]  # только 5 последних
    # --- конец ---
    return render(request, 'TS_equipment/equipment_detail.html', {'equipment': equipment})

@login_required
def assign_equipment(request, pk=None):
    if pk:
        equipment = get_object_or_404(Equipment, pk=pk)
        if request.method == 'POST':
            form = EquipmentAssignForm(request.POST, instance=equipment)
            if form.is_valid():
                old_vehicle = equipment.installed_in
                equipment = form.save()
                if old_vehicle and equipment.installed_in != old_vehicle:
                    details = f'Назначено к ТС: {equipment.installed_in} (ранее: {old_vehicle})'
                elif not old_vehicle and equipment.installed_in:
                    details = f'Назначено к ТС: {equipment.installed_in}'
                else:
                    details = f'Назначено к ТС: {equipment.installed_in}'
                log_equipment_action(
                    equipment,
                    action='Назначение к ТС',
                    user=request.user,
                    details=details
                )

                if equipment.seal_responsible:
                    email = None
                    if '@' in equipment.seal_responsible:
                        email = equipment.seal_responsible
                    else:
                        fio = equipment.seal_responsible.strip().split()
                        if len(fio) >= 2:
                            last = fio[0].lower()
                            initials = ''.join([x[0].lower() for x in fio[1:]])
                            email = f"{last}.{initials}@corporate-mail.com"
                    if email:
                        send_notification_email(
                            subject='Вам назначено оборудование',
                            message=f'Вы назначены ответственным за оборудование: {equipment.name} (серийный номер: {equipment.serial_number}).',
                            recipient_list=[email],
                        )
                messages.success(request, 'Оборудование успешно привязано к ТС!')
                return redirect('equipment_list')
        else:
            form = EquipmentAssignForm(instance=equipment)
        return render(request, 'TS_equipment/assign_equipment.html', {'form': form, 'equipment': equipment})
    else:
        equipment_list = Equipment.objects.filter(installed_in__isnull=True)
        return render(request, 'TS_equipment/assign_equipment.html', {'equipment_list': equipment_list})

@login_required
def unassign_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if equipment.installed_in:
        old_vehicle = equipment.installed_in
        equipment.installed_in = None
        equipment.save()
        log_equipment_action(
            equipment,
            action='Снятие с ТС',
            user=request.user,
            details=f'Снято с ТС: {old_vehicle}'
        )
        messages.success(request, 'Оборудование успешно снято с ТС!')
    else:
        messages.info(request, 'Оборудование уже не привязано к ТС.')
    return redirect('equipment_list')

@permission_required('TS_equipment.change_equipment', raise_exception=True)
@login_required
def seal_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        class SealForm(forms.ModelForm):
            def clean(self):
                cleaned_data = super().clean()
                if not cleaned_data.get('seal_datetime'):
                    self.add_error('seal_datetime', 'Укажите дату и время пломбирования.')
                if not cleaned_data.get('seal_responsible'):
                    self.add_error('seal_responsible', 'Укажите ответственного за пломбирование.')
                return cleaned_data
            class Meta:
                model = Equipment
                fields = ['seal_datetime', 'seal_responsible']
                widgets = {
                    'seal_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
                    'seal_responsible': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО ответственного'}),
                }
        form = SealForm(request.POST)
        if form.is_valid():
            equipment.seal_datetime = form.cleaned_data['seal_datetime']
            equipment.seal_responsible = form.cleaned_data['seal_responsible']
            equipment.unseal_datetime = None
            equipment.unseal_reason = ''
            equipment.unseal_responsible = ''
            equipment.save()
            log_equipment_action(
                equipment,
                action='Пломбирование',
                user=request.user,
                details=f"Пломбирование: {equipment.seal_responsible}, дата: {equipment.seal_datetime.strftime('%d.%m.%Y %H:%M')}"
            )
            
            if equipment.seal_responsible:
                email = None
                if '@' in equipment.seal_responsible:
                    email = equipment.seal_responsible
                else:
                    fio = equipment.seal_responsible.strip().split()
                    if len(fio) >= 2:
                        last = fio[0].lower()
                        initials = ''.join([x[0].lower() for x in fio[1:]])
                        email = f"{last}.{initials}@corporate-mail.com"
                if email:
                    send_notification_email(
                        subject='Оборудование опломбировано',
                        message=f'Вы назначены ответственным за пломбирование оборудования: {equipment.name} (серийный номер: {equipment.serial_number}).',
                        recipient_list=[email],
                    )
            messages.success(request, 'Оборудование успешно опломбировано!')
            return redirect('equipment_list')
    else:
        class SealForm(forms.ModelForm):
            class Meta:
                model = Equipment
                fields = ['seal_datetime', 'seal_responsible']
                widgets = {
                    'seal_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
                    'seal_responsible': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО ответственного'}),
                }
        initial = {}
        if not equipment.seal_datetime:
            initial['seal_datetime'] = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form = SealForm(instance=equipment, initial=initial)
    return render(request, 'TS_equipment/seal_equipment.html', {'form': form, 'equipment': equipment})

@permission_required('TS_equipment.change_equipment', raise_exception=True)
@login_required
def unseal_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    class UnsealForm(forms.ModelForm):
        def clean(self):
            cleaned_data = super().clean()
            if not cleaned_data.get('unseal_reason'):
                self.add_error('unseal_reason', 'Укажите причину снятия пломбы.')
            if not cleaned_data.get('unseal_responsible'):
                self.add_error('unseal_responsible', 'Укажите ответственного за снятие пломбы.')
            return cleaned_data
        class Meta:
            model = Equipment
            fields = ['unseal_reason', 'unseal_responsible']
            widgets = {
                'unseal_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина снятия пломбы'}),
                'unseal_responsible': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО ответственного'}),
            }
    if request.method == 'POST':
        form = UnsealForm(request.POST)
        if form.is_valid():
            equipment.unseal_datetime = timezone.now()
            equipment.unseal_reason = form.cleaned_data['unseal_reason']
            equipment.unseal_responsible = form.cleaned_data['unseal_responsible']
            equipment.save()
            log_equipment_action(
                equipment,
                action='Снятие пломбы',
                user=request.user,
                details=f"Снятие пломбы: {equipment.unseal_responsible}, причина: {equipment.unseal_reason}, дата: {equipment.unseal_datetime.strftime('%d.%m.%Y %H:%M')}"
            )
            
            if equipment.unseal_responsible:
                email = None
                if '@' in equipment.unseal_responsible:
                    email = equipment.unseal_responsible
                else:
                    fio = equipment.unseal_responsible.strip().split()
                    if len(fio) >= 2:
                        last = fio[0].lower()
                        initials = ''.join([x[0].lower() for x in fio[1:]])
                        email = f"{last}.{initials}@corporate-mail.com"
                if email:
                    send_notification_email(
                        subject='Снятие пломбы с оборудования',
                        message=f'Вы назначены ответственным за снятие пломбы с оборудования: {equipment.name} (серийный номер: {equipment.serial_number}). Причина: {equipment.unseal_reason}',
                        recipient_list=[email],
                    )
            messages.success(request, 'Пломба успешно снята!')
            return redirect('equipment_list')
    else:
        form = UnsealForm()
    return render(request, 'TS_equipment/unseal_equipment.html', {'form': form, 'equipment': equipment})

@login_required
def report_equipment_list(request):
    equipment = Equipment.objects.all()
    sealed_count = 0
    unsealed_count = 0
    no_seal_count = 0
    for e in equipment:
        if e.seal_datetime and not e.unseal_datetime:
            sealed_count += 1
        elif e.unseal_datetime:
            unsealed_count += 1
        else:
            no_seal_count += 1
    export = request.GET.get('export')
    if export == 'excel':
        from datetime import datetime
        dataset = tablib.Dataset()
        dataset.headers = ['Название', 'Серийный номер', 'ТС', 'Статус пломбы']
        for e in equipment:
            if e.seal_datetime and not e.unseal_datetime:
                status = 'Пломбировано'
            elif e.unseal_datetime:
                status = 'Снята пломба'
            else:
                status = 'Без пломбы'
            dataset.append([e.name, e.serial_number, str(e.installed_in) if e.installed_in else '', status])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=equipment_report_{timestamp}.xlsx'
        return response
    elif export == 'html':
        from datetime import datetime
        html = render_to_string('TS_equipment/report_equipment_list.html', {'equipment': equipment, 'export_mode': True, 'sealed_count': sealed_count, 'unsealed_count': unsealed_count, 'no_seal_count': no_seal_count})
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename=equipment_report_{timestamp}.html'
        return response
    return render(request, 'TS_equipment/report_equipment_list.html', {'equipment': equipment, 'sealed_count': sealed_count, 'unsealed_count': unsealed_count, 'no_seal_count': no_seal_count})

@login_required
def report_equipment_history(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    logs = equipment.equipmentlog_set.all() if hasattr(equipment, 'equipmentlog_set') else EquipmentLog.objects.filter(equipment=equipment)
    logs = logs.filter(action__in=["Пломбирование", "Снятие пломбы"]).order_by('-timestamp')
    export = request.GET.get('export')
    if export == 'excel':
        from datetime import datetime
        dataset = tablib.Dataset()
        dataset.headers = ['Дата и время', 'Операция', 'Пользователь', 'Детали']
        for log in logs:
            dataset.append([
                log.timestamp.strftime('%d.%m.%Y %H:%M'),
                log.action,
                log.user,
                log.details
            ])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=equipment_history_{equipment.pk}_{timestamp}.xlsx'
        return response
    elif export == 'html':
        from datetime import datetime
        html = render_to_string('TS_equipment/report_equipment_history.html', {'equipment': equipment, 'logs': logs, 'export_mode': True})
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename=equipment_history_{equipment.pk}_{timestamp}.html'
        return response
    return render(request, 'TS_equipment/report_equipment_history.html', {'equipment': equipment, 'logs': logs})

@login_required
def report_vehicle_equipment(request):
    vehicle_id = request.GET.get('vehicle_id')
    if vehicle_id:
        vehicles = Vehicle.objects.prefetch_related('equipment').filter(id=vehicle_id)
    else:
        vehicles = Vehicle.objects.prefetch_related('equipment').all()
    export = request.GET.get('export')
    if export == 'excel':
        from datetime import datetime
        dataset = tablib.Dataset()
        dataset.headers = ['ТС', 'Модель', 'Оборудование', 'Серийный номер', 'Статус пломбы']
        for v in vehicles:
            for eq in v.equipment.all():
                if eq.seal_datetime and not eq.unseal_datetime:
                    status = 'Пломбировано'
                elif eq.unseal_datetime:
                    status = 'Снята пломба'
                else:
                    status = 'Без пломбы'
                dataset.append([
                    v.license_plate,
                    v.model,
                    eq.name,
                    eq.serial_number,
                    status
                ])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=vehicle_equipment_report_{timestamp}.xlsx'
        return response
    elif export == 'html':
        from django.template import engines
        from datetime import datetime
        django_engine = engines['django']
        template = django_engine.get_template('TS_equipment/report_equipment_plain.html')
        html = template.render({'vehicles': vehicles})
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename=vehicle_equipment_plain_{timestamp}.html'
        return response
    return render(request, 'TS_equipment/report_vehicle_equipment.html', {'vehicles': vehicles})

@login_required
def maintenance_list(request):
    records = MaintenanceRecord.objects.all().order_by('-date')
    # Фильтры для основной таблицы
    vehicle_id = request.GET.get('vehicle')
    equipment_id = request.GET.get('equipment')
    status = request.GET.get('status')
    type_ = request.GET.get('type')
    responsible = request.GET.get('responsible')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    try:
        if vehicle_id:
            records = records.filter(vehicle_id=vehicle_id)
        if equipment_id:
            records = records.filter(equipment_id=equipment_id)
        if status:
            records = records.filter(status=status)
        if type_:
            records = records.filter(type=type_)
        if responsible:
            records = records.filter(responsible__icontains=responsible)
        if date_from:
            records = records.filter(date__gte=date_from)
        if date_to:
            records = records.filter(date__lte=date_to)
    except ValueError:
        messages.error(request, "Invalid filter parameters provided.")
        records = MaintenanceRecord.objects.none()
    # Экспорт основной таблицы
    if request.GET.get('export') == 'excel':
        try:
            from datetime import datetime
            dataset = tablib.Dataset()
            dataset.headers = ['Дата', 'Тип', 'ТС', 'Оборудование', 'Пробег/наработка', 'Ответственный', 'Статус', 'Описание']
            for r in records:
                dataset.append([
                    r.date.strftime('%d.%m.%Y'),
                    dict(MaintenanceRecord.MAINTENANCE_TYPE).get(r.type, r.type),
                    str(r.vehicle) if r.vehicle else '',
                    str(r.equipment) if r.equipment else '',
                    r.mileage or '',
                    r.responsible,
                    dict(MaintenanceRecord.STATUS_CHOICES).get(r.status, r.status),
                    r.description,
                ])
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename=maintenance_records_{timestamp}.xlsx'
            return response
        except Exception as e:
            messages.error(request, f"Error exporting data: {str(e)}")
    #Фильтры и экспорт для Истории ремонтов
    repair_vehicle_id = request.GET.get('repair_vehicle')
    repair_equipment_id = request.GET.get('repair_equipment')
    repair_responsible = request.GET.get('repair_responsible')
    repair_date_from = request.GET.get('repair_date_from')
    repair_date_to = request.GET.get('repair_date_to')
    repair_history = RepairHistory.objects.all().order_by('-date')
    if repair_vehicle_id:
        repair_history = repair_history.filter(vehicle_id=repair_vehicle_id)
    if repair_equipment_id:
        repair_history = repair_history.filter(equipment_id=repair_equipment_id)
    if repair_responsible:
        repair_history = repair_history.filter(responsible__icontains=repair_responsible)
    if repair_date_from:
        repair_history = repair_history.filter(date__gte=repair_date_from)
    if repair_date_to:
        repair_history = repair_history.filter(date__lte=repair_date_to)
    if request.GET.get('repair_export') == 'excel':
        try:
            from datetime import datetime
            dataset = tablib.Dataset()
            dataset.headers = ['Дата', 'ТС', 'Оборудование', 'Ответственный', 'Пробег/наработка', 'Описание', 'Статус']
            for r in repair_history:
                dataset.append([
                    r.date.strftime('%d.%m.%Y'),
                    str(r.vehicle) if r.vehicle else '',
                    str(r.equipment) if r.equipment else '',
                    r.responsible,
                    r.mileage or '',
                    r.description,
                    dict(MaintenanceRecord.STATUS_CHOICES).get(r.status, r.status),
                ])
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename=repair_history_{timestamp}.xlsx'
            return response
        except Exception as e:
            messages.error(request, f"Error exporting repair history: {str(e)}")
    vehicles = Vehicle.objects.all()
    equipment = Equipment.objects.all()
    responsibles = MaintenanceRecord.objects.values_list('responsible', flat=True).distinct()
    repair_responsibles = RepairHistory.objects.values_list('responsible', flat=True).distinct()
    return render(request, 'TS_equipment/maintenance_list.html', {
        'records': records,
        'repair_history': repair_history,
        'vehicles': vehicles,
        'equipment_list': equipment,
        'responsibles': responsibles,
        'repair_responsibles': repair_responsibles,
        'filter': {
            'vehicle_id': vehicle_id,
            'equipment_id': equipment_id,
            'status': status,
            'type': type_,
            'responsible': responsible,
            'date_from': date_from,
            'date_to': date_to,
        },
        'repair_filter': {
            'repair_vehicle_id': repair_vehicle_id,
            'repair_equipment_id': repair_equipment_id,
            'repair_responsible': repair_responsible,
            'repair_date_from': repair_date_from,
            'repair_date_to': repair_date_to,
        }
    })

@login_required
def maintenance_add(request):
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save()
            update_object_condition_by_maintenance(record)
            return redirect('maintenance_list')
    else:
        form = MaintenanceRecordForm()
    return render(request, 'TS_equipment/maintenance_form.html', {'form': form})

@login_required
def maintenance_edit(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        form = MaintenanceRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            record = form.save()
            update_object_condition_by_maintenance(record)
            return redirect('maintenance_list')
    else:
        form = MaintenanceRecordForm(instance=record)
    return render(request, 'TS_equipment/maintenance_form.html', {'form': form, 'edit': True, 'record': record})

@login_required
def maintenance_delete(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Запись ТОиР удалена!')
        return redirect('maintenance_list')
    return render(request, 'TS_equipment/maintenance_confirm_delete.html', {'record': record})

@login_required
def maintenance_detail(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    return render(request, 'TS_equipment/maintenance_detail.html', {'record': record})

@login_required
def maintenance_report_repair(request):
    repairs = RepairHistory.objects.all().order_by('-date')
    # Можно сгруппировать по ТС или оборудованию, если нужно
    # Экспорт в Excel
    if request.GET.get('export') == 'excel':
        from datetime import datetime
        import tablib
        dataset = tablib.Dataset()
        dataset.headers = ['Дата', 'Тип', 'ТС', 'Оборудование', 'Пробег/наработка', 'Ответственный', 'Статус', 'Описание']
        for r in repairs:
            dataset.append([
                r.date.strftime('%d.%m.%Y'),
                dict(MaintenanceRecord.MAINTENANCE_TYPE).get(r.type, r.type),
                str(r.vehicle) if r.vehicle else '',
                str(r.equipment) if r.equipment else '',
                r.mileage or '',
                r.responsible,
                dict(MaintenanceRecord.STATUS_CHOICES).get(r.status, r.status),
                r.description,
            ])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=repair_history_{timestamp}.xlsx'
        return response
    return render(request, 'TS_equipment/maintenance_report_repair.html', {'repairs': repairs})

def log_equipment_action(equipment, action, user=None, details=None):
    EquipmentLog.objects.create(
        equipment=equipment,
        action=action,
        user=user.username if user and hasattr(user, 'username') else (str(user) if user else ''),
        details=details or ''
    )

def log_vehicle_action(vehicle, action, user=None, details=None):
    from .models import VehicleLog
    VehicleLog.objects.create(
        vehicle=vehicle,
        action=action,
        user=user.username if user and hasattr(user, 'username') else (str(user) if user else ''),
        details=details or ''
    )

def update_object_condition_by_maintenance(record):
    """
    Автоматически обновляет поля repair_date/maintenance_date и is_operable у Equipment/Vehicle
    в зависимости от статуса и типа ТОиР.
    """
    obj = record.equipment or record.vehicle
    if obj is None:
        return
    # Сброс дат ТО/ремонта
    if hasattr(obj, 'repair_date'):
        obj.repair_date = None
    if hasattr(obj, 'maintenance_date'):
        obj.maintenance_date = None

    # Для оборудования
    if hasattr(obj, 'is_operable'):
        if record.status in ('in_progress', 'planned'):
            if record.type == 'repair':
                obj.is_operable = 'in_repair'
                if hasattr(obj, 'repair_date'):
                    obj.repair_date = record.date
            elif record.type == 'maintenance':
                obj.is_operable = 'on_maintenance'
                if hasattr(obj, 'maintenance_date'):
                    obj.maintenance_date = record.date
        elif record.status in ('done', 'cancelled'):
            obj.is_operable = 'operable'
        elif record.status == 'postponed':
            obj.is_operable = 'unknown'
    else:
        # Для ТС 
        if record.status in ('in_progress', 'planned'):
            if record.type == 'repair' and hasattr(obj, 'repair_date'):
                obj.repair_date = record.date
            elif record.type == 'maintenance' and hasattr(obj, 'maintenance_date'):
                obj.maintenance_date = record.date
    obj.save()

    for equipment in Equipment.objects.all():
        equipment.update_operability_status()

@login_required
def maintenance_preview(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    data = {
        'type': record.type,
        'type_display': record.get_type_display(),
        'date': record.date.strftime('%d.%m.%Y'),
        'vehicle': str(record.vehicle) if record.vehicle else '',
        'equipment': str(record.equipment) if record.equipment else '',
        'mileage': record.mileage,
        'responsible': record.responsible,
        'status': record.status,
        'status_display': record.get_status_display(),
        'description': record.description,
    }
    return JsonResponse(data)

@login_required
def equipment_log_delete(request, log_id):
    log = get_object_or_404(EquipmentLog, pk=log_id)
    equipment_pk = log.equipment.pk
    if request.method == 'POST':
        log.delete()
        messages.success(request, 'Запись журнала удалена!')
        return redirect('equipment_detail', pk=equipment_pk)
    return render(request, 'TS_equipment/equipment_log_confirm_delete.html', {'log': log})

@login_required
def report_equipment_log(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    logs = equipment.logs.all().order_by('-timestamp')
    export = request.GET.get('export')
    if export == 'excel':
        from datetime import datetime
        dataset = tablib.Dataset()
        dataset.headers = ['Дата и время', 'Операция', 'Детали']
        for log in logs:
            dataset.append([
                log.timestamp.strftime('%d.%m.%Y %H:%M'),
                log.action,
                log.details
            ])
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(dataset.export('xlsx'), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=equipment_log_{equipment.pk}_{timestamp}.xlsx'
        return response
    elif export == 'html':
        from datetime import datetime
        html = render_to_string('TS_equipment/report_equipment_log.html', {'equipment': equipment, 'logs': logs, 'export_mode': True})
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename=equipment_log_{equipment.pk}_{timestamp}.html'
        return response
    return render(request, 'TS_equipment/report_equipment_log.html', {'equipment': equipment, 'logs': logs})

@login_required
def maintenance_mark_done(request, pk):
    record = get_object_or_404(MaintenanceRecord, pk=pk)
    if request.method == 'POST' and record.status != 'done':
        from .models import RepairHistory
        RepairHistory.objects.create(
            equipment=record.equipment,
            vehicle=record.vehicle,
            type=record.type,
            date=record.date,
            mileage=record.mileage,
            description=record.description,
            responsible=record.responsible,
            cost=record.cost,
            status='done',
            file=record.file
        )
        # Устанавливаем статус исправности
        obj = record.equipment or record.vehicle
        if obj and hasattr(obj, 'is_operable'):
            obj.is_operable = 'operable'
            obj.save()
        record.delete()
        return redirect('maintenance_list')
    return redirect('maintenance_list')

@login_required
def repair_history_detail(request, pk):
    record = get_object_or_404(RepairHistory, pk=pk)
    return render(request, 'TS_equipment/repair_history_detail.html', {'record': record})

@login_required
@require_POST
def repair_history_delete(request, pk):
    record = get_object_or_404(RepairHistory, pk=pk)
    record.delete()
    return redirect('maintenance_list')

@login_required
def vehicle_log_delete(request, log_id):
    from .models import VehicleLog
    log = get_object_or_404(VehicleLog, pk=log_id)
    vehicle_pk = log.vehicle.pk
    if request.method == 'POST':
        log.delete()
        messages.add_message(request, messages.SUCCESS, 'Запись журнала ТС удалена!', extra_tags='vehiclelog')
        return redirect('vehicle_detail', pk=vehicle_pk)
    return render(request, 'TS_equipment/vehicle_log_confirm_delete.html', {'log': log})

@login_required
def test_email(request):
    if request.method == 'POST':
        subject = 'Тестовое письмо'
        message = 'Это тестовое письмо для проверки отправки почты из Django.'
        recipient = request.user.email or settings.EMAIL_HOST_USER
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False)
            messages.success(request, f'Письмо отправлено на {recipient}')
        except Exception as e:
            messages.error(request, f'Ошибка отправки: {e}')
        return redirect('dashboard')
    return render(request, 'TS_equipment/test_email.html')

def guest_login(request):
    User = get_user_model()
    guest_group_name = 'Гость'
    # Генерируем уникальный username
    while True:
        random_suffix = ''.join(random.choices(string.digits, k=6))
        guest_username = f'guest_{random_suffix}'
        if not User.objects.filter(username=guest_username).exists():
            break
    guest = User.objects.create(
        username=guest_username,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    guest.set_unusable_password()
    guest.save()
    # Добавить в группу "Гость"
    group, _ = Group.objects.get_or_create(name=guest_group_name)
    guest.groups.add(group)
    login(request, guest)
    return redirect('/')
