import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { TestsPage } from './pages/TestsPage'
import { RunPage } from './pages/RunPage'
import { HistoryPage } from './pages/HistoryPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="app-sidebar">
          <div className="app-sidebar__brand">
            <span className="app-sidebar__brand-icon">⚡</span>
            <div className="app-sidebar__brand-text">
              <span className="app-sidebar__brand-title">3-Tier Engine</span>
              <span className="app-sidebar__brand-sub">Execution Platform</span>
            </div>
          </div>
          <nav className="app-nav">
            <NavLink to="/" end>
              <span className="app-nav__icon">🧪</span>
              Tests
            </NavLink>
            <NavLink to="/run">
              <span className="app-nav__icon">▶</span>
              Run
            </NavLink>
            <NavLink to="/history">
              <span className="app-nav__icon">📊</span>
              History
            </NavLink>
          </nav>
          <div className="app-sidebar__footer">
            <span className="app-sidebar__footer-text">v1.0</span>
          </div>
        </aside>
        <main className="app-main">
          <Routes>
            <Route path="/" element={<TestsPage />} />
            <Route path="/run" element={<RunPage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
