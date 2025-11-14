from django import template

register = template.Library()

@register.filter(name='add_attr')
def add_attr(field, attr_string):
    
    attrs = {}
    for definition in attr_string.split(","):
        if "=" in definition:
            key, value = definition.split("=", 1)
            attrs[key.strip()] = value.strip()

    return field.as_widget(attrs=attrs)
