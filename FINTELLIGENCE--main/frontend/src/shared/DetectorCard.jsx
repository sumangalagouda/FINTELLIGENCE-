import Badge from './Badge';

export default function DetectorCard({ item }) {
  return (
    <article className="detector-card">
      <div>
        <strong>{item.name}</strong>
        <p>{item.reason || 'Potential suspicious activity detected.'}</p>
      </div>
      <div className="score-stack">
        <Badge value={item.severity || 'medium'} />
        <span>Score {Math.round(item.score || 0)}</span>
      </div>
    </article>
  );
}
