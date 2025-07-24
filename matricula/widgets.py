from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class ImagePreviewWidget(forms.FileInput):
    """
    Widget personalizado para mostrar previsualización de imágenes
    """
    
    def __init__(self, attrs=None, template_name=None):
        default_attrs = {
            'accept': 'image/*',
            'class': 'image-upload-input'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        output = []
        
        # Mostrar imagen actual si existe
        if value and hasattr(value, 'url'):
            output.append(
                '<div class="current-image-preview">'
                '<label>Imagen actual:</label><br>'
                f'<img src="{value.url}" alt="Imagen actual" style="max-width: 150px; max-height: 150px; border: 1px solid #ddd; border-radius: 4px; margin: 5px 0;">'
                '</div>'
            )
        
        # Input para nueva imagen
        output.append(super().render(name, value, attrs, renderer))
        
        # Contenedor para previsualización de nueva imagen
        output.append(
            '<div class="new-image-preview" style="display: none; margin-top: 10px;">'
            '<label>Vista previa:</label><br>'
            '<img id="image-preview" src="" alt="Vista previa" style="max-width: 150px; max-height: 150px; border: 1px solid #ddd; border-radius: 4px; margin: 5px 0;">'
            '</div>'
        )
        
        # JavaScript para previsualización en tiempo real
        output.append('''
        <script>
        function initializeImagePreview() {
            var input = document.querySelector('input[name="%s"]');
            var preview = document.querySelector('.new-image-preview');
            var previewImg = document.getElementById('image-preview');
            
            if (input && preview && previewImg) {
                input.addEventListener('change', function(e) {
                    var file = e.target.files[0];
                    if (file) {
                        // Validar tipo de archivo
                        if (!file.type.match('image.*')) {
                            alert('Por favor seleccione solo archivos de imagen (JPG, PNG, etc.)');
                            input.value = '';
                            return;
                        }
                        
                        // Validar tamaño (2MB)
                        if (file.size > 2 * 1024 * 1024) {
                            alert('La imagen debe ser menor a 2MB');
                            input.value = '';
                            return;
                        }
                        
                        var reader = new FileReader();
                        reader.onload = function(e) {
                            previewImg.src = e.target.result;
                            preview.style.display = 'block';
                        };
                        reader.readAsDataURL(file);
                    } else {
                        preview.style.display = 'none';
                    }
                });
            }
        }
        
        // Inicializar cuando el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeImagePreview);
        } else {
            initializeImagePreview();
        }
        
        // También inicializar cuando Jazzmin termine de cargar
        if (typeof $ !== 'undefined') {
            $(document).ready(function() {
                setTimeout(initializeImagePreview, 500);
            });
        }
        </script>
        ''' % name)
        
        return mark_safe(''.join(output)) 