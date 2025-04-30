# Plagiarism Checker

A web-based application to detect potential plagiarism by comparing text against online sources. This tool helps students, writers, and educators identify content similarity and maintain academic integrity.

## Features

- **Text Input**: Paste any text to check for plagiarism
- **File Upload**: Upload documents in various formats (.txt, .docx, .pdf)
- **Comprehensive Analysis**: Searches web sources to find matching content
- **Detailed Results**: Displays similarity score, matched sources, and specific text overlaps
- **Visual Reporting**: Visual indicators showing severity of matches and overall similarity percentage

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/plagiarism-checker.git
   cd plagiarism-checker
   ```

2. Install required dependencies:
   ```
   pip install flask nltk requests beautifulsoup4 python-docx PyPDF2
   ```

3. Run the application:
   ```
   python app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Text Input
1. Enter or paste text into the text box
2. Click "Check Plagiarism"
3. Wait for the analysis to complete
4. View detailed results showing matched sources and similarity scores

### File Upload
1. Switch to the "File Upload" tab
2. Drag and drop a file or click to browse and select
3. Supported formats: .txt, .doc, .docx, .pdf
4. Click "Check Plagiarism"
5. Review the analysis results

## How It Works

1. **Text Processing**: Content is broken into sentences and preprocessed
2. **Web Search**: Processed text is used to search for potential matching online sources
3. **Content Comparison**: Text is compared against source content using similarity algorithms
4. **Result Analysis**: Matches are identified, scored, and displayed with source information

## Project Structure

- `app.py` - Flask web application main file
- `templates/` - HTML templates
  - `index.html` - Main input page
  - `result.html` - Results display page
- `static/` - Static assets
  - `css/style.css` - Application styling
  - `js/main.js` - Client-side functionality
- `utils/` - Utility modules
  - `plagiarism_detector.py` - Core plagiarism detection logic

## Notes

- For educational purposes only
- Results should be manually verified
- The application respects rate limits to avoid overwhelming search services
- Detection accuracy depends on the available online sources

## Future Improvements

- Support for multiple languages
- Enhanced accuracy through additional detection algorithms
- PDF parsing improvements
- Integration with academic databases
- Local document comparison
