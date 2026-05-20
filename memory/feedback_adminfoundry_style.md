---
name: feedback-adminfoundry-style
description: How the user wants me to collaborate on the adminfoundry v1 refactor — pre-v1, no backwards compat, strict MVP, phase-by-phase with checkpoints.
metadata:
  type: feedback
---

The user is rebuilding adminfoundry as a pre-v1 clean rebuild. Do not optimize for backwards compatibility. Strict MVP per the v1 plan only — drop legacy features rather than keep them "just in case".

**Why:** The repo was previously a feature-heavy monolithic codebase. The user is deliberately tearing it back to a minimal v1 core (Registry → Contract → CRUD → TenantAuthContext → permission-key authz → minimal UI). Carrying forward the old surface would defeat the rebuild.

**How to apply:**
- When in doubt between "keep an attr to avoid breaking X" vs "drop it, the spec doesn't list it", drop it.
- For multi-phase work, run phase-by-phase with a checkpoint before each phase — the user wants to confirm scope/tradeoffs, not approve a single mega-PR.
- Audit + plan before code. The user picked "Audit + Plan first, then phase-by-phase with checkpoints" when offered execution modes.
- Don't commit unprompted. The pre-session refactor (huge deletion + addition) is unstaged on top of new work — that's intentional; ask before committing.
- When the user asks for "all phases", they mean the planned sequence, not parallel/autonomous bulk work.

See [[project-adminfoundry-v1-refactor]] for live state.
