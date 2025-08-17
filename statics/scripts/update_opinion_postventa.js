// Script para actualizar opinión y postventa de reservas vía API
// Usar en control_gestion_clientes.html y marketing.html

document.addEventListener('DOMContentLoaded', function() {
    // Delegación para todos los selects de opinión y postventa
    document.body.addEventListener('change', function(e) {
        if (
            e.target.matches('select[name^="opinion_"]') ||
            e.target.matches('select[name^="postventa_"]') ||
            e.target.matches('select[name^="estado_postventa_"]')
        ) {
            const select = e.target;
            const reservaId = select.name.split('_').pop();
            const row = select.closest('tr');
            let payload = { reserva_id: reservaId };
            if (row) {
                const opinionSelect = row.querySelector('select[name^="opinion_"]');
                if (opinionSelect) payload.opinion = opinionSelect.value;
                const postventaSelect = row.querySelector('select[name^="postventa_"]');
                if (postventaSelect) payload.postventa = postventaSelect.value;
                const experienciaInput = row.querySelector('input[name^="experiencia_"]');
                if (experienciaInput) payload.experiencia = experienciaInput.value;
                const estadoPostventaSelect = row.querySelector('select[name^="estado_postventa_"]');
                if (estadoPostventaSelect) payload.estado_postventa = estadoPostventaSelect.value;
                const seguimientoInput = row.querySelector('input[name^="seguimiento_"]');
                if (seguimientoInput) payload.seguimiento = seguimientoInput.value;
            }
            fetch('/api/update_reserva_opinion_postventa', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    select.classList.add('is-valid');
                    setTimeout(() => select.classList.remove('is-valid'), 1000);
                } else {
                    select.classList.add('is-invalid');
                    setTimeout(() => select.classList.remove('is-invalid'), 2000);
                    alert('Error al guardar: ' + (data.message || ''));
                }
            })
            .catch(err => {
                select.classList.add('is-invalid');
                setTimeout(() => select.classList.remove('is-invalid'), 2000);
                alert('Error de red al guardar.');
            });
        }
    });

    // Guardar experiencia o seguimiento al perder foco
    document.body.addEventListener('blur', function(e) {
        if (e.target.matches('input[name^="experiencia_"]') || e.target.matches('input[name^="seguimiento_"]')) {
            const input = e.target;
            const [field, reservaId] = input.name.split('_');
            const row = input.closest('tr');
            let payload = { reserva_id: reservaId };
            if (row) {
                const opinionSelect = row.querySelector('select[name^="opinion_"]');
                if (opinionSelect) payload.opinion = opinionSelect.value;
                const postventaSelect = row.querySelector('select[name^="postventa_"]');
                if (postventaSelect) payload.postventa = postventaSelect.value;
                const experienciaInput = row.querySelector('input[name^="experiencia_"]');
                if (experienciaInput) payload.experiencia = experienciaInput.value;
                const estadoPostventaSelect = row.querySelector('select[name^="estado_postventa_"]');
                if (estadoPostventaSelect) payload.estado_postventa = estadoPostventaSelect.value;
                const seguimientoInput = row.querySelector('input[name^="seguimiento_"]');
                if (seguimientoInput) payload.seguimiento = seguimientoInput.value;
            }
            fetch('/api/update_reserva_opinion_postventa', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    input.classList.add('is-valid');
                    setTimeout(() => input.classList.remove('is-valid'), 1000);
                } else {
                    input.classList.add('is-invalid');
                    setTimeout(() => input.classList.remove('is-invalid'), 2000);
                    alert('Error al guardar: ' + (data.message || ''));
                }
            })
            .catch(err => {
                input.classList.add('is-invalid');
                setTimeout(() => input.classList.remove('is-invalid'), 2000);
                alert('Error de red al guardar.');
            });
        }
    }, true);
});
