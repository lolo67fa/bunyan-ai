import { ToastProvider } from './components/ui.jsx';
import { useHashRoute } from './hooks/useHashRoute.js';
import AppShell from './layouts/AppShell.jsx';
import LandingPage from './pages/LandingPage.jsx';
import NewProjectPage from './pages/NewProjectPage.jsx';
import ProjectPage from './pages/ProjectPage.jsx';
import ProjectsPage from './pages/ProjectsPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';

export default function App() {
  const route = useHashRoute();
  if (route.page === 'home') {
    return (
      <ToastProvider>
        <LandingPage />
      </ToastProvider>
    );
  }
  let page;
  if (route.page === 'project') page = <ProjectPage key={route.id} id={route.id} tab={route.tab} />;
  else if (route.page === 'projects') page = <ProjectsPage />;
  else if (route.page === 'settings' || route.page === 'help') page = <SettingsPage key={route.page} focusHelp={route.page === 'help'} />;
  else page = <NewProjectPage />;
  return (
    <ToastProvider>
      <AppShell route={route}>{page}</AppShell>
    </ToastProvider>
  );
}
