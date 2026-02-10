import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { AdminDashboardApp } from './AdminDashboardApp'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AdminDashboardApp />
  </StrictMode>,
)

