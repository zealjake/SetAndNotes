# REAPER Notes

SetAndNotes now includes an in-app `Notes` page for rehearsal playback notes.

## Flow

1. Open the `Notes` tab in SetAndNotes.
2. Enter a username.
3. Choose a note type.
4. Enter the note body.
5. Submit the note.

On submit, the app:

1. Requests the current playhead from REAPER through ZealServer.
2. Creates a REAPER marker at that exact time.
3. Formats the marker as:

   `USERNAME - TYPE OF NOTE - NOTE`

4. Refreshes the note list from REAPER immediately.

## Note Type Colors

- `Cameras` -> `0,0,3`
- `Lighting/Lasers` -> `0,0,4`
- `Content` -> `0,0,5`
- `General` -> `0,0,6`

`0,0,2` is reserved for frame comments and is not used here.

## Live Sync

- ZealServer exposes `RS_SUBSCRIBE_MARKERS`.
- SetAndNotes opens one persistent connection while the `Notes` tab is active.
- ZealServer pushes `EVENT MARKERS [...]` snapshots when markers change.
- The app groups note markers under the nearest preceding default-colored song marker.

## Song Grouping

- Default-colored markers are treated as song markers.
- Their marker name is used as the song header.
- Colored note markers are grouped under the nearest preceding song marker.

## Relevant Files

- `src/setandnotes/services/reaper_socket.py`
- `src/setandnotes/services/reaper_notes.py`
- `src/setandnotes/services/reaper_marker_stream.py`
- `src/setandnotes/models/rehearsal_notes.py`
- `src/setandnotes/ui/notes_page.py`
- `src/setandnotes/main_window.py`

ZealServer side:

- `ZealReaperServer.cpp`
