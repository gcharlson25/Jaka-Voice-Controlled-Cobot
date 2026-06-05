import json
import requests
import whisper
import sounddevice as sd
import numpy as np
import os
import re
import time

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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "linear_move",
            "description": (
                "Move the robot arm in a straight line. "
                "Positive x_mm = right, negative = left. "
                "Positive y_mm = forward, negative = backward. "
                "Positive z_mm = up, negative = down. "
                "Set unused axes to 0. Default 10mm if no distance given. Default 100 mm/s."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "x_mm":      {"type": "number", "description": "X offset in mm"},
                    "y_mm":      {"type": "number", "description": "Y offset in mm"},
                    "z_mm":      {"type": "number", "description": "Z offset in mm"},
                    "speed_mms": {"type": "number", "description": "Speed in mm/s, default 100"},
                },
                "required": ["x_mm", "y_mm", "z_mm"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "circular_move",
            "description": (
                "Move the robot end effector in a circle. "
                "'xy' = horizontal circle. 'xz' = vertical circle in X-Z plane. 'yz' = vertical circle in Y-Z plane. "
                "circles = number of full loops, default 1."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "radius_mm": {"type": "number",  "description": "Radius in mm"},
                    "plane":     {"type": "string",  "enum": ["xy", "xz", "yz"]},
                    "circles":   {"type": "integer", "description": "Number of full circles, default 1"},
                    "speed_mms": {"type": "number",  "description": "Speed in mm/s, default 50"},
                },
                "required": ["radius_mm", "plane"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "motion_abort",
            "description": "Immediately stop all robot motion. Use for stop, halt, abort, emergency stop.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

def ask_ollama_tools(command):
    try:
        response = requests.post("http://localhost:11434/api/chat", json={
            "model": "llama3.2",
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You control a robot arm. Always respond by calling a tool — never with plain text. "
                        "Convert the voice command into the correct tool call."
                    ),
                },
                {"role": "user", "content": command},
            ],
            "tools": TOOLS,
        })
        result = response.json()
        message = result["message"]
        if not message.get("tool_calls"):
            return None
        tool_call = message["tool_calls"][0]
        name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        if isinstance(args, str):
            args = json.loads(args)
        return {"function": name, "args": args}
    except Exception as e:
        print(f"Ollama error: {e}")
        return None

def execute_ollama_command(tool_result):
    try:
        func = tool_result["function"]
        args = tool_result.get("args", {})

        if func == "linear_move":
            x = -(float(args.get("x_mm", 0)))  # robot's physical X axis is inverted
            y = float(args.get("y_mm", 0))
            z = float(args.get("z_mm", 0))
            speed = float(args.get("speed_mms", 100))
            if x == 0.0 and y == 0.0 and z == 0.0:
                return
            move = [x, y, z, 0, 0, 0]
            print(f"Moving: {move}")
            with open("C:/Projects/jaka_voice/command.json", "w") as f:
                json.dump(move, f)
            print("Command sent!")

        elif func == "circular_move":
            cmd = {
                "function": "circular_move",
                "radius_mm": float(args.get("radius_mm", 50)),
                "plane":     args.get("plane", "xy"),
                "circles":   int(float(args.get("circles", 1))),
                "speed":     float(args.get("speed_mms", 50)),
            }
            print(f"Moving: {cmd}")
            with open("C:/Projects/jaka_voice/command.json", "w") as f:
                json.dump(cmd, f)
            print("Command sent!")

        elif func == "motion_abort":
            cmd = {"function": "motion_abort"}
            with open("C:/Projects/jaka_voice/command.json", "w") as f:
                json.dump(cmd, f)
            print("Abort sent!")

        else:
            print(f"Unknown function: {func}")

    except Exception as e:
        print(f"Error in execute_ollama_command: {e}")

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
            while os.path.exists("C:/Projects/jaka_voice/command.json"):
                time.sleep(0.05)
    else:
        print("Sending to Ollama...")
        tool_result = ask_ollama_tools(command)
        if tool_result is None:
            print("Invalid instruction.")
            continue
        print(f"Ollama: {tool_result}")
        execute_ollama_command(tool_result)
        if tool_result["function"] != "motion_abort":
            while os.path.exists("C:/Projects/jaka_voice/command.json"):
                time.sleep(0.05)
