import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUploadCloud, FiFileText } from 'react-icons/fi';

const FileUpload = ({ onUpload }) => {
  const [error, setError] = useState('');

  const onDrop = useCallback((acceptedFiles, fileRejections) => {
    setError('');

    if (fileRejections.length > 0) {
      const rejection = fileRejections[0];
      if (rejection.errors[0].code === 'file-too-large') {
        setError('File is too large. Maximum size is 20MB.');
      } else if (rejection.errors[0].code === 'file-invalid-type') {
        setError('Invalid file type. Please upload a PDF Case File.');
      } else {
        setError(rejection.errors[0].message);
      }
      return;
    }

    if (acceptedFiles.length > 0) {
      onUpload(acceptedFiles[0]);
    }
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    maxSize: 20 * 1024 * 1024, // 20 MB
    multiple: false
  });

  return (
    <div className="fade-in">
      <div 
        {...getRootProps()} 
        className={`dropzone ${isDragActive ? 'active' : ''}`}
      >
        <input {...getInputProps()} />
        
        {acceptedFiles.length > 0 ? (
          <div>
            <FiFileText className="dropzone-icon" />
            <h3 style={{ color: 'var(--success)' }}>{acceptedFiles[0].name}</h3>
            <p>{(acceptedFiles[0].size / (1024 * 1024)).toFixed(2)} MB</p>
          </div>
        ) : (
          <div>
            <FiUploadCloud className="dropzone-icon" />
            <h3>{isDragActive ? "Drop the Case File here" : "Drag & drop a Case File"}</h3>
            <p>or click to browse from your device (PDF format, Max 20MB)</p>
          </div>
        )}
      </div>

      {error && (
        <div style={{ color: 'var(--danger)', marginTop: '1rem', textAlign: 'center', fontWeight: '500' }}>
          {error}
        </div>
      )}
    </div>
  );
};

export default FileUpload;
