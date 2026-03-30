# SetAndNotes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a desktop app that imports FOH and LTC audio files into a versioned setlist, decodes LTC from TC audio, and generates one REAPER `.RPP` project per song using a provided template file.

**Architecture:** The app is a PySide6 desktop application with a local JSON library file as the source of truth. Import, LTC decode, and export run through background jobs so the UI stays responsive. TouchDesigner is intentionally separate in v1 and later integrates by importing a session manifest that maps recorded video files to timecode ranges.

**Tech Stack:** Python 3.12+, PySide6, ffmpeg/ffprobe, an LTC decoder library or subprocess tool, pytest, Ruff, mypy, JSON persistence

---

## Product Constraints

- GUI style should feel modern and technical, not soft or playful.
- Corners should be slightly eased but not heavily rounded.
- Typography should use:
  - Headers: Aktiv Grotesk Ex Bold
  - Subheaders: Aktiv Grotesk Ex
  - Body/UI text: Aktiv Grotesk
- One `.RPP` file is generated per song.
- The `.RPP` filename comes from the setlist `long_name`, sanitized only for illegal filesystem characters.
- The app must decode LTC from the TC audio file and use decoded LTC as the authoritative project start time.
- Filenames are hints for pairing only.
- Setlist songs are stable records; new import folders like `Media/v2` and `Media/v3` add new versions to existing songs.
- Existing `.RPP` files must not be silently overwritten.

## Proposed Project Layout

```text
SetAndNotes/
  pyproject.toml
  README.md
  src/setandnotes/
    __init__.py
    app.py
    main_window.py
    styles/
      theme.py
      fonts.py
    models/
      song.py
      version.py
      library.py
      setlist_table_model.py
    services/
      file_scan.py
      file_classify.py
      media_probe.py
      ltc_decode.py
      song_match.py
      project_export.py
      template_rpp.py
      persistence.py
      validation.py
    workers/
      import_worker.py
      export_worker.py
    ui/
      song_table.py
      detail_panel.py
      import_dialog.py
      export_dialog.py
      status_bar.py
  tests/
    services/
    models/
    fixtures/
  docs/plans/
```

## Data Model

### Song

- `song_id: str`
- `long_name: str`
- `normalized_name: str`
- `bpm: float | None`
- `notes: str`
- `active_version_id: str | None`
- `created_at: str`
- `updated_at: str`

### SongVersion

- `version_id: str`
- `song_id: str`
- `label: str` (`v1`, `v2`, `v3`, etc.)
- `source_folder: str`
- `source_type: str` (`prep`, `rehearsal`)
- `main_audio_path: str | None`
- `tc_audio_path: str | None`
- `decoded_tc_start: str | None`
- `decoded_fps: str | None`
- `decode_confidence: float | None`
- `duration_seconds: float | None`
- `imported_at: str`
- `status: str` (`ready`, `warning`, `error`)
- `warnings: list[str]`

### Library

- `project_name: str`
- `library_path: str`
- `rpp_template_path: str | None`
- `songs: list[Song]`
- `versions: list[SongVersion]`
- `import_history: list[ImportBatch]`

### ImportBatch

- `batch_id: str`
- `label: str`
- `folder_path: str`
- `imported_at: str`
- `file_count: int`

## Matching and Classification Rules

- Normalize candidate filenames by:
  - lowercasing
  - stripping file extensions
  - removing known role tokens like `foh`, `track`, `master`, `lr`, `l-r`, `tc`, `timecode`, `smpte`
  - collapsing spaces, dashes, and underscores
- Main audio candidate tokens:
  - `track`
  - `foh`
  - `master`
  - `lr`
  - `l-r`
- TC candidate tokens:
  - `tc`
  - `timecode`
  - `smpte`
- Pair files by normalized base name first.
- Decode LTC on every TC candidate before finalizing any version.
- If multiple main or TC candidates match the same song, mark the row as a warning and require user review.
- If the normalized name matches an existing song, create a new version for that song.
- If no song matches, create a new song draft row and flag it as unreviewed.

## REAPER Export Rules

- Export one `.RPP` file per selected song.
- Use the provided template `.RPP` file instead of synthesizing the full format from scratch.
- Replace only the minimum required fields:
  - project start time offset
  - initial tempo marker BPM
  - media source path for FOH track
  - media source path for TC track
  - project display name if needed
