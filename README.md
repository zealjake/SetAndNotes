# SetAndNotes

Desktop tooling for importing FOH and LTC audio, managing versioned setlists, and generating REAPER projects from a template.

## Current Scope

The app currently supports:

- versioned song/library data
- import scanning for rehearsal media folders such as `Media/v2` and `Media/v3`
- filename-based FOH vs TC classification
- LTC decode from TC audio using `ltcdump`
- one `.RPP` export per song from a template contract
- a PySide6 desktop shell with setlist table, detail panel, import dialog, export dialog, and active-version switching

## Requirements

- Python 3.12+
- PySide6
- `ltcdump` and `ltcgen`
- `ffprobe`
- Aktiv Grotesk and Aktiv Grotesk Ex installed locally if you want the intended UI typography

On this machine, `ltcdump` and `ltcgen` are expected at `/opt/homebrew/bin/ltcdump` and `/opt/homebrew/bin/ltcgen`.

## Setup

Create a virtual environment and install the package in editable mode:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

If `ffprobe` is not installed yet:

```bash
brew install ffmpeg
```

If LTC tools are not installed yet:

```bash
brew install ltc-tools
```

## Run

```bash
python -m setandnotes.app
```

## Test

```bash
pytest tests -v
```

## Current Workflow

1. Launch the app.
2. Create or load a library JSON file.
3. Import a folder such as `Media/v2`.
4. Let the app classify `FOH` / `track` / `master` / `LR` files against `TC` / `timecode` / `smpte` files.
5. Review active versions in the detail panel.
6. Set BPM and long names in the setlist table.
7. Set an `.RPP` template.
8. Generate one `.RPP` per selected song.

## Important Limitations

- The real `.RPP` template format is not integrated yet.
- Export currently uses a placeholder token contract:
  - `{{SONG_LONG_NAME}}`
  - `{{PROJECT_OFFSET}}`
  - `{{BPM}}`
  - `{{MAIN_AUDIO_PATH}}`
  - `{{TC_AUDIO_PATH}}`
- The import and export dialogs are intentionally basic and still need fuller UI wiring.
- TouchDesigner manifest import is planned but not implemented yet.

## TouchDesigner Prep

The repo now includes a first-pass TouchDesigner capture guide and controller helper:

- patch guide: [touchdesigner-v1-patch.md](/Users/jake/Documents/dev/SetAndNotes/docs/touchdesigner-v1-patch.md)
- controller helper: [capture_controller.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/touchdesigner/capture_controller.py)
- bridge guide: [touchdesigner-bridge.md](/Users/jake/Documents/dev/SetAndNotes/docs/touchdesigner-bridge.md)
- current patch status: [touchdesigner-status.md](/Users/jake/Documents/dev/SetAndNotes/docs/touchdesigner-status.md)

## Project Files

- App entry: [app.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/app.py)
- Main window: [main_window.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/main_window.py)
- Import pipeline: [import_worker.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/workers/import_worker.py)
- Export pipeline: [export_worker.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/workers/export_worker.py)
- LTC decode: [ltc_decode.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/services/ltc_decode.py)
