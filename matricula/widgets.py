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
        
        # Crear ID único para este widget
        unique_id = f"drag-drop-{name}"
        
        # Zona de arrastrar y soltar (drag & drop)
        output.append(f'''
        <div id="{unique_id}" class="drag-drop-zone" style="
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            background-color: #f9f9f9;
            cursor: pointer;
            transition: all 0.3s ease;
            margin: 10px 0;
        ">
            <div class="drag-drop-content">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #999; margin-bottom: 10px;">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <p style="margin: 10px 0; color: #666; font-size: 14px;">
                    <strong>Arrastra y suelta una imagen aquí</strong><br>
                    o haz clic para seleccionar
                </p>
                <p style="margin: 5px 0; color: #999; font-size: 12px;">
                    Formatos: JPG, PNG, GIF (máx. 5MB)
                </p>
            </div>
        </div>
        ''')
        
        # Mostrar imagen actual si existe
        if value and hasattr(value, 'url'):
            output.append(
                '<div class="current-image-preview" style="margin-top: 15px;">'
                '<label style="font-weight: bold; color: #333;">Imagen actual:</label><br>'
                f'<img src="{value.url}" alt="Imagen actual" style="max-width: 200px; max-height: 200px; border: 2px solid #ddd; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
                '</div>'
            )
        
        # Input para nueva imagen (oculto, se activa con click o drag & drop)
        attrs_copy = attrs.copy() if attrs else {}
        attrs_copy['style'] = 'display: none;'
        output.append(super().render(name, value, attrs_copy, renderer))
        
        # Contenedor para previsualización de nueva imagen
        output.append(
            '<div class="new-image-preview" style="display: none; margin-top: 15px;">'
            '<label style="font-weight: bold; color: #333;">Nueva imagen (vista previa):</label><br>'
            '<img id="image-preview" src="" alt="Vista previa" style="max-width: 200px; max-height: 200px; border: 2px solid #4CAF50; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            '<button type="button" class="remove-preview-btn" style="display: block; margin: 10px 0; padding: 5px 15px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">Quitar imagen</button>'
            '</div>'
        )
        
        # JavaScript para drag & drop y previsualización en tiempo real
        output.append('''
        <script>
        (function() {
            function initializeImagePreview() {
                var inputName = "%s";
                var input = document.querySelector('input[name="' + inputName + '"]');
                var dropZone = document.getElementById('%s');
                var preview = document.querySelector('.new-image-preview');
                var previewImg = document.getElementById('image-preview');
                var removeBtn = document.querySelector('.remove-preview-btn');
                
                if (!input || !dropZone || !preview || !previewImg) {
                    console.log('Elementos no encontrados para drag & drop');
                    return;
                }
                
                // Función para procesar archivo
                function processFile(file) {
                    // Validar tipo de archivo
                    if (!file.type.match('image.*')) {
                        alert('Por favor seleccione solo archivos de imagen (JPG, PNG, GIF)');
                        return false;
                    }
                    
                    // Validar tamaño (5MB)
                    if (file.size > 5 * 1024 * 1024) {
                        alert('La imagen debe ser menor a 5MB');
                        return false;
                    }
                    
                    // Mostrar previsualización
                    var reader = new FileReader();
                    reader.onload = function(e) {
                        previewImg.src = e.target.result;
                        preview.style.display = 'block';
                        dropZone.style.borderColor = '#4CAF50';
                        dropZone.style.backgroundColor = '#f1f8f4';
                    };
                    reader.readAsDataURL(file);
                    return true;
                }
                
                // Click en la zona para abrir selector de archivos
                dropZone.addEventListener('click', function(e) {
                    e.preventDefault();
                    input.click();
                });
                
                // Cambio en input (selector de archivos tradicional)
                input.addEventListener('change', function(e) {
                    var file = e.target.files[0];
                    if (file) {
                        processFile(file);
                    }
                });
                
                // Prevenir comportamiento por defecto del navegador
                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(eventName) {
                    dropZone.addEventListener(eventName, function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                    }, false);
                });
                
                // Efectos visuales al arrastrar sobre la zona
                ['dragenter', 'dragover'].forEach(function(eventName) {
                    dropZone.addEventListener(eventName, function() {
                        dropZone.style.borderColor = '#2196F3';
                        dropZone.style.backgroundColor = '#e3f2fd';
                        dropZone.style.transform = 'scale(1.02)';
                    }, false);
                });
                
                ['dragleave', 'drop'].forEach(function(eventName) {
                    dropZone.addEventListener(eventName, function() {
                        dropZone.style.borderColor = '#ccc';
                        dropZone.style.backgroundColor = '#f9f9f9';
                        dropZone.style.transform = 'scale(1)';
                    }, false);
                });
                
                // Manejar el drop (soltar archivo)
                dropZone.addEventListener('drop', function(e) {
                    var dt = e.dataTransfer;
                    var files = dt.files;
                    
                    if (files.length > 0) {
                        var file = files[0];
                        
                        // Crear un nuevo FileList para el input
                        var dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        input.files = dataTransfer.files;
                        
                        // Procesar el archivo
                        processFile(file);
                    }
                }, false);
                
                // Botón para quitar imagen
                if (removeBtn) {
                    removeBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        input.value = '';
                        preview.style.display = 'none';
                        previewImg.src = '';
                        dropZone.style.borderColor = '#ccc';
                        dropZone.style.backgroundColor = '#f9f9f9';
                    });
                }
            }
            
            // Inicializar cuando el DOM esté listo
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initializeImagePreview);
            } else {
                initializeImagePreview();
            }
            
            // También inicializar con un delay para Jazzmin
            setTimeout(initializeImagePreview, 500);
        })();
        </script>
        ''' % (name, unique_id))
        
        return mark_safe(''.join(output)) 