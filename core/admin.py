# core/admin.py
from django.contrib import admin
from django.contrib.auth.models import Permission
from .models import Miembro, Institucion, SolicitudRegistro, User
from core.mixins import InstitucionScopedAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from config_institucional.models import Profesor
from core.forms import PendingAwareAdminAuthenticationForm
from core.views import aprobar_solicitud_registro, rechazar_solicitud_registro
# ----------- Institución -----------
@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "tipo", "correo", "matricula_activa", "es_institucion_general", "max_asignaciones_general", "telefono", "fecha_inicio", "fecha_fin", "activa")
    search_fields = ("nombre", "correo")
    list_filter   = ("tipo", "matricula_activa", "es_institucion_general", "fecha_fin")
    fields = (
        "nombre", "tipo", "correo", "telefono", "direccion",
        "fecha_inicio", "fecha_fin", "logo",
        "matricula_activa", "es_institucion_general", "max_asignaciones_general",
        "whatsapp_phone", "whatsapp_from_id", "whatsapp_token",
    )
    # Ambas fechas editables; si deseas mantenerlas iguales, la lógica se maneja en save()
    readonly_fields = ()

    @admin.display(boolean=True, description="Licencia activa")
    def activa(self, obj):
        return obj.activa


# ----------- Miembro  (usuario en colegio) -----------
@admin.register(Miembro)
class MiembroAdmin(InstitucionScopedAdmin):
    list_display  = ("usuario", "rol", "institucion")
    list_filter   = ("rol",)
    search_fields = ("usuario__email", "usuario__first_name", "usuario__last_name")
    fields        = ("institucion", "usuario", "rol")

    # --- limitar institución solo a directores ---
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if (
            db_field.name == "institucion"
            and not request.user.is_superuser            # ← nueva condición
        ):
            kwargs["queryset"] = Institucion.objects.filter(
                id=request.institucion_activa_id
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # --- superuser puede elegir libremente; director la ve readonly ---
    def get_readonly_fields(self, request, obj=None):
        return () if request.user.is_superuser else ("institucion",)

    @staticmethod
    def _identificacion_auto_docente(user):
        base = f"AUTO{str(user.id).replace('-', '')[:12]}".upper()
        return base[:20]

    def _asegurar_perfil_docente(self, request, miembro):
        if miembro.rol != Miembro.DOCENTE:
            return

        profesor = Profesor.objects.filter(
            institucion=miembro.institucion,
            usuario=miembro.usuario,
        ).first()
        if profesor is None:
            Profesor.objects.create(
                institucion=miembro.institucion,
                usuario=miembro.usuario,
                identificacion=self._identificacion_auto_docente(miembro.usuario),
                telefono="",
            )
            self.message_user(
                request,
                "Se creó automáticamente el perfil de docente en la institución seleccionada.",
            )

        perm_libro = Permission.objects.filter(
            codename="access_libro_docente",
            content_type__app_label="libro_docente",
        ).first()
        if perm_libro:
            miembro.usuario.user_permissions.add(perm_libro)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._asegurar_perfil_docente(request, obj)

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Información personal"), {"fields": ("first_name", "last_name","second_last_name")}),
        (_("Estado de cuenta"), {"fields": ("estado_solicitud",)}),
        (_("Permisos"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        (_("Fechas importantes"), {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2"),
        }),
    )
    list_display = ("email", "first_name", "last_name","second_last_name","estado_solicitud", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)
    
    def clean_email(self, email):
        """Validar que el email no esté duplicado"""
        from django.core.exceptions import ValidationError
        
        if User.objects.filter(email=email).exists():
            raise ValidationError(f"Ya existe un usuario con el email '{email}'")
        return email
    
    def save_model(self, request, obj, form, change):
        """Validar email antes de guardar"""
        if not change:  # Solo para usuarios nuevos
            try:
                self.clean_email(obj.email)
            except ValidationError as e:
                from django.contrib import messages
                messages.error(request, str(e))
                return
        
        super().save_model(request, obj, form, change)


@admin.register(SolicitudRegistro)
class SolicitudRegistroAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "telefono_whatsapp",
        "institucion_solicitada",
        "estado",
        "fecha_solicitud",
        "revisado_por",
        "fecha_revision",
    )
    list_filter = ("estado", "institucion_solicitada", "fecha_solicitud")
    search_fields = ("usuario__email", "usuario__first_name", "usuario__last_name")
    readonly_fields = ("fecha_solicitud", "fecha_revision", "revisado_por")
    fields = (
        "usuario",
        "telefono_whatsapp",
        "institucion_solicitada",
        "mensaje",
        "comprobante_pago",
        "estado",
        "motivo_revision",
        "fecha_solicitud",
        "revisado_por",
        "fecha_revision",
    )
    actions = ("aprobar", "rechazar")

    def save_model(self, request, obj, form, change):
        """
        Permite aprobar/rechazar también desde el formulario de detalle:
        si cambian el estado manualmente, ejecuta el flujo completo
        (activar usuario, crear membresía/permisos/notificación).
        """
        if change:
            previo = SolicitudRegistro.objects.filter(pk=obj.pk).first()
            if previo and previo.estado != obj.estado:
                if obj.estado == SolicitudRegistro.APROBADA:
                    aprobar_solicitud_registro(obj, request.user)
                    self.message_user(request, "Solicitud aprobada y usuario activado.")
                    return
                if obj.estado == SolicitudRegistro.RECHAZADA:
                    rechazar_solicitud_registro(
                        obj,
                        request.user,
                        motivo=obj.motivo_revision or "",
                    )
                    self.message_user(request, "Solicitud rechazada y notificada.")
                    return
        super().save_model(request, obj, form, change)

    @admin.action(description="Aprobar solicitudes seleccionadas")
    def aprobar(self, request, queryset):
        total = 0
        for solicitud in queryset.select_related("usuario"):
            if solicitud.estado == SolicitudRegistro.PENDIENTE:
                aprobar_solicitud_registro(solicitud, request.user)
                total += 1
        self.message_user(request, f"Solicitudes aprobadas: {total}")

    @admin.action(description="Rechazar solicitudes seleccionadas")
    def rechazar(self, request, queryset):
        total = 0
        for solicitud in queryset.select_related("usuario"):
            if solicitud.estado == SolicitudRegistro.PENDIENTE:
                rechazar_solicitud_registro(
                    solicitud,
                    request.user,
                    motivo=solicitud.motivo_revision or "",
                )
                total += 1
        self.message_user(request, f"Solicitudes rechazadas: {total}")


admin.site.login_form = PendingAwareAdminAuthenticationForm