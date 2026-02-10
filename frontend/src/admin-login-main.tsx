import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { AdminLoginApp } from './AdminLoginApp'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AdminLoginApp />
  </StrictMode>,
)

