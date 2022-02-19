import os
import cv2 
import random
import json
import pickle
from torchvision import transforms
from test_i3d import *
#from vid import split_by_seconds,get_video_length
#import ffmpeg
from moviepy.editor import VideoFileClip
from time import sleep
import numpy as np
import videotransforms
import numpy as np
from datasets.nslt_dataset import NSLT as Dataset
import streamlit as st

#full_video = "videos/can i help you (2).mp4"

train_split = 'preprocess/nslt_2000.json'
weights = 'checkpoints/nslt_2000_065846_0.447803.pt'
mode = 'rgb'
num_classes = 2000
save_model = './checkpoints/'



def save_uploadedfile(path,uploadedfile):
     with open(os.path.join(path,uploadedfile.name),"wb") as f:
            f.write(uploadedfile.getbuffer())
            return st.success("Saved File:{} to videos".format(uploadedfile.name))
        
def get_pred():
    with open('predictions.txt') as f:
        pred = f.readlines()
    return pred

def get_labels():
    with open('preprocess/wlasl_class_list.txt') as f:
        labels = f.readlines()
    return labels

def get_text_words():
    words = [i.split('\n')[0] for i in get_pred() ]
    map = {}
    for element in get_labels():
        first = element.split('\t')
        second = first[1].split('\n')[0]
        map[first[0]] = second
    text_words = [map[num] for num in words]
    return text_words

def read_and_write(videos_path,video_name):
    print("####Reading video####")
    id = video_name.split(".")[0]
    path=os.path.join(videos_path,video_name)
    print(path)
    capture = cv2.VideoCapture(path)
    frameNr = 0 
    while True:
        success, frame = capture.read() 
        if success:
            frameNr = frameNr+1
        else:
            print("done")
            break

    dictionary = {str(id):{
                      "subset":"test",
                      "action":[random.randint(0,2000),1,frameNr]
                    }}
    return dictionary

def write_json(dictionary):
    json_object = json.dumps(dictionary, indent = 4)
    with open("sample.json", "w") as outfile:
        print("### opening sample.json ###")
        outfile.write(json_object)

def read_and_run(root):
        test_transforms = transforms.Compose([videotransforms.CenterCrop(224)])
        dataset = Dataset("sample.json", 'test', root, mode, test_transforms)
        datasets = {'test': dataset}
        run(mode=mode, root=root, train_split="sample.json", weights=weights, datasets=datasets, num_classes=num_classes)


def split_video(full_video):
    full_video="videos/"+full_video
    current_duration = VideoFileClip(full_video).duration
    c = current_duration/3
    divide_into_count = np.ceil(c)
    single_duration = current_duration/divide_into_count
    current_video = f"{current_duration}.mp4"
    cnt = 1
    while current_duration >= single_duration:
        clip = VideoFileClip(full_video).subclip(current_duration-single_duration, current_duration)
        current_duration -= single_duration
        current_video = f"videos/clipped_videos/{cnt}.mp4"
        clip.to_videofile(current_video, codec="libx264", temp_audiofile='temp-audio.m4a', remove_temp=True, audio_codec='aac')
        cnt += 1


def get_word(video_name):
        ## Change to where the videos are located
    root = {'word':'videos'}
    videos_path="videos"
    dict_1=read_and_write(videos_path,video_name)
    write_json(dict_1)
    read_and_run(root)
    return get_text_words()

def get_sent(video_name):
    split_video(video_name)
    #os.chdir('.')
    root = {'word':'videos\clipped_videos'}
    videos_path="videos\clipped_videos"    
    complete_dict={}
    for video in os.listdir(videos_path):
        dict_2=read_and_write(videos_path,video)
        complete_dict.update(dict_2)
    write_json(complete_dict)
    read_and_run(root)
    return get_text_words()
