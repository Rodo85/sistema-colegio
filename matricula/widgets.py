import uuid

from django import forms
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

        # Identificadores únicos para aislar múltiples instancias del widget
        uid = uuid.uuid4().hex
        wrapper_id = f"image-preview-wrapper-{uid}"
        drop_zone_id = f"drag-drop-{uid}"
        preview_container_id = f"new-image-preview-{uid}"
        preview_img_id = f"image-preview-{uid}"
        remove_button_id = f"remove-preview-{uid}"

        # Contenedor principal del widget
        output.append(f'''
        <div id="{wrapper_id}" class="image-preview-widget">
        <div id="{drop_zone_id}" data-role="drop-zone" class="drag-drop-zone" style="
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
            clear_checkbox_name = name + '-clear'
            clear_checkbox_id = 'id_' + name + '-clear'
            output.append(
                '<div class="current-image-preview" style="margin-top: 15px;">'
                '<label style="font-weight: bold; color: #333;">Imagen actual:</label><br>'
                f'<img src="{value.url}" alt="Imagen actual" style="max-width: 200px; max-height: 200px; border: 2px solid #ddd; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
                '<div style="margin: 10px 0;">'
                f'<label style="display: inline-flex; align-items: center; cursor: pointer; color: #d32f2f; font-weight: normal;">'
                f'<input type="checkbox" name="{clear_checkbox_name}" id="{clear_checkbox_id}" style="margin-right: 5px; cursor: pointer;">'
                '<span>🗑️ Eliminar esta foto</span>'
                '</label>'
                '</div>'
                '</div>'
            )

        # Input para nueva imagen (oculto, se activa con click o drag & drop)
        attrs_copy = attrs.copy() if attrs else {}
        attrs_copy['style'] = 'display: none;'
        output.append(super().render(name, value, attrs_copy, renderer))
        
        # Contenedor para previsualización de nueva imagen
        output.append(
            f'<div id="{preview_container_id}" class="new-image-preview" data-role="new-preview" style="display: none; margin-top: 15px;">'
            '<label style="font-weight: bold; color: #333;">Nueva imagen (vista previa):</label><br>'
            f'<img id="{preview_img_id}" data-role="new-preview-img" src="" alt="Vista previa" style="max-width: 200px; max-height: 200px; border: 2px solid #4CAF50; border-radius: 8px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            f'<button type="button" id="{remove_button_id}" data-role="remove-preview" class="remove-preview-btn" style="display: block; margin: 10px 0; padding: 5px 15px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">Quitar imagen</button>'
            '</div>'
        )

        # JavaScript para drag & drop y previsualización en tiempo real
        output.append('''
        <script>
        (function() {
            function initializeImagePreview() {
                var wrapper = document.getElementById('%(wrapper_id)s');
                if (!wrapper) {
                    return;
                }
                if (wrapper.dataset.initialized === '1') {
                    return;
                }
                wrapper.dataset.initialized = '1';

                var input = wrapper.querySelector('input[type="file"][name="%(name)s"]');
                var dropZone = wrapper.querySelector('[data-role="drop-zone"]');
                var preview = wrapper.querySelector('[data-role="new-preview"]');
                var previewImg = wrapper.querySelector('[data-role="new-preview-img"]');
                var removeBtn = wrapper.querySelector('[data-role="remove-preview"]');

                if (!input || !dropZone || !preview || !previewImg) {
                    console.warn('ImagePreviewWidget: elementos no encontrados', {
                        input: !!input,
                        dropZone: !!dropZone,
                        preview: !!preview,
                        previewImg: !!previewImg
                    });
                    return;
                }

                function resetPreview() {
                    preview.style.display = 'none';
                    previewImg.removeAttribute('src');
                    dropZone.style.borderColor = '#ccc';
                    dropZone.style.backgroundColor = '#f9f9f9';
                    dropZone.style.transform = 'scale(1)';
                }

                function processFile(file) {
                    if (!file) {
                        return;
                    }
                    if (!file.type || !file.type.match(/^image\\//)) {
                        alert('Por favor seleccione solo archivos de imagen (JPG, PNG, GIF).');
                        resetPreview();
                        input.value = '';
                        return;
                    }
                    if (file.size > 5 * 1024 * 1024) {
                        alert('La imagen debe ser menor a 5MB.');
                        resetPreview();
                        input.value = '';
                        return;
                    }

                    var reader = new FileReader();
                    reader.onload = function(e) {
                        previewImg.src = e.target.result;
                        preview.style.display = 'block';
                        dropZone.style.borderColor = '#4CAF50';
                        dropZone.style.backgroundColor = '#f1f8f4';
                        dropZone.style.transform = 'scale(1)';
                    };
                    reader.readAsDataURL(file);
                }

                dropZone.addEventListener('click', function(e) {
                    e.preventDefault();
                    input.click();
                });

                input.addEventListener('change', function(e) {
                    processFile(e.target.files ? e.target.files[0] : null);
                });

                ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(function(eventName) {
                    dropZone.addEventListener(eventName, function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                    }, false);
                });

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

                dropZone.addEventListener('drop', function(e) {
                    var files = e.dataTransfer && e.dataTransfer.files;
                    if (!files || !files.length) {
                        return;
                    }
                    var file = files[0];
                    var assigned = false;

                    try {
                        if (window.DataTransfer) {
                            var dt = new DataTransfer();
                            Array.prototype.forEach.call(files, function(f) {
                                dt.items.add(f);
                            });
                            input.files = dt.files;
                            assigned = true;
                        }
                    } catch (err) {
                        assigned = false;
                    }

                    if (!assigned) {
                        try {
                            input.files = files;
                            assigned = input.files && input.files.length > 0;
                        } catch (assignErr) {
                            assigned = false;
                        }
                    }

                    if (!assigned) {
                        console.warn('ImagePreviewWidget: no se pudo asignar archivos al input mediante drop.');
                    }

                    processFile(file);
                }, false);

                if (removeBtn) {
                    removeBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        input.value = '';
                        resetPreview();
                    });
                }
            }

            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initializeImagePreview);
            } else {
                initializeImagePreview();
            }

            document.addEventListener('formset:added', function() {
                setTimeout(initializeImagePreview, 50);
            });

            setTimeout(initializeImagePreview, 300);
        })();
        </script>
        ''' % {
            "wrapper_id": wrapper_id,
            "name": name,
        })

        output.append('</div>')

        return mark_safe(''.join(output))