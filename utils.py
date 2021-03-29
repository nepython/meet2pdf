import os
import shutil

from natsort import natsorted, ns
import cv2
import img2pdf

from global_defaults import *


def extractImages(pathIn, pathOut, secondsPerImage=60, **kwargs):
    count = 1
    imageNumber = 0
    vidcap = cv2.VideoCapture(pathIn)
    success = True
    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    shareScreenCoverage = {"h": float(0.75), "w": float(0.75)}
    while success:
        success, image = vidcap.read()
        count += 1
        if count % (secondsPerImage * fps) == 0:
            h, w, dimension = image.shape
            croppedImageAttributes = {
                "top": int((((1 - shareScreenCoverage["h"]) / 2) * h)),
                "bottom": int((h - (((1 - shareScreenCoverage["h"]) / 2) * h))),
                "left": int(0),
                "right": int(shareScreenCoverage["w"] * w),
            }
            # to crop Google meet slides frame only and ignore the speaker part of screen
            image = image[
                croppedImageAttributes["top"] : croppedImageAttributes["bottom"],
                croppedImageAttributes["left"] : croppedImageAttributes["right"],
            ]
            try:
                cv2.imwrite(f"{pathOut}/frame{imageNumber}.jpg", image)
            except:
                pass
            finally:
                imageNumber += 1


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

def freeUpSpace(unique_id, video=True, images=True, pdf=False):
    if video:
        os.remove(f'./{videos_dir}/{unique_id}')
    if images:
        shutil.rmtree(f'./{slides_dir}/{unique_id}')
    if pdf:
        os.remove(f'./{pdfs_dir}/{unique_id}')
