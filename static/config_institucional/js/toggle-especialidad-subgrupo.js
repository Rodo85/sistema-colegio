(function() {
  function getNivelNumero() {
    var selectSubgrupo = document.getElementById('id_subgrupo');
    if (!selectSubgrupo) return null;
    // Intentar leer data-attributes si el option los trae; de lo contrario, inferir por texto
    var opt = selectSubgrupo.options[selectSubgrupo.selectedIndex];
    if (!opt) return null;
    var nivel = opt.getAttribute('data-nivel-num');
    if (nivel) return parseInt(nivel, 10);
    var txt = (opt.textContent || '').toLowerCase();
    // El __str__ de Subgrupo es "<nivel>-<seccion><letra>" ej: "10-1A"
    // Tomamos el número al inicio
    var match = txt.match(/^(\d{1,2})/);
    if (match) return parseInt(match[1], 10);
    return null;
  }

  function toggleEspecialidad() {
    var wrapper = document.querySelector('.field-especialidad_curso, [class*="field-especialidad_curso"], .form-row.field-especialidad_curso');
    if (!wrapper) return;
    var nivel = getNivelNumero();
    if (nivel === 10 || nivel === 11 || nivel === 12) {
      wrapper.style.display = '';
    } else {
      // Ocultar y limpiar si no aplica
      var select = document.getElementById('id_especialidad_curso');
      if (select) {
        try { select.value = ''; } catch(e) {}
      }
      wrapper.style.display = 'none';
    }
  }

  function init() {
    toggleEspecialidad();
    var selectSubgrupo = document.getElementById('id_subgrupo');
    if (selectSubgrupo) {
      selectSubgrupo.addEventListener('change', toggleEspecialidad);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();


