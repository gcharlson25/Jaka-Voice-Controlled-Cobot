import json
import os
import requests
from full_tools import TOOLS

def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

SYSTEM_PROMPT = (
    "You control a robot arm. Always respond by calling a tool — never with plain text. "
    "Convert the voice command into the correct tool call. "
    "The robot can fasten or unfasten screws numbered 1 through 5, or all screws at once (screw_number=0). "
    "Use screw_operation for any command involving fastening, tightening, unfastening, loosening, or removing screws."
)

class ChatGPTLLM:
    def ask(self, command):
        api_key = os.environ.get("OPENAI_API_KEY")
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": command},
                    ],
                    "tools": TOOLS,
                    "tool_choice": "required",
                },
            )
            result = response.json()
            tool_calls = result["choices"][0]["message"].get("tool_calls")
            if not tool_calls:
                return None
            name = tool_calls[0]["function"]["name"]
            args = json.loads(tool_calls[0]["function"]["arguments"])
            return {"function": name, "args": args}
        except Exception as e:
            print(f"OpenAI error: {e}")
            return None

class OllamaLLM:
    def ask(self, command):
        try:
            response = requests.post("http://localhost:11434/api/chat", json={
                "model": "llama3.2",
                "stream": False,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
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

def get_llm():
    backend = os.environ.get("LLM_BACKEND", "gpt").lower()
    if backend == "ollama":
        print("LLM backend: Ollama (llama3.2)")
        return OllamaLLM()
    print("LLM backend: ChatGPT (gpt-4o)")
    return ChatGPTLLM()

_llm = get_llm()
_backend_name = os.environ.get("LLM_BACKEND", "gpt").upper()

def ask_llm(command):
    return _llm.ask(command)
