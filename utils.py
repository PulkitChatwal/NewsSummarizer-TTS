import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from keybert import KeyBERT
from gtts import gTTS
import os
import urllib.parse
from datetime import datetime
import feedparser
import random
import re
import time
from collections import defaultdict

# Initialize models
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
kw_model = KeyBERT()

# Configuration
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0"
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept-Language': 'en-US,en;q=0.5'
    }

def get_sentiment(text):
    if not text or len(text.strip()) < 10:
        return "Neutral"
    try:
        result = sentiment_analyzer(text[:512])[0]
        label_map = {'LABEL_0': 'Negative', 'LABEL_1': 'Neutral', 'LABEL_2': 'Positive'}
        return label_map.get(result['label'], 'Neutral')
    except:
        return "Neutral"

def summarize(text):
    if not text or len(text.strip()) < 30:
        return text
    
    text = re.sub(r'\b(?:read more|continue reading|sign up|subscribe)\b.*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    
    word_count = len(text.split())
    max_len = min(120, int(word_count*0.4))
    min_len = min(60, int(max_len*0.5))
    
    try:
        summary = summarizer(text, max_length=max_len, min_length=min_len, do_sample=False)[0]['summary_text']
        return summary if summary.endswith(('.', '!', '?')) else re.sub(r'[^\.!?]*$', '', summary).strip()
    except:
        return text[:300] + "..." if len(text) > 300 else text

def get_topics(text):
    try:
        keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), top_n=3, stop_words='english')
        return [kw[0] for kw in keywords if kw[1] > 0.2 and len(kw[0].split()) < 4] or ["General"]
    except:
        return ["General"]

def get_article_content(url):
    try:
        time.sleep(1)
        response = requests.get(url, headers=get_random_headers(), timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'aside']):
            element.decompose()
        
        # Try common content selectors
        selectors = ['article', 'div.article-body', 'div.story-content', 'main']
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                content = ' '.join([p.get_text().strip() for el in elements for p in el.find_all('p')])
                if len(content.split()) > 30:
                    return content
        
        meta = soup.find('meta', attrs={'name': 'description'})
        return meta['content'] if meta and meta.get('content') else None
    except:
        return None

def fetch_articles(company):
    sources = [
        ("Google News", f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(company)}&hl=en-US&gl=US&ceid=US:en"),
        ("Reuters", f"https://www.reuters.com/search/news?blob={urllib.parse.quote_plus(company)}"),
        ("Yahoo Finance", f"https://finance.yahoo.com/quote/{urllib.parse.quote_plus(company)}/news")
    ]
    
    articles = []
    for source_name, url in sources:
        try:
            if "google.com" in url:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    desc = BeautifulSoup(entry.get('description', ''), 'html.parser').get_text()
                    if "Comprehensive, up-to-date news coverage" not in desc:
                        articles.append({
                            'title': entry.title,
                            'content': desc or entry.title,
                            'url': entry.link,
                            'source': source_name,
                            'date': datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d') if hasattr(entry, 'published_parsed') else 'Unknown'
                        })
            else:
                response = requests.get(url, headers=get_random_headers(), timeout=15)
                soup = BeautifulSoup(response.text, 'html.parser')
                # Simplified scraping logic for other sources
                # (Would add proper selectors for each source in production)
        except:
            continue
    
    return articles[:15]  # Return first 15 articles

def generate_report(company):
    articles = fetch_articles(company)
    if not articles:
        return {"error": f"No articles found for '{company}'"}, None
    
    processed = []
    for article in articles[:10]:  # Process first 10 articles
        content = get_article_content(article['url']) or article['content'] or article['title']
        summary = summarize(content)
        
        processed.append({
            "title": article['title'][:150] + ("..." if len(article['title']) > 150 else ""),
            "source": article['source'],
            "date": article['date'],
            "summary": summary,
            "sentiment": get_sentiment(summary),
            "topics": get_topics(summary),
            "url": article['url']
        })
    
    sentiment_dist = defaultdict(int)
    all_topics = []
    for article in processed:
        sentiment_dist[article['sentiment']] += 1
        all_topics.extend(article['topics'])
    
    # Generate Hindi TTS
    tts_path = None
    try:
        tts_text = f"{company} के बारे में समाचारों में {'सकारात्मक' if sentiment_dist['Positive'] > sentiment_dist['Negative'] else 'नकारात्मक'} भावना है।"
        tts = gTTS(text=tts_text, lang='hi', slow=False)
        tts_path = f"{company}_summary.mp3"
        tts.save(tts_path)
    except:
        pass
    
    return {
        "company": company,
        "articles": processed,
        "analysis": {
            "sentiment": dict(sentiment_dist),
            "top_topics": list(set([t for t in all_topics if t.lower() != 'general']))[:3]
        }
    }, tts_path