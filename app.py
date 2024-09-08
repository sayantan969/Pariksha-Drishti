import os

os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import json
import time
import threading
import cv2
import numpy as np
import soundfile as sf
import pyaudio
import wave
import requests
import webrtcvad
import librosa
from collections import defaultdict
from ultralytics import YOLO
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Hugging Face API key and URL
API_TOKEN = "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"
API_URL = "https://api-inference.huggingface.co/models/facebook/s2t-wav2vec2-large-en-de"

# Global variables
flag_count = 0
flagged_events = []
unwanted_object_timers = defaultdict(float)

# Load YOLOv8 model for object detection (CPU only)
device = 'cpu'  # Force CPU usage
yolo_model = YOLO('yolov8n.pt').to(device)

# Initialize Voice Activity Detector (VAD)
vad = webrtcvad.Vad()
vad.set_mode(3)  # 0-3, where 3 is most aggressive

# Constants
object_detection_interval = 1  # Seconds for object detection flagging threshold
stop_event = threading.Event()  # Used to stop the audio recording
audio_file_path = "mic_audio.wav"

# Function to call Hugging Face API for speech-to-text
def query(audio_data):
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, data=audio_data)
        response.raise_for_status()  # Raise error for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during transcription request: {e}")
        return {"error": "Transcription failed"}

# Function to ensure audio is at the correct sample rate
def ensure_sample_rate(audio, sample_rate, target_rate=16000):
    if sample_rate != target_rate:
        print(f"Resampling from {sample_rate} Hz to {target_rate} Hz...")
        audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_rate)
        sample_rate = target_rate
    return audio, sample_rate

# Function to detect multiple voices
def detect_multiple_voices(audio, sample_rate):
    audio, sample_rate = ensure_sample_rate(audio, sample_rate)
    chunk_duration_ms = 30  # 30ms chunks
    num_frames_per_chunk = int(sample_rate * chunk_duration_ms / 1000)

    if audio.dtype != np.int16:
        audio = (audio * 32767).astype(np.int16)

    num_active_frames = 0
    chunk_start = 0

    while chunk_start < len(audio):
        chunk_end = min(chunk_start + num_frames_per_chunk, len(audio))
        audio_chunk = audio[chunk_start:chunk_end]

        if len(audio_chunk) != num_frames_per_chunk:
            break

        try:
            if vad.is_speech(audio_chunk.tobytes(), sample_rate):
                num_active_frames += 1
        except webrtcvad.Error as e:
            print(f"VAD error: {e}")
            break

        chunk_start += num_frames_per_chunk

    return num_active_frames > 1

# Function to record audio from the microphone
def record_audio(filename, record_seconds=30, sample_rate=16000):
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    p = pyaudio.PyAudio()

    stream = p.open(format=format,
                    channels=channels,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=chunk)

    print(f"Recording for {record_seconds} seconds...")
    frames = []

    for _ in range(0, int(sample_rate / chunk * record_seconds)):
        if stop_event.is_set():
            break
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(format))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()

# Function to start audio recording in a separate thread
def start_audio_recording(filename, record_seconds=30):
    audio_thread = threading.Thread(target=record_audio, args=(filename, record_seconds))
    audio_thread.start()
    return audio_thread

# Function to report a flag event
def report_flag(reason):
    global flag_count
    flag_data = {
        "time": time.ctime(),
        "reason": reason
    }
    print(json.dumps(flag_data), flush=True)
    flagged_events.append((time.ctime(), reason))
    flag_count += 1

# Function to generate and display a report
def generate_report(frame_count, camera_cut_time, num_voices):
    report_data = {
        "totalFlags": flag_count,
        "events": flagged_events,
        "numVoices": num_voices,
        "frameCount": frame_count,
        "cameraCutTime": time.ctime(camera_cut_time) if camera_cut_time else None
    }
    
    # Ensure the directory exists
    report_dir = os.path.join("data", "public")
    os.makedirs(report_dir, exist_ok=True)
    
    report_path = os.path.join(report_dir, "report.json")
    with open(report_path, "w") as report_file:
        json.dump(report_data, report_file)
    
    print(json.dumps(report_data), flush=True)

# Function to run detection
def run_detection():
    global flag_count, flagged_events, unwanted_object_timers

    stop_event.clear()
    audio_thread = start_audio_recording(audio_file_path, record_seconds=30)  # 30 seconds

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    frame_count = 0
    start_time = time.time()
    camera_cut_time = None

    # Directory for flagged frames
    flagged_frames_dir = os.path.join("frames", "flagged")
    os.makedirs(flagged_frames_dir, exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            if camera_cut_time is None:
                camera_cut_time = time.time()
                report_flag("Camera window closed")
                break

        results = yolo_model(frame)
        detected_class_ids = results[0].boxes.cls.int().tolist()
        detected_objects = [yolo_model.names[class_id] for class_id in detected_class_ids]

        flag_raised = False

        # Flag if multiple people are detected
        if detected_objects.count('person') > 1:
            report_flag("Multiple people detected")
            flag_raised = True

        # Flag if unwanted objects are detected
        unwanted_objects = ['laptop', 'cell phone', 'tv']
        for obj in unwanted_objects:
            if obj in detected_objects:
                unwanted_object_timers[obj] += 0.1
                if unwanted_object_timers[obj] >= object_detection_interval:
                    report_flag(f"Unwanted object ({obj}) detected")
                    unwanted_object_timers[obj] = 0
                    flag_raised = True

        # Save frame only if a flag was raised
        if flag_raised:
            frame_with_boxes = results[0].plot()
            flagged_frame_path = os.path.join(flagged_frames_dir, f"flagged_frame_{frame_count:04d}.jpg")
            cv2.imwrite(flagged_frame_path, frame_with_boxes)
            print(f"Flagged frame saved: {flagged_frame_path}")

        frame_count += 1

        if time.time() - start_time >= 30 or stop_event.is_set():
            break

    cap.release()
    stop_event.set()
    audio_thread.join()

    # Process audio
    try:
        audio, sample_rate = sf.read(audio_file_path)
        with open(audio_file_path, "rb") as audio_file:
            transcription_result = query(audio_file.read())
        num_active_voices = detect_multiple_voices(audio, sample_rate=sample_rate)
        if num_active_voices:
            report_flag("Multiple voices detected")
    except Exception as e:
        print(f"Error processing audio: {e}")
        transcription_result = {"error": "Audio processing failed"}
        num_active_voices = 0

    generate_report(frame_count, camera_cut_time, num_active_voices)
    return transcription_result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    transcription_result = run_detection()
    return redirect(url_for('report'))

@app.route('/report')
def report():
    # Add a slight delay to allow report file to be written
    time.sleep(2)
    try:
        with open("data/public/report.json", "r") as report_file:
            report_data = json.load(report_file)
    except FileNotFoundError:
        report_data = {"error": "Report file not found."}
    return render_template('report.html', report=report_data)

if __name__ == "__main__":
    app.run(debug=True)