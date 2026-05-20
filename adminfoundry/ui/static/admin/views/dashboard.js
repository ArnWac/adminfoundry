// Dashboard view: card grid of every registered resource.

import { getFullContract } from "../contract.js";
import { el, mount } from "../dom.js";

const cfg = window.ADMINFOUNDRY || {};

export async function mountDashboard(root) {
  const contract = await getFullContract();
  const models = (contract.models || []).slice().sort((a, b) =>
    a.label_plural.localeCompare(b.label_plural)
  );

  if (models.length === 0) {
    mount(
      root,
      el("div", { class: "page-header" }, el("h1", {}, "Dashboard")),
      el("p", { class: "placeholder" }, "No admin models are registered yet.")
    );
    return;
  }

  const cards = models.map((m) =>
    el("a", { class: "resource-card", href: `${cfg.uiPath}/${m.resource}` }, [
      el("h3", {}, m.label_plural),
      m.description ? el("p", {}, m.description) : null,
      el("span", { class: "btn btn-sm btn-link" }, "Manage →"),
    ])
  );

  mount(
    root,
    el("div", { class: "page-header" }, [
      el("h1", {}, "Dashboard"),
    ]),
    el("div", { class: "resource-grid" }, cards)
  );
}
