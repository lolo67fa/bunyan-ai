import { MODE } from './api/client.js';
import { goHome, useHashRoute } from './hooks/useHashRoute.js';
import IdeaPage from './pages/IdeaPage.jsx';
import ProjectPage from './pages/ProjectPage.jsx';

export default function App() {
  const route = useHashRoute();
  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={goHome} aria-label="الصفحة الرئيسية">
          بُنيان <span className="accent ltr">AI</span>
        </button>
        {MODE === 'mock' && (
          <span className="mock-badge" title="بيانات تجريبية — الباك إند غير مربوط">
            Mock
          </span>
        )}
      </header>
      <main>{route.page === 'project' ? <ProjectPage key={route.id} id={route.id} /> : <IdeaPage />}</main>
      <footer className="foot muted small">نادي طويق · جامعة الملك سعود — مسار الذكاء الاصطناعي</footer>
    </>
  );
}
