# 03 - ARTEMIS as exploration baseline

Ticket: `tickets/03-artemis-baseline.md`. Question: does ARTEMIS expose enough step-level action and UI-state detail to produce a compilable trace, or only a high-level result? Is it usable as an exploration baseline later?

## Verdict

- **Compilable trace: yes, mostly, but only from its internal store, not from the MCP result.** `mobile_run_task` returns a detached background task and a `trace_id`. Every step is persisted in a SQLite database with the action, normalized tap point, the target element's text/bounds/resource-id/class, and a full UIAutomator hierarchy per screenshot. That is enough to derive Maestro steps and checkpoints. The MCP `mobile_inspect_trace` view is a lossy, LLM-oriented rendering of the same data, so a trace compiler should read the SQLite store directly.
- **Fidelity problems exist.** The recorded target metadata was wrong in 2 of 3 inspected tap/type steps (see "Evidence quality"). Recorded actions include failed steps. Resource IDs were empty for the Quiet Hours app. A compiler must re-derive the locator from the stored hierarchy rather than trust `target_text`.
- **Baseline: usable, as a black-box "agent explores, then one-shot/compile" comparator, not as a step-controlled explorer.** It is public, Apache-2.0, Google-authored. It does not give ProofLoop the device boundary (allowlist, blocked-action record), because Pro includes `adb` shell tools and its safety net is its own. Treat it as an external configuration in the eval, not a backend.

## Method and sources

Primary sources only: the upstream repo and a local checkout of it, plus data from real runs stored in that checkout.

- Upstream: https://github.com/google/artemis (README, `mcp_server/README.md`).
- Local checkout: `/Users/samirsayyed/Desktop/artemis`, `origin` = `https://github.com/google/artemis.git`, HEAD `371aa6df`, committed 2026-09-11, Apache-2.0 (`LICENSE`). Paths below are relative to it.
- Real trace data in `traces/` (`data_engine.db`, two sessions against the Quiet Hours app, a physical device `RZCX90S8HAJ`, 1080x2340, Flash profile).
- Not used as evidence: third-party write-ups and forks surfaced by web search. A Japanese third-party analysis claims the 99.1% AndroidWorld figure is not on the official leaderboard; I did not verify that, and it does not affect this question.
- I did not run ARTEMIS myself; findings come from source and two pre-existing traces. Claims about Pro-profile trace contents come from source/docs only (the stored traces are Flash).

## What the MCP surface exposes

Source: `mcp_server/README.md`, `mcp_server/tools/inspect_trace.py`.

- Five tools: `mobile_run_task`, `mobile_manage_task` (status/stop/inject_instruction), `mobile_get_device_state` (screenshot or OCR+XML hierarchy), `mobile_inspect_trace`, `mobile_diagnose`.
- `mobile_run_task` is asynchronous (detached subprocess); status and results appear in `<trace_dir>/status.json`.
- `mobile_inspect_trace` actions: `view_summary`, `search`, `view_step_screenshots` (before / after-if-failed / action-overlay image paths), `view_step_details` ("full replay of one step exactly as the agent's own context showed it": screen, reasoning, tool calls, planned action, safety-net interception, execution result; coordinates normalized). Search results are capped server-side.
- So the MCP layer does return step-level data, but oriented to an agent reading it, not to a compiler.

## What is actually stored per step

Source: `traces/data_engine.db` schema and rows; `artemis/mcp/action_executor.py` (lines ~440-485).

Tables: `sessions` (goal, status, device info, video path), `steps`, `images`, `traces` (typed event log: `action`, `llm_call`, `tool`, `log`, `agent`), plus `history_chunks`, `background_tasks`, `failed_outputs`.

