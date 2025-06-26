from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from core.models import Institucion

def seleccionar_institucion(request):
    """
    Pantalla para elegir colegio.  Maneja 3 casos:

    1) El usuario NO tiene membresías   → solo muestra aviso + botón «Salir».
    2) Tiene exactamente 1 y está activa → la selecciona automáticamente.
    3) Tiene varias                    → muestra el formulario de selección.
    """
    user = request.user
    # 0. Superusuario no pasa por aquí
    if user.is_superuser:
        return redirect("admin:index")

    membresias = user.membresias.select_related("institucion")

    # 1) Sin membresías --------------► renderizar aviso
    if not membresias.exists():
        return render(
            request,
            "core/seleccionar_institucion.html",
            {"membresias": []}
        )

    # 2) Una sola membresía activa ----► autoselección
    if membresias.count() == 1:
        inst = membresias.first().institucion
        if inst.activa:
            request.session["institucion_id"] = inst.id
            return redirect("admin:index")

    # 3) Varias membresías -------------► formulario
    if request.method == "POST":
        inst_id = request.POST.get("institucion_id")
        if inst_id:
            request.session["institucion_id"] = inst_id
            return redirect("admin:index")
        # Si llegó aquí es porque pulsó «Entrar» sin elegir
        messages.error(request, _("Debe seleccionar una institución."))

    return render(
        request,
        "core/seleccionar_institucion.html",
        {"membresias": membresias}
    )
