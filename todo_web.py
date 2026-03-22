#!/opt/homebrew/bin/python3

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from todo_lib import TodoError, apply_text_command, move_by_index, parse_todo_file


HOST = "127.0.0.1"
PORT = 8421
BASE_DIR = Path(__file__).resolve().parent


HTML = r"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Todo</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f4efe6;
        --panel: rgba(255, 252, 247, 0.9);
        --ink: #1e1a17;
        --muted: #6a5f56;
        --line: #d8cab7;
        --accent: #b24c2f;
        --accent-soft: #f3d9d0;
        --blocked: #8f6a2a;
        --blocked-soft: rgba(173, 132, 53, 0.1);
        --done: #7f8a77;
        --error: #9f2f26;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: ui-rounded, "SF Pro Text", "Helvetica Neue", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(178, 76, 47, 0.18), transparent 28%),
          linear-gradient(135deg, #f8f2e8, var(--bg));
      }

      main {
        max-width: 760px;
        margin: 0 auto;
        padding: 40px 20px 64px;
      }

      .panel {
        background: var(--panel);
        border: 1px solid rgba(216, 202, 183, 0.85);
        border-radius: 24px;
        padding: 28px;
        box-shadow: 0 18px 60px rgba(58, 41, 28, 0.08);
        backdrop-filter: blur(12px);
      }

      h1 {
        margin: 0 0 8px;
        font-size: clamp(2rem, 4vw, 3.3rem);
        line-height: 0.95;
        letter-spacing: -0.04em;
      }

      .subhead {
        margin: 0;
        color: var(--muted);
      }

      .form-help {
        margin: 10px 0 24px;
        font-size: 0.94rem;
        color: var(--muted);
      }

      form {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 10px;
      }

      input[type="text"] {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px 16px;
        font: inherit;
        background: rgba(255, 255, 255, 0.78);
      }

      button {
        border: 0;
        border-radius: 14px;
        padding: 0 18px;
        font: inherit;
        font-weight: 600;
        color: white;
        background: var(--accent);
        cursor: pointer;
      }

      .feedback {
        min-height: 1.4rem;
        margin: 10px 0 0;
        color: var(--muted);
      }

      .feedback[data-state="error"] {
        color: var(--error);
      }

      .section-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin: 28px 0 12px;
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
      }

      .count {
        font-size: 0.84rem;
        font-weight: 600;
        letter-spacing: 0;
        text-transform: none;
      }

      ul {
        list-style: none;
        padding: 0;
        margin: 0;
      }

      li + li {
        margin-top: 10px;
      }

      .item {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 14px;
        align-items: center;
        padding: 15px 16px;
        border-radius: 16px;
        border: 1px solid var(--line);
        background: rgba(255, 255, 255, 0.68);
      }

      .blocked-item {
        grid-template-columns: 1fr auto;
        background: var(--blocked-soft);
        border-color: rgba(173, 132, 53, 0.28);
      }

      .done-list .item {
        color: var(--done);
        background: rgba(127, 138, 119, 0.08);
      }

      .item-body {
        min-width: 0;
      }

      .item-text {
        overflow-wrap: anywhere;
      }

      .item-meta {
        margin: 7px 0 0;
        font-size: 0.9rem;
        color: var(--muted);
      }

      .blocked-item .item-meta {
        color: var(--blocked);
      }

      .item-text a {
        color: var(--accent);
      }

      .done-list .item-text a {
        color: inherit;
      }

      .badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        color: var(--blocked);
        background: rgba(173, 132, 53, 0.16);
      }

      .inline-button {
        padding: 9px 12px;
        border: 1px solid rgba(178, 76, 47, 0.18);
        border-radius: 12px;
        color: var(--accent);
        background: rgba(255, 255, 255, 0.8);
      }

      .inline-button:disabled {
        cursor: wait;
        opacity: 0.7;
      }

      input[type="checkbox"] {
        width: 22px;
        height: 22px;
        accent-color: var(--accent);
        cursor: pointer;
      }

      .empty {
        margin: 0;
        padding: 18px 16px;
        border: 1px dashed var(--line);
        border-radius: 16px;
        color: var(--muted);
      }
    </style>
  </head>
  <body>
    <main>
      <section class="panel">
        <h1>Todo</h1>
        <p class="subhead">Add tasks in plain English, including blockers.</p>
        <p class="form-help">Example: "talk to Francois before applying to any jobs". Checking off the blocker will automatically unblock anything waiting on it.</p>

        <form id="add-form">
          <input
            id="new-item"
            type="text"
            placeholder="Add a task or dependency"
            autocomplete="off"
            required
          >
          <button type="submit">Add</button>
        </form>
        <p id="feedback" class="feedback" aria-live="polite"></p>

        <div class="section-title">
          <span>Active</span>
          <span class="count" id="active-count"></span>
        </div>
        <ul id="active-list"></ul>

        <div class="section-title">
          <span>Blocked</span>
          <span class="count" id="blocked-count"></span>
        </div>
        <ul id="blocked-list"></ul>

        <div class="section-title">
          <span>Done</span>
          <span class="count" id="done-count"></span>
        </div>
        <ul id="done-list" class="done-list"></ul>
      </section>
    </main>

    <script>
      let feedbackTimerId = null;

      function setFeedback(message = '', state = 'info') {
        const feedback = document.getElementById('feedback');
        feedback.textContent = message;
        feedback.dataset.state = state;

        if (feedbackTimerId !== null) {
          window.clearTimeout(feedbackTimerId);
          feedbackTimerId = null;
        }

        if (message) {
          feedbackTimerId = window.setTimeout(() => {
            feedback.textContent = '';
            feedback.dataset.state = 'info';
            feedbackTimerId = null;
          }, 5000);
        }
      }

      async function apiJson(url, options = {}) {
        const response = await fetch(url, options);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.error || `Request failed with status ${response.status}.`);
        }
        if (data.message) {
          setFeedback(data.message);
        }
        return data;
      }

      async function loadTodos() {
        try {
          const data = await apiJson('/api/todos');
          renderList('active', data.active);
          renderBlockedList(data.blocked);
          renderList('done', data.done);
        } catch (error) {
          setFeedback(error.message, 'error');
        }
      }

      function renderList(section, items) {
        const list = document.getElementById(`${section}-list`);
        const count = document.getElementById(`${section}-count`);
        list.innerHTML = '';
        count.textContent = `${items.length} item${items.length === 1 ? '' : 's'}`;

        if (items.length === 0) {
          const empty = document.createElement('p');
          empty.className = 'empty';
          empty.textContent = section === 'active'
            ? 'Nothing pending.'
            : 'Nothing completed yet.';
          list.appendChild(empty);
          return;
        }

        items.forEach((text, index) => {
          const li = document.createElement('li');
          const row = document.createElement('div');
          row.className = 'item';

          const checkbox = document.createElement('input');
          checkbox.type = 'checkbox';
          checkbox.checked = section === 'done';
          checkbox.addEventListener('change', async () => {
            checkbox.disabled = true;
            try {
              await apiJson('/api/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ section, index }),
              });
              await loadTodos();
            } catch (error) {
              checkbox.disabled = false;
              setFeedback(error.message, 'error');
            }
          });

          const body = document.createElement('div');
          body.className = 'item-body';

          const span = document.createElement('span');
          span.className = 'item-text';
          appendLinkedText(span, text);
          body.appendChild(span);

          row.appendChild(checkbox);
          row.appendChild(body);
          li.appendChild(row);
          list.appendChild(li);
        });
      }

      function renderBlockedList(items) {
        const list = document.getElementById('blocked-list');
        const count = document.getElementById('blocked-count');
        list.innerHTML = '';
        count.textContent = `${items.length} item${items.length === 1 ? '' : 's'}`;

        if (items.length === 0) {
          const empty = document.createElement('p');
          empty.className = 'empty';
          empty.textContent = 'Nothing blocked right now.';
          list.appendChild(empty);
          return;
        }

        items.forEach((item, index) => {
          const li = document.createElement('li');
          const row = document.createElement('div');
          row.className = 'item blocked-item';

          const body = document.createElement('div');
          body.className = 'item-body';

          const text = document.createElement('span');
          text.className = 'item-text';
          appendLinkedText(text, item.text);

          const meta = document.createElement('p');
          meta.className = 'item-meta';
          meta.textContent = 'Blocked by ';

          const badge = document.createElement('span');
          badge.className = 'badge';
          badge.textContent = item.blocker;
          meta.appendChild(badge);

          body.appendChild(text);
          body.appendChild(meta);

          const unblockButton = document.createElement('button');
          unblockButton.type = 'button';
          unblockButton.className = 'inline-button';
          unblockButton.textContent = 'Unblock';
          unblockButton.addEventListener('click', async () => {
            unblockButton.disabled = true;
            try {
              await apiJson('/api/unblock', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index }),
              });
              await loadTodos();
            } catch (error) {
              unblockButton.disabled = false;
              setFeedback(error.message, 'error');
            }
          });

          row.appendChild(body);
          row.appendChild(unblockButton);
          li.appendChild(row);
          list.appendChild(li);
        });
      }

      function appendLinkedText(container, text) {
        const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
        const urlRegex = /https?:\/\/[^\s)]+/g;
        let cursor = 0;
        let markdownMatch;

        while ((markdownMatch = markdownLinkRegex.exec(text)) !== null) {
          if (markdownMatch.index > cursor) {
            appendFormattedText(container, text.slice(cursor, markdownMatch.index), urlRegex);
          }

          const link = document.createElement('a');
          const target = markdownMatch[2];
          link.href = /^https?:\/\//i.test(target)
            ? target
            : `/files/${encodeURIComponent(target)}`;
          link.textContent = markdownMatch[1];
          link.target = '_blank';
          link.rel = 'noreferrer noopener';
          container.appendChild(link);
          cursor = markdownMatch.index + markdownMatch[0].length;
        }

        if (cursor < text.length) {
          appendFormattedText(container, text.slice(cursor), urlRegex);
        }
      }

      function appendFormattedText(container, text, urlRegex) {
        const boldRegex = /\*\*([^*]+)\*\*/g;
        let cursor = 0;
        let match;

        while ((match = boldRegex.exec(text)) !== null) {
          if (match.index > cursor) {
            appendUrlText(container, text.slice(cursor, match.index), urlRegex);
          }

          const strong = document.createElement('strong');
          appendUrlText(strong, match[1], urlRegex);
          container.appendChild(strong);
          cursor = match.index + match[0].length;
        }

        if (cursor < text.length) {
          appendUrlText(container, text.slice(cursor), urlRegex);
        }
      }

      function appendUrlText(container, text, urlRegex) {
        let lastIndex = 0;
        let match;
        urlRegex.lastIndex = 0;

        while ((match = urlRegex.exec(text)) !== null) {
          if (match.index > lastIndex) {
            container.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
          }

          const link = document.createElement('a');
          link.href = match[0];
          link.textContent = match[0];
          link.target = '_blank';
          link.rel = 'noreferrer noopener';
          container.appendChild(link);
          lastIndex = match.index + match[0].length;
        }

        if (lastIndex < text.length) {
          container.appendChild(document.createTextNode(text.slice(lastIndex)));
        }
      }

      document.getElementById('add-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const input = document.getElementById('new-item');
        const text = input.value.trim();
        if (!text) {
          return;
        }

        try {
          await apiJson('/api/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
          });
          input.value = '';
          await loadTodos();
        } catch (error) {
          setFeedback(error.message, 'error');
        }
      });

      loadTodos();
    </script>
  </body>
