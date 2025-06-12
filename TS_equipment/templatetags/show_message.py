from django import template

register = template.Library()

@register.filter
def show_message(message, request):
    if hasattr(message, 'extra_tags'):
        if message.extra_tags == 'vehiclelog':
            return 'vehicle_detail' in getattr(request.resolver_match, 'url_name', '')
        elif message.extra_tags:
            return 'equipment_detail' in getattr(request.resolver_match, 'url_name', '')
    return True
