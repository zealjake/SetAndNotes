from __future__ import annotations

import html


def render_web_notes_page(*, username: str, token: str) -> str:
    safe_username = html.escape(username, quote=True)
    safe_token = html.escape(token, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Web Notes</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #16191d;
      color: #f3f4f6;
    }}
    body {{
      margin: 0;
      padding: 20px;
      background: linear-gradient(180deg, #16191d 0%, #0f1216 100%);
    }}
    .wrap {{
      max-width: 720px;
      margin: 0 auto;
    }}
    .user {{
      margin-bottom: 16px;
      font-size: 15px;
      opacity: 0.92;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    button {{
      border: 0;
      border-radius: 14px;
      padding: 20px 14px;
      font-size: 18px;
      font-weight: 700;
      cursor: pointer;
    }}
    .general {{ background: #64748b; color: white; }}
    .lighting {{ background: #9333ea; color: white; }}
    .content {{ background: #0f766e; color: white; }}
    .cameras {{ background: #1d4ed8; color: white; }}
    .status {{
      min-height: 24px;
      margin: 14px 0 0;
      font-size: 14px;
    }}
    dialog {{
      width: min(92vw, 640px);
      border: 0;
      border-radius: 16px;
      padding: 0;
      background: #1b2027;
      color: #f3f4f6;
    }}
    dialog::backdrop {{
      background: rgba(0, 0, 0, 0.55);
    }}
    .modal {{
      padding: 20px;
    }}
    textarea {{
      width: 100%;
      min-height: 140px;
      resize: vertical;
      box-sizing: border-box;
      margin-top: 10px;
      border-radius: 12px;
      border: 1px solid #334155;
      background: #0f1419;
      color: #f3f4f6;
      padding: 12px;
      font: inherit;
    }}
    .actions {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 14px;
    }}
    .secondary {{
      background: #334155;
    }}
    .hint {{
      margin-top: 10px;
      font-size: 13px;
      color: #94a3b8;
    }}
  </style>
</head>
<body>
  <div class="wrap" id="app" data-token="{safe_token}">
    <div class="user">Signed in as <strong>{safe_username}</strong></div>
    <div class="grid">
      <button type="button" class="general" data-note-type="General">General</button>
      <button type="button" class="lighting" data-note-type="Lighting/Lasers">Lighting</button>
      <button type="button" class="content" data-note-type="Content">Content</button>
      <button type="button" class="cameras" data-note-type="Cameras">Cameras</button>
    </div>
    <div class="status" id="status" aria-live="polite"></div>
  </div>

  <dialog id="note-dialog">
    <form method="dialog" class="modal" id="note-form">
      <h2 id="note-dialog-title">Add Note</h2>
      <textarea id="note-body" placeholder="Type note"></textarea>
      <div class="hint" id="capture-state"></div>
      <div class="actions">
        <button type="button" class="secondary" id="cancel-note">Cancel</button>
        <button type="submit" id="save-note" disabled>Save</button>
      </div>
    </form>
  </dialog>

  <script>
    const token = document.getElementById("app").dataset.token;
    const statusEl = document.getElementById("status");
    const dialog = document.getElementById("note-dialog");
    const noteBody = document.getElementById("note-body");
    const noteForm = document.getElementById("note-form");
    const dialogTitle = document.getElementById("note-dialog-title");
    const cancelButton = document.getElementById("cancel-note");
    const saveButton = document.getElementById("save-note");
    const captureState = document.getElementById("capture-state");
    let pendingCapture = null;
    let captureRequest = 0;

    function setStatus(text, isError = false) {{
      statusEl.textContent = text;
      statusEl.style.color = isError ? "#fca5a5" : "#86efac";
    }}

    async function postJson(url, payload) {{
      const response = await fetch(url, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      const data = await response.json();
      if (!response.ok) {{
        throw new Error(data.error || "Request failed");
      }}
      return data;
    }}

    async function beginCapture(noteType) {{
      const requestId = ++captureRequest;
      pendingCapture = null;
      dialogTitle.textContent = `Add ${{noteType}} Note`;
      noteBody.value = "";
      noteBody.disabled = true;
      saveButton.disabled = true;
      captureState.textContent = "Capturing timestamp...";
      dialog.showModal();
      try {{
        setStatus("");
        const capture = await postJson("/api/web-notes/capture", {{
          token,
          note_type: noteType,
        }});
        if (requestId !== captureRequest) {{
          return;
        }}
        pendingCapture = capture;
        noteBody.disabled = false;
        saveButton.disabled = false;
        captureState.textContent = "Timestamp locked. Type note and save.";
        noteBody.focus();
      }} catch (error) {{
        if (requestId !== captureRequest) {{
          return;
        }}
        dialog.close();
        setStatus(error.message, true);
      }}
    }}

    async function submitCapture() {{
      if (!pendingCapture) {{
        return;
      }}
      saveButton.disabled = true;
      noteBody.disabled = true;
      captureState.textContent = "Saving note...";
      try {{
        await postJson("/api/web-notes/submit", {{
          token,
          capture_id: pendingCapture.capture_id,
          body: noteBody.value,
        }});
        dialog.close();
        setStatus(`Saved ${{pendingCapture.note_type}} note`);
        pendingCapture = null;
      }} catch (error) {{
        saveButton.disabled = false;
        noteBody.disabled = false;
        captureState.textContent = "Timestamp locked. Type note and save.";
        setStatus(error.message, true);
      }}
    }}

    document.querySelectorAll("[data-note-type]").forEach((button) => {{
      button.addEventListener("click", () => beginCapture(button.dataset.noteType));
    }});

    noteForm.addEventListener("submit", (event) => {{
      event.preventDefault();
      submitCapture();
    }});

    cancelButton.addEventListener("click", () => {{
      captureRequest += 1;
      pendingCapture = null;
      noteBody.disabled = false;
      saveButton.disabled = false;
      captureState.textContent = "";
      dialog.close();
      setStatus("");
    }});
  </script>
</body>
</html>
"""
