import axios from 'axios';

const API_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const AUTH_URL = 'http://localhost:8000/auth';

export const signUp = async (userData) => {
  const response = await axios.post(`${AUTH_URL}/signup`, userData);
  return response.data;
};

export const signIn = async (credentials) => {
  const response = await axios.post(`${AUTH_URL}/signin`, credentials);
  return response.data;
};

export const fetchProfile = async () => {
  const token = localStorage.getItem('token');
  const response = await axios.get(`${AUTH_URL}/me`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  return response.data;
};

export const chatWithBot = async (query, documentText = null, keywords = null) => {
  const response = await axios.post(`http://localhost:8000/api/chat/`, {
    query,
    document_text: documentText,
    document_keywords: keywords
  });
  return response.data;
};

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

export const downloadOriginalCase = async (originalText, originalWordCount) => {
  const response = await api.post('/download_original', {
    original_text: originalText,
    original_word_count: originalWordCount
  }, {
    responseType: 'blob'
  });
  
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `original_case.pdf`);
  document.body.appendChild(link);
  link.click();
  
  link.parentNode.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const saveCase = async (filename, originalText, summaryText, keywords, stats) => {
  const response = await api.post('/save_case', {
    filename,
    original_text: originalText,
    summary_text: summaryText,
    keywords,
    stats
  });
  return response.data;
};

export const fetchHistory = async () => {
  const response = await api.get('/history');
  return response.data;
};

export const searchCases = async (query) => {
  const response = await api.post('/search', { query, top_k: 5 });
  return response.data;
};

export const deleteCase = async (caseId) => {
  const response = await api.delete(`/delete_case/${caseId}`);
  return response.data;
};
