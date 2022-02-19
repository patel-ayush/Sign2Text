import cv2
import streamlit as st
#from PIL import Image
import numpy as np
from api_call import correct_sent_tc_api
from sign_language_crework import get_word,get_sent,save_uploadedfile
import os

path="videos"

st.title("Sign to language")

st.markdown('<b style="font-family:Courier;font-size: 20px;">What you want to predict</b><br>', unsafe_allow_html=True)
fun_type = st.radio("",("Word","Sentence"))

st.markdown('<b style="font-family:Courier;font-size: 20px;">Upload a file</b>', unsafe_allow_html=True)
up_video = st.file_uploader("",type=(["mp4"]))

if up_video is not None:
    save_uploadedfile(path,up_video)
#video_file = st.file_uploader("video", type = ["mp4"])
    if fun_type=="Word":
        labels_list=get_word(video_name=up_video.name)
    else:
        labels_list=get_sent(video_name=up_video.name)
    
    st.markdown('<b style="font-family:Courier;font-size: 20px;">Predictions</b>', unsafe_allow_html=True)
    labels=" ".join(labels_list)
    st.write("labels : ",labels)
    st.write("Sent : ",correct_sent_tc_api(labels))
    st.video(up_video, format="video/mp4", start_time=0)   
