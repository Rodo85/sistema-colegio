# core/templatetags/admin_extras.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def user_role(context):
    """
    Devuelve el rol del usuario en la institución activa,
    o 'Superadministrador' si es superuser.
    """
    request = context["request"]
    user = request.user
    if user.is_superuser:
        return "Superadministrador"
    # busca la membresía en la institución activa
    membresia = user.membresias.filter(
        institucion_id=request.institucion_activa_id
    ).first()
    return membresia.get_rol_display() if membresia else ""
