import os
import shutil
from io import BytesIO

import cv2
import img2pdf
import imageio as io
import numpy as np
from decord import VideoReader
from decord import cpu, gpu
from natsort import natsorted, ns
from skimage.metrics import structural_similarity as ssim
import httplib2
from apiclient import discovery
from apiclient.http import MediaIoBaseDownload, MediaFileUpload

from global_defaults import *


def extract_frames(video_path, frames_dir, start=-1, end=-1, seconds=0.1, meet=True):
    """
    Extract frames from a video using decord's VideoReader
        :param video_path: path of the video
        :param frames_dir: the directory to save the frames
        :param overwrite: to overwrite frames that already exist?
        :param start: start frame
        :param end: end frame
        :param seconds: frame spacing
        :return: count of images saved
    """

    video_path = os.path.normpath(video_path)  # make the paths OS (Windows) compatible
    frames_dir = os.path.normpath(frames_dir)  # make the paths OS (Windows) compatible

    video_dir, video_filename = os.path.split(video_path)  # get the video path and filename from the path

    assert os.path.exists(video_path)  # assert the video file exists

    vidcap = cv2.VideoCapture(video_path)
    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    if fps == 0:
        return False
    seconds = int(seconds*fps)
    frameToStore = None 

    try:
        vr = VideoReader(video_path, ctx=gpu(0))  # can set to cpu or gpu
    except:
        vr = VideoReader(video_path, ctx=cpu(0))  # can set to cpu or gpu

    if (meet):
        shareScreenCoverage = {"h": float(0.75), "w": float(0.75)}
    else:
        shareScreenCoverage = {"h": float(1), "w": float(1)}
    if start < 0:  # if start isn't specified lets assume 0
        start = 0
    if end < 0:  # if end isn't specified assume the end of the video
        end = len(vr)

    frames_list = list(range(start, end, seconds))
    saved_count = 0
    frames = vr.get_batch(frames_list).asnumpy()

    for index, frame in zip(frames_list, frames):  # lets loop through the frames until the end
        save_path = os.path.join(frames_dir, video_filename, f"frame{saved_count}.jpg")  # create the save path
        newFrame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        h, w, dimension = newFrame.shape
        croppedImageAttributes = {
            "top": int((((1 - shareScreenCoverage["h"]) / 2) * h)),
            "bottom": int((h - (((1 - shareScreenCoverage["h"]) / 2) * h))),
            "left": int(0),
            "right": int(shareScreenCoverage["w"] * w),
        }
        # to crop Google meet slides frame only and ignore the speaker part of screen
        newFrame = newFrame[
            croppedImageAttributes["top"] : croppedImageAttributes["bottom"],
            croppedImageAttributes["left"] : croppedImageAttributes["right"],
        ]

        # have seen atleast 1 frame before. 
        if frameToStore is not None:
            # compare new frame with last frame
            same:bool = CheckSimilarity(frameToStore, newFrame)
            # save last frame if last frame is not same as new frame
            if not same:
                cv2.imwrite(save_path, frameToStore)  # save the extracted image
                saved_count += 1  # increment our counter by one
        frameToStore = newFrame

    # save the last image too if it was diff from prev frame
    if not same:
        cv2.imwrite(save_path, frameToStore)  # save the extracted image
        saved_count += 1
    return True


def video_to_frames(video_path, frames_dir, seconds=1, meet=True):
    """
    Extracts the frames from a video
        :param video_path: path to the video
        :param frames_dir: directory to save the frames
        :param seconds: extract 1 frames in these many seconds
        :return: path to the directory where the frames were saved, or None if fails
    """

    video_path = os.path.normpath(video_path)  # make the paths OS (Windows) compatible
    frames_dir = os.path.normpath(frames_dir)  # make the paths OS (Windows) compatible

    video_dir, video_filename = os.path.split(video_path)  # get the video path and filename from the path

    # make directory to save frames, its a sub dir in the frames_dir with the video name
    os.makedirs(os.path.join(frames_dir, video_filename), exist_ok=True)

    extract_frames(video_path, frames_dir, seconds=seconds, meet=meet)  # let's now extract the frames
    return os.path.join(frames_dir, video_filename)  # when done return the directory containing the frames

def convert2pdf(unique_id):
    imgs = []
    for fname in os.listdir(f"./{slides_dir}/{unique_id}/"):
        if not fname.endswith(".jpg"):
            continue
        path = os.path.join(f'./{slides_dir}', unique_id, fname)
        if os.path.isdir(path):
            continue
        imgs.append(path)
    imgs = natsorted(imgs, key=lambda y: y.lower())
    with open(f"./{pdfs_dir}/{unique_id}.pdf","wb") as f:
        f.write(img2pdf.convert(imgs))


# CheckSimilarity compares two images and returns True if the two images are similar
# to a threshold
def CheckSimilarity(img1: np.ndarray, img2: np.ndarray, thres=0.90):
    ''' Both img1 and img2 are nd arrays\n
        thres is a float percentage used to distinguish between same and different iamges\n 
        Returns True if the Images are similar(based on thres), False otherwise'''
    sim = ssim(img1, img2, data_range = img2.max() - img2.min(), multichannel=True) 
    if sim >= thres:
        return True
    return False



def fetch(query, sort='modifiedTime desc'):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    results = service.files().list(
        q=query,orderBy=sort,pageSize=10,fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    return items

def download_file(file_id, unique_id, credentials):
    """Downloads a file from google drive if user has been authenticated using oauth2

    Args:
        file_id (str): [The google drive id of the file]
        unique_id (str): [The name of the video that is to be used for stored file]

    Returns:
        bool: [whether the file has been successfully downloaded or not]
    """
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    # Initialise a downloader object to download the file
    # Downloads in chunks of 2MB
    downloader = MediaIoBaseDownload(fh, request, chunksize=2048000)
    done = False
    try:
        # Download the data in chunks
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        # Write the received data to the file
        with open(f'./{videos_dir}/{unique_id}', 'wb') as f:
            shutil.copyfileobj(fh, f)
        print("File Downloaded")
        # Return True if file Downloaded successfully
        return True
    except Exception as e:
        print(str(e))
        # Return False if something went wrong
        print("Something went wrong.")
        return False

def upload_file(file_id, local_file):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)
    # First retrieve the file from the API.
    file = service.files().get(fileId=file_id).execute()
    # File's new content.
    media_body = MediaFileUpload(local_file, resumable=True)
    # Send the request to the API.

    updated_file = service.files().update(
        fileId=file_id,
        #body=file,
        #newRevision=True,
        media_body=media_body).execute()


def freeUpSpace(unique_id, video=True, images=True, pdf=False):
    os.remove(f'./{pdfs_dir}/{unique_id}_tmp.pdf')
    if video:
        os.remove(f'./{videos_dir}/{unique_id}')
    if images:
        shutil.rmtree(f'./{slides_dir}/{unique_id}')
    if pdf:
        os.remove(f'./{pdfs_dir}/{unique_id}')
