from django import template

register = template.Library()

@register.filter
def format_date(value, fmt):
    if not value:
        return ''
    try:
        mapping = {
            'MM/DD/YYYY': '%m/%d/%Y',
            'DD/MM/YYYY': '%d/%m/%Y',
            'YYYY-MM-DD': '%Y-%m-%d',
        }
        py_fmt = mapping.get(fmt, '%m/%d/%Y')
        return value.strftime(py_fmt)
    except Exception:
        return value

@register.filter
def format_number(value, fmt):
    if value is None:
        return ''
    try:
        formatted = f"{float(value):,.2f}"
        if fmt == '1.000,00':
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except Exception:
        return value