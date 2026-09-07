import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppRoutes from './routes/AppRoutes.jsx'
import CustomCursor from './components/common/CustomCursor.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <CustomCursor />
    <AppRoutes />
  </StrictMode>,
)
