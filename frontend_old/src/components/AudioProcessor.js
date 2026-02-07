import React, { useState } from 'react';
import { processAudio, getAudioInfo } from '../services/api';

function AudioProcessor({ filename, onProcessComplete }) {
  const [operation, setOperation] = useState('info');
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(10);

  const handleProcess = async () => {
    setProcessing(true);
    setResult(null);
    setError('');

    try {
      const params = {
        filename,
        operation
      };

      if (operation === 'trim') {
        params.start_time = parseFloat(trimStart);
        params.end_time = parseFloat(trimEnd);
      }

      const response = await processAudio(params);
      setResult(response);
      
      if (response.output_filename) {
        onProcessComplete(response.output_filename);
      }
    } catch (err) {
      setError(`✗ ${err.message}`);
    } finally {
      setProcessing(false);
    }
  };

  const renderOperationInputs = () => {
    if (operation === 'trim') {
      return (
        <div style={{ margin: '1rem 0' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#555' }}>
            Trim Range (seconds):
          </label>
          <input
            type="number"
            placeholder="Start"
            value={trimStart}
            onChange={(e) => setTrimStart(e.target.value)}
            min="0"
          />
          <input
            type="number"
            placeholder="End"
            value={trimEnd}
            onChange={(e) => setTrimEnd(e.target.value)}
            min="0"
          />
        </div>
      );
    }
    return null;
  };

  const renderResult = () => {
    if (!result) return null;

    if (operation === 'info') {
      return (
        <div className="info-box">
          <h3 style={{ marginTop: 0 }}>Audio Information</h3>
          <p><strong>Duration:</strong> {result.duration?.toFixed(2)} seconds</p>
          <p><strong>Channels:</strong> {result.channels}</p>
          <p><strong>Sample Rate:</strong> {result.frame_rate} Hz</p>
          <p><strong>Sample Width:</strong> {result.sample_width} bytes</p>
          <p><strong>File Size:</strong> {(result.file_size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
      );
    } else {
      return (
        <div className="success-message">
          ✓ {result.message}
        </div>
      );
    }
  };

  return (
    <div className="card">
      <h2>⚙️ Process Audio</h2>
      <p style={{ color: '#666' }}>Processing: <strong>{filename}</strong></p>
      
      <div style={{ margin: '1.5rem 0' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', color: '#555' }}>
          Select Operation:
        </label>
        <select value={operation} onChange={(e) => setOperation(e.target.value)}>
          <option value="info">Get Audio Info</option>
          <option value="normalize">Normalize Volume</option>
          <option value="trim">Trim Audio</option>
        </select>
      </div>

      {renderOperationInputs()}

      <button onClick={handleProcess} disabled={processing}>
        {processing ? <span className="loading"></span> : 'Process'}
      </button>

      {renderResult()}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
}

export default AudioProcessor;
