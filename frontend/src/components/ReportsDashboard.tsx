import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  Download, 
  RefreshCw, 
  MapPin, 
  Layers, 
  ShieldAlert, 
  Info, 
  Calendar,
  Activity,
  AlertCircle
} from 'lucide-react';
import { 
  fetchWeeklyDigest, 
  fetchLocalityRepeats, 
  fetchEmergingAlerts 
} from '../services/api';

const DEPT_MAP: Record<string, string> = {
  'DEPT_RDS': 'Roads & Infrastructure',
  'DEPT_WSS': 'Water & Sewerage',
  'DEPT_ELEC': 'Electrical Services',
  'DEPT_SWM': 'Solid Waste Management',
  'DEPT_HORT': 'Horticulture & Parks',
  'DEPT_PH': 'Public Health & Vector Control',
  'DEPT_TOWN': 'Town Planning'
};

export const ReportsDashboard: React.FC = () => {
  const [digest, setDigest] = useState<any>(null);
  const [repeats, setRepeats] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [periodPreset, setPeriodPreset] = useState<'7d' | '14d' | '30d'>('7d');

  const loadReportData = async () => {
    try {
      setLoading(true);
      setError(null);
      const end = new Date();
      const start = new Date();
      const days = periodPreset === '30d' ? 30 : periodPreset === '14d' ? 14 : 7;
      start.setDate(end.getDate() - days);

      const startStr = start.toISOString().split('T')[0];
      const endStr = end.toISOString().split('T')[0];

      const [dData, rData, aData] = await Promise.all([
        fetchWeeklyDigest(startStr, endStr),
        fetchLocalityRepeats(),
        fetchEmergingAlerts()
      ]);

      setDigest(dData);
      setRepeats(rData.localities || []);
      setAlerts(aData.alerts || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load weekly reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReportData();
  }, [periodPreset]);

  const handleExportJSON = () => {
    if (!digest) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(digest, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `nagarsetu_executive_digest_${digest.report_period_start}_to_${digest.report_period_end}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  if (loading && !digest) {
    return (
      <div className="glass-panel p-24 text-center flex flex-col items-center justify-center space-y-4">
        <Activity className="w-12 h-12 animate-pulse mx-auto text-blue-500 mb-2" />
        <p className="text-sm font-bold tracking-widest uppercase text-blue-400">Compiling Executive Digest...</p>
      </div>
    );
  }

  return (
    <div className="space-y-10 pb-24">
      <style>{`
        @keyframes reportsFadeUp {
          0% {
            opacity: 0;
            transform: translateY(12px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .reports-anim-title { animation: reportsFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 0ms forwards; opacity: 0; will-change: transform, opacity; }
        .reports-anim-subtitle { animation: reportsFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 60ms forwards; opacity: 0; will-change: transform, opacity; }
        .reports-anim-controls { animation: reportsFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 120ms forwards; opacity: 0; will-change: transform, opacity; }
        .reports-anim-kpi { animation: reportsFadeUp 420ms cubic-bezier(0.22, 1, 0.36, 1) 180ms forwards; opacity: 0; will-change: transform, opacity; }
        .reports-anim-panels { animation: reportsFadeUp 450ms cubic-bezier(0.22, 1, 0.36, 1) 260ms forwards; opacity: 0; will-change: transform, opacity; }

        .reports-kpi-card {
          background: rgba(15, 23, 42, 0.90);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
          transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }
        .reports-kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
          border-color: rgba(100, 116, 139, 0.28);
        }

        .reports-panel {
          background: rgba(15, 23, 42, 0.88);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
        }

        .reports-inner-card {
          background: rgba(10, 14, 23, 0.70);
          border: 1px solid rgba(100, 116, 139, 0.12);
          border-radius: 16px;
          transition: background-color 180ms ease, border-color 180ms ease;
        }
        .reports-inner-card:hover {
          background: rgba(15, 23, 42, 0.90);
          border-color: rgba(100, 116, 139, 0.24);
        }
      `}</style>
      
      {/* Top Page Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 reports-anim-title">
        <div className="flex flex-col">
          <h1 
            className="flex items-center tracking-tight"
            style={{
              fontWeight: 850,
              letterSpacing: '-0.035em',
              fontSize: 'clamp(50px, 4.8vw, 76px)',
              lineHeight: 1.05
            }}
          >
            <BarChart3 className="w-10 h-10 sm:w-12 sm:h-12 text-[#3b82f6] mr-4 shrink-0" />
            <span 
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage: 'linear-gradient(90deg, #3b82f6, #8b5cf6)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                display: 'inline-block'
              }}
            >
              WEEKLY ACCOUNTABILITY
            </span>
          </h1>
          <p 
            className="text-xs sm:text-sm uppercase tracking-widest mt-3 reports-anim-subtitle"
            style={{
              color: '#64748B',
              fontWeight: 600
            }}
          >
            ZONE OPERATIONAL PERFORMANCE & HOTSPOT ANALYSIS
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 mt-6 md:mt-0 reports-anim-controls">
          <div className="flex items-center space-x-1.5 bg-slate-900/80 p-1.5 rounded-xl border border-slate-700/40 text-[10px] font-bold uppercase tracking-wider">
            <Calendar className="w-4 h-4 text-slate-400 ml-2 mr-1" />
            {(['7d', '14d', '30d'] as const).map((period) => (
              <button
                key={period}
                onClick={() => setPeriodPreset(period)}
                className={`px-3.5 py-1.5 rounded-lg font-bold text-xs uppercase tracking-wider transition-all duration-200 ${
                  periodPreset === period
                    ? 'bg-blue-600 text-white shadow-[0_2px_12px_rgba(37,99,235,0.35)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {period === '7d' ? '7 Days' : period === '14d' ? '14 Days' : '30 Days'}
              </button>
            ))}
          </div>

          <div className="flex space-x-2.5">
            <button 
              onClick={loadReportData} 
              className="p-2.5 bg-slate-900/80 border border-slate-700/40 rounded-xl text-slate-400 hover:text-blue-400 hover:border-blue-500/40 transition-all hover:-translate-y-0.5"
              title="Refresh Report Data"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-400' : ''}`} />
            </button>
            <button 
              onClick={handleExportJSON} 
              className="px-5 py-2.5 bg-slate-900/80 border border-slate-700/40 rounded-xl text-slate-300 hover:text-white hover:border-blue-500/40 transition-all flex items-center space-x-2 hover:-translate-y-0.5 text-xs font-bold tracking-widest uppercase"
            >
              <Download className="w-4 h-4 text-blue-400" />
              <span>Export JSON</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/30 text-rose-400 rounded-xl text-sm font-bold flex items-center mb-8 shadow-[0_0_15px_rgba(225,29,72,0.1)]">
          <AlertCircle className="w-5 h-5 mr-3" />
          {error}
        </div>
      )}

      {digest && (
        <div className="space-y-8">
          {/* Global Overview Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 md:gap-6 reports-anim-kpi">
            <div className="reports-kpi-card p-6 border-t-2 border-t-slate-400">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Total Volume</p>
              <p className="text-4xl md:text-5xl font-bold tracking-tight text-slate-200">{digest.overall_received || 0}</p>
            </div>
            <div className="reports-kpi-card p-6 border-t-2 border-t-emerald-500">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Resolved</p>
              <p className="text-4xl md:text-5xl font-bold tracking-tight text-emerald-400">{digest.overall_resolved || 0}</p>
            </div>
            <div className="reports-kpi-card p-6 border-t-2 border-t-amber-500">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Pending Action</p>
              <p className="text-4xl md:text-5xl font-bold tracking-tight text-amber-400">
                {digest.overall_pending || 0}
              </p>
            </div>
            <div className="reports-kpi-card p-6 border-t-2 border-t-rose-500">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">SLA Breached</p>
              <p className="text-4xl md:text-5xl font-bold tracking-tight text-rose-400">0</p>
            </div>
            <div className="reports-kpi-card p-6 border-t-2 border-t-violet-500 bg-violet-950/10">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Med. Resolution (Hrs)</p>
              <p className="text-4xl md:text-5xl font-bold tracking-tight text-violet-400">{digest.overall_median_resolution_hours ? digest.overall_median_resolution_hours.toFixed(1) : '-'}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 reports-anim-panels">
            
            {/* Department Breakdown */}
            <div className="xl:col-span-2 reports-panel p-6 border-t-4 border-t-blue-500">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-blue-400 flex items-center">
                  <Activity className="w-4 h-4 mr-2" /> Department Workload & Performance
                </h3>
              </div>

              {!digest.department_breakdown || digest.department_breakdown.length === 0 ? (
                <div className="p-8 text-center border-dashed border border-slate-700/50 rounded-xl bg-slate-900/30">
                  <Activity className="w-8 h-8 text-slate-500 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-slate-300">No Department Data</p>
                  <p className="text-xs text-slate-500 mt-1">No operational metrics recorded for this selected time window.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {digest.department_breakdown.map((dept: any, idx: number) => {
                    const total = digest.overall_metrics?.total_received || 1;
                    const percent = Math.round((dept.complaints_received / total) * 100);
                    const resPercent = Math.round((dept.complaints_resolved / Math.max(1, dept.complaints_received)) * 100);

                    return (
                      <div key={idx} className="reports-inner-card p-5 overflow-hidden">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                          <div className="flex-1">
                            <h4 className="text-sm font-bold text-slate-200">
                                {DEPT_MAP[dept.department] || dept.department} 
                                <span className="ml-3 font-mono text-[9px] bg-slate-900 border border-slate-700/40 text-slate-400 px-2 py-0.5 rounded">{dept.department}</span>
                            </h4>
                            <div className="flex items-center space-x-4 mt-2 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                              <span>Total: <strong className="text-slate-200">{dept.complaints_received}</strong></span>
                              <span className="text-emerald-400">Resolved: <strong>{dept.complaints_resolved}</strong></span>
                              <span className="text-amber-400">Pending: <strong>{dept.complaints_pending}</strong></span>
                              <span className="text-rose-400">High Urgency: <strong>{dept.high_urgency_unresolved}</strong></span>
                            </div>
                          </div>
                          
                          <div className="w-full sm:w-32 text-right border-l border-slate-700/25 pl-4 flex flex-col justify-center">
                            <span className="text-2xl font-bold text-slate-100">{resPercent}%</span>
                            <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Resolution</span>
                          </div>
                        </div>
                        
                        {/* Custom visual progress bars */}
                        <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden flex">
                          <div className="h-full bg-emerald-500" style={{ width: `${resPercent}%` }}></div>
                          {dept.high_urgency_unresolved > 0 && (
                            <div className="h-full bg-rose-500" style={{ width: `${(dept.high_urgency_unresolved / Math.max(1, dept.complaints_received)) * 100}%` }}></div>
                          )}
                          <div className="h-full bg-amber-500" style={{ flex: 1 }}></div>
                        </div>
                        
                        {/* Category insights */}
                        {dept.top_categories && dept.top_categories.length > 0 && (
                            <div className="mt-4 pt-4 border-t border-slate-700/20 flex flex-wrap gap-2">
                                <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mr-2 flex items-center">Top Categories:</span>
                                {dept.top_categories.map((cat: any, sIdx: number) => (
                                    <span key={sIdx} className="text-[9px] font-bold uppercase tracking-wider bg-slate-900/80 border border-slate-700/40 text-slate-300 px-2 py-0.5 rounded">
                                        {cat.category} <span className="opacity-50">({cat.count})</span>
                                    </span>
                                ))}
                            </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="space-y-6">
              {/* Emerging Alerts */}
              <div className="reports-panel p-6 border-t-4 border-t-rose-500">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-rose-400 flex items-center">
                    <ShieldAlert className="w-4 h-4 mr-2" /> Emerging Hazard Alerts
                  </h3>
                </div>
                
                {!alerts || alerts.length === 0 ? (
                  <div className="p-8 text-center bg-slate-900/30 rounded-xl border border-slate-700/40 border-dashed">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500/80 mx-auto mb-3" />
                    <p className="text-sm font-semibold text-slate-300">All Hazards Clear</p>
                    <p className="text-xs text-slate-500 mt-1">No active hazard alerts recorded in this period.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {alerts.map((a, i) => (
                      <div key={i} className="reports-inner-card p-4 border border-rose-500/20 bg-rose-950/20 space-y-3">
                        <div className="flex justify-between items-start">
                          <span className="text-[9px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 px-2 py-0.5 rounded uppercase tracking-widest">
                            {a.category.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[10px] font-bold uppercase tracking-widest text-rose-400 font-mono">#{a.contributing_complaints?.length || 0} Tickets</span>
                        </div>
                        <p className="text-xs font-medium text-slate-200 leading-relaxed">{a.trigger_explanation}</p>
                        <div className="flex items-center text-[9px] uppercase font-bold tracking-widest text-slate-400 mt-2">
                            <MapPin className="w-3 h-3 mr-1 text-slate-400"/> {a.locality || 'Multiple Zones'} {a.ward ? `(${a.ward})` : ''}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Repeat Hotspots */}
              <div className="reports-panel p-6 border-t-4 border-t-amber-500">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-amber-400 flex items-center">
                    <MapPin className="w-4 h-4 mr-2" /> Locality Hotspots
                  </h3>
                </div>
                
                {!repeats || repeats.length === 0 ? (
                  <div className="p-8 text-center bg-slate-900/30 rounded-xl border border-slate-700/40 border-dashed">
                    <MapPin className="w-8 h-8 text-slate-500 mx-auto mb-3" />
                    <p className="text-sm font-semibold text-slate-300">No Hotspots Detected</p>
                    <p className="text-xs text-slate-500 mt-1">Complaints are evenly distributed with no localized clusters.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {repeats.map((r, i) => (
                      <div key={i} className="reports-inner-card p-4 border border-amber-500/15 bg-amber-950/15 flex items-center justify-between">
                        <div>
                          <p className="text-xs font-bold text-slate-100 flex items-center">
                            <MapPin className="w-3 h-3 text-amber-400 mr-1.5" />
                            {r.locality}
                          </p>
                          <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mt-1.5">
                            Primary: <span className="text-amber-400">{DEPT_MAP[r.department] || r.department}</span>
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-2xl font-bold text-amber-400">{r.repeat_complaints}</p>
                          <p className="text-[8px] font-bold uppercase tracking-widest text-amber-400/70 mt-0.5">Repeats</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
