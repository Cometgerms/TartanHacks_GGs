import React from 'react';
import { downloadFile } from '../services/api';

function FileList({ uploadedFile, processedFile }) {
  const handleDownload = (filename) => {
    const url = downloadFile(filename);
    window.open(url, '_blank');
  };

  if (!uploadedFile && !processedFile) {
    return null;
  }

  return (
    <div className="card">
      <h2>📁 Files</h2>
      
      {uploadedFile && (
        <div style={{ marginBottom: '1rem' }}>
          <h3 style={{ color: '#666', fontSize: '1.1rem' }}>Uploaded File</h3>
          <p style={{ color: '#555' }}>
            📄 {uploadedFile}
          </p>
        </div>
      )}

      {processedFile && (
        <div>
          <h3 style={{ color: '#666', fontSize: '1.1rem' }}>Processed File</h3>
          <p style={{ color: '#555', marginBottom: '1rem' }}>
            📄 {processedFile}
          </p>
          <button onClick={() => handleDownload(processedFile)}>
            ⬇️ Download Processed File
          </button>
        </div>
      )}
    </div>
  );
}

export default FileList;
