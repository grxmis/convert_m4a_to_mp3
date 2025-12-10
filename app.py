from flask import Flask, render_template_string, request, send_from_directory, jsonify
import os
import subprocess
import uuid
import threading

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
button { padding:10px 20px; font-size:16px; margin-top:5px; cursor:pointer; }
select { width:100%; height:120px; margin-top:10px }

.file-input-wrapper { position: relative; overflow: hidden; display: inline-block; }
.file-input-wrapper button {
    background-color: #4CAF50; color: white;
    padding: 10px 20px; border-radius: 5px; cursor: pointer;
}
.file-input-wrapper input[type=file] {
    font-size: 100px; position: absolute; left: 0; top: 0; opacity: 0;
}

#status {
    margin-top:15px;
    font-weight: bold;
    color: #333;
    display: none;
}
</style>
</head>
<body>

<div class="box">
  <h2>M4A → MP3 Converter</h2>

  <div class="file-input-wrapper">
      <button>Επιλογή Αρχείων</button>
      <input type="file" id="files" multiple accept=".m4a" onchange="updateList()">
  </div><br><br>

  <select id="fileList" multiple></select><br>
  <button onclick="removeSelected()" id="removeBtn">Αφαίρεση επιλεγμένου</button><br><br>

  <button onclick="startUpload()" id="convertBtn">Μετατροπή</button>

  <div id="status">⏳ Περιμένετε όσο γίνεται η μετατροπή...</div>

  <div id="results"></div>
</div>

<script>
let selectedFiles = [];
let taskId = "";

function updateList() {
    selectedFiles = Array.from(document.getElementById("files").files);
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
    let indexes = Array.from(list.selectedOptions).map(o => parseInt(o.value));
    selectedFiles = selectedFiles.filter((_, i) => !indexes.includes(i));
    refreshList();
}

function startUpload() {
    if (selectedFiles.length === 0) { 
        alert("Επίλεξε αρχεία"); 
        return; 
    }

    document.getElementById("convertBtn").disabled = true;
    document.getElementById("removeBtn").disabled = true;
    document.getElementById("files").disabled = true;

    document.getElementById("status").style.display = "block";

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
                document.getElementById("results").innerHTML = data.links;

                // Κρύψε μήνυμα
                document.getElementById("status").style.display = "none";

                // Επανενεργοποίηση κουμπιών
                document.getElementById("convertBtn").disabled = false;
                document.getElementById("removeBtn").disabled = false;
                document.getElementById("files").disabled = false;

                // Καθαρισμός αρχείων
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

        subprocess.run([
            FFMPEG_PATH, "-y",
            "-i", input_path,
            "-codec:a", "libmp3lame",
            "-qscale:a", "2",
            output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        percent = int(((i + 1) / total) * 100)
        progress_data[task_id] = percent

        links += f'<p><a href="/download/{output_name}">{output_name}</a></p>'

    progress_data[task_id] = 100
    progress_data[task_id + "_links"] = links

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("files")
        task_id = request.form.get("taskId") or str(uuid.uuid4())

        progress_data[task_id] = 0
        threading.Thread(target=convert_files, args=(files, task_id)).start()

    return render_template_string(HTML)

@app.route("/progress/<task_id>")
def progress(task_id):
    p = progress_data.get(task_id, 0)
    links = progress_data.get(task_id + "_links", "")
    return jsonify({"progress": p, "links": links})

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
