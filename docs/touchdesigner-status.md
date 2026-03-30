# TouchDesigner Patch Status

This file tracks the current TouchDesigner patch work, what is working, what is not working, and what the app can already consume.

## Current Patch Root

- `/project1/rehearsal_capture`

## Current Structure

- `/project1/rehearsal_capture/inputs`
- `/project1/rehearsal_capture/recorders`
- `/project1/rehearsal_capture/timecode`
- `/project1/rehearsal_capture/session`
- `/project1/rehearsal_capture/ui`

## What Is Working

### Direct TouchDesigner Control

- `start_button` starts recording directly in TouchDesigner
- `stop_button` stops recording directly in TouchDesigner
- `marker_button` appends marker rows into `markers_table`
- `session_table` logs:
  - `source_id`
  - `path`
  - `tc_start`
  - `tc_end`
- `manifest_text` is populated on stop
- a session manifest JSON is written to:
  - `~/Movies/SetAndNotesCapture/BandRehearsal_session.json`

### Recorder Path

- `camA_record` confirmed working
- `camB_record` confirmed working
- recorder file paths are assigned from DAT scripts
- recorder `record` parameter is controlled from `Panel Execute DAT` scripts

### Diagnostic Bridge

- TCP bridge is working for troubleshooting
- TouchDesigner can send state to the local bridge server
- TouchDesigner can poll commands from the local bridge server
- the bridge is useful for debugging and inspection
- normal recording control should stay local inside TouchDesigner

### App Side

- SetAndNotes now has backend support for storing imported TouchDesigner sessions inside the `.zeal` project
- a TouchDesigner manifest JSON can be imported into project state via:
  - [touchdesigner_manifest.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/services/touchdesigner_manifest.py)
- SetAndNotes now has backend support for parsing rendered TouchDesigner video filenames in the form:
  - `LongName_Multicam_TCHH_MM_SS_FF.mov`
  - `LongName_WideShot1080_TCHH_MM_SS_FF.mov`
- supported rendered asset types:
  - `Multicam`
  - `WideShot1080`
- rendered video files can now be attached to the active song version backend via:
  - [touchdesigner_render_import.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/services/touchdesigner_render_import.py)
- the app now has a workflow action to import a rendered TouchDesigner folder into the current project
- the selected-song detail panel now displays attached:
  - `Multicam`
  - `WideShot1080`
  video asset paths for the active version

## What Is Not Working

### TouchDesigner Extension Loading

- `controller_code` DAT is valid
- `RehearsalCaptureExt` class exists
- manual instantiation of `RehearsalCaptureExt` works
- but the TouchDesigner **Extensions** page did not create a live extension instance
- `op('/project1/rehearsal_capture').ext.capture` evaluated to `None`
- result:
  - `start_exec` calling `ext.capture.StartRecording()` failed

Conclusion:

- the extension system wiring was the failing layer
- the direct DAT-script approach works and should be used for now

### Real LTC / Timecode Input

- `tc_value` is still a placeholder text field
- manifests currently show the same `tc_start` and `tc_end` unless the text is changed manually
- live LTC decode/input is not wired yet

### Song Naming / Automatic Song Boundaries

- marker button currently writes generic `Marker`
- song names are not yet driven from SetAndNotes
- TouchDesigner is not yet receiving setlist/song state from the app

## Current Manifest Shape

Current stop manifest contains:

- `session_name`
- `fps`
- `recordings`
- `events`
- `markers`

This is the correct direction for later app-side matching.

## Recommended Next TouchDesigner Steps

1. Replace placeholder `tc_value` with real LTC-derived current TC when hardware/input is available.
2. Add song-name input or app-driven marker names instead of generic `Marker`.
3. Expand the direct DAT-script record path to any additional camera recorders that actually exist.
4. Keep the TCP bridge available for diagnostics only.

## Recommended Next App Steps

1. Update REAPER project generation so imported video assets can be referenced or copied as part of a song version.
2. Decide whether the detail panel should allow browsing/replacing imported TD video assets manually.
3. Replace placeholder `tc_value` with real LTC-derived current TC when hardware/input is available.
