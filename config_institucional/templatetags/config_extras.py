from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter para obtener un valor de un diccionario usando una clave.
    Uso: {{ dictionary|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
