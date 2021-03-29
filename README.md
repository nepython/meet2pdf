# `meet2pdf`

Supported video formats: `['.mp4', '.mov', '.webm', '.wmv', '.mkv']`

## To launch the flask app locally for development purposes
```code
# cd meet2pdf
$ sudo apt install libgl1-mesa-glx
$ pip install -r requirements.txt
$ python main.py
# In a separate terminal run below command to get celery worker runnning
$ sudo apt install redis-server
$ celery -A main.celery worker
```

## Endpoints
* `POST /<unique_id>`
- Response would be `200`, if the video has been uploaded successfully.
- Response would be `400`, if we don't support the video format.

* `GET /<unique_id>`
- Response would be `404`, if an illegal request is made (that is video doesn't exist).
- Response would be `200` with JSON `The video is being processed`, if PDF not yet ready.
- Response would return PDF if it's ready.
