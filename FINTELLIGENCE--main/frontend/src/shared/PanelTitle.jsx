export default function PanelTitle({ icon: Icon, title }) {
  return (
    <div className="panel-title">
      {Icon && <Icon size={16} />}
      <span>{title}</span>
    </div>
  );
}