- Place both FOH and TC items at the project start.
- Use decoded LTC start as the authoritative project time offset.
- Use the song BPM for the start tempo marker.
- If a song is missing `long_name`, main audio, TC audio, decoded LTC, or BPM, block export and show validation errors.
- If the target `.RPP` already exists, require explicit overwrite confirmation.

## UI Spec

### Main Window

- Left: setlist table
- Right: detail panel for selected song/version
- Top toolbar:
  - `Open Library`
  - `New Library`
  - `Import Folder`
  - `Set RPP Template`
  - `Generate Projects`
- Bottom status bar:
  - current library path
  - import/export progress
  - validation summary

### Setlist Table Columns

- Status
- Long Name
- BPM
- Active Version
- TC Start
- Main Audio
- TC Audio
- Source Folder
- Updated

### Detail Panel

- Song metadata section
  - `long_name`
  - `bpm`
  - notes
- Active version section
  - version label
  - source folder
  - main audio path
  - TC audio path
  - decoded TC start
  - fps / drop-frame
  - decode confidence
  - warnings
- Actions
  - `Set Active Version`
  - `Generate This Project`
  - `Reveal Files`

### Visual Design

- Backgrounds should use dark charcoal and warm grey planes with strong contrast for table rows and side panels.
- Avoid highly saturated accent colors; use one restrained accent for selected rows, focus states, and primary actions.
- Borders should be visible and rectilinear.
- Corner radius target: 4px to 6px.
- Headers use Aktiv Grotesk Ex Bold with generous tracking.
- Subheaders use Aktiv Grotesk Ex.
- Body text and table cells use Aktiv Grotesk.
- Buttons should be blocky and flat, with hover and pressed states driven by contrast rather than glow.

## Background Job Rules

- Folder import, ffprobe calls, LTC decode, and project export must run off the UI thread.
- Progress should update row-by-row and remain cancellable.
- Failed jobs should annotate the affected rows instead of stopping the entire batch.

## TouchDesigner Integration Later

- Do not build TouchDesigner control into v1.
- Reserve a future import path for a TD manifest JSON containing:
  - session ID
  - camera file paths
  - TC in/out for each file segment
  - optional song marker list
- Future matching logic should map song TC ranges to camera file ranges for rehearsal video exports.

## Test Strategy

- Unit tests for filename normalization and pairing
- Unit tests for song/version matching
- Unit tests for LTC decode parsing using fixture TC files
- Unit tests for `.RPP` template substitution
- Integration test for importing a `v2` folder into an existing library
- Integration test for blocked export when required fields are missing

### Task 1: Bootstrap The Project

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/setandnotes/__init__.py`
- Create: `src/setandnotes/app.py`
- Create: `tests/__init__.py`

**Step 1: Write the failing test**

Create a smoke test that imports `setandnotes.app` and verifies the package exposes a startup entry point.

**Step 2: Run test to verify it fails**

Run: `pytest tests -v`
Expected: FAIL with import errors

**Step 3: Write minimal implementation**

- Define project metadata and dependencies in `pyproject.toml`
- Add an application entry function in `src/setandnotes/app.py`

**Step 4: Run test to verify it passes**

Run: `pytest tests -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml README.md src/setandnotes tests
git commit -m "chore: bootstrap setandnotes app"
```

### Task 2: Define Core Data Models

**Files:**
- Create: `src/setandnotes/models/song.py`
- Create: `src/setandnotes/models/version.py`
- Create: `src/setandnotes/models/library.py`
- Test: `tests/models/test_library_models.py`

**Step 1: Write the failing test**

Write tests for:
- creating a `Song`
- attaching a `SongVersion`
- selecting an active version
- serializing/deserializing library data

**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_library_models.py -v`
Expected: FAIL with missing model classes

**Step 3: Write minimal implementation**

Implement dataclass or pydantic-style models with explicit JSON conversion helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_library_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/models tests/models
git commit -m "feat: add library data models"
```

### Task 3: Build Persistence Layer

**Files:**
- Create: `src/setandnotes/services/persistence.py`
- Test: `tests/services/test_persistence.py`

**Step 1: Write the failing test**

Write tests for:
- saving a library to JSON
- loading a library from JSON
- preserving song/version relationships

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_persistence.py -v`
Expected: FAIL with missing persistence functions

