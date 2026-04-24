import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("AIzaSyCb8Jfa-RnpOV5n0GIlVHzG8chmo7oyPzQ"))
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
