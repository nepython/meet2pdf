import img2pdf
import os
from natsort import natsorted, ns

dirname = "./slides"

for folder in os.listdir(dirname):
    print (folder)
    imgs = []
    for fname in os.listdir(f"{dirname}/{folder}/"):
        if not fname.endswith(".jpg"):
            continue
        path = os.path.join(dirname, folder, fname)
        if os.path.isdir(path):
            continue
        imgs.append(path)

    imgs = natsorted(imgs, key=lambda y: y.lower())
    print(imgs)
    with open(f"{dirname}/{folder}.pdf","wb") as f:
        f.write(img2pdf.convert(imgs))



