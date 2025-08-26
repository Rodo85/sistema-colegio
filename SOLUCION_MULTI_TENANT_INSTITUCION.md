# Solución multi-tenant por institución (actualizada)

Este documento describe la solución integral aplicada para asegurar que la institución activa del usuario se respete en todo el sistema (admin, vistas y validaciones de modelos), con énfasis en los formularios del admin donde usuarios no superadministradores no deben elegir la institución manualmente.

## Problema
- Con usuarios no superadministradores, algunos formularios del admin no enviaban el campo `institucion` en el POST.
- Los modelos ejecutaban `clean()` y fallaban con mensajes como “Debe seleccionar una institución.” o `RelatedObjectDoesNotExist … has no institucion` porque la instancia aún no tenía `institucion` al validar.
- En la UI, el campo “Institución” aparecía como solo lectura o ni siquiera se renderizaba un `<input>`, por lo que nunca llegaba al servidor.

## Causa raíz
- En ciertos `ModelAdmin`, el campo `institucion` estaba fuera de `fields/fieldsets` para usuarios normales o marcado como read‑only, y por tanto no se incluía en el formulario.
- La validación de modelos accedía a relaciones (`self.institucion`) en vez de usar los sufijos `_id` cuando la relación todavía no estaba cargada.

## Solución aplicada

### 1) Mixin y contexto de institución
- `core/mixins.InstitucionScopedAdmin` filtra listados por `request.institucion_activa_id`, fija iniciales y, como red de seguridad, asigna `obj.institucion_id` en `save_model` cuando aplica.
- `core/middleware.InstitucionMiddleware` garantiza `request.institucion_activa_id` a partir de sesión o membresías.

### 2) Formularios del admin: inyección de institución
Se ajustaron los admins en `config_institucional/admin.py` para los tres modelos:
- `EspecialidadCursoLectivoAdmin`
- `SeccionCursoLectivoAdmin`
- `SubgrupoCursoLectivoAdmin`

Cambios clave por cada admin:
- Incluir siempre el campo `institucion` en `fields/fieldsets` también para usuarios no superusuarios, para que el formulario lo procese. El campo se oculta vía `widget = HiddenInput` en `get_form`.
- En `get_form` se envuelve la clase de formulario (p. ej. `FormWithInst`) para:
  - Ocultar `institucion` para usuarios no superusuarios.
  - Inyectar el valor activo en el POST si faltaba:
    - Si el form viene ligado (POST), se copia `self.data`, se calcula `key = self.add_prefix('institucion')` y se asigna `institucion_id` cuando no exista.
    - Si es un GET inicial, se configura `self.initial['institucion']`.
  - Antes de cualquier validación, se fija la relación en la instancia:
    - `self.instance.institucion_id = request.institucion_activa_id` (también repetido en `clean()` del form como refuerzo).
- `formfield_for_foreignkey` limita el queryset de `institucion` a la activa y establece `initial` para evitar que widgets JS/autocomplete la alteren.
- `save_model` mantiene una última red de seguridad: asigna `obj.institucion_id = request.institucion_activa_id` para usuarios no superusuarios.
- Se eliminaron estados read‑only sobre `institucion` en estos admins para permitir que el `<input hidden>` se envíe al servidor.

### 3) Validaciones de modelos más robustas
En `config_institucional/models.py`:
- En `clean()` de `EspecialidadCursoLectivo`, `SeccionCursoLectivo` y `SubgrupoCursoLectivo` se reemplazó el acceso a relaciones por sufijos `_id`:
  - `if not self.curso_lectivo_id: …`
  - `if not self.institucion_id: …`
Así se evita `RelatedObjectDoesNotExist` durante la validación cuando la relación aún no está resuelta.

### 4) Otros lugares relevantes ya cubiertos
- `matricula/admin.py` (Estudiante): se excluye `institucion` del formulario de usuarios normales y se asigna en `save_model` usando `request.institucion_activa_id`.
- `catalogos/admin.py` (`SubAreaInstitucionAdmin`): misma estrategia (oculto + inyección + save_model) para que usuarios normales no elijan la institución.

## Patrón a reutilizar (checklist)
Para cualquier `ModelAdmin` con FK `institucion` que deba fijarse automáticamente:
1. Incluir `institucion` en `fields/fieldsets` para todos los usuarios.
2. En `get_form`:
   - Ocultar el campo para usuarios normales.
   - Inyectar el valor en `self.data[self.add_prefix('institucion')]` cuando el form esté ligado y no exista.
   - Establecer `self.initial['institucion']` en GET.
   - Fijar `self.instance.institucion_id = request.institucion_activa_id` antes de `clean()`.
3. En `formfield_for_foreignkey`, limitar `institucion` al queryset de la activa y poner `initial`.
4. No marcar `institucion` como read‑only para usuarios normales; si se desea impedir edición, úsese el hidden widget.
5. En `save_model`, volver a asignar `obj.institucion_id = request.institucion_activa_id` para asegurar persistencia.
6. En `clean()` del modelo, preferir `_id` para validaciones de presencia.

## Verificación
- Iniciar sesión con usuario no superadministrador que tenga exactamente una membresía activa.
- Probar en admin:
  - Agregar “Especialidad por curso lectivo”.
  - Agregar “Sección por curso lectivo”.
  - Agregar “Subgrupo por curso lectivo”.
- Confirmar que el campo “Institución” no requiere interacción del usuario, no muestra error y se guarda correctamente.

## Notas
- Esta estrategia evita depender de input visibles y resiste widgets JS (autocomplete/select2) que no envían el valor si no hay interacción.
- Mantener `InstitucionMiddleware` y contexto de sesión consistentes (`request.institucion_activa_id`).
