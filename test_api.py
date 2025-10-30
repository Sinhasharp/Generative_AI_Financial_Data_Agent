import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("Error: OPENROUTER_API_KEY not found.")
    print("Please check your .env file.")
else:
    print("API Key loaded successfully.")
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        print("Sending test message to API...")

        completion = client.chat.completions.create(
            extra_headers={},
            model="tngtech/deepseek-r1t2-chimera:free",
            messages=[
                {
                    "role": "user",
                    "content": "Respond with only the word: 'Success'"
                }
            ]
        )
        
        response_message = completion.choices[0].message.content
        print(f"API Response: {response_message}")

    except Exception as e:
        print(f"An error occurred: {e}")