// Script para calcular pendientes según la lógica de negocio en control_gestion_clientes
(function() {
    var rows = document.querySelectorAll('table.table tbody tr');
    var pendientes = 0;
    rows.forEach(function(row) {
        var estadoPago = row.querySelector('[data-estado-pago]');
        var ventaCobrada = row.querySelector('[data-venta-cobrada]');
        var ventaEmitida = row.querySelector('[data-venta-emitida]');
        if (!estadoPago || !ventaCobrada || !ventaEmitida) return;
        var esVerde = (estadoPago.textContent.trim() === 'Pagado') &&
                      (ventaCobrada.textContent.trim() === 'Cobrada') &&
                      (ventaEmitida.textContent.trim() === 'Emitida');
        if (!esVerde) pendientes++;
    });
    var pendientesElem = document.getElementById('pendientes-js');
    if (pendientesElem) pendientesElem.textContent = pendientes;
})();
