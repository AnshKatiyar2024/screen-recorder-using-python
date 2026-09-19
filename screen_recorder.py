import sys
import cv2
import pyautogui 
import numpy as np 
import pyaudio 
import wave
import os
import time
from PyQt5.QtCore import QTimer 
from threading import Thread
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QHBoxLayout
)
from PyQt5.QtCore import QThread, pyqtSignal 
#from moviepy.editor import VideoFileClip, AudioFileClip

class AudioRecorder(Thread):
    def __init__(self, filename):
        super()._init_()
        self.filename = filename
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.recording = False

    def run(self):
        self.recording = True
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )

        while self.recording:
            data = self.stream.read(self.chunk)
            self.frames.append(data)

    def stop(self):
        self.recording = False
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        with wave.open(self.filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))

class ScreenRecorder(QThread):
    recording_signal = pyqtSignal(str)

    def __init__(self, filename):
        super()._init_()
        self.filename = filename
        self.recording = False
        self.frames = []
        self.start_time = None

    def run(self):
        self.recording = True
        self.start_time = time.time()

        screen_size = pyautogui.size()

        # Video writer setup
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(self.filename, fourcc, 20.0, screen_size)

        self.recording_signal.emit("Recording started...")

        while self.recording:
            img = pyautogui.screenshot()
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.write(frame)

        self.recording_signal.emit("Recording stopped.")
        out.release()

    def stop(self):
        self.recording = False

    def get_duration(self):
        if self.start_time:
            return round(time.time() - self.start_time, 2)
        return 0

class ScreenRecorderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.screen_recorder = None
        self.audio_recorder = None
        self.timer = QTimer(self)
        self.recording_time = 0
        self.timer.timeout.connect(self.update_timer)

    def init_ui(self):
        self.setWindowTitle("Advanced Screen Recorder with Audio")
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Status: Ready", self)
        layout.addWidget(self.status_label)

        # File path display
        self.file_path_label = QLabel("File Path: Not Selected", self)
        layout.addWidget(self.file_path_label)

        # Timer label
        self.timer_label = QLabel("Recording Time: 00:00", self)
        layout.addWidget(self.timer_label)

        # Start button
        self.start_button = QPushButton("Start Recording", self)
        self.start_button.clicked.connect(self.start_recording)
        layout.addWidget(self.start_button)

        # Stop button
        self.stop_button = QPushButton("Stop Recording", self)
        self.stop_button.clicked.connect(self.stop_recording)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)

        # Pause button
        self.pause_button = QPushButton("Pause Recording", self)
        self.pause_button.clicked.connect(self.pause_recording)
        self.pause_button.setEnabled(False)
        layout.addWidget(self.pause_button)

        self.setLayout(layout)

    def start_recording(self):
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Recording", "", "Video Files (.avi *.mp4);;All Files ()", options=options
        )
        if not filename:
            return

        video_filename = filename
        audio_filename = filename.rsplit('.', 1)[0] + "_audio.wav"

        self.screen_recorder = ScreenRecorder(video_filename)
        self.audio_recorder = AudioRecorder(audio_filename)

        self.screen_recorder.recording_signal.connect(self.update_status)

        self.audio_recorder.start()
        self.screen_recorder.start()

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.pause_button.setEnabled(True)
        self.file_path_label.setText(f"File Path: {video_filename}")

        self.timer.start(1000)

    def stop_recording(self):
        if self.screen_recorder and self.audio_recorder:
            # Stop audio and video recorders
            self.audio_recorder.stop()
            self.screen_recorder.stop()
            self.screen_recorder.wait()
            self.audio_recorder.join()

            # Combine the audio and video into a single file
            video_clip = VideoFileClip(self.screen_recorder.filename)
            audio_clip = AudioFileClip(self.audio_recorder.filename)

            # Set the audio of the video clip to the recorded audio
            video_clip = video_clip.set_audio(audio_clip)

            # Save the final output file (combining audio and video)
            output_filename = self.screen_recorder.filename.rsplit('.', 1)[0] + "_final.mp4"
            video_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")

            # Clean up the temporary audio file
            os.remove(self.audio_recorder.filename)

            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.pause_button.setEnabled(False)

            self.timer.stop()
            self.status_label.setText(f"Status: Recording saved to {output_filename}")

    def pause_recording(self):
        if self.screen_recorder and self.screen_recorder.recording:
            self.screen_recorder.stop()
            self.status_label.setText("Status: Recording paused.")
            self.pause_button.setText("Resume Recording")
        else:
            self.screen_recorder.start()
            self.status_label.setText("Status: Recording resumed.")
            self.pause_button.setText("Pause Recording")

    def update_status(self, message):
        self.status_label.setText(f"Status: {message}")

    def update_timer(self):
        if self.screen_recorder:
            self.recording_time = self.screen_recorder.get_duration()
            minutes, seconds = divmod(int(self.recording_time), 60)
            self.timer_label.setText(f"Recording Time: {minutes:02d}:{seconds:02d}")
            
    # def merge_audio_video(self, video_filename, audio_filename, output_filename):
    #     # Merge the video and audio using ffmpeg
    #     ffmpeg.input(video_filename).output(audio_filename, vcodec='copy', acodec='aac', strict='experimental').run()
    #     self.status_label.setText(f"Status: Merged video and audio into {output_filename}")
    

    def stop_recording(self):
        if self.screen_recorder and self.audio_recorder:
            # Stop audio and video recorders
            self.audio_recorder.stop()
            self.screen_recorder.stop()
            self.screen_recorder.wait()
            self.audio_recorder.join()

            # Combine the audio and video into a single file
            video_clip = VideoFileClip(self.screen_recorder.filename)
            audio_clip = AudioFileClip(self.audio_recorder.filename)

            # Set the audio of the video clip to the recorded audio
            video_clip = video_clip.set_audio(audio_clip)  


            # Save the final output file (combining audio and video)
            output_filename = self.screen_recorder.filename.rsplit('.', 1)[0] + "_final.mp4"
            video_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")

            # Clean up the temporary audio file
            os.remove(self.audio_recorder.filename)

            # Update UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.pause_button.setEnabled(False)

            self.timer.stop()
            self.status_label.setText(f"Status: Recording saved to {output_filename}")

if __name__ == "__main__": 

    app = QApplication(sys.argv)
    screen_recorder = ScreenRecorderApp()
    screen_recorder.show()
    sys.exit(app.exec_())


