document.addEventListener('DOMContentLoaded', function() {
    // Get the current page path
    const currentPath = window.location.pathname;

    // Handle index page functionality
    if (currentPath === '/') {
        setupIndexPage();
    }
    // Handle results page functionality
    else if (currentPath === '/result') {
        setupResultsPage();
    }
});

function setupIndexPage() {
    const form = document.getElementById('plagiarismForm');
    const contentInput = document.getElementById('contentInput');
    const wordCountElement = document.getElementById('wordCount');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorDiv = document.getElementById('error');
    const errorMessage = document.getElementById('errorMessage');
    const clearButton = document.getElementById('clearButton');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const removeFile = document.getElementById('removeFile');

    // Tab switching functionality
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all tabs
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked tab
            this.classList.add('active');
            document.getElementById(this.dataset.tab).classList.add('active');

            // Toggle required attributes based on active tab
            if (this.dataset.tab === 'text-input') {
                contentInput.setAttribute('required', '');
                fileInput.removeAttribute('required');
            } else if (this.dataset.tab === 'file-upload') {
                contentInput.removeAttribute('required');
                fileInput.setAttribute('required', '');
            }
        });
    });

    // Update word count as user types
    contentInput.addEventListener('input', function() {
        const text = contentInput.value.trim();
        const wordCount = text.split(/\s+/).filter(Boolean).length;
        wordCountElement.textContent = wordCount;
    });

    // File upload handling
    dropZone.addEventListener('click', function() {
        fileInput.click();
    });

    fileInput.addEventListener('change', function(e) {
        handleFileSelection(e.target.files[0]);
    });

    // Drag and drop functionality
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', function() {
        this.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');

        if (e.dataTransfer.files.length) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    // Remove file
    removeFile.addEventListener('click', function(e) {
        e.preventDefault(); // Prevent form submission
        e.stopPropagation(); // Prevent triggering other events
        fileInput.value = '';
        fileInfo.classList.add('hidden');
    });

    function handleFileSelection(file) {
        if (!file) return;

        // Check file type
        const validTypes = ['.txt', '.doc', '.docx', '.pdf'];
        const fileExt = '.' + file.name.split('.').pop().toLowerCase();

        if (!validTypes.includes(fileExt)) {
            showError('Invalid file type. Please upload a .txt, .doc, .docx, or .pdf file.');
            return;
        }

        // Show file info
        fileName.textContent = file.name;
        fileSize.textContent = formatFileSize(file.size);
        fileInfo.classList.remove('hidden');
    }

    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' bytes';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    }

    // Clear button functionality
    clearButton.addEventListener('click', function() {
        const activeTab = document.querySelector('.tab-content.active').id;

        if (activeTab === 'text-input') {
            contentInput.value = '';
            wordCountElement.textContent = '0';
        } else if (activeTab === 'file-upload') {
            fileInput.value = '';
            fileInfo.classList.add('hidden');
        }
    });

    // Form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();

        const activeTab = document.querySelector('.tab-content.active').id;
        let formData = new FormData();

        if (activeTab === 'text-input') {
            const text = contentInput.value.trim();

            if (!text) {
                showError('Please enter some text to check for plagiarism.');
                return;
            }

            formData.append('text', text);
            formData.append('source_type', 'text');

        } else if (activeTab === 'file-upload') {
            if (!fileInput.files.length) {
                showError('Please select a file to check for plagiarism.');
                return;
            }

            formData.append('file', fileInput.files[0]);
            formData.append('source_type', 'file');
        }

        // Hide any previous errors
        errorDiv.classList.add('hidden');

        // Show loading indicator
        loadingIndicator.classList.remove('hidden');

        // Submit the form data
        fetch('/check', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showError(data.error);
                loadingIndicator.classList.add('hidden');
            } else {
                // Redirect to results page
                window.location.href = '/result';
            }
        })
        .catch(error => {
            showError('An error occurred while checking plagiarism: ' + error.message);
            loadingIndicator.classList.add('hidden');
        });
    });

    function showError(message) {
        errorMessage.textContent = message;
        errorDiv.classList.remove('hidden');
    }
}

