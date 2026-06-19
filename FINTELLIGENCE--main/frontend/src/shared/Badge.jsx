const severityClass = (value = '') => {
  const normalized = value.toLowerCase();
  if (normalized.includes('critical')) return 'critical';
  if (normalized.includes('high')) return 'high';
  if (normalized.includes('medium')) return 'medium';
  return 'low';
};

export default function Badge({ value }) {
  return <span className={`badge ${severityClass(value)}`}>{value || 'clear'}</span>;
}
