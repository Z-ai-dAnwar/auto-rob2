# Maintainability Refactor Design

## Purpose

Improve codebase maintainability while preserving the current RoB 2 pipeline behavior. The refactor should make fast iteration easier by reducing large-file friction, clarifying module boundaries, and removing obvious dead or redundant code without changing public APIs, output schemas, prompts, deterministic judgment behavior, or runtime configuration.

## Non-Goals

- No broad package reorganization.
- No prompt rewrites unless needed to preserve imports during a move.
- No deterministic judge behavior changes.
- No output JSON or Markdown schema changes.
- No CLI or public API breaking changes.
- No real LLM calls in tests.
- No refactors that make domain methodology harder to inspect.

## Public Compatibility

These surfaces must remain stable:

- `main.py` assessment CLI behavior.
- `benchmark.py` benchmark CLI behavior.
- `rob2_pipeline.pipeline.run_assessment(...)`.
- LangGraph node names and graph behavior.
- Existing environment variables and defaults.
- Generated report/data filenames and payload shapes.
- Existing tests that encode behavior.

When moving code, keep compatibility re-exports or thin wrappers where they reduce import churn for active development.

## Recommended Approach

Use a targeted, staged refactor. Each stage should be small enough to review independently and should run focused tests before moving to the next risky stage.

1. Hygiene baseline:
   - Fix current Ruff issues.
   - Remove trivial unused imports or obviously dead code.
   - Avoid unrelated formatting churn.

2. Split `rob2_pipeline/pdf_ingestion.py` along existing responsibilities:
   - Docling conversion and text extraction.
   - Docling document representation and section parsing.
   - Paper evidence extraction and XML parsing.
   - Keyword and fallback evidence helpers.
   - Censoring/context helpers.

   Keep `rob2_pipeline.pdf_ingestion` as the stable import facade during the refactor.

3. Split `rob2_pipeline/nodes/evidence_packets.py` by concern:
   - Evidence contract definitions.
   - Candidate and fallback source selection.
   - Missing-evidence and negative-flag detection.
   - Packet grading and fact extraction.
   - Prompt-facing packet rendering.

   Keep `evidence_packet_builder_node`, `build_evidence_packets`, and `packet_block_for_domain` import-compatible.

4. Reduce repeated domain-node scaffolding only where behavior is genuinely shared:
   - Consider a helper for simple single-call SQ nodes such as D1, D3, and D5.
   - Leave D2 and D4 explicit because they contain branching and outcome/effect-sensitive behavior.
   - Do not hide domain-specific prompt, parser, or judge behavior behind a generic framework.

5. Documentation and verification:
   - Update architecture docs only when module paths or responsibilities change.
   - Keep test additions focused on moved helpers and compatibility imports.
   - Run focused tests for touched subsystems after each slice.
   - Run the full test suite before declaring the refactor complete.

## Risk Controls

- Prefer moving functions unchanged before editing internals.
- Keep compatibility facades until the active development branch no longer needs old imports.
- Avoid changing prompt text, XML tag expectations, and judge decision tables.
- Use tests to catch behavior drift before applying simplification.
- Keep commits grouped by subsystem so active development can rebase or review them easily.

## Success Criteria

- Full test suite passes.
- Ruff check passes.
- Large hotspot modules are smaller and have clearer responsibilities.
- Existing CLI/API calls continue to work.
- Existing output schemas remain unchanged.
- The refactor makes future feature changes easier by clarifying where ingestion, packet construction, retrieval, judging, and reporting logic live.
