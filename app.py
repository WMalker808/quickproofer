#!/Users/max_walker/GPTproofer/bin/python3

from flask import Flask, render_template, request
from dotenv import load_dotenv
import openai
import os
import re

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Get input text from the form
        raw_text = request.form.get('raw_text', '')
        
        try:
            # Read prompt from file
            with open('prompt.txt', 'r') as file:
                prompt = file.read()
            
            # Generate response from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",
                temperature=0.9,
                top_p=0.4,
                messages=[{
                    "role": "user",
                    "content": prompt + raw_text
                }]
            )
            
            # Get the output text
            output = response.choices[0].message.content
            
            # Process the output
            output = re.sub(r'\n\n', r'<p>', output)
            
            # Save to output.html
            with open('output.html', 'w') as file:
                file.write(output)
                
            return render_template('index.html', input_text=raw_text, output_text=output)
            
        except Exception as e:
            return render_template('index.html', error=str(e))
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
