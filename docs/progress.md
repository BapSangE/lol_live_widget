# Implementation ledger — LoL Live Widget v1.0

## 2026-10-16 expanded history space and shared width

- Set compact and expanded width to 350px; compact remains 62px high, expanded is 400px, settings remains 300px.
- Expanded history reserves at least 120px for two ordinary records, with body scrolling on small work areas. Native geometry and initial size use the same dimensions.
- Desktop 19/19, Rust 3/3, TypeScript/Vite build pass. Browser measurements confirm compact 350×62, expanded 350×400 and a 120px history area with full statistics and archive notice visible.

## 2026-10-16 compact latest record

- Added a persistent latest-record row below the compact scorebar; current match/game only, ellipsis + full tooltip, click to expand history.
- Compact window is now 270×62. Updated native initial size, screen clamping, expansion bottom anchor and moved-window persistence calculations together.
- Verified in browser with the actual LCK archive: GEN/HLE score above, latest kill-window record below, retained after ticker expiry. Restored public live waiting mode after playback verification.
- Desktop 19/19, Rust 3/3, TypeScript/Vite production build pass. Windows runtime/DPI checks remain pending.

## 2026-10-16 public unofficial source

- Added opt-in `LIVE_PROVIDER=public`: public schedule HTML discovery and keyless stats feed. No page JavaScript execution or copied API keys.
- Added `scripts/run_live.py` and `라이브 위젯 실행.command`; existing LCK replay launcher retained.
- Real local HTTP: live mode healthy, 40 upcoming Worlds matches, no ongoing match at verification. Next listed start is 2026-10-17 03:00 KST.
- Fixed feed window advancement, empty-gap recovery, terminal-frame ingestion and shared discovery retry behavior; corrected connected/no-match UI to 경기 대기.
- Fresh verification: server 40/40, desktop 17/17, TypeScript/Vite production build, changed Python Ruff checks and diff whitespace checks pass.
- Live match score/event progression remains pending an actual ongoing match. See [public source validation](unofficial_live_validation.md) for evidence and known limitations.

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

## 2026 LCK capture validation

- Selected 2026-09-13 LCK final GEN–HLE game1 from public official schedule HTML; no web-app code execution or key extraction.
- Archived 7 contiguous windows (~69.263s, 363 raw frames / 333 unique / 30 identical duplicates), matching kill details, and independent terminal snapshot with SHA-256 provenance.
- Actual observed scorers: HLE Kanavi (Naafiri) +1, GEN Duro (Milio) +1. Cross-feed K/D/A matches.
- RED: direct detector omitted MULTIKILL_WINDOW because duplicate frames cleared its pending window. GREEN: exact duplicate returns without correction handling; capture regression passes.
- Ruling: Test only the acquired ~70-second sample and separate final snapshot. Do not call this full-game, live, or desktop playback verification; cost: those need further coverage.
- Fixture characterization: revision counts unique accepted frames (333), not raw transport frames (363). SSE test consumes response.read() before inspecting content.
- Server verification updated to 27/27; source capture report is docs/lck_2026_capture_test.md.
