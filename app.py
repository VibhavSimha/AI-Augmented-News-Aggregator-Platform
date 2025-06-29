from flask import Flask, jsonify, request, render_template
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
from groq import Groq
import requests
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


# Initialize Groq API client
client = Groq(api_key="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")
nltk.download('stopwords')

def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = set(stopwords.words("english"))
    keywords = [word for word in words if word not in stop_words]
    common_words = Counter(keywords).most_common(5)
    return [word for word, _ in common_words]

def search_google_news(query):
    params = {
        "q": query,
        "tbm": "nws",
        "api_key": "1d11049f87ffd8baa1b1dae3491fc5035cab436281453426b3adef58088af61c"
    }
    url = "https://serpapi.com/search"
    response = requests.get(url, params=params)
    results = response.json()
    return results.get("news_results", [])

def get_historical_events(headline):
    query = (
        f"List exactly 5 key historical events related to: {headline}. "
        "Arrange them from the oldest to the most recent. "
        "Each point should briefly describe a major event that shaped the topic."
    )
    messages = [{"role": "user", "content": query}]
    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content.split("\n")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_headline', methods=['POST'])
def process_headline():
    try:
        headline = request.json['headline']
        events = get_historical_events(headline)[1:-1]
        
        timeline_data = []
        for event in events:
            if not event.strip():
                continue
            
            keywords = extract_keywords(event)
            articles = search_google_news(" ".join(keywords))
            timeline_data.append({
                "event": event.strip(),
                "articles": articles[:3] if articles else []
            })
        
        return jsonify(timeline_data)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)