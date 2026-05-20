// adminfoundry minimal UI shell.
//
// Responsibility is intentionally small:
//   * Submit the login form, store the access token, redirect to /dashboard.
//   * Read the access token on app pages and redirect to /login if missing.
//   * Provide a sign-out button that clears the token and returns to /login.
//
// All real data rendering is driven by the contract + CRUD APIs and would be
// added in a follow-up phase. The shell only proves the route + auth wiring.
'use strict';

(function () {
  const cfg = window.ADMINFOUNDRY || {};
  const TOKEN_KEY = 'adminfoundry_access';
  const view = document.body.dataset.view;

  function token() { return localStorage.getItem(TOKEN_KEY); }
  function setToken(value) { localStorage.setItem(TOKEN_KEY, value); }
  function clearToken() { localStorage.removeItem(TOKEN_KEY); }
  function redirect(path) { window.location.href = cfg.uiPath + path; }

  if (view === 'login') {
    const form = document.getElementById('login-form');
    const err = document.getElementById('login-error');
    if (token()) {
      redirect('/dashboard');
      return;
    }
    if (!form) return;
    form.addEventListener('submit', async function (event) {
      event.preventDefault();
      err.hidden = true;
      const data = new FormData(form);
      try {
        const resp = await fetch(cfg.authPrefix + '/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: data.get('email'),
            password: data.get('password'),
          }),
        });
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({}));
          throw new Error(body.detail || 'Sign in failed.');
        }
        const body = await resp.json();
        setToken(body.access_token);
        redirect('/dashboard');
      } catch (e) {
        err.textContent = e.message;
        err.hidden = false;
      }
    });
    return;
  }

  if (!token()) {
    redirect('/login');
    return;
  }

  const signout = document.getElementById('signout');
  if (signout) {
    signout.addEventListener('click', function () {
      clearToken();
      redirect('/login');
    });
  }

  const root = document.getElementById('app-root');
  if (root) {
    root.dataset.loading = 'false';
    root.textContent = 'adminfoundry — ' + (cfg.view || 'view') +
      (cfg.resource ? ' / ' + cfg.resource : '') +
      (cfg.recordId ? ' / ' + cfg.recordId : '');
  }
})();
