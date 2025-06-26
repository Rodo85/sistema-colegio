# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Institucion, Miembro

# ----------- Institución -----------
@admin.register(Institucion)
class InstitucionAdmin(admin.ModelAdmin):
    list_display  = ("nombre", "tipo", "correo", "telefono", "fecha_inicio", "fecha_fin", "activa")
    search_fields = ("nombre", "correo")
    list_filter   = ("tipo", "fecha_fin")

    @admin.display(boolean=True, description="Licencia activa")
    def activa(self, obj):
        return obj.activa


# ----------- Miembro  (usuario en colegio) -----------
@admin.register(Miembro)
class MiembroAdmin(admin.ModelAdmin):
    list_display  = ("usuario", "institucion", "rol")
    list_filter   = ("rol", "institucion")
    search_fields = ("usuario__email", "institucion__nombre")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Información personal"), {"fields": ("first_name", "last_name")}),
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
    list_display = ("email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)