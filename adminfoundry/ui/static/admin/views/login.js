// Login form. Lives on /admin/login (login.html), not inside app.html.

import { APIError, auth, tokenStore } from "../api.js";

const cfg = window.ADMINFOUNDRY || {};

export function mountLogin() {
  if (tokenStore.isLoggedIn()) {
    window.location.href = `${cfg.uiPath}/dashboard`;
    return;
  }
  const form = document.getElementById("login-form");
  const errorBox = document.getElementById("login-error");
  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.hidden = true;
    const data = new FormData(form);
    try {
      const res = await auth.login(data.get("email"), data.get("password"));
      tokenStore.set(res.access_token);
      window.location.href = `${cfg.uiPath}/dashboard`;
    } catch (err) {
      const message = err instanceof APIError ? err.message : "Sign in failed.";
      errorBox.textContent = message;
      errorBox.hidden = false;
    }
  });
}
