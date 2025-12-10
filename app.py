from flask import Flask, render_template_string, request, send_from_directory, jsonify
import os
import subprocess
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_mp3"
FFMPEG_PATH = "ffmpeg"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

progress_data = {}

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>M4A → MP3 Converter</title>
  <style>
    body { font-family: Arial; background:#f2f2f2; padding:30px }
    .box { background:white; padding:20px; max-width:600px; margin:auto; border-radius:10px }
    button { padding:10px 20px; font-size:16px }
    .progress-bar { width:100%; background:#ddd; border-radius:10px; overflow:hidden; margin-top:10px }
    .progress-bar-fill { height:25px; width:0%; background:#4CAF50; text-align:center; color:white; }
  </style>
</head>
<body>

<div class="box">
  <h2>M4A → MP3 Converter</h2>

  <input type="file" id="files" multiple accept=".m4a"><br><br>
  <button onclick="startUpload()">Μετατροπή</button>

  <div class="progress-bar">
    <div class="progress-bar-fill" id="bar">0%</div>
  </div>

  <div id="results"></div>
</div>

<script>
let taskId = "";

function startUpload() {
  let files = document.getElementById("files").files;
  if (files.length === 0) { alert("Επίλεξε αρχεία"); return; }

  taskId = crypto.randomUUID();
  let formData = new FormData();
  formData.append("taskId", taskId);

  for (let f of files) formData.append("files", f);

  fetch("/", { method: "POST", body: formData });
  pollProgress();
}

function pollProgress() {
  fetch("/progress/" + taskId)
    .then(r => r.json())
    .then(data => {
      let p = data.progress;
      document.getElementById("bar").style.width = p + "%";
      document.getElementById("bar").innerText = p + "%";

      if (p < 100) {
        setTimeout(pollProgress, 1000);
      } else {
        document.getElementById("results").innerHTML = data.links;
      }
    });
}
</script>

</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("files")
        task_id = request.form.get("taskId")

        total = len(files)
        progress_data[task_id] = 0
        links = ""

        for i, file in enumerate(files):
            input_path = os.path.join(UPLOAD_FOLDER, file.filename)
            output_name = os.path.splitext(file.filename)[0] + ".mp3"
            output_path = os.path.join(OUTPUT_FOLDER, output_name)

            file.save(input_path)

            command = [
                FFMPEG_PATH, "-y",
                "-i", input_path,
                "-codec:a", "libmp3lame",
                "-qscale:a", "2",
                output_path
            ]
            subprocess.run(command)

            percent = int(((i + 1) / total) * 100)
            progress_data[task_id] = percent

            links += f'<p><a href="/download/{output_name}">{output_name}</a></p>'

        progress_data[task_id] = 100
        progress_data[task_id + "_links"] = links

    return render_template_string(HTML)

@app.route("/progress/<task_id>")
def progress(task_id):
    p = progress_data.get(task_id, 0)
    links = progress_data.get(task_id + "_links", "")
    return jsonify({"progress": p, "links": links})

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True) 
    