import os

from flask import Flask, request, jsonify, send_from_directory, abort, current_app, send_file
from flask_cors import CORS, cross_origin
from celery import Celery

from global_defaults import *
from utils import video_to_frames, convert2pdf, freeUpSpace


################ FLASK DECLARATIONS ####################
app = Flask(__name__)
# Max file size that can be uploaded
app.config['MAX_CONTENT_LENGTH'] = max_video_size

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

################ CELERY DECLARATIONS ###################
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


##################### MAIN WEBAPP #######################
@cross_origin
@app.route('/')
def index():
    return send_from_directory("./", "index.html")


@cross_origin
@app.route('/<unique_id>', methods=['POST', 'GET'])
def upload_files(unique_id):
    if (request.method == 'GET'):
        # Search for PDF
        if os.path.exists(f'./{pdfs_dir}/{unique_id}.pdf'):
            return send_file(f'./{pdfs_dir}/{unique_id}.pdf', attachment_filename='{}.pdf')
        # if it doesn't exist then search in videos directory if a video with this id exists
        elif os.path.exists(f'./{videos_dir}/{unique_id}'):
            # If video exists then send message that it is being processed
            return jsonify({'error': 'The video is being processed'}), 403
        # If video doesn't exist then return error
        return jsonify({'error': 'No PDF with this id exists'}), 404
    if (request.method == 'POST'):
        uploaded_file = request.files['file']
        filename = uploaded_file.filename
        meet = bool(int(request.form.get('meet', True)))
        seconds = int(request.form.get('seconds', 60))
        if filename != '':
            file_ext = os.path.splitext(filename)[1]
            # The file extensions that shall be allowed
            if file_ext not in ['.mp4', '.mov', '.webm', '.wmv', '.mkv']:
                return jsonify({'error': 'File extension not supported'}), 400
        uploaded_file.save(os.path.join(f'./{videos_dir}', unique_id))
        # Start an async function to process the video which keeps running in background
        convert2images.delay(unique_id, meet, seconds)
        return jsonify({'uploaded': unique_id}), 200


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
        frames = video_to_frames(video_path=file, frames_dir=f"./{slides_dir}", seconds=seconds, meet=meet)
        if frames: # If no frames have been generated due to poor video
            convert2pdf(unique_id)
        freeUpSpace(unique_id)
    except OSError:
        print("Directory '{0}' can not be created".format(unique_id))
        print(file, " didn't complete successfully.")

if __name__ == "__main__":
	app.run()
######################### END ###########################
