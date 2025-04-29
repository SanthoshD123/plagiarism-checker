import requests
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time
import random

# Download necessary NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class PlagiarismDetector:
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]

    def preprocess_text(self, text):
        """Clean and tokenize the text"""
        # Remove special characters and convert to lowercase
        text = re.sub(r'[^\w\s]', '', text.lower())

        # Tokenize into sentences
        sentences = sent_tokenize(text)

        # Remove stopwords
        filtered_sentences = []
        for sentence in sentences:
            if len(sentence.split()) > 5:  # Only keep sentences with more than 5 words
                filtered_sentences.append(' '.join([word for word in sentence.split() if word not in self.stop_words]))

        return filtered_sentences

    def search_web(self, query, num_results=5):
        """Search the web for possible sources of plagiarism"""
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }

        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = []

            # Find search result links
            for result in soup.select('.tF2Cxc'):
                link = result.select_one('.yuRUbf a')
                if link and link.get('href'):
                    links.append({
                        'url': link['href'],
                        'title': link.select_one('h3').get_text() if link.select_one('h3') else 'Unknown'
                    })

            # Alternative selector pattern if the above doesn't work
            if not links:
                for result in soup.select('div.g'):
                    link = result.select_one('a')
                    if link and link.get('href'):
                        title_el = result.select_one('h3') or result.select_one('.LC20lb')
                        title = title_el.get_text() if title_el else 'Unknown'
                        links.append({'url': link['href'], 'title': title})

            return links[:num_results]

        except Exception as e:
            print(f"Error during web search: {e}")
            return []

    def fetch_content(self, url):
        """Fetch and extract content from a URL"""
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()

            # Get text
            text = soup.get_text()

            # Break into lines and remove leading/trailing space
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            print(f"Error fetching content from {url}: {e}")
            return ""

    def calculate_similarity(self, text1, text2):
        """Calculate similarity between two texts using Jaccard similarity"""
        set1 = set(text1.split())
        set2 = set(text2.split())

        intersection = len(set1.intersection(set2))
        union = len(set1) + len(set2) - intersection

        if union == 0:
            return 0
        return intersection / union

    def detect_plagiarism(self, text, min_similarity=0.5):
        """Detect plagiarism in the given text"""
        sentences = self.preprocess_text(text)
        results = []

        # Process sentences in chunks to avoid too many search queries
        chunk_size = min(3, len(sentences))
        for i in range(0, len(sentences), chunk_size):
            chunk = sentences[i:i + chunk_size]
            query = " ".join(chunk)

            if len(query.split()) < 5:
                continue

            sources = self.search_web(query)

            for source in sources:
                url = source['url']
                title = source['title']

                # Fetch content from the URL
                content = self.fetch_content(url)

                if not content:
                    continue

                # Preprocess the content
                source_sentences = self.preprocess_text(content)

                # Compare each sentence with source sentences
                for j, sentence in enumerate(chunk):
                    highest_similarity = 0
                    similar_source_text = ""

                    for source_sentence in source_sentences:
                        similarity = self.calculate_similarity(sentence, source_sentence)

                        if similarity > highest_similarity:
                            highest_similarity = similarity
                            similar_source_text = source_sentence

                    if highest_similarity >= min_similarity:
                        results.append({
                            'sentence': sentences[i + j],
                            'similarity': highest_similarity,
                            'source': {
                                'url': url,
                                'title': title,
                                'text': similar_source_text
                            }
                        })

            # Sleep to avoid rate limiting
            time.sleep(2)

        return results


# For testing
if __name__ == "__main__":
    detector = PlagiarismDetector()
    sample_text = "Python is an interpreted high-level general-purpose programming language. Its design philosophy emphasizes code readability with its use of significant indentation."
    results = detector.detect_plagiarism(sample_text)

    for result in results:
        print(f"Plagiarized sentence: {result['sentence']}")
        print(f"Similarity score: {result['similarity']:.2f}")
        print(f"Source: {result['source']['title']} ({result['source']['url']})")
        print(f"Similar text: {result['source']['text']}")
        print("-" * 80)