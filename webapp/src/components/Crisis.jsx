const CRISIS_CONTACTS = `📞 8-800-2000-122 — горячая линия доверия (24/7)
🆘 112 или 03 — экстренная помощь
💬 @psyhelp_ru_bot — чат поддержки в Telegram`

export default function Crisis({ settings, onUpdate }) {
  return (
    <div className="card">
      <h3>🆘 Безопасность</h3>

      <div className="field">
        <label>
          <input
            type="checkbox"
            checked={settings.enable_crisis_detection}
            onChange={(e) =>
              onUpdate({ enable_crisis_detection: e.target.checked })
            }
          />{' '}
          Кризисное обнаружение
        </label>
      </div>

      <div className="field">
        <label>Чувствительность: {settings.crisis_sensitivity}</label>
        <input
          type="range"
          min="1"
          max="5"
          value={settings.crisis_sensitivity}
          onChange={(e) =>
            onUpdate({ crisis_sensitivity: parseInt(e.target.value, 10) })
          }
        />
      </div>

      <div style={{ marginTop: 16, fontSize: '0.9rem', lineHeight: 1.6 }}>
        <strong>Контакты поддержки:</strong>
        <pre style={{ whiteSpace: 'pre-wrap', marginTop: 8, fontFamily: 'inherit' }}>
          {CRISIS_CONTACTS}
        </pre>
      </div>
    </div>
  )
}
