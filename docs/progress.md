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
