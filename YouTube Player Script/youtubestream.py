1. Copy and paste this command into your terminal to install all required libraries:
   pip install opencv-python numpy flask flask-sock yt-dlp

2.Copy script and run:

import time
import yt_dlp
from flask_sock import Sock
import cv2
from flask import Flask
import threading
import numpy as np

app = Flask(__name__)
sock = Sock(app)

vid_url = ""
width = 0
height = 0
buf = b""

def do_video():
    global vid_url, width, height, buf
    
    f1 = None
    while True:
        if vid_url == "":
            f1 = None
            time.sleep(1)
            continue
            
        try:
            info = yt_dlp.YoutubeDL({"format": "worst", "quiet": True}).extract_info(vid_url, download=False)
            stream = info["url"]
        except:
            print("err get link")
            vid_url = ""
            continue
            
        cap = cv2.VideoCapture(stream)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0:
            fps = 30
        
        while cap.isOpened() and vid_url != "":
            t = time.time()
            ret, frame = cap.read()
            if not ret:
                break
            
            if width > 0 and height > 0:
                try:
                    b = int(min(frame.shape[1] / width, frame.shape[0] / height) * 0.4)
                    b = (b // 2) * 2 + 1
                    
                    f2 = cv2.GaussianBlur(frame, (b, b), 0)
                    f2 = cv2.resize(f2, (width, height))
                    f2 = cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)
                    
                    if f1 is not None and f2.shape == f1.shape:
                        d = np.max(cv2.absdiff(f2, f1), axis=2)
                        f2[d < 12] = f1[d < 12]
                        
                    f1 = f2.copy()
                    buf = f2.tobytes()
                except:
                    pass
            
            d = (1 / fps / 1.17) - (time.time() - t)
            if d > 0:
                time.sleep(d)
        
        cap.release()

@sock.route("/stream")
def handle_ws(ws):
    global vid_url, width, height
    
    def read_msg():
        global vid_url, width, height
        
        while True:
            try:
                m = ws.receive()
                
                if m.startswith("dim:"):
                    dims = m.replace("dim:", "").split(",")
                    width = int(dims[0])
                    height = int(dims[1])
                    
                if m.startswith("url:"):
                    vid_url = m.replace("url:", "").strip()
                    
                if m == "stop":
                    vid_url = ""
                    
            except:
                break
                
    threading.Thread(target=read_msg, daemon=True).start()
    
    last = 0
    
    while True:
        if time.time() - last > 0.05:
            if buf != b"":
                try:
                    ws.send(buf)
                except:
                    break
                    
            last = time.time()
            
        time.sleep(0.01)

threading.Thread(target=do_video, daemon=True).start()

try:
    app.run(port=8080, use_reloader=False)
except KeyboardInterrupt:
    print("server stopped")
