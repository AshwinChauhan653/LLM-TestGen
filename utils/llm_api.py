import os
import openai
from dotenv import load_dotenv
import requests

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_gpt_response(prompt, model="gpt-4o-mini"):
    try:
        response = client.chat.completions.create(
            model=model,
            store=True,
            messages=[
                {"role": "system", "content": "You are an expert software tester."},
                {"role": "user", "content": prompt}
            ],
          
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error: {str(e)}"
    

def get_deepseek_response(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are an expert software tester."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "max_tokens": 500
        }

        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()  # Raises exception for 4XX/5XX responses
        
        result = response.json()
        print("🔍 DeepSeek RAW response:", result)  # Debugging output

        # Updated response parsing - check different possible structures
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
        elif "output" in result:  # Some APIs use "output" instead
            return result["output"].strip()
        elif "text" in result:  # Some APIs use "text"
            return result["text"].strip()
        else:
            return "❌ Error: Unexpected response format from DeepSeek API"

    except requests.exceptions.RequestException as e:
        return f"❌ DeepSeek API Request Error: {str(e)}"
    except Exception as e:
        return f"❌ DeepSeek Processing Error: {str(e)}"
    


import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def get_gemini_response(prompt):
    try:
        # Use the correct model name - "gemini-pro" instead of just "gemini"
        model = genai.GenerativeModel("gemini-pro")
        
        # Gemini expects a specific message format
        response = model.generate_content(
            f"You are an expert software tester. {prompt}"
        )
        
        # Properly handle the response structure
        if response and hasattr(response, 'text'):
            return response.text.strip()
        elif response and hasattr(response, 'candidates'):
            # Alternative way to extract response if .text isn't available
            return response.candidates[0].content.parts[0].text.strip()
        else:
            return "❌ Error: Unexpected response format from Gemini"
            
    except Exception as e:
        return f"❌ Gemini Error: {str(e)}"
    



"""### 
from openai import OpenAI

client = OpenAI(
  api_key="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"
)

completion = client.chat.completions.create(
  model="gpt-4o-mini",
  store=True,
  messages=[
    {"role": "user", "content": "write a haiku about ai"}
  ]
)

print(completion.choices[0].message);"
"""

