(() => {
  const dialog = document.querySelector(".auth-dialog");
  const loginForm = document.querySelector("#login-form");
  const registerForm = document.querySelector("#register-form");
  const authMessage = document.querySelector(".auth-message");
  const authTitle = document.querySelector("#auth-title");
  const tabs = [...document.querySelectorAll("[data-auth-mode]")];
  const signoutButton = document.querySelector(".signout-button");
  const navAuth = document.querySelector(".nav-auth");
  const createAccountButton = document.querySelector(".account-button");
  const authTabs = document.querySelector(".auth-tabs");
  const toast = document.querySelector(".toast");
  const menuToggle = document.querySelector(".menu-toggle");
  const primaryNav = document.querySelector("#primary-nav");
  let toastTimer;
  let currentUser = null;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add("is-visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(
      () => toast.classList.remove("is-visible"),
      2800,
    );
  }

  function csrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  }

  async function sendJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      const fieldErrors = data.fields
        ? Object.values(data.fields).flat().join(" ")
        : "";
      throw new Error(
        fieldErrors || data.error || "No pudimos completar la solicitud.",
      );
    }
    return data;
  }

  function setAuthMode(mode) {
    const isRegister = mode === "register";
    loginForm.hidden = isRegister;
    registerForm.hidden = !isRegister;
    authTitle.innerHTML = isRegister
      ? "Un buen comienzo<br><em>empieza por aquí.</em>"
      : "Qué bueno<br><em>verte por aquí.</em>";
    authMessage.textContent = "";
    authMessage.classList.remove("is-success");
    tabs.forEach((tab) => {
      const active = tab.dataset.authMode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
    });
  }

  function openAuth(mode) {
    if (currentUser) {
      showSignedInState(currentUser);
    } else {
      setAuthMode(mode);
    }
    if (!dialog.open) dialog.showModal();
  }

  function closeMobileMenu() {
    menuToggle.setAttribute("aria-expanded", "false");
    menuToggle.setAttribute("aria-label", "Abrir menú");
    primaryNav.classList.remove("is-open");
  }

  function showSignedInState(user) {
    authTabs.hidden = true;
    loginForm.hidden = true;
    registerForm.hidden = true;
    authTitle.textContent = `Hola, ${user.username}.`;
    authMessage.textContent = `Sesión iniciada como ${user.email}.`;
    authMessage.classList.add("is-success");
    signoutButton.hidden = false;
  }

  function setSignedIn(user) {
    currentUser = user;
    navAuth.textContent = `Hola, ${user.username}`;
    navAuth.dataset.openAuth = "login";
    createAccountButton.hidden = true;
    showSignedInState(user);
  }

  document.querySelectorAll("[data-open-auth]").forEach((button) => {
    button.addEventListener("click", () => {
      closeMobileMenu();
      openAuth(button.dataset.openAuth);
    });
  });
  document
    .querySelector(".dialog-close")
    .addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  tabs.forEach((tab) =>
    tab.addEventListener("click", () => setAuthMode(tab.dataset.authMode)),
  );

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    authMessage.textContent = "";
    const formData = new FormData(loginForm);
    try {
      const data = await sendJson("/api/usuarios/login/", {
        email: formData.get("email"),
        password: formData.get("password"),
      });
      setSignedIn(data.user);
      showToast("Qué gusto tenerte de vuelta.");
      window.setTimeout(() => dialog.close(), 650);
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    authMessage.textContent = "";
    const formData = new FormData(registerForm);
    try {
      const data = await sendJson("/api/usuarios/", {
        username: formData.get("username"),
        email: formData.get("email"),
        password: formData.get("password"),
      });
      setSignedIn(data.user);
      showToast("Tu cuenta ya está lista.");
      window.setTimeout(() => dialog.close(), 650);
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });

  signoutButton.addEventListener("click", async () => {
    try {
      await sendJson("/api/usuarios/logout/", {});
      currentUser = null;
      signoutButton.hidden = true;
      createAccountButton.hidden = false;
      navAuth.textContent = "Iniciar sesión";
      authTabs.hidden = false;
      setAuthMode("login");
      authMessage.textContent = "Has cerrado sesión.";
      authMessage.classList.add("is-success");
      showToast("Sesión cerrada.");
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });

  fetch("/api/usuarios/me/", { credentials: "same-origin" })
    .then((response) => {
      if (response.status === 204 || response.status === 401) return null;
      if (!response.ok) throw new Error("No pudimos comprobar tu sesión.");
      return response.json();
    })
    .then((data) => {
      if (data?.user) setSignedIn(data.user);
    })
    .catch(() => showToast("No pudimos comprobar tu sesión."));

  menuToggle.addEventListener("click", () => {
    const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!isOpen));
    menuToggle.setAttribute(
      "aria-label",
      isOpen ? "Abrir menú" : "Cerrar menú",
    );
    primaryNav.classList.toggle("is-open", !isOpen);
  });
  primaryNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Abrir menú");
      primaryNav.classList.remove("is-open");
    });
  });

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      document
        .querySelectorAll("[data-filter]")
        .forEach((chip) => chip.classList.remove("is-active"));
      button.classList.add("is-active");
      document.querySelectorAll(".product-card").forEach((card) => {
        card.hidden =
          button.dataset.filter !== "all" &&
          card.dataset.category !== button.dataset.filter;
      });
    });
  });

  let bagCount = 0;
  document.querySelectorAll("[data-add-to-bag]").forEach((button) => {
    button.addEventListener("click", () => {
      bagCount += 1;
      document.querySelector(".bag-count").textContent = String(bagCount);
      showToast(`${button.dataset.addToBag} añadido a tu bolsa.`);
    });
  });
})();
