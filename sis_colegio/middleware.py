class NoCacheMiddleware:
    """
    Middleware para evitar el caché del navegador en desarrollo
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers más agresivos para evitar caché
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        response['Surrogate-Control'] = 'no-store'
        response['X-Accel-Expires'] = '0'
        
        # Headers adicionales para archivos estáticos
        if request.path.startswith('/static/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Vary'] = 'Accept-Encoding'
        
        return response


# Rutas que usan el admin base (logout, menú) y deben evitar caché para no tener CSRF stale
_NO_CACHE_PREFIXES = ("/admin/", "/docente/", "/matricula/", "/comedor/", "/evaluaciones/", "/ingreso/")


class AdminNoCacheMiddleware:
    """
    Evita que el navegador reutilice HTML viejo (forms con CSRF stale).
    Aplica a admin y a vistas que extienden base_site (docente, matrícula, etc.).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        content_type = (response.get("Content-Type") or "").lower()
        if "text/html" in content_type and any(request.path.startswith(p) for p in _NO_CACHE_PREFIXES):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"
            response["Vary"] = "Cookie"

        return response
