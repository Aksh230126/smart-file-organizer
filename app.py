from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential 
from azure.storage.blob import BlobServiceClient
import pyodbc
import os
import uuid
import mimetypes
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Azure Blob Storage Configuration
AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=smartfileorganizer;AccountKey=U+/89A/YwXIsvJKtvmZDLCJ2H8BMnTANgMtfUQpKl15VFUJZEGWY99VOMBVk30pweIlfXA3YYPAq+ASt+sa1YA==;EndpointSuffix=core.windows.net'
CONTAINER_NAME = 'file-uploads'
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Azure SQL Database Configuration
server = 'filemetadata-dbserver.database.windows.net'
database = 'file_metadata_db'
username = 'Akshata_2310'
password = 'Aksh@2301'
driver = '{ODBC Driver 18 for SQL Server}'


db_connection = pyodbc.connect(
    f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
)
db_cursor = db_connection.cursor()

# Get category folder
def get_category(content_type):
    if content_type == 'application/pdf':
        return 'pdfs'
    elif content_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return 'documents'
    elif content_type.startswith('image/'):
        return 'images'
    elif content_type.startswith('video/'):
        return 'videos'
    elif content_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
        return 'spreadsheets'
    else:
        return 'others'

# Analyze file using Azure Form Recognizer
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

# Home
@app.route('/')
def index():
    return render_template('index.html')

# Upload logic
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

    blob_name = f"{category}/{uuid.uuid4()}-{filename}"
    blob_client = container_client.get_blob_client(blob_name)

    try:
        file_data = file.read()

        # Upload to Azure Blob
        blob_client.upload_blob(file_data)

        # Analyze content
        extracted_text = analyze_file_with_form_recognizer(file_data)

        # Save metadata to SQL database
        insert_query = """
            INSERT INTO FileMetadata1 (Id, FileName, Category, UploadTime, BlobPath, ExtractedText)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        record_id = str(uuid.uuid4())
        db_cursor.execute(insert_query, (
            record_id,
            filename,
            category,
            datetime.utcnow(),
            blob_name,
            extracted_text[:500]  # Optional: limit to 500 characters
        ))
        db_connection.commit()

        flash(f"File '{filename}' uploaded to '{category}' folder successfully.")
        return render_template("result.html", filename=filename, category=category, extracted_text=extracted_text)

    except Exception as e:
        return f"Upload failed: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
