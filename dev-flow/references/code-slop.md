# Code AI-Slop Patterns (`C-n`)

Catalog of code-level AI-authorship tells for the `slop-hunter` agent. Each
finding raised against this catalog MUST cite its pattern ID (Rule A). Some
patterns are co-owned by another aspect and are deferred under Rule B — see the
`slop-hunter` agent for the deferral table.

The defining property of AI-native code is that the failure mode looks like the
success mode: it compiles, lints clean, has descriptive names, and handles every
exception, yet carries tells a careful author would strip. No single tell is
proof — weight findings by the clustering and density of tells in one change,
and prefer one well-evidenced finding over many speculative ones.

## Patterns

### C-1 — Comment restates the code

Co-owned with `comments`. A comment that narrates what the next line plainly
does.

- Before: `i += 1  # increment i by 1`
- After: `i += 1`

### C-2 — Vestigial edit narration

Co-owned with `comments`. Comments that describe the editing history, the
generation session, or the task — rather than the code. Includes assistant
bookmarks (`# I was here`, `// as requested`) and PR/ticket back-references in
source.

- Before: `# removed old logic; previously we looped here` / `// NEW:` /
  `# Here's the function you asked for`
- After: (delete the comment)

### C-3 — Defensive validation for impossible cases

Null/None checks or re-validation on values that internal code already
guarantees.

- Before: `user = get_current_user()  # never None here\nif user is None:\n    raise RuntimeError("no user")`
- After: `user = get_current_user()`

### C-4 — Single-use abstraction

Co-owned with `code` (YAGNI). A helper, wrapper, or interface introduced with
exactly one caller and no second use in sight.

- Before: a `def _format_name(n): return n.strip().title()` called once.
- After: inline the expression at its single call site.

### C-5 — No-consumer backwards-compat shim

Co-owned with `code` (YAGNI). A re-export, alias, or deprecation path for code
that has no existing consumers.

- Before: `# keep old name for compatibility\nlegacy_fn = new_fn`
- After: (delete; new code needs no migration path)

### C-6 — Padded docstring

Marketing adjectives, restating the signature, or multi-paragraph blocks on
trivial functions.

- Before: `"""A robust, efficient, scalable utility that adds two numbers together in a performant manner."""`
- After: `"""Add two numbers."""` (or no docstring for an obvious helper)

### C-7 — Test asserts the mock, not the outcome

Co-owned with `tests`. A test whose only assertion is that a mock/framework
method was called.

- Before: `service.save(x)\nassert mock_db.save.called`
- After: assert the observable result: `assert repo.get(x.id) == x`

### C-8 — Silenced rather than deleted dead code

`_unused` renames, `# noqa`, `// eslint-disable` used to quiet code that should
just be removed.

- Before: `_result = compute()  # noqa: F841`
- After: (delete the unused statement)

### C-9 — Swallowed errors / empty catch

Co-owned with `errors`. Over-broad handlers that discard exceptions or fabricate
silent fallbacks for conditions that should propagate.

- Before: `try:\n    do()\nexcept Exception:\n    pass`
- After: let it raise, or handle the specific exception with intent.

### C-10 — Speculative configuration

Co-owned with `code` (YAGNI). Flags, parameters, or config for hypothetical
future requirements with no current caller.

- Before: `def render(self, *, experimental_mode=False, future_format=None):` with neither argument used.
- After: `def render(self):`

### C-11 — Hallucinated import

A plausible-sounding module or symbol that does not exist. Severity `important`
(the code cannot run). Verify against the dependency manifest (`package.json`,
`requirements.txt`, `go.mod`); skip if no manifest is in the diff context.

- Before: `from express_validator_utils import sanitize`
- After: use a real, declared dependency.

### C-12 — Stale / deprecated API

A training-cutoff API that still "works" so it passes tests.

- Before: `const buf = new Buffer(data)` / `url.parse(req.url)`
- After: `const buf = Buffer.from(data)` / `new URL(req.url, base)`

### C-13 — Copy-paste clone

Co-owned with `simplify`. A large near-identical block duplicated with one field
changed where a human would extract a helper. Respect "three similar lines beats
a premature abstraction" — flag only sizable clones, not C-4-style premature
abstraction.

- Before: two ~30-line route handlers identical except for a table name.
- After: one parameterized handler.

### C-14 — Hardcoded placeholder secret/value

`critical` when it reaches a security-relevant path.

- Before: `SECRET_KEY = "your-secret-key"` / `password = "change-me"`
- After: load from configuration/environment; never commit placeholders.

### C-15 — Stylistic discontinuity

The change uses different naming, error-handling, or logging conventions than
the surrounding file/module — the clearest tell of code generated in isolation.

- Before: `camelCase` locals dropped into an all-`snake_case` module; `print()`
  debugging in a module that uses a structured logger everywhere else.
- After: match the conventions already in the file.

### C-16 — Comment-as-section-header banners

Banner comments and uniform comment density (evenly distributed explanatory
comments rather than clustered around the genuinely non-obvious).

- Before: `# ===== User Authentication =====`
- After: (delete; let function/section names carry the structure)

## Sources

- "5 Code Smells Only AI Creates" (dev.to) — hallucinated import, copy-paste
  clone, empty catch, stale API, over-engineered singleton.
- "Code Review Checklist for AI-Generated Code" (gitautoreview.com).
- "How to Identify If Code Is Written by AI" (aquilax.ai) — stylistic
  discontinuity, comment-as-section-header, what-not-why comments, uniform
  comment density, placeholder secrets.
- "9 Dead Giveaways That AI Wrote This Code" / LLM-native code-smell coverage.
