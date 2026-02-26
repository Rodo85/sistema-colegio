# core/admin.py
from django.contrib import admin
from .models import Miembro, Institucion, SolicitudRegistro, User
from core.mixins import InstitucionScopedAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
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