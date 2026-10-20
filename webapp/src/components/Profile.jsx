import { useState } from 'react'

const PERSONALITIES = ['заботливая', 'строгая', 'веселая', 'ностальгическая']

export default function Profile({ settings, onUpdate }) {
  const persona = settings.persona || {}
  const relationship = settings.relationship || {}
  const [habitDraft, setHabitDraft] = useState('')
  const [tabooDraft, setTabooDraft] = useState('')
  const [noteDraft, setNoteDraft] = useState(relationship.notes || '')

  function patchPersona(patch) {
    onUpdate({ persona: { ...persona, ...patch } })
  }

  function patchRelationship(patch) {
    onUpdate({ relationship: { ...relationship, ...patch } })
  }

  function addHabit() {
    const v = habitDraft.trim()
    if (!v) return
    const habits = [...(persona.habits || []), v].slice(0, 6)
    setHabitDraft('')
    patchPersona({ habits })
  }

  function removeHabit(h) {
    patchPersona({ habits: (persona.habits || []).filter((x) => x !== h) })
  }

  function addTaboo() {
    const v = tabooDraft.trim()
    if (!v) return
    const taboos = [v, ...(persona.taboos || []).filter((x) => x !== v)].slice(0, 6)
    setTabooDraft('')
    patchPersona({ taboos })
  }

  return (
    <div className="card">
      <h3>👤 Личное</h3>

      <div className="field">
        <label>Твоё имя</label>
        <input
          value={settings.user_name || ''}
          onChange={(e) => onUpdate({ user_name: e.target.value })}
          placeholder="Как к тебе обращаться"
        />
      </div>

      <div className="field">
        <label>Пол</label>
        <select
          value={settings.user_gender}
          onChange={(e) => onUpdate({ user_gender: e.target.value })}
        >
          <option value="не указано">Не указано</option>
          <option value="мужской">Мужской</option>
          <option value="женский">Женский</option>
        </select>
      </div>

      <div className="field">
        <label>Имя мамы</label>
        <input
          value={settings.mama_name}
          onChange={(e) => onUpdate({ mama_name: e.target.value })}
        />
      </div>

      <div className="field">
        <label>Характер мамы</label>
        <select
          value={settings.mama_personality}
          onChange={(e) => onUpdate({ mama_personality: e.target.value })}
        >
          {PERSONALITIES.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <h3 style={{ marginTop: 20 }}>👩 Карточка мамы</h3>
      <p style={{ fontSize: '0.9rem', opacity: 0.8, marginBottom: 8 }}>
        Статус сейчас: <strong>{settings.mama_status || 'дома'}</strong>
      </p>

      <div className="field">
        <label>Город</label>
        <input
          value={persona.city || ''}
          onChange={(e) => patchPersona({ city: e.target.value })}
        />
      </div>
      <div className="field">
        <label>Возраст</label>
        <input
          type="number"
          value={persona.age || ''}
          onChange={(e) => patchPersona({ age: Number(e.target.value) || persona.age })}
        />
      </div>
      <div className="field">
        <label>Чем занимается</label>
        <input
          value={persona.occupation || ''}
          onChange={(e) => patchPersona({ occupation: e.target.value })}
        />
      </div>
      <div className="field">
        <label>О себе</label>
        <textarea
          rows={3}
          value={persona.backstory || ''}
          onChange={(e) => patchPersona({ backstory: e.target.value })}
        />
      </div>

      <div className="field">
        <label>Привычки</label>
        <ul className="memory-preview">
          {(persona.habits || []).map((h) => (
            <li key={h}>
              {h}{' '}
              <button type="button" className="btn btn-secondary" onClick={() => removeHabit(h)}>
                ✕
              </button>
            </li>
          ))}
        </ul>
        <div className="quick-actions">
          <input
            value={habitDraft}
            onChange={(e) => setHabitDraft(e.target.value)}
            placeholder="Новая привычка"
          />
          <button type="button" className="btn" onClick={addHabit}>
            Добавить
          </button>
        </div>
      </div>

      <div className="field">
        <label>Чего не делать</label>
        <ul className="memory-preview">
          {(persona.taboos || []).map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
        <div className="quick-actions">
          <input
            value={tabooDraft}
            onChange={(e) => setTabooDraft(e.target.value)}
            placeholder="Например: не читай нотации"
          />
          <button type="button" className="btn" onClick={addTaboo}>
            Добавить
          </button>
        </div>
      </div>

      <h3 style={{ marginTop: 20 }}>💬 Память отношений</h3>
      <div className="field">
        <label>Стиль общения</label>
        <select
          value={relationship.chat_style || 'смешанно'}
          onChange={(e) => patchRelationship({ chat_style: e.target.value })}
        >
          <option value="коротко">коротко</option>
          <option value="смешанно">смешанно</option>
          <option value="развернуто">развернуто</option>
        </select>
      </div>
      <div className="field">
        <label>Заметки об отношениях</label>
        <textarea
          rows={2}
          value={noteDraft}
          onChange={(e) => setNoteDraft(e.target.value)}
          onBlur={() => patchRelationship({ notes: noteDraft })}
        />
      </div>
    </div>
  )
}
