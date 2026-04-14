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
        setError('Invalid file type. Supported: PDF, JPG, PNG');
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
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxSize: 20 * 1024 * 1024, // 20 MB
    multiple: false
  });

  return (
    <div>
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
            <h3>{isDragActive ? "Drop it here" : "Drop a document or image here"}</h3>
            <p>or click to pick a file (works with PDF, JPG, and PNG)</p>
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
