# Decisions log

One entry per decision, with its reason. Entries are never edited after the fact.
A change of mind is a new entry that names the one it replaces.

Seeded 2026-10-15.

| ID | Date | Decision | Reason | Status |
|----|------|----------|--------|--------|
| D001 | 2026-10-15 | Source is ANAC via the Open Contracting Partnership mirror, CC BY 4.0, treated as frozen (January 2020 to September 2025). | ANAC's own portal refused automated requests; the mirror serves bulk files. The mirror's update frequency is blank and its quality review dates from 2022. | settled |
| D002 | 2026-10-15 | DuckDB, single file. The gate lives in application code with an append-only decisions table, not in foreign keys. | Read-heavy columnar analytics, one writer, one laptop. Cost: no database-level enforcement, stated plainly in the README. | settled |
| D003 | 2026-10-15 | No dbt. Plain SQL files run in order by a thin Python runner. | dbt is already on the CV from the commerce platform; here it adds setup time and a dependency and shows nothing new. | settled |
| D004 | 2026-10-15 | Charts are rendered as SVG in Python. No JavaScript, no CDN. | Static files, identical rendering everywhere, fastest route to something working. | settled |
| D005 | 2026-10-15 | `site/` is committed although generated. | The git diff between runs shows which published numbers changed: an audit trail for a project about trustworthy numbers. | settled |
| D006 | | Treatment of RTI and consortia in entity resolution. | Decide after recon shows what the data carries (membership data may be absent). | **open** |
| D007 | 2026-10-15 | Comparability thresholds as written in `gate.toml`: min populatedness 0.50, max populatedness spread 0.20, volume ratio band [0.5, 2.0], max composition drift 0.15. | 0.50 mirrors the recon rule that excludes a year with under half of tenderer counts populated. The 2x volume band treats a doubling or halving as a change of population. Spread 0.20 and drift 0.15 are judgement calls with no empirical basis yet; they are fixed now precisely so they cannot be tuned to the results. | proposed: confirm before the first indicator run |
| D008 | 2026-10-15 | No chart ever ranks named entities by a risk indicator. | A leaderboard reads as an accusation whatever the caption says. | settled, permanent |
| D009 | 2026-10-15 | Named entities are restricted to legal persons. Sole traders (ditte individuali, liberi professionisti) appear only in aggregates. | A CC BY licence governs copyright, not data protection. Conservative route, no analytical cost. Not legal advice. | settled |
| D010 | 2026-10-15 | Four indicators, cuttable to two (awarded value, single-bidder share) if B4 is not done by the end of week 2. | Concentration depends on entity resolution and cannot be published without it. | settled |
| D011 | | Repository name, licence and site language. Proposed: `appalti-observatory`, MIT for code (data stays CC BY, credited separately), English prose with Italian terms in italics. | | **open** |
| D012 | 2026-10-15 | Labelled pairs split dev/test with a fixed seed. Test is opened once per recorded decision. | Same discipline as the RAG project. | settled |
| D013 | 2026-10-15 | Recon decision rules (see `docs/recon.md`) are committed before any recon query is run. | Prevents rationalising the architecture branch after seeing the answers. | settled |
