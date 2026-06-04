import requests
import json
import whisper
import sounddevice as sd
import numpy as np
import os

print("Loading Whisper model...")
model = whisper.load_model("base")
print("Ready!")

def record_and_transcribe():
    print("Listening for 5 seconds...")
    sample_rate = 16000
    duration = 5
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32', device=1)
    sd.wait()
    recording = recording.flatten()
    print("Transcribing...")
    result = model.transcribe(recording, fp16=False)
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
        move[axis_map[parsed["axis"]]] = parsed["distance"] * parsed["direction"]
        print(f"Moving: {move}")
        with open("C:/Projects/jaka_voice/command.json", "w") as f:
            json.dump(move, f)
        print("Command sent!")
    except Exception as e:
        print(f"Error in execute_command: {e}")

while True:
    command = record_and_transcribe()
    print(f"You said: {command}")
    if "quit" in command.lower():
        break
    print("Sending to Ollama...")
    parsed = ask_ollama(command)
    print(f"Parsed: {parsed}")
    execute_command(parsed)