- `steps.action_taken` (JSON), example fields: `action` (`click`, `input_text`, `report_task_status`), `coordinates` and `normalized_coordinates` in a 0-1000 space (converted from pixels as `v*1000/width|height`), `args` (`target` index, `target_description`, `text`, `clear_exist`), and the resolved element: `target_text`, `target_bounds` (normalized), `target_resource_id`, `target_class`.
- `steps.last_execution_result` (JSON): `status` (`dispatched` / `failed`) and a result string; failures carry the error text (for example "Invalid target index 253").
- `steps.pre_image_name` / `post_image_name` link to `images`, each with `ui_tree` (full UIAutomator hierarchy: text, resource-id, content-desc, class, package, clickable/checked/enabled, bounds, parsed_bounds) and `ocr_result`. In the sample DB 12 of 12 images had a `ui_tree`; 1 had OCR. `post_image_name` is null on failed steps.
- `steps.extra_metadata`: token usage and perceptual hashes (`pre_image_dhash`, `post_image_dhash`) of before/after screens.
- Also: per-step model reasoning (`operator_raw_thinking`), a screen recording (`recording.mp4` with `recording.json` offsets), and `traces/<id>/steps.json` (empty `[]` in the sample - do not rely on it).
- Pro profile adds a Markdown task plan with `verify`/`assert` checkpoints at `<trace_dir>/notes/task_plan.md` and Checker verdicts (README "Pro Profile"; `inspect_trace.py` `view_summary` reads the plan file). Unverified by me against a Pro run.

## Evidence quality (from the two sample sessions)

Session `0c896a2a...` (Flash, goal: create a Quiet Hours schedule "ARTEMIS Test"; ended `cancelled`, 12 steps) and session `692d75e1...` (1 step, status `completed`, a single `report_task_status`).

- Of the 12 steps, 10 are `click` and 2 `input_text`; 5 had an empty `target_text` and most carried a null result `post_image` only when failed. Several steps were failed retries (stale index 253 against a 36-element list).
- Recorded target metadata did not match intent: step 2 typed "ARTEMIS Test" with `target_text` "Quick Start Templates"; step 3's `target_description` was "Saturday button" but `target_text` was "Create Schedule" with bounds around the screen title. The click coordinate is trustworthy (it is what was dispatched); the element attribution is not.
- `target_resource_id` was empty on every recorded step. The hierarchy shows `package=com.sam.quiethours` with empty `resource-id`, so locators must be text or content-desc.
- Implication: the compiler must treat the action record as "what was tapped where", then resolve the locator itself against the pre-step `ui_tree` at that coordinate, and verify the effect against the post-step tree. It cannot copy `target_text`.

## Fit against ProofLoop requirements

| Need (SPEC) | ARTEMIS | Note |
| --- | --- | --- |
| Every action recorded with visible UI state (story 12) | Yes: action + pre/post hierarchy + screenshots | Read DB, not MCP summary |
| Screenshots and recording retained (13) | Yes | `recording.mp4`, `images/` |
| Dynamic locators first, coordinate fallback (18-20) | Partial | Coordinates reliable; element attribution unreliable; resource IDs empty for this app |
| Explicit waits derived from observed signals (14, 21) | Not provided | Waits are model-turn latency; compiler must infer from hierarchy diffs |
| Checkpoints / assertions (22) | Pro Checker plans with `verify`/`assert` | Free-text goals, not ProofLoop's structured plan |
| Device boundary with allowlist, blocked-action record (38-42) | No | Pro has ADB shell, history/video tools; own Safety Net is model/XML-based, not ProofLoop's allowlist |
| Untrusted-text separation (40) | Not guaranteed | Own prompts only |
| Clean snapshot per run (9) | No | Uses the connected device as-is; env manager is ProofLoop's job |
| Determinism / seeds | No | Sample trace shows a drifting path and cancellation |

## Recommendation for the map

1. Do not make ARTEMIS the device backend; keep mobile-mcp per SPEC.
2. Keep ARTEMIS as an optional external baseline (configuration "ARTEMIS explores, ProofLoop compiles from its SQLite trace, then the same Verifier"). Cost: an adapter that reads `data_engine.db` (sessions/steps/images) and normalizes to ProofLoop's trace schema (ticket 06).
3. When tracing, pin the schema fields above and add a sanity check that discards `target_text` unless it matches the hierarchy node at the tapped coordinate.

## Open items not resolved

- Pro-profile traces (plan, Checker output) not inspected directly; only documented in README/source.
- ARTEMIS needs a configured multimodal model API key; the local config uses an OpenAI-compatible `minicpm-v-4.7-1b` (`/Users/samirsayyed/Desktop/quiet-hours/artemis-local.jsonc`). Cost per run under Sonnet-class models was not measured.
- Whether `status.json` and the MCP result include a structured final result beyond text was not examined.
