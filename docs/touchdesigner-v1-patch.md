# TouchDesigner V1 Patch

This is the first usable TouchDesigner patch layout for rehearsal capture.

The goal of v1 is:

- ingest 2 video feeds
- read LTC/timecode
- record both feeds for the whole rehearsal
- log TC start/end for each recorded file
- write a session manifest JSON for SetAndNotes

Do not try to build automatic song splitting in TouchDesigner yet. Keep TouchDesigner responsible for capture and metadata only.

## Patch Layout

Create this top-level structure:

- `/rehearsal_capture`
- `/rehearsal_capture/inputs`
- `/rehearsal_capture/recorders`
- `/rehearsal_capture/timecode`
- `/rehearsal_capture/session`
- `/rehearsal_capture/ui`

## Inputs COMP

Inside `/rehearsal_capture/inputs` create:

- `camA_in`
- `camB_in`
- `ltc_audio_in`
- `camA_null`
- `camB_null`
- `ltc_null`

Recommended operator types:

- `camA_in`: your real video ingest node, usually `Video Device In TOP`
- `camB_in`: your real video ingest node, usually `Video Device In TOP`
- `ltc_audio_in`: `Audio Device In CHOP`
- `camA_null`: `Null TOP`
- `camB_null`: `Null TOP`
- `ltc_null`: `Null CHOP`

Wire:

- `camA_in -> camA_null`
- `camB_in -> camB_null`
- `ltc_audio_in -> ltc_null`

## Recorders COMP

Inside `/rehearsal_capture/recorders` create:

- `camA_record`
- `camB_record`
- `controller_ext`

Recommended operator types:

- `camA_record`: `Movie File Out TOP`
- `camB_record`: `Movie File Out TOP`
- `controller_ext`: `Text DAT`

Wire:

- `/rehearsal_capture/inputs/camA_null -> camA_record`
- `/rehearsal_capture/inputs/camB_null -> camB_record`

The Python extension on the parent `/rehearsal_capture` COMP should drive both recorder file paths and their `record` parameters.

## Timecode COMP

Inside `/rehearsal_capture/timecode` create:

- `tc_value`
- `tc_display`

Recommended operator types:

- `tc_value`: whatever CHOP/DAT path you use to get current LTC-derived timecode
- `tc_display`: `Text TOP` or `Text DAT` for operator confidence

For v1, it is enough that you can reliably read one current TC string like:

- `01:00:00:00`
- `01:10:23:12`

If LTC decode inside TD is not ready on day one, you can stub this with a manual text field and finish the rest of the patch first.

## Session COMP

Inside `/rehearsal_capture/session` create:

- `session_table`
- `markers_table`
- `manifest_text`

Recommended operator types:

- `session_table`: `Table DAT`
- `markers_table`: `Table DAT`
- `manifest_text`: `Text DAT`

Suggested `session_table` columns:

- `source_id`
- `path`
- `tc_start`
- `tc_end`

Suggested `markers_table` columns:

- `song_name`
- `tc_value`

The controller should update these from its in-memory session state.

## UI COMP

Inside `/rehearsal_capture/ui` create:

- `start_button`
- `stop_button`
- `marker_button`
- `status_text`

Operator type suggestions:

- buttons: `Button COMP`
- status text: `Text TOP` or `Text DAT`

## Controller Extension

Use the plain Python controller in:

- [capture_controller.py](/Users/jake/Documents/dev/SetAndNotes/src/setandnotes/touchdesigner/capture_controller.py)

That module already handles:

- record path generation
- session start
- session stop
- marker collection
- manifest build
- manifest JSON write

You can wrap it in a TouchDesigner extension class like this:

```python
from pathlib import Path

from setandnotes.touchdesigner.capture_controller import CaptureController


class RehearsalCaptureExt:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.controller = CaptureController(
            session_name="BandRehearsal",
            output_root=Path.home() / "Movies" / "SetAndNotesCapture",
            fps="25",
        )

    def _current_tc(self):
        return self.ownerComp.op("timecode/tc_value").text.strip()

    def _recorders(self):
        return {
            "camA": self.ownerComp.op("recorders/camA_record"),
            "camB": self.ownerComp.op("recorders/camB_record"),
        }

    def StartRecording(self):
        source_paths = {}
        for source_id in ("camA", "camB"):
            path = self.controller.build_record_path(source_id)
            source_paths[source_id] = path
            self._recorders()[source_id].par.file = str(path)

        self.controller.start_recording(
            tc_start=self._current_tc(),
            source_paths=source_paths,
        )

        for recorder in self._recorders().values():
            recorder.par.record = 1

        self.RefreshTables()

    def StopRecording(self):
        for recorder in self._recorders().values():
            recorder.par.record = 0

        self.controller.stop_recording(tc_end=self._current_tc())
        manifest_path = self.controller.write_manifest()
        self.ownerComp.op("session/manifest_text").text = manifest_path.read_text()
        self.RefreshTables()

    def AddMarker(self, song_name):
        self.controller.add_marker(song_name, tc_value=self._current_tc())
        self.RefreshTables()

    def RefreshTables(self):
        session_table = self.ownerComp.op("session/session_table")
        markers_table = self.ownerComp.op("session/markers_table")

        session_table.clear()
        session_table.appendRow(["source_id", "path", "tc_start", "tc_end"])
        for entry in self.controller.build_manifest()["recordings"]:
            session_table.appendRow([
                entry["source_id"],
                entry["path"],
                entry["tc_start"],
                entry["tc_end"] or "",
            ])

        markers_table.clear()
        markers_table.appendRow(["song_name", "tc_value"])
        for marker in self.controller.build_manifest()["markers"]:
            markers_table.appendRow([marker["song_name"], marker["tc_value"]])
```

## Minimal First Build

When you open TouchDesigner, do this in order:

1. Build the COMP structure exactly as listed above.
2. Get `camA_in` and `camB_in` showing live video.
3. Get one current TC string visible in `timecode/tc_value`.
4. Add the extension to `/rehearsal_capture`.
5. Make the Start and Stop buttons call `parent().StartRecording()` and `parent().StopRecording()`.

At that point, the patch is useful even before markers or splitting are refined.

## What You Need To Tell Me Next

Once you have the shell built, send me:

- which operator types you used for `camA_in` and `camB_in`
- how LTC is arriving
- what node is producing the current TC string

Then I can adapt the extension code to your exact TouchDesigner network instead of the generic names above.
