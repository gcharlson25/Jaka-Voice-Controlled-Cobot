import json
import requests
from tools import TOOLS

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
