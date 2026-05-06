import requests
import feedparser
from datetime import datetime, timedelta
import json
import os

class DataSources:
    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_github_trends(self, topic="ai", days=7):
        """Fetch trending AI repos from GitHub"""
        date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        url = f"https://api.github.com/search/repositories?q=topic:{topic}+pushed:>{date}&sort=stars&order=desc"
        
        try:
            response = requests.get(url)
            repos = response.json().get('items', [])[:5]
            
            results = []
            for repo in repos:
                results.append(f"- {repo['name']}: {repo['description']} (⭐ {repo['stargazers_count']})")
            
            return "\n".join(results)
        except Exception as e:
            return f"Error fetching GitHub data: {e}"
    
    def get_arxiv_papers(self, topic="AI", max_results=5):
        """Fetch recent papers from ArXiv"""
        import urllib.parse
        query = urllib.parse.quote(f"all:{topic}")
        url = f"http://export.arxiv.org/api/query?search_query={query}&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
        
        try:
            feed = feedparser.parse(url)
            results = []
            for entry in feed.entries:
                title = entry.title.replace('\n', ' ').strip()
                summary = entry.summary[:200] + "..." if len(entry.summary) > 200 else entry.summary
                results.append(f"- {title}\n  {summary}")
            
            return "\n".join(results)
        except Exception as e:
            return f"Error fetching ArXiv data: {e}"
    
    def get_tech_news(self, topic="artificial intelligence"):
        """Fetch tech news"""
        try:
            feed = feedparser.parse("https://feeds.feedburner.com/oreilly/radar/ai")
            results = []
            for entry in feed.entries[:5]:
                results.append(f"- {entry.title}")
            return "\n".join(results) if results else "No news found"
        except:
            return "Tech news unavailable"
    
    def collect_all(self, topic="AI infrastructure"):
        """Collect data from all sources"""
        print("📡 Collecting data from multiple sources...")
        
        data = {
            "github": self.get_github_trends("ai"),
            "arxiv": self.get_arxiv_papers("AI"),
            "news": self.get_tech_news(),
            "timestamp": datetime.now().isoformat(),
            "topic": topic
        }
        
        filename = f"{self.data_dir}/research_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        combined = f"""
GitHub Trending AI Repos:
{data['github']}

Recent ArXiv Papers:
{data['arxiv']}

Tech News Headlines:
{data['news']}
"""
        return combined, filename

# Test it
if __name__ == "__main__":
    ds = DataSources()
    data, filepath = ds.collect_all()
    print(data)
    print(f"\n💾 Saved to: {filepath}")