function setupResultsPage() {
    const loadingResults = document.getElementById('loadingResults');
    const resultsContent = document.getElementById('resultsContent');
    const sourcesContainer = document.getElementById('sourcesContainer');
    const overallPercentage = document.getElementById('overallPercentage');
    const sourcesCount = document.getElementById('sourcesCount');
    const matchesCount = document.getElementById('matchesCount');
    const meterValue = document.getElementById('meterValue');
    const interpretationText = document.getElementById('interpretationText');
    const noMatches = document.getElementById('noMatches');

    // Poll for results
    checkResults();

    function checkResults() {
        fetch('/results')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'processing') {
                    // If still processing, poll again after a delay
                    setTimeout(checkResults, 2000);
                } else if (data.status === 'complete') {
                    // Show results
                    displayResults(data);
                } else {
                    // Show error
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error fetching results:', error);
                setTimeout(checkResults, 3000);
            });
    }

    function displayResults(data) {
        // Hide loading indicator
        loadingResults.style.display = 'none';

        // Show results content
        resultsContent.classList.remove('hidden');

        // Update summary
        const percentage = data.overall_percentage;
        overallPercentage.textContent = percentage + '%';
        sourcesCount.textContent = data.results.length;
        matchesCount.textContent = data.total_matches;

        // Update meter
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (percentage / 100) * circumference;
        meterValue.style.strokeDasharray = circumference;
        meterValue.style.strokeDashoffset = offset;

        // Set meter color based on percentage
        if (percentage < 15) {
            meterValue.style.stroke = '#4CAF50'; // Green
        } else if (percentage < 30) {
            meterValue.style.stroke = '#FFC107'; // Yellow
        } else {
            meterValue.style.stroke = '#F44336'; // Red
        }

        // Set interpretation
        if (percentage < 15) {
            interpretationText.innerHTML = '<p><strong>Low similarity:</strong> Your content appears mostly original. Any matches are likely common phrases or coincidental similarities.</p>';
        } else if (percentage < 30) {
            interpretationText.innerHTML = '<p><strong>Moderate similarity:</strong> Some portions of your text match existing content. Consider revising the highlighted sections.</p>';
        } else {
            interpretationText.innerHTML = '<p><strong>High similarity:</strong> Significant portions of your text match existing content. Careful review and revision is recommended.</p>';
        }

        // Display matches or no matches message
        if (data.results.length === 0) {
            noMatches.classList.remove('hidden');
        } else {
            // Sort results by similarity (highest first)
            const sortedResults = data.results.sort((a, b) => b.avg_similarity - a.avg_similarity);

            // Display each source and its matches
            sourcesContainer.innerHTML = '';
            sortedResults.forEach((source, index) => {
                // Create source card element
                const sourceCard = document.createElement('div');
                sourceCard.className = 'source-card';

                // Create source header
                const sourceHeader = document.createElement('div');
                sourceHeader.className = 'source-header';
                sourceHeader.innerHTML = `
                    <h3><a href="${source.url}" target="_blank" rel="noopener noreferrer">${source.title}</a></h3>
                    <span class="similarity-badge" style="background-color: ${getSimilarityColor(source.avg_similarity)}">
                        ${Math.round(source.avg_similarity * 100)}% similar
                    </span>
                `;

                // Create matches container
                const matchesContainer = document.createElement('div');
                matchesContainer.className = 'matches-container';

                // Add each matched sentence
                source.matched_sentences.forEach(match => {
                    const matchItem = document.createElement('div');
                    matchItem.className = 'match-item';
                    matchItem.innerHTML = `
                        <div class="match-text">
                            <i class="fas fa-quote-left"></i> ${match.sentence}
                        </div>
                        <div class="match-source">
                            <strong>Similar to:</strong> ${match.source_text}
                        </div>
                        <div class="match-similarity">
                            <div class="similarity-bar">
                                <div class="similarity-filled" style="width: ${match.similarity * 100}%; background-color: ${getSimilarityColor(match.similarity)}"></div>
                            </div>
                            <span>${Math.round(match.similarity * 100)}% match</span>
                        </div>
                    `;
                    matchesContainer.appendChild(matchItem);
                });

                // Assemble source card
                sourceCard.appendChild(sourceHeader);
                sourceCard.appendChild(matchesContainer);
                sourcesContainer.appendChild(sourceCard);
            });
        }
    }

    function getSimilarityColor(similarity) {
        // Convert similarity (0-1) to a color from green to red
        const percent = similarity * 100;

        if (percent < 15) {
            return '#4CAF50'; // Green
        } else if (percent < 30) {
            return '#FFC107'; // Yellow
        } else if (percent < 50) {
            return '#FF9800'; // Orange
        } else {
            return '#F44336'; // Red
        }
    }
}