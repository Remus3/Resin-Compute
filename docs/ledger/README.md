# Per-session ledger

One file per session: `session-<n>.md`, where n is the `SESSION:` counter in
`RSC-NEXT-SESSION.txt`. The newest session is the highest n.

- `/done` writes the session's file here and adds one line for it to the
  "Session files" list in `docs/LEDGER.md`, newest first. A session file is
  written once and not rewritten by later sessions, so `/done` no longer
  rewrites a half-megabyte file every session.
- Inside a session file the entries are newest first, in the same shape the
  historic ledger used: a `## YYYY-MM-DD - <what landed>` heading, then what
  was actually measured rather than what was intended.
- `docs/LEDGER.md` stays the index and keeps the ledger's preamble. Its historic
  body (everything before per-session files) lives verbatim in
  `archive-<YYYY-MM>.md` month files here, newest first.
- Closed `ROADMAP.md` entries go to `docs/roadmap-archive/<YYYY-MM>.md`, not here.
