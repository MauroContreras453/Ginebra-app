// Script para autocalcular campos en reservas.html
// Usa la misma lógica que el backend de Flask

// Porcentaje de comisión del ejecutivo (usuario actual) debe ser inyectado desde la plantilla
let PORCENTAJE_COMISION_EJECUTIVO = 0.10; // Valor por defecto, se sobreescribe desde la plantilla

function safeFloat(val) {
  if (!val) return 0;
  return parseFloat(val.toString().replace(',', '.')) || 0;
}

function calcularCamposReserva() {
  const total = safeFloat(document.getElementById('precio_venta_total').value);
  const hotel = safeFloat(document.getElementById('hotel_neto').value);
  const vuelo = safeFloat(document.getElementById('vuelo_neto').value);
  const traslado = safeFloat(document.getElementById('traslado_neto').value);
  const seguro = safeFloat(document.getElementById('seguro_neto').value);
  const circuito = safeFloat(document.getElementById('circuito_neto').value);
  const crucero = safeFloat(document.getElementById('crucero_neto').value);
  const excursion = safeFloat(document.getElementById('excursion_neto').value);
  const paquete = safeFloat(document.getElementById('paquete_neto').value);

  // Precio venta neto es la suma de todos los netos
  const precio_venta_neto = hotel + vuelo + traslado + seguro + circuito + crucero + excursion + paquete;
  // Ganancia total = precio_venta_total - precio_venta_neto
  const ganancia_total = total - precio_venta_neto;
  // Comisión ejecutivo y agencia según backend
  const comision_ejecutivo = ganancia_total * PORCENTAJE_COMISION_EJECUTIVO;
  const comision_agencia = ganancia_total - comision_ejecutivo;

  document.getElementById('precio_venta_neto').value = precio_venta_neto.toFixed(2);
  document.getElementById('ganancia_total').value = ganancia_total.toFixed(2);
  document.getElementById('comision_ejecutivo').value = comision_ejecutivo.toFixed(2);
  document.getElementById('comision_agencia').value = comision_agencia.toFixed(2);
}

function inicializarCalculoReserva(porcentajeEjecutivo) {
  PORCENTAJE_COMISION_EJECUTIVO = porcentajeEjecutivo;
  [
    'precio_venta_total',
    'hotel_neto',
    'vuelo_neto',
    'traslado_neto',
    'seguro_neto',
    'circuito_neto',
    'crucero_neto',
    'excursion_neto',
    'paquete_neto'
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', calcularCamposReserva);
    }
  });
}
