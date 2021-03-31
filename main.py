import os
import json

import ocrmypdf
from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    abort,
    current_app,
    send_file,
    url_for,
    redirect,
    render_template,
    make_response,
)
from flask_cors import CORS, cross_origin
from celery import Celery
from oauth2client import client
from oauth2client.file import Storage

from global_defaults import *
from utils import video_to_frames, convert2pdf, freeUpSpace, download_file, GetYT


################ FLASK DECLARATIONS ####################
app = Flask(__name__,
        static_url_path='/assets',
        static_folder='assets'
    )
# Max file size that can be uploaded
app.config["MAX_CONTENT_LENGTH"] = max_video_size

cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"

app.config["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
app.config["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

################ CELERY DECLARATIONS ###################
celery = Celery(app.name, broker=app.config["CELERY_BROKER_URL"])
celery.conf.update(app.config)


##################### MAIN WEBAPP #######################
@cross_origin
@app.route("/")
def index():
    return send_from_directory("./", "index.html")


@cross_origin
@app.route("/<unique_id>", methods=["POST", "GET"])
def upload_files(unique_id):
    if request.method == "GET":
        return _get_pdf_or_error(unique_id)
    if request.method == "POST":
        mode = int(request.form.get("mode"))
        meet = bool(int(request.form.get("meet", True)))
        seconds = int(request.form.get("seconds", 60))

        if mode == 0:  # Plain upload
            uploaded_file = request.files["file"]
            filename = uploaded_file.filename
            if filename != "":
                file_ext = os.path.splitext(filename)[1]
                # The file extensions that shall be allowed
                if file_ext not in [".mp4", ".mov", ".webm", ".wmv", ".mkv"]:
                    return jsonify({"error": "File extension not supported"}), 400
            uploaded_file.save(os.path.join(f"./{videos_dir}", unique_id))
            # Start an async function to process the video which keeps running in background
            convert2images.delay(unique_id, meet, seconds)
            return jsonify({"uploaded": unique_id}), 200

        if mode == 1:  # GDrive Upload
            link = request.form.get("link")
            if os.path.exists("client_id.json") == False:
                print("Client secrets file (client_id.json) not found in the app path.")
            credentials = _get_credentials(unique_id)
            if not credentials:
                return (
                    jsonify(
                        {
                            "error": "Your credentials have expired kindly logout and login again."
                        }
                    ),
                    404,
                )
            success = download_file(link, unique_id, credentials)
            if success:
                convert2images.delay(unique_id, meet, seconds)
                return jsonify({"uploaded": unique_id}), 200
            else:
                return (
                    jsonify({"error": "File could not be accessed, try again later."}),
                    400,
                )
            return redirect(url_for("index"))

        if mode == 2:  # YouTube Upload
            link = request.form.get("link")
            _, title = GetYT(link, unique_id)
            success = os.path.exists(f'./{videos_dir}/{unique_id}.mp4')
            if success:
                os.rename(f'./{videos_dir}/{unique_id}.mp4', f'./{videos_dir}/{unique_id}')
                convert2images.delay(unique_id, meet=meet, seconds=seconds)
                return jsonify({"uploaded": unique_id}), 200
            else:
                return  jsonify({"error": "Video could not downloaded"}), 400


@cross_origin
@app.route("/user/validate", methods=["GET"])
def logged_in():
    cred = request.cookies.get("drive")
    if cred:
        return jsonify({}), 200
    return jsonify({}), 403


@cross_origin
@app.route("/user/oauth2callback")
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        "client_id.json",
        scope="https://www.googleapis.com/auth/drive",
        redirect_uri=url_for("oauth2callback", _external=True),
    )  # access drive api using developer credentials
    flow.params["include_granted_scopes"] = "true"
    if "code" not in request.args:
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)
    else:
        auth_code = request.args.get("code")
        credentials = flow.step2_exchange(auth_code).to_json()
        resp = make_response(redirect("/?mode=1"))
        resp.set_cookie("drive", credentials)
        return resp


def _get_pdf_or_error(unique_id):
    if os.path.exists(f"./{pdfs_dir}/{unique_id}.pdf"):  # Search for PDF
        return send_file(f"./{pdfs_dir}/{unique_id}.pdf", attachment_filename="{}.pdf")
    elif os.path.exists(
        f"./{videos_dir}/{unique_id}"
    ):  # if it doesn't exist then search in videos directory if a video with this id exists
        return jsonify({"error": "The video is being processed"}), 403
    return (
        jsonify({"error": "No PDF with this id exists"}),
        404,
    )  # If video doesn't exist then return error


def _get_credentials(unique_id):
    os.makedirs(f"./{credentials_dir}", exist_ok=True)
    credential_path = f"./{credentials_dir}/{unique_id}.json"
    credentials = json.loads(request.cookies.get("drive"))
    open(credential_path, "w").write(request.cookies.get("drive"))
    store = Storage(credential_path)
    credentials = store.get()
    os.remove(credential_path)
    if not credentials or credentials.invalid:
        print("Credentials not found.")
        return False
    else:
        print("Credentials fetched successfully.")
        return credentials


@cross_origin
@app.route("/google7506ff0ebc1e342c.html")
def google_verification():
    return send_from_directory("./", "google7506ff0ebc1e342c.html")


################## CELERY TASK ##########################
@celery.task
def convert2images(unique_id, meet, seconds):
    file = f"./{videos_dir}/{unique_id}"
    directory = unique_id  # Directory
    parent_dir = f"./{slides_dir}"  # Parent Directory path
    path = os.path.join(parent_dir, directory)  # Path
    try:
        os.makedirs(path, exist_ok=True)
        print("Directory '%s' created successfully" % directory)
        frames = video_to_frames(
            video_path=file, frames_dir=f"./{slides_dir}", seconds=seconds, meet=meet
        )
        if frames:  # If no frames have been generated due to poor video
            convert2pdf(unique_id)
            ocrmypdf.ocr(
                f"./{pdfs_dir}/{unique_id}.pdf",
                f"./{pdfs_dir}/{unique_id}.pdf",
                deskew=True,
                pdf_renderer="hocr",
                language="eng",
            )
        freeUpSpace(unique_id)
    except OSError:
        print("Directory '{0}' can not be created".format(unique_id))
        print(file, " didn't complete successfully.")


if __name__ == "__main__":
    app.run()
######################### END ###########################
