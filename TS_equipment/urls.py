from django.contrib.auth.views import LoginView
from django.urls import path
from . import views
from .views_report_plain import report_vehicle_equipment_plain

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    # Маршруты для транспорта
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_add, name='vehicle_add'),
    path('vehicles/<int:pk>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicles/<int:pk>/delete/', views.vehicle_delete, name='vehicle_delete'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('vehicles/log/<int:log_id>/delete/', views.vehicle_log_delete, name='vehicle_log_delete'),

    # Маршруты для оборудования
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/add/', views.equipment_add, name='equipment_add'),
    path('equipment/<int:pk>/edit/', views.equipment_edit, name='equipment_edit'),
    path('equipment/<int:pk>/delete/', views.equipment_delete, name='equipment_delete'),
    path('equipment/<int:pk>/', views.equipment_detail, name='equipment_detail'),
    path('equipment/<int:pk>/unassign/', views.unassign_equipment, name='unassign_equipment'),
    path('equipment/<int:pk>/seal/', views.seal_equipment, name='seal_equipment'),
    path('equipment/<int:pk>/unseal/', views.unseal_equipment, name='unseal_equipment'),

    # Маршрут для назначения оборудования
    path('assign/<int:pk>/', views.assign_equipment, name='assign_equipment'),
    path('assign/', views.assign_equipment, name='assign_equipment'),

    # Маршруты для отчетов
    path('reports/equipment/', views.report_equipment_list, name='report_equipment_list'),
    path('reports/equipment/<int:pk>/history/', views.report_equipment_history, name='report_equipment_history'),
    path('reports/vehicles/', views.report_vehicle_equipment, name='report_vehicle_equipment'),
    path('reports/vehicles/plain/', report_vehicle_equipment_plain, name='report_vehicle_equipment_plain'),
    path('reports/maintenance/repair/', views.maintenance_report_repair, name='maintenance_report_repair'),

    # Маршруты для ТОиР
    path('maintenance/', views.maintenance_list, name='maintenance_list'),
    path('maintenance/add/', views.maintenance_add, name='maintenance_add'),
    path('maintenance/<int:pk>/edit/', views.maintenance_edit, name='maintenance_edit'),
    path('maintenance/<int:pk>/delete/', views.maintenance_delete, name='maintenance_delete'),
    path('maintenance/<int:pk>/', views.maintenance_detail, name='maintenance_detail'),
    path('maintenance/<int:pk>/preview/', views.maintenance_preview, name='maintenance_preview'),
    path('maintenance/<int:pk>/done/', views.maintenance_mark_done, name='maintenance_mark_done'),

    # Маршруты для журналов оборудования
    path('equipment/log/<int:log_id>/delete/', views.equipment_log_delete, name='equipment_log_delete'),
    path('reports/equipment/<int:pk>/log/', views.report_equipment_log, name='report_equipment_log'),

    # Маршруты для истории ремонтов
    path('repair-history/<int:pk>/', views.repair_history_detail, name='repair_history_detail'),
    path('repair-history/<int:pk>/delete/', views.repair_history_delete, name='repair_history_delete'),

    # Маршруты для администрирования
    path('admin/login/', LoginView.as_view(template_name='TS_equipment/login.html', redirect_authenticated_user=False, next_page='/'), name='login'),

    # Тестовый маршрут для отправки почты
    path('test-email/', views.test_email, name='test_email'),
]
