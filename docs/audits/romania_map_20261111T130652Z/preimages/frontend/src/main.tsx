import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { restoreSession } from './store/auth'
import { ApiError } from './lib/api'

async function start() {
  try {
    await restoreSession()
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 401)) {
      document.getElementById('root')!.textContent = (error as Error).message
      return
    }
  }
  createRoot(document.getElementById('root')!).render(
    <StrictMode><App /></StrictMode>,
  )
}
void start()
