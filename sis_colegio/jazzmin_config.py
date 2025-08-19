# Configuración personalizada de Jazzmin para el menú principal
# Este archivo define los iconos y configuraciones del menú lateral

JAZZMIN_SETTINGS = {
    "copyright": "Ing. Rodolfo Garro Monge",
    "welcome_sign": "Sistema Integral de Gestión Administrativa y Educativa",
    "site_title": "Cole Smart",
    "site_header": "Cole Smart",
    "site_brand": "Cole Smart",
    
    # Configuración del menú principal
    "order_with_respect_to": [
        "core",
        "matricula", 
        "catalogos",
        "config_institucional",
        "auth",
    ],
    
    # Iconos personalizados para las aplicaciones
    "icons": {
        # Core y autenticación
        "core.user": "fas fa-users",
        "core.institucion": "fas fa-university",
        "core.membresia": "fas fa-user-tie",
        "auth.group": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield",
        
        # Matrícula
        "matricula.estudiante": "fas fa-user-graduate",
        "matricula.personacontacto": "fas fa-address-book",
        "matricula.encargadoestudiante": "fas fa-user-friends",
        "matricula.matriculaacademica": "fas fa-clipboard-list",
        "matricula.plantillaimpresionmatricula": "fas fa-file-alt",
        
        # Catálogos globales
        "catalogos.adecuacion": "fas fa-wheelchair",
        "catalogos.canton": "fas fa-map-marker-alt",
        "catalogos.distrito": "fas fa-map-pin",
        "catalogos.escolaridad": "fas fa-graduation-cap",
        "catalogos.especialidad": "fas fa-certificate",
        "catalogos.estadocivil": "fas fa-heart",
        "catalogos.modalidad": "fas fa-clock",
        "catalogos.nacionalidad": "fas fa-flag",
        "catalogos.nivel": "fas fa-layer-group",
        "catalogos.ocupacion": "fas fa-briefcase",
        "catalogos.parentesco": "fas fa-family",
        "catalogos.provincia": "fas fa-globe-americas",
        "catalogos.sexo": "fas fa-venus-mars",
        "catalogos.subarea": "fas fa-book-open",
        "catalogos.tipoidentificacion": "fas fa-id-card",
        
        # Configuración institucional
        "config_institucional.periodolectivo": "fas fa-calendar-alt",
        "config_institucional.seccion": "fas fa-chalkboard",
        "config_institucional.subgrupo": "fas fa-users",
    },
    
    # Configuración del menú lateral
    "show_sidebar": True,
    "navigation_expanded": True,
    
    # Personalización de colores
    "changeform_format": "horizontal_tabs",
    
    # Enlaces personalizados en el menú superior
    "topmenu_links": [
        {"app": "core"},
        {"app": "matricula"},
        {"app": "catalogos"},
        {"app": "config_institucional"},
    ],
    
    # Enlaces personalizados para matrícula
    "custom_links": {
        "matricula": [
            {
                "name": "Consulta de Estudiante",
                "url": "consulta_estudiante",
                "icon": "fas fa-search",
                "permissions": ["matricula.view_estudiante"],
            },
        ]
    },
    
    # Configuraciones adicionales
    "show_ui_builder": False,
    "show_jazzmin_version": False,
    
    # Personalización del menú
    "menu_title": "Menú Principal",
    
    # Agrupación de menús
    "menu_groups": [
        {
            "name": "Gestión Académica",
            "icon": "fas fa-graduation-cap",
            "models": [
                "matricula.estudiante",
                "matricula.matriculaacademica",
                "matricula.plantillaimpresionmatricula",
            ]
        },
        {
            "name": "Contactos y Encargados",
            "icon": "fas fa-address-book",
            "models": [
                "matricula.personacontacto",
                "matricula.encargadoestudiante",
            ]
        },
        {
            "name": "Catálogos Globales",
            "icon": "fas fa-database",
            "models": [
                "catalogos.provincia",
                "catalogos.canton", 
                "catalogos.distrito",
                "catalogos.nivel",
                "catalogos.especialidad",
                "catalogos.subarea",
                "catalogos.adecuacion",
                "catalogos.escolaridad",
                "catalogos.ocupacion",
                "catalogos.estadocivil",
                "catalogos.parentesco",
                "catalogos.sexo",
                "catalogos.nacionalidad",
                "catalogos.tipoidentificacion",
                "catalogos.modalidad",
            ]
        },
        {
            "name": "Configuración Institucional",
            "icon": "fas fa-cogs",
            "models": [
                "config_institucional.periodolectivo",
                "config_institucional.seccion",
                "config_institucional.subgrupo",
            ]
        },
        {
            "name": "Administración del Sistema",
            "icon": "fas fa-shield-alt",
            "models": [
                "core.institucion",
                "core.user",
                "core.membresia",
                "auth.group",
            ]
        },
    ],
}

# Configuración de la interfaz de usuario
JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-teal",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "cosmo",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    }
}
