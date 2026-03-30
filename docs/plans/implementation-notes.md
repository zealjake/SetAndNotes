# Implementation Notes

## Architecture Snapshot

- `Library` owns songs and their versions.
- `Song` keeps a stable identity across prep and rehearsal updates.
- `SongVersion` stores imported media paths plus decoded LTC data.
- Import flow:
  - discover media files
  - classify main vs TC candidates
  - decode LTC for TC files
  - attach a new version to matching songs
  - save library JSON
- Export flow:
  - validate selected songs
  - block invalid rows
  - confirm before overwrite
  - render one `.RPP` per song from the template contract

## UI State

- Main window shell is present.
- Setlist table is backed by a Qt table model over the real library.
- Detail panel supports:
  - current song display
  - active version selection
  - newer-version warning
  - explicit rebuild request
- Import/export dialogs exist but are intentionally minimal.

## Font Direction

- Headers should prefer Aktiv Grotesk Ex Bold.
- Subheaders should prefer Aktiv Grotesk Ex.
- Body should prefer Aktiv Grotesk.
- Font loading soft-fails to system fonts when the families are unavailable.

## Remaining Integration Work

- Replace the placeholder `.RPP` token system with edits against the real REAPER template file.
- Wire proper file pickers for:
  - library open/save
  - import folder selection
  - `.RPP` template selection
  - export output folder
- Connect import/export completion back into the visible table/detail UI state more fully.
- Add TouchDesigner manifest import for recorded video mapping by timecode range.
- Improve row presentation:
  - validation badges
  - version metadata
  - source folder visibility
  - decode confidence

## Environment Notes

- Tests currently pass without `ffprobe` by stubbing probe calls where needed.
- LTC decode tests rely on `ltcgen` and `ltcdump`.
- The workspace is not currently a git repository, so no commits were created during implementation.
