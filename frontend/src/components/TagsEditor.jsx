import { useState } from 'react';
import { FiX, FiPlus } from 'react-icons/fi';
import { updateCaseTags } from '../api';

const TagsEditor = ({ caseId, initialTags = [], onTagsUpdate }) => {
  const [tags, setTags] = useState(initialTags);
  const [inputVisible, setInputVisible] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  const handleAddTag = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || tags.includes(trimmed)) {
      setInputVisible(false);
      setInputValue('');
      return;
    }
    const newTags = [...tags, trimmed];
    setTags(newTags);
    setInputVisible(false);
    setInputValue('');
    await saveTags(newTags);
  };

  const handleRemoveTag = async (tagToRemove) => {
    const newTags = tags.filter(t => t !== tagToRemove);
    setTags(newTags);
    await saveTags(newTags);
  };

  const saveTags = async (newTags) => {
    if (!caseId) return;
    setIsSaving(true);
    try {
      await updateCaseTags(caseId, newTags);
      if (onTagsUpdate) onTagsUpdate(newTags);
    } catch (err) {
      console.warn('Failed to save tags:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    } else if (e.key === 'Escape') {
      setInputVisible(false);
      setInputValue('');
    }
  };

  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>Tags:</span>
        {tags.map((tag) => (
          <span
            key={tag}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              padding: '0.25rem 0.5rem',
              background: 'var(--accent-primary)',
              color: '#fff',
              borderRadius: '12px',
              fontSize: '0.75rem',
              fontWeight: '500'
            }}
          >
            {tag}
            <FiX
              size={12}
              style={{ cursor: 'pointer' }}
              onClick={() => handleRemoveTag(tag)}
            />
          </span>
        ))}
        {inputVisible ? (
          <input
            autoFocus
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleAddTag}
            placeholder="tag name..."
            style={{
              padding: '0.2rem 0.5rem',
              fontSize: '0.75rem',
              border: '1px solid var(--accent-primary)',
              borderRadius: '12px',
              background: 'var(--bg-card)',
              color: 'var(--text-main)',
              outline: 'none',
              width: '100px'
            }}
          />
        ) : (
          <button
            onClick={() => setInputVisible(true)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.2rem',
              padding: '0.25rem 0.5rem',
              fontSize: '0.75rem',
              background: 'transparent',
              color: 'var(--accent-primary)',
              border: '1px dashed var(--accent-primary)',
              borderRadius: '12px',
              cursor: 'pointer'
            }}
          >
            <FiPlus size={12} /> Add tag
          </button>
        )}
        {isSaving && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Saving...</span>}
      </div>
    </div>
  );
};

export default TagsEditor;
