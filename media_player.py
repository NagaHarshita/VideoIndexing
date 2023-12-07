import tkinter as tk
from tkinter import ttk, filedialog
import cv2
from PIL import Image, ImageTk
from pydub import AudioSegment
import simpleaudio as sa
import time


class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Player")

        # Video player variables
        self.video_path = None
        self.cap = None
        self.playing = False

        # Audio player variables
        self.audio_path = None
        self.audio = None

        self.frames_count = 0
        self.frame_rate = 30

        # Create UI
        self.create_widgets()

    def create_widgets(self):
        # Create buttons
        self.play_button = ttk.Button(
            self.root, text="Play", command=self.play_video)
        self.pause_button = ttk.Button(
            self.root, text="Pause", command=self.pause_video)
        self.reset_button = ttk.Button(
            self.root, text="Reset", command=self.reset_video)

        # Grid layout
        self.play_button.grid(row=0, column=0, padx=5, pady=5)
        self.pause_button.grid(row=0, column=1, padx=5, pady=5)
        self.reset_button.grid(row=0, column=2, padx=5, pady=5)

        # Create label for video display
        self.label = ttk.Label(self.root)
        self.label.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

        # Create menu
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open Video", command=self.open_video)
        menu_bar.add_cascade(label="File", menu=file_menu)

    def open_video(self):
        # Open a file dialog to select a video file
        file_path = filedialog.askopenfilename()

        if file_path:
            self.video_path = file_path
            self.cap = cv2.VideoCapture(self.video_path)

            # Open the corresponding audio file
            audio_path = self.video_path.replace(".mp4", ".wav")
            self.audio_path = audio_path
            self.audio = AudioSegment.from_file(audio_path, format="wav")

            self.play_video()

    def play_video(self):
        if self.cap and not self.playing:
            self.playing = True
            self.play_button["state"] = "disabled"
            self.pause_button["state"] = "enabled"
            self.reset_button["state"] = "enabled"
            self.play_frame()

            # Play audio
            if self.audio:
                self.play_audio()

    def play_frame(self):
        if self.playing and self.cap:
            ret, frame = self.cap.read()
            if ret:
                img = self.convert_image(frame)
                self.label.configure(image=img)
                self.label.image = img

                self.frames_count = self.frames_count + 1
                # Adjust delay for video speed
                if (self.frames_count % 3 == 1):
                    self.root.after(33, self.play_frame)
                else:
                    self.root.after(30, self.play_frame)
            else:
                self.reset_video()

    def play_audio(self):
        audio_data = self.audio.raw_data
        wave_obj = sa.WaveObject(
            audio_data, num_channels=self.audio.channels, bytes_per_sample=self.audio.sample_width)
        self.audio_play_obj = wave_obj.play()

    def pause_video(self):
        if self.cap and self.playing:
            self.playing = False
            self.play_button["state"] = "enabled"
            self.pause_button["state"] = "disabled"
            self.reset_button["state"] = "enabled"

            # Pause audio
            self.pause_audio()

    def pause_audio(self):
        if hasattr(self, 'audio_play_obj') and self.audio_play_obj:
            self.audio_play_obj.stop()
            seconds_elapsed = float(self.frames_count)/float(30)
            self.audio = AudioSegment.from_file(
                self.audio_path, format="wav", start_second=seconds_elapsed)

    def reset_video(self):
        if self.cap:
            self.cap.release()
            self.cap = cv2.VideoCapture(self.video_path)
            self.playing = False
            self.play_button["state"] = "enabled"
            self.pause_button["state"] = "disabled"
            self.reset_button["state"] = "disabled"
            self.label.configure(image=None)
            self.frames_count = 0

            # Stop audio
            self.stop_audio()
            self.audio = AudioSegment.from_file(self.audio_path, format="wav")

    def stop_audio(self):
        if hasattr(self, 'audio_play_obj') and self.audio_play_obj:
            self.audio_play_obj.stop()

    def convert_image(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_frame)
        img = ImageTk.PhotoImage(img)
        return img


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoPlayerApp(root)
    root.mainloop()
