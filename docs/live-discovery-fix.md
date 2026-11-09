# Live discovery fix — 2026-11-04

Goal: discover TES–IG and future live Worlds matches missing from schedule HTML, without changing the UI or adding dependencies.

Evidence: schedule HTML contains 40 completed and 6 unstarted events, but no TES–IG. The official public `homeEvents` persisted query with eventState=inProgress returns TES–IG (115660540726095109), game 3 (115660540726095112).

Approach: merge public GraphQL live events into the existing HTML schedule before existing normalization. Live events override stale HTML entries. Reuse httpx, the existing access/error handling, and frame collection. Use the current registered public query ID; record that a site deployment can require updating it. No API keys, UI options, new dependencies, or guessed game IDs.

Plan:
- [x] Add regression tests for a live match absent from HTML, stale HTML, game transitions, and malformed/query errors. Watch failure.
- [x] Add the public query to the existing provider; preserve approval, HTTP errors, league filter, and completed-match behavior.
- [x] Run the server suite; actual TES–IG source timestamps and gold advanced in two samples on 2026-11-04. Final server suite: 50 passed.
- [x] Package corrected server into the existing Mac app; signature verified, patch/source provided. See final runtime verification limitation below.

The fix changes the shared collector only; existing desktop UI and platform packaging are reused.

Additional root cause: feed 400 BAD_QUERY_PARAMETER explicitly requires each window end to be at least 50 seconds old. Previous now−20s logic violated this. Latest window start is now−60s (rounded down to ten seconds), preserving the existing overlap and scan logic. Regression test reproduces the rejection and passes after correction.

Baseline: 43 server tests passed outside socket sandbox. Final (2026-11-05): 50 passed, one pre-existing Starlette/httpx deprecation warning.

Public query provenance: https://lolesports.com/_next/static/chunks/3e8z8q4bdpnuz.js — homeEvents persisted query e4da9fd0ab89ecdb783912d74799688d1f52f1edc9b87497d3409c74d9b4291a, retrieved 2026-11-04. No credentials used.

Final set-start fix: HTTP 204 from the statistics feed means no published frames yet. Treat this as an empty window, not a JSON parsing/source failure. Regression test failed before the fix and passed after it.

## Verification and limits

- Final source suite: 50 passed; Ruff check and formatting passed. The single Starlette/httpx deprecation warning existed at baseline.
- On 2026-11-04 the corrected provider collected TES–IG game 3: timestamps advanced from 00:33:59.924Z to 00:34:09.210Z; TES gold 31,138 → 31,346 and IG gold 33,760 → 33,981.
- The earlier frozen app returned real TES–IG game-3 state and an SSE state event. Its next request hit a transient ConnectTimeout, so continuous frozen-runtime success was NOT established.
- The final app includes the HTTP-204 fix and passes `codesign --verify --deep --strict`. PyInstaller build passed.
- Final frozen smoke execution on 2026-11-05 is blocked in this sandbox: Failed to initialize sync semaphore / semctl: Operation not permitted. This is an environment restriction, not a successful runtime test.
- Current official discovery query succeeds, with 5 scheduled matches and no active match at verification time.
- Native UI verification was unavailable because the computer-use tool timed out. No app was installed or replaced in /Applications.
- Query IDs are maintained by the public website and can change in a future deployment.

Ponytail instructions applied directly from https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md ; no global plugin or lifecycle hooks installed.

## Platform delivery status (2026-11-05)

The collector source is shared by Windows and macOS. Packaging stays separate:

| Platform | Build entry point | Current fix status |
| --- | --- | --- |
| Windows x64 | `scripts/build_windows_portable.py`, `.github/workflows/windows-portable.yml` | Source fix included; a new portable EXE still needs a Windows build and smoke test. Existing released EXE is unchanged. |
| macOS arm64 | `scripts/build_macos_portable.py` | Local repaired app packaged and signature verified. Final runtime checks have the limitations above. Existing GitHub DMG is unchanged. |

Do not label an older platform binary as containing this fix. Publish rebuilt platform artifacts only with their own build and validation evidence.

## Released v0.2.1 (2026-11-09)

The earlier local sandbox limitations and unreleased-binary status above are historical. Both platforms have now been built and smoke-tested in native GitHub Actions environments from fe4cd5679055f2cbbae6399f4f645e569b304412.

- Windows x64 EXE: https://github.com/BapSangE/lol_live_widget/actions/runs/42539786226 — build, tests, and frozen-server smoke test passed.
- macOS arm64 DMG: https://github.com/BapSangE/lol_live_widget/actions/runs/42539788353 — build, tests, frozen-server smoke test, app signature verification, and DMG verification passed.
- Release: https://github.com/BapSangE/lol_live_widget/releases/tag/v0.2.1 — separate EXE and DMG assets with SHA256SUMS.txt.
- These checks establish native packaging and server startup, not full GUI or a complete live series observed on both platforms.
