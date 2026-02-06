import React, { useState } from 'react';
import { uploadAudioFile } from '../services/api';

function AudioUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      setMessage('');
      setError('');
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setMessage('');
    setError('');

    try {
      const response = await uploadAudioFile(selectedFile);
      setMessage(`✓ ${response.message}`);
      onUploadSuccess(response.filename);
    } catch (err) {
      setError(`✗ ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="card">
      <h2>📤 Upload Audio File</h2>
      
      <div style={{ margin: '1.5rem 0' }}>
        <input
          type="file"
          id="audio-file"
          accept="audio/*"
          onChange={handleFileSelect}
        />
        <label htmlFor="audio-file" className="file-input-label">
          Choose Audio File
        </label>
        
        {selectedFile && (
          <p style={{ marginTop: '1rem', color: '#555' }}>
            Selected: <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
          </p>
        )}
      </div>

      <button 
        onClick={handleUpload} 
        disabled={!selectedFile || uploading}
      >
        {uploading ? <span className="loading"></span> : 'Upload'}
      </button>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default AudioUpload;
