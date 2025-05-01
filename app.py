from flask import Flask, render_template, request, jsonify
from utils.plagiarism_detector import PlagiarismDetector
import re
import json
import threading
import os
import tempfile
from werkzeug.utils import secure_filename
import traceback

# For document processing
try:
    import docx  # for .docx files
except ImportError:
    print("python-docx not installed. .docx support will be limited.")

try:
    import PyPDF2  # for .pdf files
except ImportError:
    print("PyPDF2 not installed. .pdf support will be limited.")

app = Flask(__name__, static_folder='static', template_folder='templates')
detector = PlagiarismDetector()

# Configure upload settings
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'txt', 'doc', 'docx', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure the directory for results exists
os.makedirs(os.path.join('static'), exist_ok=True)


@app.route('/')
def index():
    return render_template('index.html')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(file):
    """Extract text content from uploaded file based on file type"""
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    # Save the file temporarily
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)

    text = ""
    try:
        if file_ext == 'txt':
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        elif file_ext == 'docx':
            try:
                doc = docx.Document(temp_path)
                text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except Exception as e:
                return f"Error processing .docx file: {str(e)}"

        elif file_ext == 'pdf':
            try:
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page_num in range(len(pdf_reader.pages)):
                        text += pdf_reader.pages[page_num].extract_text()
            except Exception as e:
                return f"Error processing .pdf file: {str(e)}"

        elif file_ext == 'doc':
            return "Legacy .doc format is not directly supported. Please convert to .docx or copy text."

    except Exception as e:
        return f"Error processing file: {str(e)}\n{traceback.format_exc()}"

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass  # Ignore if we can't delete the temp file

    return text


@app.route('/check', methods=['POST'])
def check_plagiarism():
    source_type = request.form.get('source_type', 'text')
    text = ""

    try:
        if source_type == 'text':
            text = request.form.get('text', '')
        elif source_type == 'file':
            if 'file' not in request.files:
                return jsonify({
                    'error': 'No file provided',
                    'results': []
                })

            file = request.files['file']

            if file.filename == '':
                return jsonify({
                    'error': 'No file selected',
                    'results': []
                })

            if not allowed_file(file.filename):
                return jsonify({
                    'error': f'Invalid file type. Allowed types are {", ".join(ALLOWED_EXTENSIONS)}',
                    'results': []
                })

            # Extract text from the file
            text = extract_text_from_file(file)

            if isinstance(text, str) and text.startswith("Error"):
                return jsonify({
                    'error': text,
                    'results': []
                })

        if not text:
            return jsonify({
                'error': 'No text content found',
                'results': []
            })

        # Remove excessive whitespace and normalize text
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 20:
            return jsonify({
                'error': 'Text is too short for plagiarism detection',
                'results': []
            })

        # Start analysis in a background thread to prevent timeout
        thread = threading.Thread(target=analyze_text, args=(text,))
        thread.start()

        return jsonify({
            'message': 'Analysis started',
            'status': 'processing'
        })

    except Exception as e:
        app.logger.error(f"Error in check_plagiarism: {e}\n{traceback.format_exc()}")
        return jsonify({
            'error': f'An unexpected error occurred: {str(e)}',
            'results': []
        })


def analyze_text(text):
    try:
        # This function runs in a separate thread
        results = detector.detect_plagiarism(text)

        # Create directory if it doesn't exist
        os.makedirs('static', exist_ok=True)

        # Store results in a file (in a real app, you'd use a database)
        with open('static/last_results.json', 'w') as f:
            json.dump(results, f)
    except Exception as e:
        # Log the error but continue
        print(f"Error in analyze_text: {e}")
        # Save empty results to indicate completion
        with open('static/last_results.json', 'w') as f:
            json.dump([], f)


@app.route('/results', methods=['GET'])
def get_results():
    try:
        # Check if results file exists
        if not os.path.exists('static/last_results.json'):
            return jsonify({
                'status': 'processing',
                'message': 'Analysis still in progress or no results available'
            })

        with open('static/last_results.json', 'r') as f:
            results = json.load(f)

        # Group results by source URL
        grouped_results = {}
        total_plagiarism_score = 0

        for item in results:
            url = item['source']['url']
            if url not in grouped_results:
                grouped_results[url] = {
                    'url': url,
                    'title': item['source']['title'],
                    'matched_sentences': [],
                    'avg_similarity': 0
                }

            grouped_results[url]['matched_sentences'].append({
                'sentence': item['sentence'],
                'similarity': item['similarity'],
                'source_text': item['source']['text']
            })

            # Update average similarity
            similarities = [s['similarity'] for s in grouped_results[url]['matched_sentences']]
            grouped_results[url]['avg_similarity'] = sum(similarities) / len(similarities)

            # Add to total plagiarism score
            total_plagiarism_score += item['similarity']

        # Calculate overall plagiarism percentage
        if results:
            overall_percentage = (total_plagiarism_score / len(results)) * 100
        else:
            overall_percentage = 0

        return jsonify({
            'results': list(grouped_results.values()),
            'overall_percentage': round(overall_percentage, 2),
            'total_matches': len(results),
            'status': 'complete'
        })

    except FileNotFoundError:
        return jsonify({
            'status': 'processing',
            'message': 'Analysis still in progress or no results available'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error retrieving results: {str(e)}'
        })


@app.route('/result')
def result_page():
    return render_template('result.html')


if __name__ == '__main__':
    app.run(debug=True)