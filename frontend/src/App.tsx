import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { TestsPage } from './pages/TestsPage'
import { RunPage } from './pages/RunPage'
import { HistoryPage } from './pages/HistoryPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <nav className="app-nav">
        <span className="app-nav__brand">3-Tier Execution Engine</span>
        <NavLink to="/" end>Tests</NavLink>
        <NavLink to="/run">Run</NavLink>
        <NavLink to="/history">History</NavLink>
      </nav>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<TestsPage />} />
          <Route path="/run" element={<RunPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
