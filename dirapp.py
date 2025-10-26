import os, shutil
from pathlib import Path
from flask import Flask, abort, render_template_string, send_file, request, redirect, url_for
from werkzeug.utils import safe_join

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
VOLUME = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "/data")  # Railway mounts your volume here
PORT = int(os.getenv("PORT", "8080"))                     # Railway sets PORT automatically
DELETE_TOKEN = os.getenv("BROWSER_DELETE_TOKEN", "")      # Optional safety token

app = Flask(__name__)

# -------------------------------------------------------------------
# BASIC HTML TEMPLATE
# -------------------------------------------------------------------
HTML = """<!doctype html>
<meta charset="utf-8">
<title>Volume Browser</title>
<h1>Volume: {{ base }}</h1>
<p><small>Path: /{{ rel }}</small></p>
<ul>
  {% for name, is_dir in entries %}
    <li>
      {% if is_dir %}
        📁 <a href="{{ url_for('index', subpath=(rel + '/' if rel else '') + name) }}">{{ name }}/</a>
      {% else %}
        📄 <a href="{{ url_for('raw', subpath=(rel + '/' if rel else '') + name) }}" target="_blank">{{ name }}</a>
        | <a href="{{ url_for('download', subpath=(rel + '/' if rel else '') + name) }}">download</a>
        | <form style="display:inline" method="post" action="{{ url_for('delete', subpath=(rel + '/' if rel else '') + name) }}">
            {% if token %}<input type="hidden" name="token" value="{{ token }}">{% endif %}
            <button type="submit">delete</button>
          </form>
      {% endif %}
    </li>
  {% endfor %}
</ul>
{% if parent %}
  <p><a href="{{ url_for('index', subpath=parent) }}">⬆️ up</a></p>
{% endif %}
"""

# -------------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------------
def list_dir(rel=""):
    abs_dir = safe_join(VOLUME, rel)
    if not abs_dir or not os.path.isdir(abs_dir):
        abort(404)
    items = sorted(os.listdir(abs_dir))
    entries = [(n, os.path.isdir(os.path.join(abs_dir, n))) for n in items]
    parts = [p for p in rel.split("/") if p]
    parent = "/".join(parts[:-1]) if parts else None
    return entries, parent

@app.get("/", defaults={"subpath": ""})
@app.get("/<path:subpath>")
def index(subpath):
    entries, parent = list_dir(subpath)
    return render_template_string(
        HTML, base=VOLUME, entries=entries, rel=subpath, parent=parent, token=DELETE_TOKEN
    )

@app.get("/raw/<path:subpath>")
def raw(subpath):
    d, f = os.path.split(subpath)
    directory = safe_join(VOLUME, d) if d else VOLUME
    target = safe_join(directory, f)
    if not directory or not (target and os.path.isfile(target)):
        abort(404)
    return send_file(target)  # inline view

@app.get("/download/<path:subpath>")
def download(subpath):
    d, f = os.path.split(subpath)
    directory = safe_join(VOLUME, d) if d else VOLUME
    target = safe_join(directory, f)
    if not directory or not (target and os.path.isfile(target)):
        abort(404)
    return send_file(target, as_attachment=True, download_name=f)

@app.post("/delete/<path:subpath>")
def delete(subpath):
    if DELETE_TOKEN and request.form.get("token") != DELETE_TOKEN:
        abort(403)
    d, f = os.path.split(subpath)
    base = safe_join(VOLUME, d) if d else VOLUME
    target = safe_join(base, f)
    if not target or not os.path.exists(target):
        abort(404)
    if os.path.isdir(target):
        shutil.rmtree(target)
    else:
        os.remove(target)
    parent = "/".join([p for p in (d or "").split("/") if p])
    return redirect(url_for("index", subpath=parent))

# -------------------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------------------
if __name__ == "__main__":
    Path(VOLUME).mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=PORT)
