import { useState, lazy, Suspense } from 'react';
import type { NavigationPath } from './lib/types';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { LoadingState } from './components/common/StatusStates';

const OverviewPage = lazy(() =>
  import('./pages/OverviewPage').then((m) => ({ default: m.OverviewPage }))
);
const ForecastExplorerPage = lazy(() =>
  import('./pages/ForecastExplorerPage').then((m) => ({ default: m.ForecastExplorerPage }))
);
const AccuracyAnalysisPage = lazy(() =>
  import('./pages/AccuracyAnalysisPage').then((m) => ({ default: m.AccuracyAnalysisPage }))
);

export function App() {
  const [currentPath, setCurrentPath] = useState<NavigationPath>('overview');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [cutoffHour, setCutoffHour] = useState(15);
  const [startDate, setStartDate] = useState('2026-01-01');
  const [endDate, setEndDate] = useState('2026-01-31');

  const handleDateChange = (start: string, end: string) => {
    setStartDate(start);
    setEndDate(end);
  };

  return (
    <div className="min-h-screen bg-surface-canvas text-text-primary flex flex-col font-inter">
      {/* 240px Fixed Sidebar */}
      <Sidebar
        currentPath={currentPath}
        onNavigate={setCurrentPath}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content Frame */}
      <div className="lg:pl-60 min-h-screen flex flex-col">
        {/* Top Fixed Header */}
        <Header
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          startDate={startDate}
          endDate={endDate}
          cutoffHour={cutoffHour}
          onCutoffChange={setCutoffHour}
        />

        {/* Viewport Content */}
        <main className="pt-[60px] w-full min-h-screen bg-surface-canvas">
          <Suspense fallback={<LoadingState message="Loading analytical view..." />}>
            {currentPath === 'overview' && (
              <OverviewPage
                cutoffHour={cutoffHour}
                startDate={startDate}
                endDate={endDate}
              />
            )}

            {currentPath === 'forecast-explorer' && (
              <ForecastExplorerPage
                cutoffHour={cutoffHour}
                onCutoffChange={setCutoffHour}
                startDate={startDate}
                endDate={endDate}
                onDateChange={handleDateChange}
              />
            )}

            {currentPath === 'accuracy-analysis' && (
              <AccuracyAnalysisPage
                cutoffHour={cutoffHour}
                startDate={startDate}
                endDate={endDate}
              />
            )}
          </Suspense>
        </main>
      </div>
    </div>
  );
}

export default App;
