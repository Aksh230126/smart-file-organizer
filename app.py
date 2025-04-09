from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential 
from azure.storage.blob import BlobServiceClient
import os
import uuid
import mimetypes

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For flashing messages

# Azure Blob Storage Configuration
AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=smartfileorganizer;AccountKey=U+/89A/YwXIsvJKtvmZDLCJ2H8BMnTANgMtfUQpKl15VFUJZEGWY99VOMBVk30pweIlfXA3YYPAq+ASt+sa1YA==;EndpointSuffix=core.windows.net'
CONTAINER_NAME = 'file-uploads'
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Categorize files based on content type
def get_category(content_type):
    if content_type.startswith('image/'):
        return 'images'
    elif content_type.startswith('video/'):
        return 'videos'
    elif content_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return 'documents'
    elif content_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        return 'spreadsheets'
    else:
        return 'others'

# Analyze file content using Azure Form Recognizer
def analyze_file_with_form_recognizer(file_data):
    endpoint = os.getenv("FORM_RECOGNIZER_ENDPOINT")
    key = os.getenv("FORM_RECOGNIZER_KEY")

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document(
        model_id="prebuilt-document",
        document=file_data
    )

    result = poller.result()
    extracted_text = "\n".join([line.content for page in result.pages for line in page.lines])
    return extracted_text

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# File upload and analysis
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    filename = secure_filename(file.filename)
    content_type, _ = mimetypes.guess_type(filename)
    category = get_category(content_type or '')

    # Create blob path
    blob_name = f"{category}/{uuid.uuid4()}-{filename}"
    blob_client = container_client.get_blob_client(blob_name)

    try:
        # Read file data for upload and analysis
        file_data = file.read()

        # Upload to Azure Blob
        blob_client.upload_blob(file_data)

        # Analyze with Form Recognizer
        extracted_text = analyze_file_with_form_recognizer(file_data)

        flash(f"File '{filename}' uploaded to '{category}' folder successfully.")
        return render_template("result.html", filename=filename, category=category, extracted_text=extracted_text)

    except Exception as e:
        return f"Upload failed: {e}", 500

# Run app
if __name__ == '__main__':
    app.run(debug=True)
