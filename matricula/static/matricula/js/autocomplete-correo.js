// Script para autocompletar el correo en el admin de Estudiante
(function() {
    function updateCorreo() {
        var identificacion = document.getElementById('id_identificacion');
        var correo = document.getElementById('id_correo');
        if (identificacion && correo && !correo.dataset.userEdited) {
            correo.value = identificacion.value ? identificacion.value + '@est.mep.go.cr' : '';
        }
    }
    document.addEventListener('DOMContentLoaded', function() {
        var identificacion = document.getElementById('id_identificacion');
        var correo = document.getElementById('id_correo');
        if (identificacion && correo) {
            identificacion.addEventListener('input', updateCorreo);
            correo.addEventListener('input', function() {
                // Si el usuario edita el correo, no lo sobreescribas automáticamente
                correo.dataset.userEdited = 'true';
            });
        }
    });
})(); 