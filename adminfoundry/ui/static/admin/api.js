// HTTP client around fetch().
//
// Speaks the adminfoundry envelope:
//   { "error": { "code", "message", "fields?", "request_id?" } }
//
// Resolves to parsed JSON on 2xx. Rejects with APIError on 4xx/5xx.
// Auto-redirects to /login on 401.

const cfg = window.ADMINFOUNDRY || {};
const TOKEN_KEY = "adminfoundry_access";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
  isLoggedIn: () => !!localStorage.getItem(TOKEN_KEY),
};

export class APIError extends Error {
  constructor(status, payload) {
    const env = (payload && payload.error) || {};
    super(env.message || `HTTP ${status}`);
    this.status = status;
    this.code = env.code || `http_${status}`;
    this.fields = Array.isArray(env.fields) ? env.fields : [];
    this.requestId = env.request_id || null;
    this.envelope = env;
  }
  fieldErrors() {
    const map = {};
    for (const f of this.fields) {
      if (f && f.name) map[f.name] = f.message || "Invalid value.";
    }
    return map;
  }
}

export function redirectToLogin() {
  tokenStore.clear();
  if (window.ADMINFOUNDRY?.view !== "login") {
    window.location.href = `${cfg.uiPath}/login`;
  }
}

async function request(method, path, body, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const token = tokenStore.get();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const init = { method, headers };
  if (body !== undefined) init.body = JSON.stringify(body);

  const resp = await fetch(path, init);

  if (resp.status === 401 && !opts.skipAuthRedirect) {
    redirectToLogin();
    throw new APIError(401, await safeJson(resp));
  }

  if (resp.status === 204) return null;

  const payload = await safeJson(resp);
  if (!resp.ok) throw new APIError(resp.status, payload);
  return payload;
}

async function safeJson(resp) {
  try {
    return await resp.json();
  } catch {
    return null;
  }
}

// --- public API ---

export const auth = {
  login: (email, password) =>
    request("POST", `${cfg.authPrefix}/login`, { email, password }, { skipAuthRedirect: true }),
  me: () => request("GET", `${cfg.authPrefix}/me`),
  logoutAll: () => request("POST", `${cfg.authPrefix}/logout-all`),
};

export const admin = {
  contract: () => request("GET", `${cfg.adminPrefix}/_contract`),
  contractFor: (resource) => request("GET", `${cfg.adminPrefix}/_contract/${resource}`),

  list: (resource, { limit = 25, offset = 0, search = "" } = {}) => {
    const qs = new URLSearchParams({ limit, offset });
    if (search) qs.set("search", search);
    return request("GET", `${cfg.adminPrefix}/${resource}?${qs}`);
  },
  read: (resource, id) => request("GET", `${cfg.adminPrefix}/${resource}/${encodeURIComponent(id)}`),
  create: (resource, payload) => request("POST", `${cfg.adminPrefix}/${resource}`, payload),
  update: (resource, id, payload) =>
    request("PATCH", `${cfg.adminPrefix}/${resource}/${encodeURIComponent(id)}`, payload),
  remove: (resource, id) =>
    request("DELETE", `${cfg.adminPrefix}/${resource}/${encodeURIComponent(id)}`),

  runAction: (resource, action, ids) =>
    request("POST", `${cfg.adminPrefix}/${resource}/_actions/${action}`, { ids }),
};
