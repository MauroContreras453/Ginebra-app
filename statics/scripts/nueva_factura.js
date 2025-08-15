// Auto-habilitar fecha de pago cuando el estado es "Pagado"
document.getElementById('estado').addEventListener('change', function() {
  const fechaPago = document.getElementById('fecha_pago');
  if (this.value === 'Pagado' && !fechaPago.value) {
    fechaPago.value = new Date().toISOString().split('T')[0];
  }
});
