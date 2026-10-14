# Implementation ledger — LoL Live Widget v1.0

- Baseline: 67a5022, README only; branch feat/lol-live-widget-mvp.
- Ruling: Use an isolated feature branch in the current checkout rather than another worktree. The workspace is empty and user authorized implementation; cost: changes visible in this checkout.
- Ruling: Phase 0 Windows validation cannot execute on this macOS host. Implement both alpha backends and Windows CI, keep native alpha opt-in until hardware verification. Cost: Windows release remains gated.
- Ruling: Provider credentials and approval absent. Live mode fails closed; replay is the default and visibly labelled. Cost: actual live adapter response compatibility remains unverified.
- Interfaces: detector emits MatchEvent to memory store; REST and SSE consume immutable snapshots; /sync supplies cursor to desktop stream. Shared contracts include DRAGON_SOUL.
- Tasks: [ ] foundations [ ] offline UI [ ] native window/settings [ ] collector [ ] detector [ ] sync integration [ ] packaging/docs.

- Detector RED: 5 failures, then 6/6 pass. Store RED: 5 missing behaviors, then 11/11 server suite pass.
- API RED: 2 missing endpoint failures, then 13/13 server suite pass.
- Client policy RED: 5 failures, then 5/5 pass. Stream/store RED: 2 failures, then 7/7 pass. UI RED: 2 failures, then 9/9 pass.
- OpenAPI generated; TypeScript directly aliases generated schemas.
- Typecheck initially failed because nullable Pydantic defaults become optional request fields in OpenAPI. stat formatter now treats undefined as unsupported as well as null.
- Rust SDK diagnosis: installed macOS27 SDK incompatible with current linker; SDKROOT=MacOSX15.4.sdk compiles and Rust tests pass 3/3. No system SDK changes.
- Desktop production bundle built; browser compact/expanded rendered with DEMO label.
- Ruling: Native backend opt-in, CSS default until Windows spike evidence; avoids treating platform compatibility as proven.

## Final review and verification

- Fresh reviewer: no Critical findings, five Important findings. All five reproduced with regression tests and fixed:
  - independent 60-second discovery / next live match switching;
  - observation chronology retains new-game events when prior history fills capacity;
  - first native alpha failure retains CSS opacity until native handoff succeeds;
  - ended summary keeps polling until terminal frame ingestion;
  - epoch replacement clears old pagination cursor.
- Additional RED→GREEN: reconnect permits new live ticker events; unknown settings version resets safely; rolling 20-second kills span adjacent frames; null correction breaks counter continuity.
- Pagination test fixture changed to a >20-second gap to avoid newly required aggregate events while independently testing cursor order.
- Final: minor (deferred): provider-specific health last_error is not assigned on all failures; authoritative top-level health/sourceError still reports the collector error.
- Final: minor (deferred): previous-history button can remain visible after cursor exhaustion and repeat an empty page.
- Latest local verification: server 20/20; desktop 15/15; Rust 3/3; TypeScript check and production Vite build pass.
- Expected failure-path console messages occur in client tests. Server suite emits one upstream Starlette/httpx deprecation warning, not a test failure.
- Actual local HTTP: matches and /sync returned valid replay JSON; SSE emitted state with epoch cursor. Intentional two-second stream sampling ended with curl timeout 28 because stream stays open.
- Ruling: Keep feature branch unmerged and unpublished. Implementation authorization does not require remote publishing; cost: user still needs to choose integration/deployment.
- Ruling: Two low-impact review notes deferred as above. Cost: provider sub-health may be optimistic, and exhausted history button can perform redundant reads.

## Status

- Foundations, offline UI, collector, detector, REST/SSE integration: implemented and locally verified.
- Windows commands, tray, atomic settings, geometry, installer configuration and Windows CI: implemented; host Rust compilation/unit tests pass. Windows build/runtime/installer/hardware checks remain unexecuted.
- Phase 0 Windows screenshot/alpha choice evidence: pending Windows hardware/VM.
- Actual live API validation, credentials/rights, official-match comparison and public release: pending; live mode fails closed without approval/key.
- CI workflow is prepared but not dispatched; no Windows installer artifact has been produced in this session.

- Code formatting normalized with Prettier/Ruff; Ruff check passes. Broad collector catches are intentional provider-boundary isolation.
