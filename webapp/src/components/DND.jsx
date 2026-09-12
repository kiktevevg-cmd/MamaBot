export default function DND({ settings, onUpdate, onActivate }) {
  return (
    <div className="card">
      <h3>🌙 Режим тишины</h3>

      <div className="quick-actions">
        <button className="btn" onClick={() => onActivate(1)}>
          🔇 1 час
        </button>
        <button className="btn" onClick={() => onActivate(2)}>
          🔇 2 часа
        </button>
        <button className="btn" onClick={() => onActivate(8)}>
          🔇 До утра (8ч)
        </button>
      </div>

      <div className="field" style={{ marginTop: 16 }}>
        <label>
          <input
            type="checkbox"
            checked={settings.dnd_enabled}
            onChange={(e) => onUpdate({ dnd_enabled: e.target.checked })}
          />{' '}
          DND включён
        </label>
      </div>

      {settings.dnd_until && (
        <p style={{ fontSize: '0.85rem', color: '#666', marginTop: 8 }}>
          До: {new Date(settings.dnd_until).toLocaleString('ru-RU')}
        </p>
      )}
    </div>
  )
}
