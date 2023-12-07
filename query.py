import argparse
import os
import math
import pickle
import copy
import time
from scenedetect import SceneManager, StatsManager, ThresholdDetector, open_video
from media_player import VideoPlayerApp
import tkinter as tk
import numpy as np
import cv2

DIR_NAME = "dataset/"
META_DATA_FILE_PATH = "dataset/video_meta_data.pkl"
dataset_info = {}


def computeFrameAverage(frame: np.ndarray) -> float:
    num_pixel_values = float(frame.shape[0] * frame.shape[1] * frame.shape[2])
    avg_pixel_value = np.sum(frame[:, :, :]) / num_pixel_values
    return avg_pixel_value


def processRGB(file_name):

    width = 352
    height = 288
    fps = 30

    frame_size = width * height * 3
    total_frames = int(np.fromfile(
        file_name, dtype=np.uint8).shape[0] / frame_size)

    averages = []
    with open(file_name, 'rb') as file:
        for _ in range(total_frames):
            frame_data = np.fromfile(file, dtype=np.uint8, count=frame_size)

            frame = frame_data.reshape((height, width, 3))

            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            avg = computeFrameAverage(frame)
            averages.append(avg)
    return averages


def createVideoInfo(video_data, video_name):
    i = 0
    while i < len(video_data):

        avg_rgb = math.floor(video_data[i])
        cnt = 1
        j = i

        while (j < len(video_data)-1 and avg_rgb == math.floor(video_data[j+1])):
            cnt = cnt + 1
            j = j + 1

        if (avg_rgb, j-i+1) in dataset_info:
            dataset_info[(avg_rgb, j-i+1)].append((video_name, i+1))
        else:
            dataset_info[(avg_rgb, j-i+1)] = [(video_name, i+1)]
        i = j + 1


def getDataFromPickleDump(video_path):
    pickle_path = video_path.replace(".mp4", ".pkl")
    with open(pickle_path, 'rb') as handle:
        data = pickle.load(handle)

    data_dict = dict()
    for i in range(len(data)):
        data_dict[i] = data[i]
    return data_dict


def computeVideoMetaData(file_name):
    # generate CSV files for all dataset videos
    video_list = [file for file in os.listdir(
        DIR_NAME) if file.endswith('.mp4')]
    video_data = []
    for video in video_list:
        video_path = DIR_NAME + video
        video_data = getDataFromPickleDump(video_path)
        # video_data = getFrameStats(video_path)
        createVideoInfo(video_data, video)

    with open(file_name, 'wb') as handle:
        pickle.dump(dataset_info, handle, protocol=pickle.HIGHEST_PROTOCOL)


def checkAndCreateVideoData(force):
    if (os.path.isfile(META_DATA_FILE_PATH)):
        # file already exists
        if (force):
            print("Deleting the existing meta data file:", META_DATA_FILE_PATH)
            os.remove(META_DATA_FILE_PATH)
            computeVideoMetaData(META_DATA_FILE_PATH)
    else:
        # there is no file -> create a new file
        computeVideoMetaData(META_DATA_FILE_PATH)


def getFrameStats(query_video):
    video = open_video(query_video)
    scene_manager = SceneManager(StatsManager())
    scene_manager.add_detector(ThresholdDetector())
    scene_manager.detect_scenes(
        video=video,
        show_progress=False
    )
    return scene_manager.stats_manager._frame_metrics


def generateRLE(frame_stats):
    i = 0
    rle = []
    while i < len(frame_stats):
        avg_rgb = math.floor(frame_stats[i])
        cnt = 1
        j = i

        while (j < len(frame_stats)-1 and avg_rgb == math.floor(frame_stats[j+1])):
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
    while (bin_number < len(rle)):
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
                if (next_candidate_video_name == candidate_video_name and next_candidate_start_frame_number == candidate_start_frame_number + rle[bin_number][1]):
                    candidate_set.add(candidate_video_name)
                    candidates_temp.append(next_candidate)
                    frame_set.add(candidate_start_frame_number)

        bin_number = bin_number + 1
        candidates = copy.deepcopy(candidates_temp)

        if (len(candidate_set) == 1 and len(frame_set) == 1):
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


def matchVideo(recreateVideoData, queryVideo):
    # create dataset meta data if not exists
    checkAndCreateVideoData(recreateVideoData)

    # query the current video
    frame_stats = processRGB(queryVideo)
    start_frame, video_name = getMatchingVideoInfo(frame_stats)
    print("Query video:", queryVideo)
    print("Video Name:", video_name)
    print("frame offset:", start_frame-1)
    return video_name, start_frame - 2


def playVideo(video_name, start_frame):
    video_path = DIR_NAME + video_name
    root = tk.Tk()
    app = VideoPlayerApp(root, video_path, start_frame)
    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--recreateVideoData", action='store_true')
    parser.add_argument("--noShowUI", action='store_true')
    parser.add_argument("--queryVideo", type=str, required=False)

    args = parser.parse_args()

    start_time = time.time()
    video_name, start_frame = matchVideo(
        args.recreateVideoData, args.queryVideo)
    print("Query completed in %.4f seconds" % (time.time() - start_time))

    if (args.noShowUI == False):
        playVideo(video_name, start_frame)
