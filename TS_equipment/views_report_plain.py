from django.template import Template, Context
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Vehicle
import codecs
import os

@login_required
def report_vehicle_equipment_plain(request):
    vehicles = Vehicle.objects.prefetch_related('equipment').all()
    from datetime import datetime
    # Абсолютный путь к шаблону plain
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'TS_equipment', 'report_equipment_plain.html')
    with codecs.open(template_path, encoding='utf-8') as f:
        template_string = f.read()
    template = Template(template_string)
    html = template.render(Context({'vehicles': vehicles}))
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    response = HttpResponse(html, content_type='text/html')
    response['Content-Disposition'] = f'attachment; filename=vehicle_equipment_plain_{timestamp}.html'
    return response
