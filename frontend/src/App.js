import React, { useState } from 'react';
import './App.css';
import AudioUpload from './components/AudioUpload';
import AudioProcessor from './components/AudioProcessor';
import FileList from './components/FileList';

function App() {
  const [uploadedFile, setUploadedFile] = useState(null);
  const [processedFile, setProcessedFile] = useState(null);

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎵 Audio Processing Studio</h1>
        <p>Upload, process, and download your audio files</p>
      </header>
      
      <main className="App-main">
        <div className="container">
          <AudioUpload 
            onUploadSuccess={(filename) => setUploadedFile(filename)}
          />
          
          {uploadedFile && (
            <AudioProcessor 
              filename={uploadedFile}
              onProcessComplete={(filename) => setProcessedFile(filename)}
            />
          )}
          
          <FileList 
            uploadedFile={uploadedFile}
            processedFile={processedFile}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
