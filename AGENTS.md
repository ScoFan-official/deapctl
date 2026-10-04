<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

## Agent skills

### Issue tracker

The tracker IS the Trellis task system: specs/tickets land in `.trellis/tasks/` (spec → task dir + `prd.md`; ticket → child task + `blocked_by` meta). `.scratch/inbox/` holds raw inbound items awaiting triage. See `.trellis/spec/agents/issue-tracker.md`.

### Triage labels

Five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) as task `meta.triage` values. See `.trellis/spec/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` + `docs/adr/` at repo root, created lazily by `/domain-modeling`. See `.trellis/spec/agents/domain.md`.

### Multi-agent split

- **Devin** (`.devin/skills/`): implementation and bug fixes through the Trellis lifecycle above.
- **Antigravity** (`.agents/skills/`, `.agents/rules/`): owns `README.md` maintenance — see `.agents/rules/readme-ownership.md`.
