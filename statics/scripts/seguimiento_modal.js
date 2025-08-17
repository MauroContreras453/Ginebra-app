// seguimiento_modal.js
// Muestra un modal para editar el campo seguimiento en postventa

document.addEventListener('DOMContentLoaded', function() {
    // Crear el modal si no existe
    if (!document.getElementById('seguimientoModal')) {
        const modalHtml = `
        <div class="modal fade" id="seguimientoModal" tabindex="-1" aria-labelledby="seguimientoModalLabel" aria-hidden="true">
          <div class="modal-dialog modal-lg">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="seguimientoModalLabel">Editar Seguimiento</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
              </div>
              <div class="modal-body">
                <textarea id="seguimientoModalTextarea" class="form-control" rows="10"></textarea>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-custom" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-custom" id="guardarSeguimientoModal">Guardar</button>
              </div>
            </div>
          </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    let currentInput = null;
    // Delegación para inputs de seguimiento

    // Abrir modal al hacer click en el preview
    document.body.addEventListener('click', function(e) {
      if (e.target.classList.contains('seguimiento-preview') || e.target.classList.contains('experiencia-preview')) {
        const preview = e.target;
        let textarea = null;
        if (preview.classList.contains('seguimiento-preview')) {
          textarea = preview.parentElement.querySelector('textarea[name^="seguimiento_"]');
        } else if (preview.classList.contains('experiencia-preview')) {
          textarea = preview.parentElement.querySelector('textarea[name^="experiencia_"]');
        }
        if (textarea) {
          currentInput = textarea;
          const modal = new bootstrap.Modal(document.getElementById('seguimientoModal'));
          document.getElementById('seguimientoModalTextarea').value = textarea.value;
          modal.show();
        }
      }
    });

  // Guardar cambios del modal al textarea y actualizar el preview
  document.getElementById('guardarSeguimientoModal').addEventListener('click', function() {
    if (currentInput) {
      currentInput.value = document.getElementById('seguimientoModalTextarea').value;
      // Actualizar el preview
      let preview = null;
      if (currentInput.name.startsWith('seguimiento_')) {
        preview = currentInput.parentElement.querySelector('.seguimiento-preview');
      } else if (currentInput.name.startsWith('experiencia_')) {
        preview = currentInput.parentElement.querySelector('.experiencia-preview');
      }
      if (preview) preview.textContent = currentInput.value;
      // Disparar evento blur para que el JS original guarde el cambio
      currentInput.dispatchEvent(new Event('blur'));
    }
    bootstrap.Modal.getInstance(document.getElementById('seguimientoModal')).hide();
  });
});
