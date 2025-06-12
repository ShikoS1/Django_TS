from django import forms
from .models import Vehicle, Equipment, MaintenanceRecord

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['category', 'license_plate', 'model', 'manufacturer', 'year', 'vin', 'color', 'note']
        labels = {
            'category': 'Категория',
            'license_plate': 'Гос. номер',
            'model': 'Модель',
            'manufacturer': 'Производитель',
            'year': 'Год выпуска',
            'vin': 'VIN',
            'color': 'Цвет',
            'note': 'Примечание',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите гос. номер'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите модель'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите производителя'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите год выпуска'}),
            'vin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите VIN'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите цвет'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Примечание', 'rows': 2}),
        }

class EquipmentForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super().clean()
        # Пломбирование
        seal_datetime = cleaned_data.get('seal_datetime')
        seal_responsible = cleaned_data.get('seal_responsible')
        # Снятие пломбы
        unseal_datetime = cleaned_data.get('unseal_datetime')
        unseal_reason = cleaned_data.get('unseal_reason')
        unseal_responsible = cleaned_data.get('unseal_responsible')
        errors = {}
        if seal_datetime and not seal_responsible:
            errors['seal_responsible'] = 'Укажите ответственного за пломбирование.'
        if unseal_datetime:
            if not unseal_reason:
                errors['unseal_reason'] = 'Укажите причину снятия пломбы.'
            if not unseal_responsible:
                errors['unseal_responsible'] = 'Укажите ответственного за снятие пломбы.'
        if errors:
            raise forms.ValidationError(errors)
        return cleaned_data

    class Meta:
        model = Equipment
        fields = [
            'name', 'serial_number', 'category', 'description', 'installed_date',
            'seal_datetime', 'seal_responsible',
            'unseal_datetime', 'unseal_reason', 'unseal_responsible',
            'unscheduled_seal_date', 'unscheduled_seal_reason',
            'maintenance_date', 'maintenance_reason',
            'repair_date', 'repair_reason',
        ]
        labels = {
            'name': 'Название',
            'serial_number': 'Серийный номер',
            'category': 'Категория',
            'description': 'Описание',
            'installed_date': 'Дата установки',
            'seal_datetime': 'Дата и время пломбирования',
            'seal_responsible': 'Ответственный за пломбирование',
            'unseal_datetime': 'Дата и время снятия пломбы',
            'unseal_reason': 'Причина снятия пломбы',
            'unseal_responsible': 'Ответственный за снятие пломбы',
            'unscheduled_seal_date': 'Дата внепланового пломбирования',
            'unscheduled_seal_reason': 'Причина внепланового пломбирования',
            'maintenance_date': 'Дата технического обслуживания',
            'maintenance_reason': 'Причина технического обслуживания',
            'repair_date': 'Дата ремонта',
            'repair_reason': 'Причина ремонта',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите серийный номер'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Описание', 'rows': 2}),
            'installed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'seal_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'seal_responsible': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО ответственного'}),
            'unseal_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'unseal_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина снятия пломбы'}),
            'unseal_responsible': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО ответственного'}),
            'unscheduled_seal_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'unscheduled_seal_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина внепланового пломбирования'}),
            'maintenance_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'maintenance_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина ТО'}),
            'repair_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'repair_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина ремонта'}),
        }

class EquipmentAssignForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['installed_in']
        labels = {'installed_in': 'Транспортное средство'}
        widgets = {
            'installed_in': forms.Select(attrs={'class': 'form-select'}),
        }

class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRecord
        fields = [
            'equipment', 'vehicle', 'type', 'date', 'mileage', 'description',
            'responsible', 'cost', 'status', 'file'
        ]
        labels = {
            'equipment': 'Оборудование',
            'vehicle': 'ТС',
            'type': 'Тип работ',
            'date': 'Дата работ',
            'mileage': 'Пробег/наработка',
            'description': 'Описание работ',
            'responsible': 'Ответственный',
            'cost': 'Стоимость',
            'status': 'Статус',
            'file': 'Документ',
        }
        widgets = {
            'equipment': forms.Select(attrs={'class': 'form-select'}),
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mileage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Пробег/наработка'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Описание работ'}),
            'responsible': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО ответственного'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Стоимость'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
