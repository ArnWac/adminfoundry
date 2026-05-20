// Detail view: read-only render of one record.

import { APIError, admin } from "../api.js";
import { getResourceContract } from "../contract.js";
import { el, mount, showToast } from "../dom.js";
import { formatValue } from "../format.js";

const cfg = window.ADMINFOUNDRY || {};

export async function mountDetail(root, resource, recordId) {
  const contract = await getResourceContract(resource);
  let record;
  try {
    record = await admin.read(resource, recordId);
  } catch (err) {
    const message = err instanceof APIError ? err.message : String(err);
    mount(root, errorScreen(resource, message));
    return;
  }

  const grid = el("dl", { class: "detail-grid" });
  for (const field of contract.fields) {
    grid.appendChild(el("dt", {}, prettify(field.name)));
    const formatted = formatValue(record[field.name], field);
    const dd = el("dd", { class: formatted.muted ? "muted" : "" }, formatted.text);
    if (formatted.mono) dd.style.fontFamily = "ui-monospace, SFMono-Regular, monospace";
    grid.appendChild(dd);
  }

  mount(
    root,
    el("nav", { class: "crumbs" }, [
      el("a", { href: `${cfg.uiPath}/dashboard` }, "Dashboard"),
      " / ",
      el("a", { href: `${cfg.uiPath}/${resource}` }, contract.label_plural),
      ` / ${prettify(recordId)}`,
    ]),
    el("div", { class: "page-header" }, [
      el("h1", {}, `${contract.label} detail`),
      el("div", { class: "page-actions" }, [
        el(
          "a",
          {
            class: "btn",
            href: `${cfg.uiPath}/${resource}/${encodeURIComponent(recordId)}/edit`,
          },
          "Edit"
        ),
        el(
          "a",
          {
            class: "btn btn-danger",
            href: `${cfg.uiPath}/${resource}/${encodeURIComponent(recordId)}/delete`,
          },
          "Delete"
        ),
      ]),
    ]),
    el("div", { class: "card" }, grid)
  );
}

function errorScreen(resource, message) {
  return el("div", {}, [
    el("nav", { class: "crumbs" }, [
      el("a", { href: `${cfg.uiPath}/${resource}` }, "← back to list"),
    ]),
    el("div", { class: "card" }, el("p", { class: "form-error" }, message)),
  ]);
}

function prettify(name) {
  return String(name).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
