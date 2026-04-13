import { FiCoffee, FiBookOpen, FiFileText } from 'react-icons/fi';

const SummaryOptions = ({ selectedLength, onSelect, selectedLanguage, onLanguageChange }) => {
  const options = [
    {
      id: 'short',
      title: 'Short',
      desc: 'Quick overview (~50-100 words)',
      icon: <FiCoffee size={24} className="text-gradient" />
    },
    {
      id: 'medium',
      title: 'Medium',
      desc: 'Balanced detail (~100-200 words)',
      icon: <FiFileText size={24} className="text-gradient" />
    },
    {
      id: 'long',
      title: 'Detailed',
      desc: 'In-depth summary (~200-400 words)',
      icon: <FiBookOpen size={24} className="text-gradient" />
    }
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.5rem', width: '100%' }}>
        <div className="form-container">
          <label htmlFor="language-select" style={{ fontWeight: '500', color: 'var(--text-main)' }}>Summary Language:</label>
          <select 
            id="language-select" 
            value={selectedLanguage} 
            onChange={(e) => onLanguageChange(e.target.value)}
            className="select-trigger"
            style={{ width: 'auto' }}
          >
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="mr">Marathi</option>
            <option value="bn">Bengali</option>
            <option value="ta">Tamil</option>
            <option value="te">Telugu</option>
            <option value="gu">Gujarati</option>
            <option value="kn">Kannada</option>
            <option value="ml">Malayalam</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
          </select>
        </div>
      </div>
      <div className="options-container fade-in">
        {options.map((opt) => (
          <div
            key={opt.id}
            className={`option-card ${selectedLength === opt.id ? 'selected' : ''}`}
            onClick={() => onSelect(opt.id)}
          >
            <div style={{ marginBottom: '1rem' }}>{opt.icon}</div>
            <h4>{opt.title}</h4>
            <p>{opt.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SummaryOptions;
