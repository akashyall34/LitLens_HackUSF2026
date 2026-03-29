import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import JoinWorkspace from './components/JoinWorkspace.tsx'

const root = document.getElementById('root')!
const isJoinPath = window.location.pathname === '/join'

createRoot(root).render(
  <StrictMode>{isJoinPath ? <JoinWorkspace /> : <App />}</StrictMode>,
)
