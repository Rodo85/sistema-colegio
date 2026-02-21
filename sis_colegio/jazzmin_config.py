# Configuración personalizada de Jazzmin para el menú principal
# Este archivo define los iconos y configuraciones del menú lateral

JAZZMIN_SETTINGS = {
    "copyright": "Ing. Rodolfo Garro Monge",
    "welcome_sign": "Sistema Integral de Gestión Administrativa y Educativa",
    "site_title": "School Smart",
    "site_header": "School Smart",
    "site_brand": "School Smart",
    "site_logo": "sis_colegio/img/Logo-Peque-School-Smart.png",
    "site_icon": "sis_colegio/img/Logo-Peque-School-Smart.png",

    
    "order_with_respect_to": [
        "core",
        "matricula", 
        "comedor",
        "catalogos",
        "config_institucional",
        "auth",
    ],
    
    "icons": {
        "core.user": "fas fa-users",
        "core.institucion": "fas fa-university",
        "core.membresia": "fas fa-user-tie",
        "auth.group": "fas fa-users-cog",
        "auth.user": "fas fa-user-shield",
        
        "matricula.estudiante": "fas fa-user-graduate",
        "matricula.personacontacto": "fas fa-address-book",
        "matricula.encargadoestudiante": "fas fa-user-friends",
        "matricula.matriculaacademica": "fas fa-clipboard-list",
        "matricula.plantillaimpresionmatricula": "fas fa-file-alt",
        "comedor.becacomedor": "fas fa-utensils",
        "comedor.registroalmuerzo": "fas fa-qrcode",
        "comedor.tiquetecomedor": "fas fa-ticket-alt",
        "comedor.registroalmuerzoTiquete": "fas fa-receipt",
        
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
        
        "config_institucional.periodolectivo": "fas fa-calendar-alt",
        "config_institucional.seccion": "fas fa-chalkboard",
        "config_institucional.subgrupo": "fas fa-users",
    },
    
    "show_sidebar": True,
    "navigation_expanded": True,
    
    "changeform_format": "horizontal_tabs",
    
    "topmenu_links": [
        {"app": "core"},
        {"app": "matricula"},
        {"app": "comedor"},
        {"app": "catalogos"},
        {"app": "config_institucional"},
    ],
    
    "custom_links": {
        "matricula": [
            {
                "name": "Consulta de Estudiante",
                "url": "matricula:consulta_estudiante",
                "icon": "fas fa-search",
                "permissions": ["matricula.access_consulta_estudiante"],
            },
            {
                "name": "Reporte de Matrícula",
                "url": "matricula:reporte_matricula",
                "icon": "fas fa-chart-pie",
                "permissions": [
                    "matricula.access_reporte_matricula",
                ],
            },
            {
                "name": "Reporte PAS por Sección",
                "url": "matricula:reporte_pas_seccion",
                "icon": "fas fa-id-card-alt",
                "permissions": ["matricula.access_reporte_pas_seccion"],
            },
        ],
        "comedor": [
            {
                "name": "Registrar beca",
                "url": "comedor:registrar_beca",
                "icon": "fas fa-user-check",
                "permissions": ["comedor.access_registro_beca_comedor"],
            },
            {
                "name": "Almuerzo",
                "url": "comedor:almuerzo",
                "icon": "fas fa-qrcode",
                "permissions": ["comedor.access_almuerzo_comedor"],
            },
            {
                "name": "Reportes comedor",
                "url": "comedor:reportes",
                "icon": "fas fa-chart-bar",
                "permissions": ["comedor.access_reportes_comedor"],
            },
            {
                "name": "Tiquetes",
                "url": "comedor:tiquetes",
                "icon": "fas fa-ticket-alt",
                "permissions": ["comedor.access_tiquetes_comedor"],
            },
        ],
    },
    
    "show_ui_builder": False,
    "show_jazzmin_version": False,
    
    # Configuración del logo
    "site_logo_classes": "img-fluid",
    "brand_colour": False,
    
    # Configuración adicional del logo
    "welcome_sign": "Sistema Integral de Gestión Administrativa y Educativa",
    "login_logo": "sis_colegio/img/Logo-School-Smart.png",
    "login_logo_dark": "sis_colegio/img/Logo-School-Smart.png",
    
    "menu_title": "Menú Principal",
    
    "menu_groups": [
        {
            "name": "Gestión Académica",
            "icon": "fas fa-graduation-cap",
            "models": [
                "matricula.estudiante",
                "matricula.matriculaacademica",
            ]
        },
    ],
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    
    # Colores por defecto de Jazzmin (tema claro)
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": False,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
}