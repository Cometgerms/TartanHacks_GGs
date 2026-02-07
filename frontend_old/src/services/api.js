import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadAudioFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Upload failed');
  }
};

export const processAudio = async (params) => {
  try {
    const response = await api.post('/api/process', params);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Processing failed');
  }
};

export const getAudioInfo = async (filename) => {
  try {
    const response = await api.post('/api/process', {
      filename,
      operation: 'info',
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to get audio info');
  }
};

export const downloadFile = (filename) => {
  return `${API_BASE_URL}/api/download/${filename}`;
};

export const listFiles = async () => {
  try {
    const response = await api.get('/api/files');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Failed to list files');
  }
};

export default api;
