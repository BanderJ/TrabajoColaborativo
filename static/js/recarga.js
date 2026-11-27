// Modo demo: la página se recarga sola cuando cambia un archivo del proyecto
// o cuando la carpeta cambia de rama. Solo se carga con debug activado.
(function () {
  // Firma del proyecto en el momento en que se dibujó esta página
  var firma = document.currentScript.dataset.firma || null;

  function revisar() {
    fetch('/__cambios', { cache: 'no-store' })
      .then(function (respuesta) { return respuesta.json(); })
      .then(function (datos) {
        if (firma && datos.firma !== firma) {
          location.reload();
          return;
        }
        firma = datos.firma;
        setTimeout(revisar, 1000);
      })
      .catch(function () {
        // El servidor se está reiniciando: se vuelve a intentar en un segundo.
        setTimeout(revisar, 1000);
      });
  }

  revisar();
})();
