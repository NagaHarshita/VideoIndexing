import os
import storage
import recognise as recog

def register(path):
    recog.register_song(path)

def recognise(path):
    result = recog.recognise_song(path)
    print(result)

def initialize_db():
    storage.setup_db()

if __name__ == "__main__":
    # print("Select options from below")
    # print("1: Initialize DB")
    # initialize_db()

    # print("2: Register song")
    # register(path="../../../Audios/video" + "11.wav")

    # print("3: Recognize song")
    recognise("../../../queries/video" + "11" + "_1.wav")