**Step 3: Write minimal implementation**

Implement save/load functions using stable JSON structure and atomic file writes.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_persistence.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/services/persistence.py tests/services/test_persistence.py
git commit -m "feat: add library persistence"
```

### Task 4: Implement Filename Classification

**Files:**
- Create: `src/setandnotes/services/file_classify.py`
- Test: `tests/services/test_file_classify.py`

**Step 1: Write the failing test**

Cover:
- role token removal
- normalized name generation
- main audio classification
- TC classification
- ambiguous filename cases

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_file_classify.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement deterministic token-based classifiers and normalization helpers.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_file_classify.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/services/file_classify.py tests/services/test_file_classify.py
git commit -m "feat: classify media files by role"
```

### Task 5: Implement Media Scanning And Probe

**Files:**
- Create: `src/setandnotes/services/file_scan.py`
- Create: `src/setandnotes/services/media_probe.py`
- Test: `tests/services/test_file_scan.py`

**Step 1: Write the failing test**

Write tests for:
- scanning supported media files from a folder
- ignoring unsupported files
- collecting basic metadata through a stubbed `ffprobe` layer

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_file_scan.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement file discovery and a probe abstraction that can call `ffprobe`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_file_scan.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/services/file_scan.py src/setandnotes/services/media_probe.py tests/services/test_file_scan.py
git commit -m "feat: scan and probe media files"
```

### Task 6: Implement LTC Decode Service

**Files:**
- Create: `src/setandnotes/services/ltc_decode.py`
- Create: `tests/fixtures/ltc/`
- Test: `tests/services/test_ltc_decode.py`

**Step 1: Write the failing test**

Write tests for:
- decoding first valid LTC frame from fixture audio
- returning fps / drop-frame mode
- reporting low-confidence or failed decode

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_ltc_decode.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Wrap the chosen LTC decoder behind a small service API that returns a structured decode result.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_ltc_decode.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/services/ltc_decode.py tests/services/test_ltc_decode.py tests/fixtures/ltc
git commit -m "feat: decode ltc from tc audio"
```

### Task 7: Implement Song Matching And Versioning

**Files:**
- Create: `src/setandnotes/services/song_match.py`
- Test: `tests/services/test_song_match.py`

**Step 1: Write the failing test**

Write tests for:
- creating new songs from imported files
- attaching `v2` and `v3` versions to existing songs
- warning on ambiguous pairs
- preserving stable song IDs

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_song_match.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement import matching using normalized names plus decoded LTC metadata.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_song_match.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/services/song_match.py tests/services/test_song_match.py
git commit -m "feat: match imported files into versioned songs"
```

### Task 8: Build RPP Template Export Service

**Files:**
- Create: `src/setandnotes/services/template_rpp.py`
- Create: `src/setandnotes/services/project_export.py`
- Test: `tests/services/test_project_export.py`

**Step 1: Write the failing test**

Write tests for:
- loading a template `.RPP`
- substituting project offset, BPM, and media file paths
- writing output filename from `long_name`
- blocking export on missing required values

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_project_export.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement template parsing/substitution and export validation rules.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_project_export.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/services/template_rpp.py src/setandnotes/services/project_export.py tests/services/test_project_export.py
git commit -m "feat: export reaper projects from template"
```

### Task 9: Build The Table Model And Validation Layer

**Files:**
- Create: `src/setandnotes/models/setlist_table_model.py`
- Create: `src/setandnotes/services/validation.py`
- Test: `tests/models/test_setlist_table_model.py`

**Step 1: Write the failing test**

Write tests for:
- table row rendering from library data
- edited BPM and long name values updating the model
- validation state propagation to status column

**Step 2: Run test to verify it fails**

