import math

import numpy as np
import video_audio_libs
from PIL import Image
import os
from tqdm import tqdm

from tempfile import TemporaryFile


# mic_frequency = 44100 #Hz
# fps = 30
# audio1 = []
# video1 = []


def group_audio_video_sync(image_in_dir, img_rescale, audio_in, fps):
  audio1 = []
  video1 = []

  time, signal, mic_freq = video_audio_libs.audio2numpy(audio_in)
  print(len(signal))

  file1 = os.listdir(image_in_dir)

  for f in tqdm(file1):
    img = Image.open(f"{image_in_dir}/{f}")
    img.thumbnail(img_rescale, Image.ANTIALIAS)
    np_img = np.array(img)
    video1.append(np_img)

  index = 0
  for f in tqdm(file1):
    chunk = []
    for s in range(int(math.floor(len(signal)/len(file1)))): #mic_freq/fps
      chunk.append(signal[index])
      index = index + 1
    audio1.append(chunk)
  print(index)

  video1 = np.array(video1)
  audio1 = np.array(audio1)

  np.savez("data.npz", audio=audio1, video=video1)

  return audio1, video1

def data_to_wave(data):
  signal = []

  for i in tqdm(data):
    for a in i:
      signal.append(a)

# audio, video = group_audio_video_sync("Frames/1", (500, 500), "Raw_Data/Audio/1.wav", 30)

# print(len(audio[0])*len(video))

npzfile = np.load("data.npz")
audio = npzfile['audio']
video = npzfile['video']
# print(npzfile.files)
print(video[0][0].shape)