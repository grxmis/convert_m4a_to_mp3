from flask import Flask, render_template_string, request, send_from_directory
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output_mp3"
FFMPEG_PATH = "ffmpeg"  # Στο Render είναι διαθέσιμο με αυτό το όνομα

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

HTML = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>M4A to MP3 Converter</title>
</head>
<body style="font-family: Arial; background:#f5f5f5; padding:40px">

<h2>M4A → MP3 Converter</h2>

<form method="post" enctype="multipart/form-data">
    <input type="file" name="files" multiple accept=".m4a"><br><br>
    <button type="submit">Convert</button>
</form>

{% if files %}
    <h3>Converted files:</h3>
    <ul>
    {% for f in files %}
        <li><a href="/download/{{f}}">{{f}}</a></li>
    {% endfor %}
    </ul>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    converted_files = []
    if request.method == "POST":
        uploaded_files = request.files.getlist("files")

        for file in uploaded_files:
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

            converted_files.append(output_name)

    return render_template_string(HTML, files=converted_files)

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)
