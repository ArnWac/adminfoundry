// Superadmin "enter tenant" action, shared by the tenant list + detail.
//
// Records a global tenant_access audit event (server-side), sets the active
// tenant to the returned slug, and reloads into the tenant dashboard. The
// superadmin keeps their own rights — this is a scoped context switch, not
// impersonation.

import { APIError, root, tenantStore } from "./api.js";
import { showToast } from "./dom.js";

const cfg = window.ASTERION || {};

export async function openTenant(tenantId) {
  try {
    const tenant = await root.enterTenant(tenantId);
    if (tenant && tenant.slug) {
      tenantStore.set(tenant.slug);
      window.location.assign(`${cfg.uiPath}/dashboard`);
    }
  } catch (err) {
    const message = err instanceof APIError ? err.message : String(err);
    showToast(`Could not open tenant: ${message}`, { type: "error" });
  }
}
