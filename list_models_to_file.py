from google import genai
import os
from dotenv import load_dotenv

def list_gemini_models():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    with open("gemini_models.txt", "w") as f:
        for model in client.models.list():
            f.write(f"{model.name}\n")

if __name__ == "__main__":
    list_gemini_models()
