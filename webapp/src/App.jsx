import { useEffect, useState } from 'react'
import { api, getUserId } from './api/client'
import Settings from './components/Settings'
import Memory from './components/Memory'
import DND from './components/DND'
import Crisis from './components/Crisis'
import Profile from './components/Profile'

const TABS = [
  { id: 'home', label: '🏠 Главная' },
  { id: 'chat', label: '💬 Общение' },
  { id: 'dnd', label: '🌙 Тишина' },
  { id: 'memory', label: '🧠 Память' },
  { id: 'profile', label: '👤 Личное' },
  { id: 'crisis', label: '🆘 Безопасность' },
]

export default function App() {
  const [tab, setTab] = useState('home')
  const [settings, setSettings] = useState(null)
  const [facts, setFacts] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [userId, setUserId] = useState(0)

  useEffect(() => {
    const tg = window.Telegram?.WebApp
    try {
      tg?.ready()
      tg?.expand()
      if (tg?.themeParams?.bg_color) {
        document.documentElement.style.setProperty(
          '--tg-theme-bg-color',
          tg.themeParams.bg_color
        )
      }
    } catch (_) {
      /* ignore */
    }

    const id = getUserId()
    setUserId(id)
    loadData(id)
  }, [])

  async function loadData(id = userId) {
    setError('')
    if (!id) {
      setLoading(false)
      setError('Не удалось определить пользователя Telegram. Закройте Mini App и откройте снова из бота.')
      return
    }
    setLoading(true)
    try {
      const [s, f] = await Promise.all([
        api.getSettings(id),
        api.getFacts(id),
      ])
      setSettings(s)
      setFacts(f.facts || {})
    } catch (e) {
      console.error(e)
      setError(
        `Не удалось загрузить данные: ${e.message || e}. Проверьте, что API/туннель запущены.`
      )
    } finally {
      setLoading(false)
    }
  }

  async function updateSettings(fields) {
    const updated = await api.updateSettings({ user_id: userId, ...fields })
    setSettings(updated)
  }

  async function handleDnd(hours) {
    await api.activateDnd({ user_id: userId, duration_hours: hours })
    await loadData()
  }

  async function handleClearMemory(scope, topic) {
    await api.clearMemory({ user_id: userId, scope, topic })
    await loadData()
  }

  async function handleDeleteFact(key) {
    await api.deleteFact({ user_id: userId, key })
    await loadData()
  }

  if (loading) {
    return <div className="app loading">Загрузка настроек...</div>
  }

  if (error) {
    return (
      <div className="app">
        <div className="card">
          <h3>Не удалось открыть Mini App</h3>
          <p style={{ marginTop: 8, lineHeight: 1.5 }}>{error}</p>
          <button className="btn" style={{ marginTop: 12 }} onClick={() => loadData()}>
            Повторить
          </button>
          <p style={{ marginTop: 12, fontSize: '0.85rem', color: '#888' }}>
            Пока можно пользоваться настройками в чате: /settings
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="header">
        <h1>Заботливая мама 👩</h1>
        <p className="status">
          {settings?.dnd_enabled ? '🔇 Тишина' : 'Активна 🌸'}
        </p>
      </div>

      {tab !== 'home' && (
        <div className="tabs">
          {TABS.filter((t) => t.id !== 'home').map((t) => (
            <button
              key={t.id}
              className={`tab ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {tab === 'home' && (
        <>
          <div className="card">
            <h3>📌 Быстрые действия</h3>
            <div className="quick-actions">
              <button className="btn" onClick={() => handleDnd(2)}>
                🔇 Тишина на 2 часа
              </button>
              <button
                className="btn btn-secondary"
                onClick={() => handleClearMemory('all')}
              >
                🧹 Забыть всё
              </button>
            </div>
          </div>

          <div className="card">
            <h3>📋 Память мамы</h3>
            <ul className="memory-preview">
              {Object.entries(facts).length === 0 && (
                <li>Пока пусто — расскажи маме о себе</li>
              )}
              {Object.entries(facts)
                .slice(0, 5)
                .map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}
                  </li>
                ))}
            </ul>
          </div>

          <button className="btn" onClick={() => setTab('chat')}>
            ⚙️ Настройки
          </button>
        </>
      )}

      {tab === 'chat' && settings && (
        <Settings settings={settings} onUpdate={updateSettings} />
      )}
      {tab === 'dnd' && settings && (
        <DND settings={settings} onUpdate={updateSettings} onActivate={handleDnd} />
      )}
      {tab === 'memory' && (
        <Memory facts={facts} onDelete={handleDeleteFact} onClear={handleClearMemory} />
      )}
      {tab === 'profile' && settings && (
        <Profile settings={settings} onUpdate={updateSettings} />
      )}
      {tab === 'crisis' && settings && (
        <Crisis settings={settings} onUpdate={updateSettings} />
      )}
    </div>
  )
}
