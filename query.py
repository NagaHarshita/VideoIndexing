import numpy as np
import argparse
import os
import pandas as pd
import math
import pickle
import shutil
import copy
import time
from scenedetect import SceneManager, StatsManager, detect, ThresholdDetector, open_video

DIR_NAME = "dataset/"
META_DATA_FILE_PATH = "dataset/video_meta_data.pkl"
dataset_info = {}

def createVideoCSV(video_path, result_path):
    command = 'scenedetect -i '+ video_path + ' -s ' + result_path + ' detect-threshold'
    os.system(command)

def createVideoInfo(video_data, video_name):
    i = 0
    while i < len(video_data):

        avg_rgb = math.floor(video_data.iloc[i]["average_rgb"])
        cnt = 1
        j = i
        
        while(j<len(video_data)-1 and avg_rgb == math.floor(video_data.iloc[j+1]["average_rgb"])):
            cnt = cnt + 1
            j = j + 1

        if (avg_rgb, j-i+1) in dataset_info:
            dataset_info[(avg_rgb, j-i+1)].append((video_name, video_data.iloc[i]["Frame Number"]))
        else:
            dataset_info[(avg_rgb, j-i+1)] = [(video_name, video_data.iloc[i]["Frame Number"])]
        i = j + 1

def createCSVForAllVideos(force):
    results_folder = DIR_NAME + "csvs/"
    
    if(os.path.isdir(results_folder)):
        if(force):
            print("recreating the folder:", results_folder)
            shutil.rmtree(results_folder)
    
    video_list = [file for file in os.listdir(DIR_NAME) if file.endswith('.mp4')]
    for video in video_list:
        video_path = DIR_NAME + video
        result_path = DIR_NAME + 'csvs/' + video + ".csv"
        createVideoCSV(video_path, result_path)

def computeVideoMetaData(file_name, force):
    # generate CSV files for all dataset videos
    createCSVForAllVideos(force)
    video_list = [file for file in os.listdir(DIR_NAME) if file.endswith('.mp4')]
    video_data = []
    for video in video_list:
        file_path = DIR_NAME + "csvs/" + video + ".csv"
        video_data = pd.read_csv(file_path)
        createVideoInfo(video_data, video)

    with open(file_name, 'wb') as handle:
        pickle.dump(dataset_info, handle, protocol=pickle.HIGHEST_PROTOCOL)

def checkAndCreateVideoData(force):
    if(os.path.isfile(META_DATA_FILE_PATH)):
        # file already exists
        if(force):
            print("Deleting the existing meta data file:", META_DATA_FILE_PATH)
            os.remove(META_DATA_FILE_PATH)
        else:
            print("Meta data already exists")
    else:
        # there is no file -> create a new file
        computeVideoMetaData(META_DATA_FILE_PATH, force)

def getFrameStats(query_video):
    video = open_video(query_video)
    scene_manager = SceneManager(StatsManager())
    scene_manager.add_detector(ThresholdDetector())
    scene_manager.detect_scenes(
        video=video,
        show_progress= False
    )
    return scene_manager.stats_manager._frame_metrics

def generateRLE(frame_stats):
    i = 0
    rle = []
    while i < len(frame_stats):
        avg_rgb = math.floor(frame_stats[i]["average_rgb"])
        cnt = 1
        j = i
        
        while(j<len(frame_stats)-1 and avg_rgb == math.floor(frame_stats[j+1]["average_rgb"])):
            cnt = cnt + 1
            j = j + 1
        rle.append((avg_rgb, j-i+1))
        i = j + 1
    return rle

def getMatchingFramesCount(bin_number, rle):
    sum = 0
    for i in range(bin_number):
        sum = sum + rle[i][1]
    return sum

def matchSignature(rle, video_data):
    bin_number = 1

    curr_bin = rle[bin_number]
    candidates = video_data[curr_bin]
    while(bin_number < len(rle)):
        candidate_set = set()
        frame_set = set()
        candidates_temp = []

        for candidate in candidates:
            # for every candidate video
            candidate_video_name = candidate[0]
            candidate_start_frame_number = candidate[1]

            for next_candidate in video_data[rle[bin_number + 1]]:
                next_candidate_video_name = next_candidate[0]
                next_candidate_start_frame_number = next_candidate[1]
                if(next_candidate_video_name == candidate_video_name and next_candidate_start_frame_number == candidate_start_frame_number + rle[bin_number][1]):
                    candidate_set.add(candidate_video_name)
                    candidates_temp.append(next_candidate)
                    frame_set.add(candidate_start_frame_number)
        
        bin_number = bin_number + 1
        candidates = copy.deepcopy(candidates_temp)

        if(len(candidate_set) == 1):
            break
    
    number_of_matching_frames = getMatchingFramesCount(bin_number - 1, rle)
    return list(frame_set)[0] - number_of_matching_frames, list(candidate_set)[0]

def getMatchingVideoInfo(frame_stats):
    # load dataset meta data
    with open(META_DATA_FILE_PATH, 'rb') as handle:
        video_data = pickle.load(handle)
    
    rle = generateRLE(frame_stats)
    frame_number, video_name = matchSignature(rle, video_data)
    return frame_number, video_name

def matchVideo(recreateVideoData, noShowUI, queryVideo):
    # create dataset meta data if not exists
    checkAndCreateVideoData(recreateVideoData)

    # query the current video
    frame_stats = getFrameStats(queryVideo)
    start_frame, video_name = getMatchingVideoInfo(frame_stats)
    print(start_frame)
    print(video_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--recreateVideoData", action='store_true')
    parser.add_argument("--noShowUI", action='store_true')
    parser.add_argument("--queryVideo", type=str, required=False)

    args = parser.parse_args()

    start_time = time.time()
    matchVideo(args.recreateVideoData, args.noShowUI, args.queryVideo)
    print("--- %s seconds ---" % (time.time() - start_time))