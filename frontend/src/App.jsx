import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import QueryPage from './pages/QueryPage'
import './index.css'

export default function App() {
  return (
    <BrowserRouter>
      <div>
        <nav style={{
          display: 'flex',
          gap: '1rem',
          marginBottom: '1.5rem',
          paddingBottom: '1rem',
          borderBottom: '1px solid #27272a',
        }}>
          <NavLink
            to="/query"
            style={({ isActive }) => ({
              color: isActive ? '#3b82f6' : '#a1a1aa',
              textDecoration: 'none',
              fontWeight: isActive ? 600 : 400,
            })}
          >
            Ask
          </NavLink>
          <NavLink
            to="/upload"
            style={({ isActive }) => ({
              color: isActive ? '#3b82f6' : '#a1a1aa',
              textDecoration: 'none',
              fontWeight: isActive ? 600 : 400,
            })}
          >
            Upload
          </NavLink>
        </nav>

        <Routes>
          <Route path="/" element={<QueryPage />} />
          <Route path="/query" element={<QueryPage />} />

          <Route path="/upload" element={<UploadPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
