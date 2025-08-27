// Evita que Jazzmin olist ocultan filtros de admin si quedan sin opciones
// Mantiene visibles los <select> de filtros en la changelist aunque el queryset
// sea vacío o el valor seleccionado no esté en el listado recalculado.
(function() {
  function ensureOption(select) {
    if (!select) return;
    // Si no hay opciones, agregar un placeholder para que no se oculte
    if (select.options.length === 0) {
      var opt = document.createElement('option');
      opt.value = '';
      opt.textContent = '—';
      select.appendChild(opt);
    }
    // Asegurar que el valor actual siga existiendo como opción visible
    var current = (new URLSearchParams(window.location.search)).get(select.name);
    if (current && !Array.from(select.options).some(o => o.value === current)) {
      var optSel = document.createElement('option');
      optSel.value = current;
      optSel.textContent = 'Seleccionado';
      optSel.selected = true;
      select.appendChild(optSel);
    }
    // Mostrar explícitamente el contenedor del filtro
    var wrapper = select.closest('.field-box, .filter, .js-filter, li');
    if (wrapper) {
      wrapper.style.display = '';
      wrapper.classList.remove('hidden');
    }
  }

  function run() {
    // Selects comunes de filtros en Jazzmin
    document.querySelectorAll('form[action$="changelist"] select, .changelist-filter select').forEach(ensureOption);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();


