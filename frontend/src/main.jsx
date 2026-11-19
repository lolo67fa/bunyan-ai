import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import { applyPrefs } from './lib/prefs.js';
import './styles/tokens.css';
import './styles/app.css';

applyPrefs();

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
