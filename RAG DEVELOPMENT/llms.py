
from openai import OpenAI
import anthropic
import os
from get_content_from_app_prop import read_properties
import google.generativeai as genai

props = read_properties('application.properties')

class CallLLM:
    def __init__(self, temperature=0.7, top_p=1.0, max_tokens=15000):
        self.props = read_properties('application.properties')
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

    def autograder_openai(self, 
                          prompt, 
                          api_key=props["OPEN_AI_API_KEY_VASU23049942"]):
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            # model="gpt-4o-mini",
            model="gpt-4o", 
            messages=[{"role": "user", "content": prompt}],
            temperature= self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens
        )

        return response.choices[0].message.content
    
    # Anthropic Claude 3.5
    def autograder_anthropic(self, 
                          prompt):
        
        client = anthropic.Anthropic(api_key=props["ANTHROPIC_API_KEY"])

        
        kwargs = {
            "model": "claude-3-7-sonnet-20250219",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        # Add top_p if not default
        if self.top_p != 1.0:
            kwargs["top_p"] = self.top_p
        
        response = client.messages.create(**kwargs)
        return response.content[0].text

    # Llama-3.3 70B (Hugging Face API)
    def autograder_llama(self, 
                         prompt, 
                         api_key=props["HF_API_KEY"]):

        client = OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=api_key,
        )

        try:
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct:fireworks-ai",
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Llama request failed: {e}")
            return None


    def autograder_gemini(self, 
                         prompt, 
                         api_key=props["GOOGLE_API_KEY"]):
            
        genai.configure(api_key=api_key)
        model_name = "gemini-2.5-flash"
        model = genai.GenerativeModel(model_name)
        # Pass temperature, top_p and map max_tokens -> max_output_tokens
        resp = model.generate_content(
            prompt
        )
        return resp.text.strip()
    