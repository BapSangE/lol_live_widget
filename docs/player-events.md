# Named player kill/death events

Goal: preserve source player names and per-player cumulative kills/deaths, then show independent deltas in the existing history and ticker. Never invent a killer-victim pair.

Changes:
- Optional internal RawFrame.players preserves backward compatibility with older demo/replay fixtures. Source metadata supplies names; missing names are skipped, invalid/missing counters stay null.
- Per-game/player high-water counters prevent bootstrap, duplicate, correction, missing-data, and new-set false alerts. Complete named kill coverage suppresses duplicate team KILL_DELTA records; partial coverage retains the team total.
- Add PLAYER_KILL and PLAYER_DEATH to the public event enum and generated client types. Existing single strongest-event ticker behavior remains: all events stay in history, while simultaneous alerts share one ticker.
- Add named filters and enable them once when older settings migrate. playerEventsInitialized persists through Rust serialization; later opt-outs remain respected. The fallback filter is labelled Team kills (player information unavailable).

Verification:
- Server: 56 tests passed, including real LCK metadata/K/D → normalization → detector → store/sync/SSE messages.
- UI: 32 tests passed; TypeScript and production build checked.
- Independent code review found no definite correctness defects. Existing normalized historical replay files do not contain player data, so those older replay fixtures still use team events. New raw-feed captures exercise named events.

Scope: no new external API, dependency, exact kill attribution, new ticker queue, or champion UI. Windows and macOS builds use the same collector with separate native packaging.
