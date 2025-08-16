// balance_mensual.js
// Script para formatear y recalcular la tabla de balance mensual

function formatoMiles(num) {
    num = Number(num) || 0;
    return num.toLocaleString('es-CL', {maximumFractionDigits: 0});
}
function parseMiles(str) {
    if (!str) return 0;
    return parseInt(String(str).replace(/\./g, '').replace(/[^\d-]/g, '')) || 0;
}
function actualizarFila(tr) {
    const ingresosAgentes = parseMiles(tr.querySelector('.ingresos-agentes').textContent.replace('$',''));
    const ingresosExternos = parseMiles(tr.querySelector('.ingresos-externos').value);
    const egresosComision = parseMiles(tr.querySelector('.egresos-comision').textContent.replace('$',''));
    const egresosAdministracion = parseMiles(tr.querySelector('.egresos-administracion').value);
    const otrosEgresos = parseMiles(tr.querySelector('.otros-egresos').value);
    // Ganancia/Pérdida
    const ganancia = ingresosAgentes + ingresosExternos - egresosComision - egresosAdministracion - otrosEgresos;
    tr.querySelector('.ganancia-perdida').textContent = '$' + formatoMiles(ganancia);
    // % Margen
    const ingresos = ingresosAgentes + ingresosExternos;
    const egresos = egresosComision + egresosAdministracion + otrosEgresos;
    let margen = 0.0;
    if (egresos > 0 && ingresos > 0) {
        margen = (100 - ((egresos / ingresos) * 100));
    }
    tr.querySelector('.margen-porcentaje').textContent = margen.toFixed(1) + '%';
}
function formatearInput(input) {
    let val = parseMiles(input.value);
    input.value = formatoMiles(val);
}
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.input-miles').forEach(input => {
        input.addEventListener('input', function() {
            actualizarFila(input.closest('tr'));
        });
        input.addEventListener('blur', function() {
            formatearInput(input);
            actualizarFila(input.closest('tr'));
        });
        // Formatear al cargar
        formatearInput(input);
    });
    document.querySelectorAll('#tabla-balance-mensual tbody tr').forEach(tr => {
        actualizarFila(tr);
    });
});
