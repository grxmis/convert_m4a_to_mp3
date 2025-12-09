from flask import Flask, render_template_string, request, send_from_directory, jsonify
import os
import subprocess
import threading
import time
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
    .box { background:white; padding:20px; max-width:650px; margin:auto; border-radius:10px }
    button { padding:8px 16px; margin-top:5px; }
    select { width:100%; height:150px }
    .progress-bar { width:100%; background:#ddd; border-radius:10px; overflow:hidden; margin-top:10px }
    .progress-bar-fill { height:25px; width:0%; background:#4CAF50; text-align:center; color:white; transition: width 0.4s; }
  </style>
</head>
<body>

<div class="box">
  <h2>M4A → MP3 Converter</h2>

  <input type="file" id="files" multiple accept=".m4a"><br><br>
  <button onclick="addFiles()">Προσθήκη στη λίστα</button>

  <h4>Λίστα αρχείων</h4>
  <select id="fileList" multiple></select><br>
  <button onclick="removeSelected()">Αφαίρεση επιλεγμένου</button><br><br>

  <button onclick="startConvert()">Μετατροπή</button>

  <div class="progress-bar">
    <div class="progress-bar-fill" id="bar">0%</div>
  </div>

  <div id="results"></div>
</div>

<script>
let selectedFiles = [];
let taskId = "";

function addFiles() {
  let input = document.getElementById("files");
  for (let f of input.files) {
    selectedFiles.push(f);
  }
  refreshList();
}

function refreshList() {
  let list = document.getElementById("fileList");
  list.innerHTML = "";
  selectedFiles.forEach((f, i) => {
    let opt = document.createElement("option");
    opt.value = i;
    opt.text = f.name;
    list.appendChild(opt);
  });
}

function removeSelected() {
  let list = document.getElementById("fileList");
  let indexes = Array.from(list.selectedOptions).map(o => o.value);
  selectedFiles = selectedFiles.filter((_, i) => !indexes.includes(String(i)));
  refreshList();
}

function startConvert() {
  if (selectedFiles.length === 0) return alert("Δεν υπάρχουν αρχεία!");

  taskId = crypto.randomUUID();
  let formData = new FormData();
  formData.append("taskId", taskId);

  for (let f of selectedFiles) {
    formData.append("files", f);
  }

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
        setTimeout(pollProgress, 500);
      } else {
        document.getElementById("results").innerHTML = data.links;
        selectedFiles = [];
        refreshList();
      }
    });
}
</script>

</body>
</html>
"""

def convert_files(files, task_id):
    total = len(files)
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

        # Fake smooth progress (για ομαλή μπάρα)
        for step in range(5):
            current = int(((i + (step+1)/5) / total) * 100)
            progress_data[task_id] = current
            time.sleep(0.2)

        links += f'<p><a href="/download/{output_name}">{output_name}</a></p>'

    progress_data[task_id] = 100
    progress_data[task_id + "_links"] = links

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("files")
        task_id = request.form.get("taskId") or str(uuid.uuid4())
        progress_data[task_id] = 0

        thread = threading.Thread(target=convert_files, args=(files, task_id))
        thread.start()

    return render_template_string(HTML)

@app.route("/progress/<task_id>")
def progress(task_id):
    p = progress_data.get(task_id, 0)
    links = progress_data.get(task_id + "_links", "")
    return jsonify({"progress": p, "links": links})

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
