from flask import Flask, render_template, request
from dotenv import load_dotenv
import openai
import os
import re
import trafilatura
from trafilatura.settings import use_config

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    raise ValueError("OpenAI API key not found in environment variables")

def prepare_input(prompt_template, text):
    """Prepare the input text by cleaning whitespace and combining with prompt"""
    text = text.replace('\r\n', '\n').strip()
    marker = "===TEXT TO CHECK===\n"
    
    if '[Text will appear here]' in prompt_template:
        final_prompt = prompt_template.replace('[Text will appear here]', marker + text)
    else:
        final_prompt = prompt_template + "\n" + marker + text
    
    return final_prompt

def validate_response(output, raw_text):
    """Validate the API response meets our requirements"""
    if any(phrase in output.lower() for phrase in [
        "please provide", "didn't provide", "no text", "error"
    ]):
        raise ValueError("Invalid response format from API")
    
    if len(output) < len(raw_text) * 0.9:
        raise ValueError("API response appears to be incomplete")
        
    if '<b style=' in output and not (
        'color:red' in output and 'color:green' in output
    ):
        raise ValueError("API response has incorrect markup format")
    
    return True

def extract_guardian_text(url):
    """Extract text content from Guardian URL using trafilatura"""
    if not url.startswith('https://www.theguardian.com/'):
        raise ValueError("URL must be from The Guardian (theguardian.com)")
    
    config = use_config()
    config.set("DEFAULT", "CLEANING", "strip")
    
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Failed to download the article")
    
    text = trafilatura.extract(downloaded, config=config, include_formatting=True)
    if not text:
        raise ValueError("Failed to extract text from the article")
    
    # Convert double line breaks to paragraphs while preserving other formatting
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.replace('\n\n', '</p><p>')
    text = '<p>' + text + '</p>'
    text = text.replace('<p></p>', '')
    
    return text

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        raw_text = request.form.get('raw_text', '').strip()
        guardian_url = request.form.get('guardian_url', '').strip()
        
        if not raw_text and not guardian_url:
            return render_template('index.html', error="No text or URL provided")
            
        if guardian_url:
            try:
                raw_text = extract_guardian_text(guardian_url)
            except Exception as e:
                return render_template('index.html', 
                                    guardian_url=guardian_url,
                                    error=f"Error extracting article: {str(e)}")
        
        try:
            try:
                with open('prompt.txt', 'r') as file:
                    prompt_template = file.read()
            except FileNotFoundError:
                raise
            
            final_prompt = prepare_input(prompt_template, raw_text)
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a proofreader. You MUST return the COMPLETE input text. If there are errors, mark them using HTML. If there are no errors, return the exact input text unchanged. Never return messages, only the processed text."
                    },
                    {
                        "role": "user",
                        "content": final_prompt
                    }
                ]
            )
            
            output = response.choices[0].message.content
            
            validate_response(output, raw_text)
            
            try:
                with open('output.html', 'w') as file:
                    file.write(output)
            except Exception as e:
                raise
                
            return render_template('index.html', 
                                input_text=raw_text, 
                                guardian_url=guardian_url,
                                output_text=output)
            
        except Exception as e:
            return render_template('index.html', error=str(e))
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
