# Prose AI-Slop Patterns (`P-n`)

Catalog of prose-level AI-authorship tells for the `slop-hunter` agent, condensed
from the `humanizer` skill and 2025–2026 analyses of LLM writing. Applies
anywhere prose lives: standalone docs (`.md`, `.rst`, `.txt`) and code
comments/docstrings. Every finding raised against this catalog MUST cite its
pattern ID (Rule A).

No single P-pattern is proof — human writers use em-dashes and say "delve". The
signal is clustering. Raise a prose-slop finding when several tells co-occur in
one passage, not on an isolated word. Project conventions in `AGENTS.md` /
`CLAUDE.md` win (a repo that mandates emoji headings suppresses `P-7`).

## Patterns

### P-1 — Significance / legacy inflation

- Before: "Established in 1989, marking a pivotal moment in the evolution of the field."
- After: "Established in 1989 to publish regional statistics."

### P-2 — Promotional language

- Before: "a seamless, powerful, cutting-edge solution that boasts rich features"
- After: "supports CSV export and scheduled reports."

### P-3 — Superficial `-ing` pseudo-depth and the hedging-verb family

`ensuring`, `highlights`, `supports`, `reflects`, `underpins`, `aligns with`.
Per 2026 analyses this verb family is now the strongest lexical tell ("ensuring"
over-represented ~4.3x); a human just says what the thing does.

- Before: "The cache layer, ensuring robustness and highlighting the importance of speed, ..."
- After: "The cache layer reduces median latency from 200ms to 40ms."

### P-4 — Rule-of-three padding

- Before: "fast, reliable, and scalable"
- After: "handles 10k requests/sec."

### P-5 — Em-dash overuse

Weak on its own now (only ~18.5% of AI text carries one) — treat as
corroborating, never a standalone finding.

- Before: "The tool — which is new — works well — most of the time."
- After: "The tool is new and works well most of the time."

### P-6 — Title Case In Headings

- Before: `## Strategic Negotiations And Global Partnerships`
- After: `## Strategic negotiations and global partnerships`

### P-7 — Emoji-decorated headings or bullets

- Before: `🚀 **Launch:** ships in Q3`
- After: `The product ships in Q3.`

### P-8 — Inline-header vertical lists

- Before: `- **Performance:** improved through optimized algorithms.`
- After: prose that names the actual change.

### P-9 — Negative parallelism / tailing negation

- Before: "It's not just a tool, it's a movement." / "The options come from the
  selection, no guessing."
- After: "It is a tool." / "The options come from the selection."

### P-10 — Filler and excessive hedging

- Before: "In order to achieve this, it is important to note that it could
  potentially possibly help."
- After: "This helps."

### P-11 — Signposting

- Before: "Let's dive in. Here's what you need to know."
- After: (delete; start with the content)

### P-12 — Chatbot artifacts / cutoff disclaimers

- Before: "Great question! I hope this helps! While details are limited as of my
  last update, ..."
- After: (delete; state the fact directly)

### P-13 — The "crucial role in shaping" sentence shape

Statistically the single most formulaic LLM structure.

- Before: "Caching plays a crucial role in shaping system performance." /
  "is essential for" / "serves as a testament to"
- After: "Caching cuts repeated database reads."

### P-14 — Evidence-free intensifier adverbs

`significantly`, `effectively`, `directly`, `increasingly`, `vastly`. If a number
can't back the intensifier, cut it.

- Before: "significantly improves performance"
- After: "cuts p95 latency by 30%."

### P-15 — Vocabulary clichés

`delve`, `tapestry`, `realm`, `multifaceted`, `pivotal`, `bustling`,
`underscore`, `testament`, `foster`, `embark`, `myriad`, `leverage`, `robust`,
`holistic`, `comprehensive`, `synergy`, `paradigm`, `groundbreaking`,
`transformative`. Individually fine; clustered they produce press-release
texture.

- Before: "Let's delve into this comprehensive, robust tapestry of features."
- After: "These features cover authentication, billing, and reporting."

## Sources

- Wikipedia, "Signs of AI writing" (via the `humanizer` skill).
- Kobak et al. 2025, "excess vocabulary"; list at
  `github.com/berenslab/llm-excess-vocab`.
- writehuman.ai, "The Real Signature of AI Writing Isn't the Em-Dash Anymore"
  (2026) — hedging verbs, "crucial role in shaping", intensifiers.
- bloomberry.ai AI-writing-patterns database; telltale-ai; synkrlab phrase list.
