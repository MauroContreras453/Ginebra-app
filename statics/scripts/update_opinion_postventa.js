// Script para actualizar opinión y postventa de reservas vía API
// Usar en control_gestion_clientes.html y marketing.html

document.addEventListener('DOMContentLoaded', function() {
    // Delegación para todos los selects de opinión y postventa
    document.body.addEventListener('change', function(e) {
        if (e.target.matches('select[name^="opinion_"]') || e.target.matches('select[name^="postventa_"]')) {
            const select = e.target;
            const [field, reservaId] = select.name.split('_');
            const row = select.closest('tr');
            let opinion = null, postventa = null, experiencia = null;
            if (row) {
                const opinionSelect = row.querySelector('select[name^="opinion_"]');
                const postventaSelect = row.querySelector('select[name^="postventa_"]');
                const experienciaInput = row.querySelector('input[name^="experiencia_"]');
                if (opinionSelect) opinion = opinionSelect.value;
                if (postventaSelect) postventa = postventaSelect.value;
                if (experienciaInput) experiencia = experienciaInput.value;
            }
            const payload = {
                reserva_id: reservaId,
                opinion: opinion,
                postventa: postventa,
                experiencia: experiencia
            };
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

    // Guardar experiencia al perder foco
    document.body.addEventListener('blur', function(e) {
        if (e.target.matches('input[name^="experiencia_"]')) {
            const input = e.target;
            const [field, reservaId] = input.name.split('_');
            const row = input.closest('tr');
            let opinion = null, postventa = null, experiencia = input.value;
            if (row) {
                const opinionSelect = row.querySelector('select[name^="opinion_"]');
                const postventaSelect = row.querySelector('select[name^="postventa_"]');
                if (opinionSelect) opinion = opinionSelect.value;
                if (postventaSelect) postventa = postventaSelect.value;
            }
            const payload = {
                reserva_id: reservaId,
                opinion: opinion,
                postventa: postventa,
                experiencia: experiencia
            };
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
