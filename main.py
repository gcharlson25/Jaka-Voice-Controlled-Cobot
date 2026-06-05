import re
import time
import os
import numpy as np
import sounddevice as sd
import whisper

from tools import execute_command, execute_llm_command, COMMAND_FILE
from llm import ask_llm, _backend_name

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

while True:
    audio = record_with_vad()
    command = transcribe(audio)
    print(f"You said: {command}")
    if "quit" in command.lower() or "program over" in command.lower():
        print("Ending program.")
        open("C:/Projects/jaka_voice/quit.signal", "w").close()
        break
    command = re.sub(r'\b' + STOP_WORD + r'\b\.?\s*$', '', command, flags=re.IGNORECASE).strip()
    if not command:
        continue
    sub_commands = [s.strip().strip('.,') for s in re.split(r'\band\b|\bthen\b|,', command, flags=re.IGNORECASE) if s.strip().strip('.,')]
    parsed_parts = [parse_command(s) for s in sub_commands]

    if sub_commands and all(p is not None for p in parsed_parts):
        for parsed in parsed_parts:
            print(f"Parsed: {parsed}")
            execute_command(parsed)
            while os.path.exists(COMMAND_FILE):
                time.sleep(0.05)
    else:
        print("Sending to LLM...")
        tool_result = ask_llm(command)
        if tool_result is None:
            print("Invalid instruction.")
            continue
        print(f"{_backend_name}: {tool_result}")
        execute_llm_command(tool_result)
        if tool_result["function"] != "motion_abort":
            while os.path.exists(COMMAND_FILE):
                time.sleep(0.05)
