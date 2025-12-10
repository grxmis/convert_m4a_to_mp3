from flask import Flask, render_template_string, request, send_from_directory, jsonify
import os
import subprocess
import zipfile
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_mp3"
ZIP_FOLDER = "zips"
FFMPEG_PATH = "ffmpeg"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

progress_data = {}

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>M4A → MP3 Converter</title>
  <style>
    body { font-family: Arial; background:#f2f2f2; padding:30px }
    .box { background:white; padding:20px; max-width:600px; margin:auto; border-radius:10px; text-align:center }
    #fileInput { display:none }
    .green-btn {
      background:#2ecc71;
      color:white;
      border:none;
      padding:12px 25px;
      font-size:16px;
      border-radius:6px;
      cursor:pointer;
    }
    select { width:100%; height:150px; margin-top:15px }
    button { padding:10px 20px; font-size:16px; margin-top:10px; cursor:pointer }
    #wait { margin-top:15px; font-weight:bold; display:none }
  </style>
</head>
<body>

<div class="box">
  <h2>M4A → MP3 Converter</h2>

  <input type="file" id="fileInput" multiple accept=".m4a" onchange="updateFileList()">

  <button class="green-btn" onclick="document.getElementById('fileInput').click()">Επιλογή αρχείων</button>

  <select id="fileList" multiple></select>

  <br>
  <button onclick="removeSelected()">Αφαίρεση επιλεγμένου</button>

  <br>
  <button id="convertBtn" onclick="startUpload()">Μετατροπή</button>

  <div id="wait">Παρακαλώ περιμένετε όσο γίνεται η μετατροπή..</div>

  <div id="results"></div>
  <div id="downloadAll"></div>
</div>

<script>
let selectedFiles = [];
let taskId = "";

function updateFileList() {
  let input = document.getElementById("fileInput");
  let list = document.getElementById("fileList");

  for (let file of input.files) {
    selectedFiles.push(file);
  }

  list.innerHTML = "";
  selectedFiles.forEach((file, index) => {
    let opt = document.createElement("option");
    opt.value = index;
    opt.text = file.name;
    list.appendChild(opt);
  });

  input.value = "";
}

function removeSelected() {
  let list = document.getElementById("fileList");
  let index = list.selectedIndex;

  if (index > -1) {
    selectedFiles.splice(index, 1);

    list.innerHTML = "";
    selectedFiles.forEach((file, i) => {
      let opt = document.createElement("option");
      opt.value = i;
      opt.text = file.name;
      list.appendChild(opt);
    });
  }
}

function startUpload() {
  if (selectedFiles.length === 0) {
    alert("Επίλεξε αρχεία!");
    return;
  }

  document.getElementById("wait").style.display = "block";
  document.getElementById("results").innerHTML = "";
  document.getElementById("downloadAll").innerHTML = "";
  document.getElementById("convertBtn").disabled = true;

  taskId = crypto.randomUUID();
  let formData = new FormData();
  formData.append("taskId", taskId);

  for (let f of selectedFiles) {
    formData.append("files", f);
  }

  fetch("/", { method: "POST", body: formData });
  pollStatus();
}

function pollStatus() {
  fetch("/progress/" + taskId)
    .then(r => r.json())
    .then(data => {
      if (data.progress < 100) {
        setTimeout(pollStatus, 1000);
      } else {
        document.getElementById("wait").style.display = "none";
        document.getElementById("convertBtn").disabled = false;
        selectedFiles = [];
        document.getElementById("fileList").innerHTML = "";
        document.getElementById("results").innerHTML = data.links;

        if (data.zip) {
          document.getElementById("downloadAll").innerHTML =
            '<br><a href="/download_zip/' + data.zip + '"><button class="green-btn">Λήψη όλων (ZIP)</button></a>';
        }
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
        created_files = []

        for i, file in enumerate(files):
            input_path = os.path.join(UPLOAD_FOLDER, file.filename)
            base_name = os.path.splitext(file.filename)[0]
            output_name = base_name + ".mp3"
            output_path = os.path.join(OUTPUT_FOLDER, output_name)

            file.save(input_path)

            cmd = [
                FFMPEG_PATH, "-y",
                "-i", input_path,
                "-codec:a", "libmp3lame",
                "-qscale:a", "2",
                output_path
            ]
            subprocess.run(cmd)

            created_files.append(output_name)

            percent = int(((i + 1) / total) * 100)
            progress_data[task_id] = percent

            links += f'<p><a href="/download/{output_name}">{output_name}</a></p>'

        # Δημιουργία ZIP
        zip_name = f"{task_id}.zip"
        zip_path = os.path.join(ZIP_FOLDER, zip_name)

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for f in created_files:
                zipf.write(os.path.join(OUTPUT_FOLDER, f), f)

        progress_data[task_id] = 100
        progress_data[task_id + "_links"] = links
        progress_data[task_id + "_zip"] = zip_name

    return render_template_string(HTML)

@app.route("/progress/<task_id>")
def progress(task_id):
    return jsonify({
        "progress": progress_data.get(task_id, 0),
        "links": progress_data.get(task_id + "_links", ""),
        "zip": progress_data.get(task_id + "_zip", "")
    })

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

@app.route("/download_zip/<filename>")
def download_zip(filename):
    return send_from_directory(ZIP_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
