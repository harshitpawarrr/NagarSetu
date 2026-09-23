import React, { useState, useEffect } from 'react';
import { 
  Inbox, 
  Layers, 
  FileText, 
  ShieldCheck, 
  Activity, 
  BarChart3,
  CheckCircle2,
  Terminal,
  Cpu
} from 'lucide-react';
import { Dashboard } from './components/Dashboard';
import { TriageQueue } from './components/TriageQueue';
import { ComplaintDetailWorkbench } from './components/ComplaintDetailWorkbench';
import { ClusterWorkbench } from './components/ClusterWorkbench';
import { ReportsDashboard } from './components/ReportsDashboard';
import { EvaluationDashboard } from './components/EvaluationDashboard';
import { ComplaintsList } from './components/ComplaintsList';

export const App: React.FC = () => {
  const [currentRoute, setCurrentRoute] = useState<string>('dashboard');
  const [activeComplaintId, setActiveComplaintId] = useState<string | null>(null);

  const [renderedRoute, setRenderedRoute] = useState<string>('dashboard');
  const [renderedComplaintId, setRenderedComplaintId] = useState<string | null>(null);
  const [isFading, setIsFading] = useState<boolean>(false);

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') || '/dashboard';
      let nextRoute = 'dashboard';
      let nextId = null;

      if (hash.startsWith('/complaints/') && hash !== '/complaints') {
        nextId = hash.replace('/complaints/', '');
        nextRoute = 'detail';
      } else if (hash === '/clusters') {
        nextRoute = 'clusters';
      } else if (hash === '/complaints') {
        nextRoute = 'complaints';
      } else if (hash === '/reports') {
        nextRoute = 'reports';
      } else if (hash === '/evaluation') {
        nextRoute = 'evaluation';
      } else if (hash === '/triage') {
        nextRoute = 'triage';
      }
      
      setCurrentRoute(nextRoute);
      setActiveComplaintId(nextId);
    };

    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  useEffect(() => {
    if (currentRoute !== renderedRoute || activeComplaintId !== renderedComplaintId) {
      setIsFading(true);
      const timer = setTimeout(() => {
        setRenderedRoute(currentRoute);
        setRenderedComplaintId(activeComplaintId);
        setIsFading(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [currentRoute, activeComplaintId, renderedRoute, renderedComplaintId]);

  const navigateTo = (route: string, complaintId?: string) => {
    if (route === 'detail' && complaintId) {
      window.location.hash = `/complaints/${complaintId}`;
    } else if (route === 'clusters') {
      window.location.hash = '/clusters';
    } else if (route === 'complaints') {
      window.location.hash = '/complaints';
    } else if (route === 'reports') {
      window.location.hash = '/reports';
    } else if (route === 'evaluation') {
      window.location.hash = '/evaluation';
    } else if (route === 'triage') {
      window.location.hash = '/triage';
    } else {
      window.location.hash = '/dashboard';
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-transparent text-slate-200 relative overflow-hidden">
      
      {/* Editorial Navigation Header */}
      <header className="bg-[#050B14] border-b border-white/5 px-8 py-5 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center space-x-16">
          
          <div className="flex items-center space-x-4 cursor-pointer group" onClick={() => navigateTo('dashboard')}>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-slate-100 uppercase font-mono group-hover:text-cyan-400 transition-colors duration-300">NagarSetu<span className="text-slate-500 font-normal ml-2 tracking-normal">नगर सेतु</span></h1>
              <p className="text-[9px] text-slate-500 font-bold tracking-widest uppercase mt-0.5">Zone Office Desk</p>
            </div>
          </div>

          {/* Editorial Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-6">
            {[
              { id: 'dashboard', label: 'Overview' },
              { id: 'triage', label: 'Triage' },
              { id: 'complaints', label: 'Complaints' },
              { id: 'clusters', label: 'Incidents' },
              { id: 'reports', label: 'Reports' },
              { id: 'evaluation', label: 'Evaluation' },
            ].map(nav => (
              <button
                key={nav.id}
                onClick={() => navigateTo(nav.id)}
                className={`relative py-2 text-xs font-bold uppercase tracking-widest transition-all duration-300 ${
                  currentRoute === nav.id
                    ? 'text-cyan-400'
                    : 'text-slate-500 hover:text-slate-200'
                }`}
              >
                <span>{nav.label}</span>
                {currentRoute === nav.id && (
                  <span className="absolute bottom-0 left-0 w-full h-[2px] bg-cyan-400 rounded-t-sm"></span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* System & Mode Metadata */}
        <div className="flex items-center space-x-6 text-[9px] uppercase font-bold tracking-widest text-slate-500">
          <div className="hidden md:flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
            <span>Read-Only</span>
          </div>
          <div className="hidden md:flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span className="text-amber-500/80">Demo Dataset</span>
          </div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500/80" />
            <span className="text-emerald-500/80">Safety Active</span>
          </div>
        </div>
      </header>


      {/* Main Workspace Area */}
      <main className="flex-1 w-full max-w-[1600px] mx-auto p-4 sm:p-6 md:p-8 relative z-10">
        <div className={isFading ? 'animate-page-exit' : 'animate-page-enter'}>
          {renderedRoute === 'dashboard' ? (
            <Dashboard onNavigate={navigateTo} />
          ) : renderedRoute === 'detail' && renderedComplaintId ? (
            <ComplaintDetailWorkbench
              complaintId={renderedComplaintId}
              onBack={() => navigateTo('triage')}
            />
          ) : renderedRoute === 'clusters' ? (
            <ClusterWorkbench
              onSelectComplaint={(cid) => navigateTo('detail', cid)}
            />
          ) : renderedRoute === 'reports' ? (
            <ReportsDashboard />
          ) : renderedRoute === 'evaluation' ? (
            <EvaluationDashboard />
          ) : renderedRoute === 'complaints' ? (
            <ComplaintsList
              onSelectComplaint={(cid) => navigateTo('detail', cid)}
            />
          ) : (
            <TriageQueue
              onSelectComplaint={(cid) => navigateTo('detail', cid)}
            />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="px-8 py-6 bg-[#030712]/90 border-t border-white/5 text-[10px] uppercase tracking-widest text-slate-500 flex flex-wrap justify-between items-center gap-4 relative z-10 mt-auto">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="flex items-center space-x-2 text-emerald-500/70"><ShieldCheck className="w-3 h-3" /><span>Read-only source</span></span>
          <span className="text-slate-800 hidden sm:inline">/</span>
          <span>No live govt connection</span>
          <span className="text-slate-800 hidden sm:inline">/</span>
          <span>Human approval required</span>
          <span className="text-slate-800 hidden sm:inline">/</span>
          <span>AI outputs explainable</span>
        </div>
        <div className="flex items-center space-x-4">
          <span>Desk ID: <strong className="font-mono text-cyan-500/80">OP-ZONE-42</strong></span>
        </div>
      </footer>
    </div>
  );
};

export default App;