Run: `pytest tests/models/test_setlist_table_model.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement a Qt table model backed by the library plus a validation service that emits row-level warnings/errors.

**Step 4: Run test to verify it passes**

Run: `pytest tests/models/test_setlist_table_model.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/models/setlist_table_model.py src/setandnotes/services/validation.py tests/models/test_setlist_table_model.py
git commit -m "feat: add setlist table model and validation"
```

### Task 10: Build The Base UI Shell

**Files:**
- Create: `src/setandnotes/main_window.py`
- Create: `src/setandnotes/ui/song_table.py`
- Create: `src/setandnotes/ui/detail_panel.py`
- Create: `src/setandnotes/ui/status_bar.py`
- Create: `src/setandnotes/styles/theme.py`
- Create: `src/setandnotes/styles/fonts.py`
- Test: `tests/ui/test_main_window.py`

**Step 1: Write the failing test**

Write a Qt smoke test that asserts:
- the main window opens
- the table and detail panel exist
- toolbar actions are present

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_main_window.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement the main window layout, typography loading hooks, and the initial theme constants.

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/test_main_window.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/main_window.py src/setandnotes/ui src/setandnotes/styles tests/ui/test_main_window.py
git commit -m "feat: build base desktop ui shell"
```

### Task 11: Implement Import Worker Flow

**Files:**
- Create: `src/setandnotes/workers/import_worker.py`
- Create: `src/setandnotes/ui/import_dialog.py`
- Test: `tests/services/test_import_pipeline.py`

**Step 1: Write the failing test**

Write an integration test for:
- importing a folder
- classifying files
- decoding LTC
- matching songs
- writing updated library state

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_import_pipeline.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement the threaded import worker and basic import dialog/status handling.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_import_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/workers/import_worker.py src/setandnotes/ui/import_dialog.py tests/services/test_import_pipeline.py
git commit -m "feat: import folders into the versioned setlist"
```

### Task 12: Implement Export Worker Flow

**Files:**
- Create: `src/setandnotes/workers/export_worker.py`
- Create: `src/setandnotes/ui/export_dialog.py`
- Test: `tests/services/test_export_pipeline.py`

**Step 1: Write the failing test**

Write an integration test for:
- generating projects for selected songs
- stopping export on invalid rows
- requiring confirmation before overwrite

**Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_export_pipeline.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement the threaded export worker and export summary dialog.

**Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_export_pipeline.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/workers/export_worker.py src/setandnotes/ui/export_dialog.py tests/services/test_export_pipeline.py
git commit -m "feat: export song projects in batch"
```

### Task 13: Add Version Management UX

**Files:**
- Modify: `src/setandnotes/ui/detail_panel.py`
- Modify: `src/setandnotes/main_window.py`
- Test: `tests/ui/test_version_management.py`

**Step 1: Write the failing test**

Write tests for:
- setting an active version
- surfacing newer imported versions
- preserving the existing `.RPP` until user explicitly rebuilds

**Step 2: Run test to verify it fails**

Run: `pytest tests/ui/test_version_management.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Add version selection controls and update warnings/actions in the detail panel.

**Step 4: Run test to verify it passes**

Run: `pytest tests/ui/test_version_management.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/setandnotes/ui/detail_panel.py src/setandnotes/main_window.py tests/ui/test_version_management.py
git commit -m "feat: manage active song versions"
```

### Task 14: Add Documentation And Packaging Notes

**Files:**
- Modify: `README.md`
- Create: `docs/plans/implementation-notes.md`

**Step 1: Write the failing test**

No code test required. Review manually against actual setup steps.

**Step 2: Document**

Add:
- app purpose
- dependency installation
- font installation expectations
- ffmpeg requirement
- LTC decoder requirement
- how to create a library
- how to import `v2` / `v3` folders
- how to set the `.RPP` template
- how to generate projects

**Step 3: Verify**

Run the app from a clean virtual environment and follow the README steps.
Expected: successful startup and import/export flow with fixture data.

**Step 4: Commit**

```bash
git add README.md docs/plans/implementation-notes.md
git commit -m "docs: add usage and setup guide"
```

## Verification Checklist

- `pytest tests -v`
- `ruff check .`
- `mypy src`
- Manual import test with sample `v1` and `v2` folders
- Manual export test using a real `.RPP` template
- Manual UI check on macOS with installed Aktiv Grotesk font family

## Open Technical Decisions To Resolve Early

- Which LTC decoder to standardize on for macOS: Python library vs bundled CLI wrapper
- Exact `.RPP` template substitution points once a real template file is provided
- Whether the exported `.RPP` should also rename internal REAPER track names to match song metadata
- Whether project output should live in a single folder or a per-version export tree
