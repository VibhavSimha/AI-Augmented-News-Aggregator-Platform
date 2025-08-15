# News Aggregator

This is a news aggregator project built using the MERN stack (MongoDB, Express, React, Node.js) and the NewsAPI.org API. The project allows users to view news articles from various sources.

## Getting Started

These instructions will help you set up the project on your local machine for development and testing purposes.

### Prerequisites

- Node.js and npm installed on your machine
- A NewsAPI.org API key
- A [Groq API key](https://console.groq.com/keys) (for chatbot and news contextualizer)
- A [SerpAPI key](https://serpapi.com/manage-api-key) (for news timeline/contextualizer)

### Installation

1. Fork the repository on GitHub.
2. Clone the repository to your local machine.

#### Server Setup

3. Navigate to the server directory and create a new file named `.env`.
4. Add your NewsAPI.org API key to the `.env` file in the following format:  
   ```
   API_KEY=your_news_api_key
   ```
5. In `app.py`, set your Groq API key and SerpAPI key:
   ```python
   client = Groq(api_key="your_groq_api_key")
   # ...
   params = {
       "q": query,
       "tbm": "nws",
       "api_key": "your_serpapi_key"
   }
   ```
6. In the server directory, run `npm install` (if using Node.js backend) or set up your Python environment and install dependencies:
   ```
   pip install flask flask-cors nltk groq requests
   ```
7. Start the server by running:
   ```
   node server.js
   ```
   or for Flask:
   ```
   python app.py
   ```

#### Client Setup

8. Navigate to the client directory and run:
   ```
   npm install
   ```
9. Start the client by running:
   ```
   npm run dev
   ```

## Usage

Once the project is set up and running, you can view news articles from various sources on the client side.

### Features

- **News Timeline/Contextualizer:**  
  Uses Groq API and SerpAPI to generate a timeline of key historical events and related news articles for a given headline.

- **Chatbot (Ask AI):**  
  Uses Groq API to answer user questions about a news article.

### API Keys Required

- **NewsAPI.org:** For fetching news articles.
- **Groq API:** For AI-powered chatbot and contextual timeline.
- **SerpAPI:** For fetching related news articles for timeline events.
