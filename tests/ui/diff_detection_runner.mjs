// Node test runner for the pure-data detection in diff.js
// (Roadmap 5.1b). Invoked by tests/ui/test_diff_detection.py via
// subprocess so the JS contract is checked in CI without pulling in
// a full JS test framework.
//
// Reads the source path from process.argv[2] and runs assertions
// against the exported looksLikeAuditDiff function. Exits non-zero
// on failure with a message on stderr.

import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";

const sourcePath = process.argv[2];
if (!sourcePath) {
  console.error("usage: node diff_detection_runner.mjs <path/to/diff.js>");
  process.exit(2);
}

// diff.js imports ./dom.js + ./format.js — we only test the pure
// detection function, so stub out the helpers via an import map
// hack: we just don't call functions that touch them.
const module = await import(pathToFileURL(sourcePath).href);
const { looksLikeAuditDiff } = module;

// --- positive cases ---
assert.equal(
  looksLikeAuditDiff({ title: ["", "Hello"] }),
  true,
  "audit-shape: single field with [before, after]"
);
assert.equal(
  looksLikeAuditDiff({ title: [null, "Hello"], owner_id: ["alice", "bob"] }),
  true,
  "audit-shape: multiple fields, mixed null/value"
);
assert.equal(
  looksLikeAuditDiff({ count: [3, 5] }),
  true,
  "audit-shape: numeric values"
);

// --- negative cases ---
assert.equal(looksLikeAuditDiff(null), false, "null is not a diff");
assert.equal(looksLikeAuditDiff(undefined), false, "undefined is not a diff");
assert.equal(looksLikeAuditDiff({}), false, "empty object is not a diff");
assert.equal(looksLikeAuditDiff([1, 2]), false, "array is not a diff");
assert.equal(
  looksLikeAuditDiff({ title: "Hello" }),
  false,
  "plain string values are not a diff"
);
assert.equal(
  looksLikeAuditDiff({ title: ["only-one"] }),
  false,
  "1-element array is not a diff"
);
assert.equal(
  looksLikeAuditDiff({ title: ["a", "b", "c"] }),
  false,
  "3-element array is not a diff"
);
assert.equal(
  looksLikeAuditDiff({ title: ["", "Hello"], extra: { not: "an array" } }),
  false,
  "one bad field invalidates the whole blob"
);

console.log("ok");