</html>
"""


class TodoHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        if self.path == "/":
            self._send_html()
            return
        if self.path == "/api/todos":
            active, blocked, done = parse_todo_file()
            self._send_json(
                {
                    "active": [item.text for item in active],
                    "blocked": [
                        {"text": item.text, "blocker": item.blocker} for item in blocked
                    ],
                    "done": [item.text for item in done],
                }
            )
            return
        if self.path.startswith("/files/"):
            self._send_file(self.path.removeprefix("/files/"))
            return
        self.send_error(404)

    def _send_file(self, relative_path: str) -> None:
        requested = unquote(relative_path)
        file_path = (BASE_DIR / requested).resolve()
        try:
            file_path.relative_to(BASE_DIR)
        except ValueError:
            self.send_error(403)
            return

        if not file_path.is_file():
            self.send_error(404)
            return

        body = file_path.read_bytes()
        content_type, _ = mimetypes.guess_type(file_path.name)
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
            if self.path == "/api/add":
                text = payload.get("text", "").strip()
                if not text:
                    self._send_json({"error": "Text is required."}, status=400)
                    return
                result = apply_text_command(text)
                self._send_json({"ok": True, **result})
                return
            if self.path == "/api/toggle":
                section = payload.get("section")
                index = payload.get("index")
                if section not in {"active", "done"} or not isinstance(index, int):
                    self._send_json({"error": "Invalid toggle payload."}, status=400)
                    return
                result = move_by_index(section, index)
                self._send_json({"ok": True, **result})
                return
            if self.path == "/api/unblock":
                index = payload.get("index")
                if not isinstance(index, int):
                    self._send_json({"error": "Invalid unblock payload."}, status=400)
                    return
                result = move_by_index("blocked", index)
                self._send_json({"ok": True, **result})
                return
        except (TodoError, ValueError, IndexError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), TodoHandler)
    print(f"Todo app running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
