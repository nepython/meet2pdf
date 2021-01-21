## Optimized for Google Meet Recordings
## For other records you might want to comment out the cropping part

## directory structure - Current directory should contain this file, jpgtopdf.py and a folder "videos". Place all the video files in ./videos
## Upon completion a ./slides will be formed. It will be having folders corresponding to each video. For example, ./slides/vid1, ./slides/vid2 and so on.

import cv2
import os

fileList = os.listdir("./videos/")
print(fileList)


def extractImages(pathIn, pathOut):
    print(pathIn)
    print(pathOut)
    count = 1
    vidcap = cv2.VideoCapture(pathIn)
    success = True
    fps = int(vidcap.get(cv2.CAP_PROP_FPS))
    secondsPerImage = 30

    shareScreenCoverage = {"h": float(0.75), "w": float(0.75)}

    while success:
        success, image = vidcap.read()
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
                cv2.imwrite(f"{pathOut}/frame{count}.jpg", image)
            except:
                print(f"nah, {count} failed")
            finally:
                count += 1


for file in fileList:
    # converts abc.mp4 to abc
    fileName = file[:-4]
    file = f"./videos/{file}"
    directory = fileName  # Directory
    parent_dir = "./slides"  # Parent Directory path
    path = os.path.join(parent_dir, directory)  # Path
    try:  # Create the directory
        os.makedirs(path, exist_ok=True)
        print("Directory '%s' created successfully" % directory)
        extractImages(file, f"./slides/{fileName}")
        print(file, " is done.")
    except OSError as error:
        print("Directory '%s' can not be created")
        print(file, " didn't complete successfully.")