"""
Flask Backend for Audio Processing Application
Handles audio file uploads and processing
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import io
from audio_processor import AudioProcessor

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'flac', 'm4a'}

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize audio processor
audio_processor = AudioProcessor()


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Audio Processing Backend API',
        'version': '1.0.0'
    })


@app.route('/api/upload', methods=['POST'])
def upload_audio():
    """Upload audio file for processing"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    return jsonify({
        'message': 'File uploaded successfully',
        'filename': filename,
        'filepath': filepath
    }), 200


@app.route('/api/process', methods=['POST'])
def process_audio():
    """Process uploaded audio file"""
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400
    
    filename = data['filename']
    operation = data.get('operation', 'info')
    
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(input_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        if operation == 'info':
            result = audio_processor.get_audio_info(input_path)
        elif operation == 'normalize':
            output_filename = f"normalized_{filename}"
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
            audio_processor.normalize_audio(input_path, output_path)
            result = {'output_filename': output_filename, 'message': 'Audio normalized successfully'}
        elif operation == 'trim':
            start_time = data.get('start_time', 0)
            end_time = data.get('end_time', 10)
            output_filename = f"trimmed_{filename}"
            output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)
            audio_processor.trim_audio(input_path, output_path, start_time, end_time)
            result = {'output_filename': output_filename, 'message': 'Audio trimmed successfully'}
        else:
            return jsonify({'error': 'Invalid operation'}), 400
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download processed audio file"""
    filepath = os.path.join(app.config['PROCESSED_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(filepath, as_attachment=True)


@app.route('/api/files', methods=['GET'])
def list_files():
    """List all uploaded and processed files"""
    uploaded = os.listdir(app.config['UPLOAD_FOLDER']) if os.path.exists(app.config['UPLOAD_FOLDER']) else []
    processed = os.listdir(app.config['PROCESSED_FOLDER']) if os.path.exists(app.config['PROCESSED_FOLDER']) else []
    
    return jsonify({
        'uploaded': uploaded,
        'processed': processed
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
