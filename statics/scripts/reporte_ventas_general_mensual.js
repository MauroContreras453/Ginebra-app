// Definir los arrays como variables JS
var datosEstadoPagoArr = window.datosEstadoPagoArr || [];
var datosVentaCobradaArr = window.datosVentaCobradaArr || [];
var datosVentaEmitidaArr = window.datosVentaEmitidaArr || [];

const datosEstadoPago = {
  labels: ['Pagado', 'No Pagado'],
  datasets: [{
    data: datosEstadoPagoArr,
    backgroundColor: ['#28a745', '#dc3545'] // Verde, Rojo
  }]
};
const datosVentaCobrada = {
  labels: ['Cobrada', 'No Cobrada'],
  datasets: [{
    data: datosVentaCobradaArr,
    backgroundColor: ['#28a745', '#dc3545'] // Verde, Rojo
  }]
};
const datosVentaEmitida = {
  labels: ['Emitida', 'No Emitida'],
  datasets: [{
    data: datosVentaEmitidaArr,
    backgroundColor: ['#28a745', '#dc3545'] // Verde, Rojo
  }]
};
// Renderizar los gráficos
new Chart(document.getElementById('graficoEstadoPago'), {
  type: 'pie',
  data: datosEstadoPago,
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#fff', font: { size: 14 } } },
      title: { display: false }
    }
  }
});
new Chart(document.getElementById('graficoVentaCobrada'), {
  type: 'pie',
  data: datosVentaCobrada,
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#fff', font: { size: 14 } } },
      title: { display: false }
    }
  }
});
new Chart(document.getElementById('graficoVentaEmitida'), {
  type: 'pie',
  data: datosVentaEmitida,
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#fff', font: { size: 14 } } },
      title: { display: false }
    }
  }
});
