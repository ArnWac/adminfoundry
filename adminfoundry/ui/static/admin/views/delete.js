// Delete confirmation page.
//
// Shows a small summary of the record so the user knows what they're about
// to remove, then sends DELETE on confirm.

import { APIError, admin } from "../api.js";
import { getResourceContract } from "../contract.js";
import { el, mount, showToast } from "../dom.js";
import { formatValue } from "../format.js";

const cfg = window.ADMINFOUNDRY || {};

export async function mountDelete(root, resource, recordId) {
  const contract = await getResourceContract(resource);

  let record;
  try {
    record = await admin.read(resource, recordId);
  } catch (err) {
    const message = err instanceof APIError ? err.message : String(err);
    mount(root, errorScreen(resource, message));
    return;
  }

  const summary = el("dl", { class: "detail-grid" });
  for (const field of contract.fields.slice(0, 5)) {
    summary.appendChild(el("dt", {}, prettify(field.name)));
    const formatted = formatValue(record[field.name], field);
    summary.appendChild(el("dd", { class: formatted.muted ? "muted" : "" }, formatted.text));
  }

  const errorBox = el("p", { class: "form-error", hidden: true });
  const confirmBtn = el("button", { class: "btn btn-danger" }, "Delete permanently");
  const cancelLink = el(
    "a",
    {
      class: "btn btn-link",
      href: `${cfg.uiPath}/${resource}/${encodeURIComponent(recordId)}`,
    },
    "Cancel"
  );

  confirmBtn.addEventListener("click", async () => {
    errorBox.hidden = true;
    confirmBtn.disabled = true;
    try {
      await admin.remove(resource, recordId);
      showToast(`${contract.label} deleted.`);
      window.location.href = `${cfg.uiPath}/${resource}`;
    } catch (err) {
      confirmBtn.disabled = false;
      const message = err instanceof APIError ? err.message : String(err);
      errorBox.textContent = message;
      errorBox.hidden = false;
    }
  });

  mount(
    root,
    el("nav", { class: "crumbs" }, [
      el("a", { href: `${cfg.uiPath}/dashboard` }, "Dashboard"),
      " / ",
      el("a", { href: `${cfg.uiPath}/${resource}` }, contract.label_plural),
      ` / ${prettify(recordId)} / Delete`,
    ]),
    el("div", { class: "page-header" }, [
      el("h1", {}, `Delete ${contract.label.toLowerCase()}?`),
    ]),
    el("div", { class: "card" }, [
      el("p", {}, "This action cannot be undone."),
      summary,
      el("div", { class: "form-actions" }, [confirmBtn, cancelLink]),
      errorBox,
    ])
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
