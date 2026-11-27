// Pide confirmación antes de enviar los formularios marcados con data-confirmar
// (por ejemplo, eliminar un libro o un lector).
document.addEventListener('submit', function (evento) {
  var mensaje = evento.target.dataset.confirmar;
  if (mensaje && !window.confirm(mensaje)) {
    evento.preventDefault();
  }
});
