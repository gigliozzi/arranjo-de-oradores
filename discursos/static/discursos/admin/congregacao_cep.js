(function () {
  "use strict";

  function onlyDigits(value) {
    return (value || "").replace(/\D/g, "");
  }

  function setValueIfEmpty(id, value) {
    const field = document.getElementById(id);
    if (field && value && !field.value) {
      field.value = value;
      field.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function setValue(id, value) {
    const field = document.getElementById(id);
    if (field && value) {
      field.value = value;
      field.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  async function fetchCep(cepField) {
    const cep = onlyDigits(cepField.value);
    if (cep.length !== 8 || cepField.dataset.lastFetchedCep === cep) {
      return;
    }

    cepField.dataset.lastFetchedCep = cep;
    cepField.classList.add("cep-loading");

    try {
      const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const data = await response.json();

      if (!response.ok || data.erro) {
        return;
      }

      setValue("id_cep", data.cep);
      setValueIfEmpty("id_logradouro", data.logradouro);
      setValueIfEmpty("id_bairro", data.bairro);
      setValueIfEmpty("id_cidade", data.localidade);
      setValueIfEmpty("id_estado", data.uf);
    } catch (error) {
      console.warn("Não foi possível consultar o CEP no ViaCEP.", error);
    } finally {
      cepField.classList.remove("cep-loading");
    }
  }

  function setupCepLookup() {
    const cepField = document.getElementById("id_cep");
    if (!cepField) {
      return;
    }

    cepField.setAttribute("autocomplete", "postal-code");
    cepField.addEventListener("blur", function () {
      fetchCep(cepField);
    });
    cepField.addEventListener("input", function () {
      if (onlyDigits(cepField.value).length === 8) {
        fetchCep(cepField);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupCepLookup);
  } else {
    setupCepLookup();
  }
})();
