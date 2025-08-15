// Mostrar/ocultar panel basado en empresa seleccionada
document.addEventListener('DOMContentLoaded', function() {
    const empresaSelect = document.querySelector('select[name="empresa_id"]');
    const panelAdmin = document.getElementById('panel-admin');
    
    if (empresaSelect) {
        empresaSelect.addEventListener('change', function() {
            if (this.value) {
                // Se podría mostrar el panel inmediatamente o esperar a confirmar
            } else {
                panelAdmin.style.display = 'none';
            }
        });
    }
});
