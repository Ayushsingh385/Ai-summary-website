import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
});

export const uploadPdf = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const summarizeText = async (text, length) => {
  const response = await api.post('/summarize', { text, length });
  return response.data;
};

export const extractKeywords = async (text) => {
  const response = await api.post('/keywords', { text });
  return response.data;
};

export const downloadSummary = async (summary, originalWordCount, summaryWordCount, format) => {
  const response = await api.post('/download', {
    summary,
    original_word_count: originalWordCount,
    summary_word_count: summaryWordCount,
    format
  }, {
    responseType: 'blob', // Important for file downloads
  });
  
  // Create a download link and trigger it
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `summary.${format}`);
  document.body.appendChild(link);
  link.click();
  
  // Cleanup
  link.parentNode.removeChild(link);
  window.URL.revokeObjectURL(url);
};
