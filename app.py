from flask import Flask, render_template_string, request, send_from_directory, jsonify
import os
import subprocess
import uuid
import zipfile

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_mp3"
ZIP_FOLDER = "zips"
FFMPEG_PATH = "ffmpeg"  # Σε Windows, βάλτε πλήρη διαδρομή π.χ. r"C:\ffmpeg\bin\ffmpeg.exe"

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
.box { background:white; padding:20px; max-width:600px; margin:auto; border-radius:10px }
button { padding:10px 20px; font-size:16px; margin-top:5px; cursor:pointer; }
select { width:100%; height:120px; margin-top:10px }
.green-btn { background-color:#4CAF50; color:white; border:none; border-radius:5px; cursor:pointer; }
#waitMsg { margin-top:10px; font-weight:bold; color:blue; display:none; }
</style>
</head>
<body>

<div class="box">
  <h2>M4A → MP3 Converter</h2>

  <div>
      <label class="green-btn">
          Επιλογή Αρχείων
          <input type="file" id="files" multiple accept=".m4a" style="display:none" onchange="updateList()">
      </label>
  </div><br>

  <select id="fileList" multiple></select><br>
  <button onclick="removeSelected()" id="removeBtn">Αφαίρεση επιλεγμένου</button><br><br>

  <button onclick="startUpload()" id="convertBtn">Μετατροπή</button>
  <div id="waitMsg">Παρακαλώ περιμένετε όσο γίνεται η μετατροπή...</div>

  <div id="zipbox"></div>
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
    if (selectedFiles.length === 0) { alert("Επίλεξε αρχεία"); return; }

    document.getElementById("convertBtn").disabled = true;
    document.getElementById("removeBtn").disabled = true;
    document.getElementById("files").disabled = true;
    document.getElementById("waitMsg").style.display = "block";
    document.getElementById("zipbox").innerHTML = "";

    taskId = crypto.randomUUID();
    let formData = new FormData();
    formData.append("taskId", taskId);

    for (let f of selectedFiles) formData.append("files", f);

    fetch("/", { method: "POST", body: formData });
    pollProgress();
}

function pollProgress() {
    fetch("/progress/" + taskId)
        .then(r => r.json())
        .then(data => {
            if (data.progress < 100) {
                setTimeout(pollProgress, 1000);
            } else {
                document.getElementById("waitMsg").style.display = "none";
                document.getElementById("zipbox").innerHTML =
                    '<a href="/download_zip/' + data.zip + '">' +
                    '<button class="green-btn">Λήψη όλων σε ZIP</button></a>';

                document.getElementById("convertBtn").disabled = false;
                document.getElementById("removeBtn").disabled = false;
                document.getElementById("files").disabled = false;

                selectedFiles = [];
                refreshList();
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
        progress_data[task_id] = 0
        mp3_files = []

        for file in files:
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
            mp3_files.append(output_path)

        # Δημιουργία ZIP
        zip_name = f"{task_id}.zip"
        zip_path = os.path.join(ZIP_FOLDER, zip_name)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for mp3 in mp3_files:
                zipf.write(mp3, os.path.basename(mp3))

        progress_data[task_id] = 100
        progress_data[task_id + "_zip"] = zip_name

    return render_template_string(HTML)

@app.route("/progress/<task_id>")
def progress(task_id):
    p = progress_data.get(task_id, 0)
    zip_name = progress_data.get(task_id + "_zip", "")
    return jsonify({"progress": p, "zip": zip_name})

@app.route("/download_zip/<filename>")
def download_zip(filename):
    return send_from_directory(ZIP_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
