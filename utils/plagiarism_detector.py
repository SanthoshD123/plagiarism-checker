import requests
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import time
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

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
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        ]
        self.debug_mode = True  # Set to True to enable detailed logging

    def preprocess_text(self, text):
        """Clean and tokenize the text while preserving important context"""
        # Basic cleanup but preserve sentence structure
        text = re.sub(r'\s+', ' ', text).strip()

        # Tokenize into sentences
        sentences = sent_tokenize(text)

        # Filter out very short sentences but don't remove stopwords
        filtered_sentences = []
        for sentence in sentences:
            # Keep sentences with at least 4 words
            if len(sentence.split()) >= 4:
                # Keep original sentence but normalize whitespace
                normalized = ' '.join(sentence.split())
                filtered_sentences.append(normalized)

        return filtered_sentences

    def search_web(self, query, num_results=5):
        """Search the web for possible sources of plagiarism with better error handling"""
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }

        links = []
        try:
            if self.debug_mode:
                print(f"Searching for: {query[:50]}...")

            response = requests.get(search_url, headers=headers, timeout=15)

            # Log response code for debugging
            if self.debug_mode:
                print(f"Search response code: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Try multiple selector patterns
                for selector in ['.tF2Cxc', '.g .yuRUbf', '.g', 'div[data-hveid]']:
                    results = soup.select(selector)

                    if self.debug_mode:
                        print(f"Selector '{selector}' found {len(results)} results")

                    for result in results:
                        link_element = result.select_one('a[href^="http"]')
                        if link_element and link_element.get('href'):
                            url = link_element['href']

                            # Skip Google-specific URLs
                            if 'google.com' in url:
                                continue

                            # Find title element
                            title_element = result.select_one('h3') or result.select_one('.LC20lb')
                            title = title_element.get_text() if title_element else 'Unknown Title'

                            # Add to links if not already there
                            link_info = {'url': url, 'title': title}
                            if link_info not in links:
                                links.append(link_info)

                    # If we found links, no need to try other selectors
                    if links:
                        break

                # Log results for debugging
                if self.debug_mode:
                    print(f"Found {len(links)} potential sources")

            elif response.status_code == 429:
                print("Rate limited by search engine. Try again later.")
                # Sleep longer to respect rate limits
                time.sleep(30)
            else:
                print(f"Search failed with status code: {response.status_code}")

        except Exception as e:
            print(f"Error during web search: {str(e)}")
            # Sleep on error to avoid rapid retries
            time.sleep(5)

        return links[:num_results]

    def fetch_content(self, url):
        """Fetch and extract content from a URL with improved error handling"""
        try:
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=15)

            if self.debug_mode:
                print(f"Fetch response code for {url}: {response.status_code}")

            if response.status_code != 200:
                print(f"Failed to fetch {url}: HTTP {response.status_code}")
                return ""

            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script, style, and nav elements
            for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
                element.extract()

            # Get text from main content area if possible
            main_content = soup.select_one('main') or soup.select_one('article') or soup.select_one('#content') or soup

            # Get text
            text = main_content.get_text()

            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text
        except Exception as e:
            print(f"Error fetching content from {url}: {e}")
            return ""

    def calculate_similarity(self, text1, text2):
        """Calculate similarity between two texts using TF-IDF and cosine similarity"""
        # Fall back to Jaccard similarity for very short texts
        if len(text1.split()) < 3 or len(text2.split()) < 3:
            set1 = set(text1.split())
            set2 = set(text2.split())
            intersection = len(set1.intersection(set2))
            union = len(set1) + len(set2) - intersection
            return intersection / union if union > 0 else 0

        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)  # Ensure it's a regular float for JSON serialization
        except Exception as e:
            print(f"Error in similarity calculation: {e}")
            # Fall back to simpler method if vectorizer fails
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            common_words = words1.intersection(words2)
            if not words1 or not words2:
                return 0
            return len(common_words) / max(len(words1), len(words2))

    def detect_plagiarism(self, text, min_similarity=0.3):
        """Detect plagiarism in the given text with improved algorithm"""
        if self.debug_mode:
            print(f"Starting plagiarism detection on text of length {len(text)}")

        sentences = self.preprocess_text(text)

        if self.debug_mode:
            print(f"Preprocessed into {len(sentences)} sentences")

        results = []

        # Use a more selective approach - choose sentences with potential signals
        selected_sentences = []

        # Select longer, more content-rich sentences
        for sentence in sentences:
            words = sentence.split()
            # Look for sentences with enough substance but not too long
            if 8 <= len(words) <= 25:
                selected_sentences.append(sentence)

        # If we don't have enough sentences, just use the original ones
        if len(selected_sentences) < 3:
            selected_sentences = sentences[:5]  # Limit to first 5 to avoid excessive searching

        if self.debug_mode:
            print(f"Selected {len(selected_sentences)} sentences for detailed checking")

        # Process sentences individually for better precision
        for i, sentence in enumerate(selected_sentences):
            if i >= 5:  # Limit processing to 5 sentences to avoid rate limiting
                break

            if self.debug_mode:
                print(f"Processing sentence {i + 1}/{len(selected_sentences)}: {sentence[:50]}...")

            query = sentence
            sources = self.search_web(query)

            # Sleep between queries to avoid rate limiting
            time.sleep(random.uniform(3, 6))

            for source in sources:
                url = source['url']
                title = source['title']

                if self.debug_mode:
                    print(f"Checking source: {title} ({url})")

                # Fetch content from the URL
                content = self.fetch_content(url)

                if not content:
                    if self.debug_mode:
                        print("No content retrieved, skipping")
                    continue

                # Get chunks of the content to compare with
                content_sentences = self.preprocess_text(content)

                # If we have too many sentences, sample them
                if len(content_sentences) > 100:
                    # Sample every nth sentence to cover the document
                    n = max(1, len(content_sentences) // 100)
                    content_sentences = content_sentences[::n]

                if self.debug_mode:
                    print(f"Comparing with {len(content_sentences)} sentences from source")

                highest_similarity = 0
                similar_source_text = ""

                # Compare with each content sentence
                for source_sentence in content_sentences:
                    similarity = self.calculate_similarity(sentence, source_sentence)

                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        similar_source_text = source_sentence

                if self.debug_mode:
                    print(f"Highest similarity: {highest_similarity:.4f}")

                if highest_similarity >= min_similarity:
                    results.append({
                        'sentence': sentence,
                        'similarity': highest_similarity,
                        'source': {
                            'url': url,
                            'title': title,
                            'text': similar_source_text
                        }
                    })

                    if self.debug_mode:
                        print(f"Match found! Added to results.")

                # Short sleep between processing different sources
                time.sleep(1)

        if self.debug_mode:
            print(f"Plagiarism detection complete. Found {len(results)} matches.")

        return results

    def test_detection(self, sample_text):
        """Test the plagiarism detection with detailed logging"""
        print("\n=== TESTING PLAGIARISM DETECTION ===")
        print(f"Sample text: {sample_text[:100]}...")

        # Preprocess text
        sentences = self.preprocess_text(sample_text)
        print(f"Preprocessed into {len(sentences)} sentences")

        # Select one sentence for testing
        if sentences:
            test_sentence = sentences[0]
            print(f"Testing with sentence: {test_sentence}")

            # Search web
            sources = self.search_web(test_sentence)
            print(f"Found {len(sources)} potential sources")

            results = []
            # Test each source
            for source in sources[:2]:  # Limit to 2 sources for testing
                url = source['url']
                print(f"Fetching content from: {url}")
                content = self.fetch_content(url)

                if content:
                    print(f"Retrieved {len(content)} characters of content")
                    content_preview = content[:100].replace('\n', ' ')
                    print(f"Content preview: {content_preview}...")

                    # Calculate similarity
                    similarity = self.calculate_similarity(test_sentence, content[:500])
                    print(f"Similarity score: {similarity:.4f}")

                    if similarity > 0.1:  # Lower threshold for testing
                        results.append({
                            'sentence': test_sentence,
                            'similarity': similarity,
                            'source': {
                                'url': url,
                                'title': source['title'],
                                'text': content[:200].replace('\n', ' ')
                            }
                        })
                else:
                    print("Failed to retrieve content")

            return results
        else:
            print("No valid sentences found for testing")
            return []


# For testing
if __name__ == "__main__":
    detector = PlagiarismDetector()
    sample_text = "Python is an interpreted high-level general-purpose programming language. Its design philosophy emphasizes code readability with its use of significant indentation."
    results = detector.test_detection(sample_text)

    for result in results:
        print(f"Plagiarized sentence: {result['sentence']}")
        print(f"Similarity score: {result['similarity']:.2f}")
        print(f"Source: {result['source']['title']} ({result['source']['url']})")
        print(f"Similar text: {result['source']['text']}")
        print("-" * 80)