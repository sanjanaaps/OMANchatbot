import google.generativeai as genai
import os

print("Available Models:")
for m in genai.list_models():
    print(f"- {m.name}: {m.supported_generation_methods}")
print("\nIf you don't see gemini-pro in the list above, you may need to ensure your API key has access to it.")