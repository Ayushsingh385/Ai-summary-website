import { FiCoffee, FiBookOpen, FiFileText } from 'react-icons/fi';

const SummaryOptions = ({ selectedLength, onSelect }) => {
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
  );
};

export default SummaryOptions;
