<!-- markdownlint-disable MD013 -->

# Drain flow (visual reference)

Companion diagrams for the `dev-flow:draining-beads` skill and the `/drain`
command. These are a human-oriented map of control flow that the skill prose
specifies authoritatively — when this doc and the skill disagree, the skill (and
the spec it cites) wins. See:

- `dev-flow/skills/draining-beads/SKILL.md` — sentinel design, 12-step protocol,
  halt conditions, lessons mechanism, edge cases
- `dev-flow/commands/drain.md` — operator entry point (pre-flight, create bead,
  emit `/goal` condition)
- `dev-flow/commands/drain-with-worker.md` + `dev-flow/references/drain-with-worker.md`
  — detached cmux worker + surface-aware watchdog
- `docs/superpowers/specs/2026-05-22-drain-skill-design.md` — design spec (source
  of truth)

## 1. Controller / worker split and the `/goal` loop

`/drain` (the controller turn) only sets up state and **emits** the `/goal`
worker condition; it never fires `/goal` itself (a user-only built-in — ADR
`fhsk-e4i`). A user or driver submits that condition to a worker session, whose
Stop hook re-fires it once per bead until the sentinel is met or a halt clears
the goal.

```mermaid
flowchart TD
    op(["operator runs /drain &lt;mode&gt; &lt;scope&gt;"]) --> pre{"pre-flight<br/>state OK?"}
    pre -->|no| refuse["refuse with reason"]
    pre -->|yes| bead["create drain bead<br/>bd create type=drain"]
    bead --> sentinel["compose sentinel + stamp metadata"]
    sentinel --> emit["emit /goal worker condition"]
    emit --> submit(["user / cmux / SDK driver<br/>submits the condition"])
    submit --> worker["worker session: one bead per turn"]
    worker --> stop{"Stop hook:<br/>goal met?"}
    stop -->|no, re-fire condition| worker
    stop -->|yes, clean sentinel| finish["autonomous finish (see §3)"]
    worker -.->|structural halt| halt["/goal clear + PushNotification<br/>bead stays in_progress, resumable"]

    classDef gate fill:#fde68a,stroke:#b45309
    classDef stop fill:#fecaca,stroke:#b91c1c
    classDef done fill:#dcfce7,stroke:#15803d
    class pre,stop gate
    class refuse,halt stop
    class finish done
```

## 2. Per-iteration protocol (one bead per `/goal` re-fire)

Each re-fire runs exactly one bead through the 12-step body. Step 0 guards
workspace isolation; step 1 checks the sentinel (and, when met, hands off to the
autonomous finish in §3); steps 2 and the rejection/dirty-tree branches are the
structural halts. Two details the diagram compresses: the rejection
circuit-breaker is recorded at step 10 and only *trips* on the next re-fire's
step 2 (which scans `rejection:`/`halt:` notes written by prior iterations), and
a lost claim race at step 5 restarts the iteration rather than proceeding.

```mermaid
flowchart TD
    fire(["/goal re-fire"]) --> s0{"step 0: workspace<br/>isolated?"}
    s0 -->|no| haltIso["note halt + /goal clear + exit"]
    s0 -->|yes| s1{"step 1: sentinel met?"}
    s1 -->|yes| done["close drain bead<br/>then autonomous finish, §3"]
    s1 -->|no| s2{"step 2: prior halt note<br/>or rejection N=3+ note?"}
    s2 -->|yes| haltCB["note halt + /goal clear + exit"]
    s2 -->|no| s34["steps 3-4: read lessons,<br/>pick next ready bead"]
    s34 --> empty{"queue empty but<br/>sentinel unmet?"}
    empty -->|yes| haltStall["halt: stalled queue"]
    empty -->|no| s56["steps 5-6: claim + load context"]
    s56 --> s7["step 7: dispatch implementer subagent"]
    s7 --> blocked{"implementer<br/>BLOCKED?"}
    blocked -->|yes| haltBlk["halt: blocked on task"]
    blocked -->|no| s8{"step 8: two-stage<br/>review pass?"}
    s8 -->|no, rejected| s10["step 10: reopen,<br/>record rejection round"]
    s10 --> s11
    s8 -->|yes| s9["step 9: bd close task"]
    s9 --> s11{"step 11: tree clean?"}
    s11 -->|no| haltDirty["halt: dirty tree"]
    s11 -->|yes| s12(["step 12: iteration ends<br/>Stop hook re-fires"])
    s12 --> fire

    classDef gate fill:#fde68a,stroke:#b45309
    classDef stop fill:#fecaca,stroke:#b91c1c
    classDef done fill:#dcfce7,stroke:#15803d
    class s0,s1,s2,empty,blocked,s8,s11 gate
    class haltIso,haltCB,haltStall,haltBlk,haltDirty stop
    class done done
```

## 3. Terminal path: autonomous finish at the clean sentinel

When the sentinel is met, the worker finishes the branch **autonomously** — no
menu, no prompt — by invoking `dev-flow:finishing-a-development-branch` in its
non-interactive mode (ADR `fhsk-8g6`). The action is fixed to Option 2 (push +
create PR) followed by the `/review-pr` gate. Merge, keep, and discard stay
human-only. The drain bead is closed **only after a clean finish**; an aggregate
test failure or a push/PR failure routes to halt condition #3 and leaves the
drain bead `in_progress` for resume.

```mermaid
flowchart TD
    met(["sentinel met"]) --> note["bd note result: complete"]
    note --> invoke["invoke finishing-a-development-branch<br/>(autonomous mode)"]
    invoke --> tests{"tests pass?"}
    tests -->|no| haltTests["drain halt #3:<br/>bead stays in_progress"]
    tests -->|yes| push["worker pushes branch + opens PR<br/>(Option 2 — no menu)"]
    push --> ok{"push / PR<br/>succeeded?"}
    ok -->|no| haltVcs["drain halt #3:<br/>bead stays in_progress"]
    ok -->|yes| gate["/review-pr &lt;n&gt;"]
    gate --> verdict{"verdict?"}
    verdict -->|changes requested| addr["/address-findings &lt;n&gt;"]
    addr --> gate
    verdict -->|pass| close["bd close drain bead<br/>(completed cleanly)"]
    close --> notify(["PushNotification:<br/>drain complete, PR open"])

    classDef gate fill:#fde68a,stroke:#b45309
    classDef stop fill:#fecaca,stroke:#b91c1c
    classDef done fill:#dcfce7,stroke:#15803d
    class tests,ok,verdict gate
    class haltTests,haltVcs stop
    class notify done
```

## Related ADRs

| ADR | Decision |
|-----|----------|
| `fhsk-thw` | Use `/goal` over `/loop` for autonomous bead-queue drains |
| `fhsk-e4i` | Never invoke `/goal` from a skill; emit the condition for a user/driver |
| `fhsk-eqt` | Store the iteration protocol in the skill, not the `/goal` condition |
| `fhsk-zds` | Use the drain bead as the cross-session handoff carrier |
| `fhsk-ce3` | Store drain lessons in bd notes, not the prompt body |
| `fhsk-dtk` | Gate detached worker launch behind `AskUserQuestion`, never auto-fire |
| `fhsk-8g6` | Drain finishes the branch autonomously (push + PR) at the clean sentinel |
