(function () {
  "use strict";

  function ajustarAcoesAdmin() {
    document.querySelectorAll("select[name='action']").forEach(function (select) {
      const placeholder = select.querySelector("option[value='']");
      if (placeholder) {
        placeholder.textContent = "Escolha uma ação para as notificações";
      }
    });

    document.querySelectorAll("button[name='index']").forEach(function (button) {
      if (button.textContent.trim().toLowerCase() === "ir") {
        button.textContent = "Executar";
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ajustarAcoesAdmin);
  } else {
    ajustarAcoesAdmin();
  }
})();
