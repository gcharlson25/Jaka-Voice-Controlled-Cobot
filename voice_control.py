import requests
import json
import whisper
import sounddevice as sd
import numpy as np
import os
import re

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.04   # RMS energy — raise further if still triggering on background noise
SILENCE_DURATION = 1.2     # seconds of quiet before we stop recording
PRE_SPEECH_BUFFER = 0.4    # seconds of audio kept before speech starts
MAX_RECORD_SECONDS = 8     # hard cap so it never records forever in noisy environments
STOP_WORD = "over"         # say this at the end of your command to force stop

print("Loading Whisper model...")
model = whisper.load_model("tiny")
print("Ready!")

def record_with_vad():
    chunk_duration = 0.03   # 30ms frames
    chunk_size = int(SAMPLE_RATE * chunk_duration)
    silence_limit = int(SILENCE_DURATION / chunk_duration)
    pre_buf_limit = int(PRE_SPEECH_BUFFER / chunk_duration)
    max_speech_chunks = int(MAX_RECORD_SECONDS / chunk_duration)

    chunks = []
    pre_buffer = []
    speech_started = False
    silence_count = 0
    speech_chunk_count = 0

    print("Waiting for speech...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                        device=1, blocksize=chunk_size) as stream:
        while True:
            chunk, _ = stream.read(chunk_size)
            rms = np.sqrt(np.mean(chunk ** 2))

            if not speech_started:
                pre_buffer.append(chunk.copy())
                if len(pre_buffer) > pre_buf_limit:
                    pre_buffer.pop(0)
                if rms > SILENCE_THRESHOLD:
                    speech_started = True
                    print("Speech detected...")
                    chunks.extend(pre_buffer)
            else:
                chunks.append(chunk.copy())
                speech_chunk_count += 1
                if speech_chunk_count >= max_speech_chunks:
                    print("Max duration reached, processing...")
                    break
                if rms < SILENCE_THRESHOLD:
                    silence_count += 1
                    if silence_count >= silence_limit:
                        break
                else:
                    silence_count = 0

    return np.concatenate(chunks).flatten()

def transcribe(audio):
    print("Transcribing...")
    result = model.transcribe(audio, fp16=False)
    return result["text"].strip()

def ask_ollama(command):
    response = requests.post("http://localhost:11434/api/chat", json={
        "model": "llama3.2",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": """You are a robot controller. Convert movement commands to JSON only.
Rules:
- right/left = x axis, right is direction 1, left is -1
- forward/backward = y axis, forward is 1, backward is -1
- up/down = z axis, up is 1, down is -1
- distance is always in mm as a whole number, never convert units
- distance can be written as mm, millimeters, or millimetres, always output as a whole number
If the input is not a valid movement command, respond with exactly: {"error": "invalid"}
Respond with only valid JSON like: {"axis": "x", "distance": 10, "direction": 1}
No explanation. No other text. Only JSON."""
            },
            {
                "role": "user",
                "content": command
            }
        ]
    })
    result = response.json()
    text = result["message"]["content"]
    return json.loads(text)

def execute_command(parsed):
    try:
        axis_map = {"x": 0, "y": 1, "z": 2}
        move = [0, 0, 0, 0, 0, 0]
        value = parsed["distance"] * parsed["direction"]
        if parsed["axis"] == "x":
            value = -value  # robot's physical X axis is opposite to named direction
        move[axis_map[parsed["axis"]]] = value
        print(f"Moving: {move}")
        with open("C:/Projects/jaka_voice/command.json", "w") as f:
            json.dump(move, f)
        print("Command sent!")
    except Exception as e:
        print(f"Error in execute_command: {e}")

while True:
    audio = record_with_vad()
    command = transcribe(audio)
    print(f"You said: {command}")
    if "quit" in command.lower() or "program over" in command.lower():
        print("Ending program.")
        break
    # strip stop word from end of command before sending to Ollama
    command = re.sub(r'\b' + STOP_WORD + r'\b\.?\s*$', '', command, flags=re.IGNORECASE).strip()
    if not command:
        continue
    print("Sending to Ollama...")
    try:
        parsed = ask_ollama(command)
        if parsed.get("error") == "invalid":
            print("Invalid instruction.")
            continue
        print(f"Parsed: {parsed}")
        execute_command(parsed)
    except Exception:
        print("Invalid instruction.")
