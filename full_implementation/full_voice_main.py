import re
import time
import os
import json
import numpy as np
import sounddevice as sd
import whisper

from full_tools import execute_command, execute_finetuned_command, execute_screw_command, connect_robot
from full_llm_finetuned import ask_llm, _backend_name

VISION_COMMAND_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision_command.json")

def send_vision_command(action):
    with open(VISION_COMMAND_FILE, "w") as f:
        json.dump({"action": action}, f)
    print(f"Vision command sent: {action}")

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.04
SILENCE_DURATION = 1.2
PRE_SPEECH_BUFFER = 0.4
MAX_RECORD_SECONDS = 10
STOP_WORD = "over"

DIRECTION_MAP = {
    "right":     ("x",  1),
    "left":      ("x", -1),
    "forward":   ("y",  1),
    "backwards": ("y", -1),
    "backward":  ("y", -1),
    "back":      ("y", -1),
    "up":        ("z",  1),
    "down":      ("z", -1),
}

connect_robot()

print("Loading Whisper model...")
model = whisper.load_model("small")
print("Ready!")

def record_with_vad():
    chunk_duration = 0.03
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

def parse_command(text):
    words = re.findall(r"[\w']+", text.lower())
    axis, direction = None, None
    for word in words:
        if word in DIRECTION_MAP:
            axis, direction = DIRECTION_MAP[word]
            break
    if axis is None:
        return None
    match = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
    distance = int(float(match.group(1))) if match else 10
    return {"axis": axis, "distance": distance, "direction": direction}

SCREW_NUMBER_WORDS = {
    "one": 1, "1": 1,
    "two": 2, "to": 2, "too": 2, "2": 2,
    "three": 3, "3": 3,
    "four": 4, "for": 4, "4": 4,
    "five": 5, "5": 5,
}

def parse_screw_command(text):
    t = text.lower()
    if re.search(r'\b(unfasten|loosen|unscrew)\b', t):
        action = "unfasten"
    elif re.search(r'\b(fasten|tighten)\b', t):
        action = "fasten"
    else:
        return None
    if re.search(r'\ball\b', t):
        return {"action": action, "screw_number": 0}
    for word, n in SCREW_NUMBER_WORDS.items():
        if re.search(r'\b' + word + r'\b', t):
            return {"action": action, "screw_number": n}
    return None

while True:
    audio = record_with_vad()
    command = transcribe(audio)
    print(f"You said: {command}")
    if "quit" in command.lower() or "program over" in command.lower():
        print("Ending program.")
        break
    if "calibrate" in command.lower():
        send_vision_command("calibrate")
        continue
    if "align" in command.lower():
        send_vision_command("align")
        continue
    command = re.sub(r'\b' + STOP_WORD + r'\b\.?\s*$', '', command, flags=re.IGNORECASE).strip()
    if not command:
        continue
    sub_commands = [s.strip().strip('.,') for s in re.split(r'\band\b|\bthen\b|,', command, flags=re.IGNORECASE) if s.strip().strip('.,')]
    parsed_parts = []
    for s in sub_commands:
        screw = parse_screw_command(s)
        if screw is not None:
            parsed_parts.append(("screw", screw))
        else:
            move = parse_command(s)
            parsed_parts.append(("move", move) if move is not None else None)

    if sub_commands and all(p is not None for p in parsed_parts):
        for kind, parsed in parsed_parts:
            print(f"Parsed: {kind} {parsed}")
            if kind == "screw":
                execute_screw_command(parsed["action"], parsed["screw_number"])
            else:
                execute_command(parsed)
    else:
        print("Sending to LLM...")
        tool_results = ask_llm(command)
        if not tool_results:
            print("Invalid instruction.")
            continue
        print(f"{_backend_name}: {tool_results}")
        for tool_result in tool_results:
            execute_finetuned_command(tool_result)