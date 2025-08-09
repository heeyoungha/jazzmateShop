import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'  // MainPage 대신 App import
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />  {/* MainPage 대신 App 사용 */}
  </React.StrictMode>,
)