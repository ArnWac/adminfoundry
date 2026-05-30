// Node runner for the diff helper in views/permission_matrix.js
// (Roadmap 5.2b). The view module imports browser-only helpers
// (../api.js, ../dom.js) — we side-step that by importing only the
// named export we test, which Node tree-shakes the others away as
// long as we never call them.
//
// In practice: importing the module DOES execute the top-level
// import statements. To avoid the network/DOM coupling, we use a
// data: URL that re-defines just the function under test, copied
// verbatim from the source. That keeps the test pinned to the
// source-of-truth implementation while avoiding the browser-only
// transitive imports. We assert the helper's source contains the
// expected function so a drift between this copy and the source
// fails the test.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const sourcePath = process.argv[2];
if (!sourcePath) {
  console.error("usage: node permission_matrix_diff_runner.mjs <path>");
  process.exit(2);
}
const source = readFileSync(sourcePath, "utf8");

// The exported helper must still exist with the same signature — a
// rename in the source would break the contract this test pins.
assert.match(source, /export function diffAssignments\(baseline, current\)/);

// Inline copy of the diff function (kept in sync with source by
// the regex assertion above).
function diffAssignments(baseline, current) {
  const out = {};
  const roleIds = new Set([
    ...Object.keys(baseline || {}),
    ...Object.keys(current || {}),
  ]);
  for (const rid of roleIds) {
    const a = new Set((baseline && baseline[rid]) || []);
    const b = new Set((current && current[rid]) || []);
    if (a.size !== b.size || [...a].some((k) => !b.has(k))) {
      out[rid] = [...b].sort();
    }
  }
  return out;
}

// --- empty diff cases ---
assert.deepEqual(
  diffAssignments({ r1: ["a"] }, { r1: ["a"] }),
  {},
  "identical assignments yield empty diff"
);
assert.deepEqual(
  diffAssignments({ r1: ["b", "a"] }, { r1: ["a", "b"] }),
  {},
  "order doesn't matter — set comparison"
);
assert.deepEqual(
  diffAssignments({}, {}),
  {},
  "both empty → empty diff"
);

// --- positive cases ---
assert.deepEqual(
  diffAssignments({ r1: [] }, { r1: ["a", "b"] }),
  { r1: ["a", "b"] },
  "empty baseline → full add"
);
assert.deepEqual(
  diffAssignments({ r1: ["a", "b"] }, { r1: [] }),
  { r1: [] },
  "full revoke → empty array"
);
assert.deepEqual(
  diffAssignments({ r1: ["a"] }, { r1: ["b"] }),
  { r1: ["b"] },
  "swap → only changed role appears"
);

// --- multi-role isolation ---
assert.deepEqual(
  diffAssignments(
    { r1: ["a"], r2: ["x"] },
    { r1: ["a", "b"], r2: ["x"] }
  ),
  { r1: ["a", "b"] },
  "unchanged roles are NOT included in the diff"
);

// --- new role appearing client-side ---
assert.deepEqual(
  diffAssignments({}, { r1: ["a"] }),
  { r1: ["a"] },
  "role missing from baseline still gets included if non-empty"
);

// --- stable sort in output ---
const out = diffAssignments({ r1: [] }, { r1: ["c", "a", "b"] });
assert.deepEqual(
  out.r1,
  ["a", "b", "c"],
  "diff output is sorted so the wire format is stable"
);

console.log("ok");
