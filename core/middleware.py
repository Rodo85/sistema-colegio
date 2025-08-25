from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from core.models import Institucion


class InstitucionMiddleware(MiddlewareMixin):

    def __call__(self, request):
        request.institucion_activa_id = None
        user = getattr(request, "user", None)

        if request.path.startswith("/admin/logout/"):
            request.session.pop("institucion_id", None)
            return self.get_response(request)
            
        # ── 1. Superadmin: pasa directo ──────────────────────────────
        if user and user.is_authenticated and user.is_superuser:
            return self.get_response(request)
        
        # ── 2. Usuario autenticado normal ────────────────────────────
        if user and user.is_authenticated:
            try:
                inst_id = request.session.get("institucion_id")

                if inst_id:                                              # ya había elegido
                    inst = Institucion.objects.filter(pk=inst_id).first()
                    if inst and inst.activa:
                        request.institucion_activa_id = inst_id
                    else:                                                # licencia expirada
                        request.session.pop("institucion_id", None)
                        inst_id = None

                # Si no hay institución válida, ver cuántas membresías tiene
                if request.institucion_activa_id is None:
                    membresias = user.membresias.select_related("institucion")

                    # 2a. Solo 1 colegio → lo asigna automáticamente
                    if membresias.count() == 1:
                        inst = membresias.first().institucion
                        if inst.activa:
                            request.session["institucion_id"] = inst.pk
                            request.institucion_activa_id = inst.pk

                    # 2b. Más de 1 colegio o ninguno válido → forzar selección
                    if request.institucion_activa_id is None and request.path != "/seleccionar-institucion/":
                        return redirect("seleccionar_institucion")
            except Exception as e:
                # Log del error para debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error en InstitucionMiddleware: {e}")
                # Continuar sin institución activa

        # ── 3. Continuar la cadena de middlewares / vista ────────────
        return self.get_response(request)
