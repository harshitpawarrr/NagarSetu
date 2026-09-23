import React, { useState, useEffect, useMemo } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Search, 
  ShieldAlert, 
  ArrowUpDown, 
  RefreshCw,
  Target,
  Layers
} from 'lucide-react';
import { fetchComplaints } from '../services/api';

interface ComplaintsListProps {
  onSelectComplaint: (complaintId: string) => void;
}

const DEPT_MAP: Record<string, string> = {
  'DEPT_RDS': 'Roads & Infrastructure',
  'DEPT_WSS': 'Water & Sewerage',
  'DEPT_ELEC': 'Electrical Services',
  'DEPT_SWM': 'Solid Waste Management',
  'DEPT_HORT': 'Horticulture & Parks',
  'DEPT_PH': 'Public Health & Vector Control',
  'DEPT_TOWN': 'Town Planning'
};

export const ComplaintsList: React.FC<ComplaintsListProps> = ({ onSelectComplaint }) => {
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [departmentFilter, setDepartmentFilter] = useState<string>('');
  const [urgencyFilter, setUrgencyFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchComplaints({
        page_size: 100,
      });
      const rawList = Array.isArray(res) ? res : (res?.data || res?.items || []);
      const normalized = rawList.map((c: any) => ({
        ...c,
        channel: c.original_channel || c.channel || 'unknown',
        summary: c.summary || c.original_text || c.text || 'No description',
      }));
      setComplaints(normalized);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch complaints');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = useMemo(() => {
    return complaints
      .filter(c => {
        if (departmentFilter && c.department !== departmentFilter) return false;
        if (urgencyFilter && c.urgency !== urgencyFilter) return false;
        if (searchTerm) {
          const term = searchTerm.toLowerCase();
          const haystack = [
            c.complaint_id,
            c.summary,
            c.department,
            c.ward,
            c.normalized_locality
          ].filter(Boolean).join(' ').toLowerCase();
          if (!haystack.includes(term)) return false;
        }
        return true;
      })
      .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
  }, [complaints, departmentFilter, urgencyFilter, searchTerm]);

  const summaryStats = useMemo(() => {
    return {
      total: complaints.length,
      critical: complaints.filter(c => c.urgency === 'CRITICAL').length,
      unresolved: complaints.filter(c => c.processing_status === 'OPERATOR_REVIEW_PENDING').length
    };
  }, [complaints]);

  const getUrgencyColor = (u: string) => {
    if (u === 'CRITICAL') return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    if (u === 'HIGH') return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    if (u === 'MEDIUM') return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
    return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
  };

  const getStatusColor = (s: string) => {
    if (s === 'OPERATOR_APPROVED') return 'text-emerald-400';
    if (s === 'MANUAL_REVIEW_FLAGGED') return 'text-rose-400';
    return 'text-cyan-400';
  };

  return (
    <div className="space-y-10 pb-12">
      <style>{`
        @keyframes complaintsFadeUp {
          0% {
            opacity: 0;
            transform: translateY(12px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .complaints-anim-title { animation: complaintsFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 0ms forwards; opacity: 0; will-change: transform, opacity; }
        .complaints-anim-subtitle { animation: complaintsFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 60ms forwards; opacity: 0; will-change: transform, opacity; }
        .complaints-anim-kpi-1 { animation: complaintsFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 120ms forwards; opacity: 0; will-change: transform, opacity; }
        .complaints-anim-kpi-2 { animation: complaintsFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 180ms forwards; opacity: 0; will-change: transform, opacity; }
        .complaints-anim-kpi-3 { animation: complaintsFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 240ms forwards; opacity: 0; will-change: transform, opacity; }
        .complaints-anim-filter { animation: complaintsFadeUp 420ms cubic-bezier(0.22, 1, 0.36, 1) 300ms forwards; opacity: 0; will-change: transform, opacity; }
        .complaints-anim-list { animation: complaintsFadeUp 440ms cubic-bezier(0.22, 1, 0.36, 1) 360ms forwards; opacity: 0; will-change: transform, opacity; }

        .complaints-kpi-card {
          background: rgba(15, 23, 42, 0.90);
          border: 1px solid rgba(100, 116, 139, 0.14);
          box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
          transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }
        .complaints-kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
          border-color: rgba(100, 116, 139, 0.28);
        }

        .complaints-filter-panel {
          background: rgba(22, 33, 56, 0.82);
          border: 1px solid rgba(100, 116, 139, 0.18);
          box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
          border-radius: 18px;
          backdrop-filter: blur(8px);
        }

        .complaints-table-container {
          background: rgba(15, 23, 42, 0.88);
          border: 1px solid rgba(100, 116, 139, 0.14);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
          overflow: hidden;
        }

        .complaint-table-row {
          transition: transform 180ms ease, background-color 180ms ease, box-shadow 180ms ease;
        }
        .complaint-table-row:hover {
          transform: translateY(-1px);
          background: rgba(30, 41, 59, 0.45);
          box-shadow: inset 0 0 0 1px rgba(100, 116, 139, 0.25);
        }
      `}</style>
      
      {/* Header */}
      <div className="flex flex-col mb-10 complaints-anim-title">
        <h1 
          className="flex items-center tracking-tight"
          style={{
            fontWeight: 850,
            letterSpacing: '-0.035em',
            fontSize: 'clamp(52px, 5vw, 78px)',
            lineHeight: 1.05
          }}
        >
          <Layers className="w-10 h-10 sm:w-12 sm:h-12 text-[#16b981] mr-4 shrink-0" />
          <span 
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage: 'linear-gradient(90deg, #16b981, #22c7d8)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              display: 'inline-block'
            }}
          >
            CIVIC SIGNALS
          </span>
        </h1>
        <p 
          className="text-xs sm:text-sm uppercase tracking-widest mt-3 complaints-anim-subtitle"
          style={{
            color: '#64748B',
            fontWeight: 600
          }}
        >
          REVIEW INCOMING SIGNALS BEFORE THEY BECOME INCIDENTS
        </p>
      </div>

      {/* Analytics Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="complaints-kpi-card p-6 border-l-4 border-l-emerald-500 complaints-anim-kpi-1">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Total Ingested</p>
          <p className="text-4xl font-bold text-slate-100">{summaryStats.total}</p>
        </div>
        <div className="complaints-kpi-card p-6 border-l-4 border-l-rose-500 complaints-anim-kpi-2">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Critical Priority</p>
          <p className="text-4xl font-bold text-rose-400">{summaryStats.critical}</p>
        </div>
        <div className="complaints-kpi-card p-6 border-l-4 border-l-cyan-500 complaints-anim-kpi-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Unresolved Signals</p>
          <p className="text-4xl font-bold text-cyan-400">{summaryStats.unresolved}</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="complaints-filter-panel p-4 flex flex-wrap gap-4 items-center justify-between complaints-anim-filter">
        <div className="flex flex-wrap items-center gap-4 w-full md:w-auto">
          <div className="relative flex-1 md:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search signal ID or content..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 text-xs bg-slate-900/60 border border-slate-700/40 rounded-lg text-slate-200 placeholder:text-slate-500 focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all outline-none"
            />
          </div>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="text-xs font-bold uppercase tracking-widest px-4 py-2.5 bg-slate-900/60 border border-slate-700/40 rounded-lg text-slate-300 focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all outline-none"
          >
            <option value="">All Departments</option>
            {Object.entries(DEPT_MAP).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
        </div>
        <button 
          onClick={loadData} 
          disabled={loading} 
          className="p-2.5 bg-slate-900/60 border border-slate-700/40 rounded-lg hover:border-emerald-500/50 text-emerald-400 transition-colors"
          title="Refresh Signals"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Data Table */}
      <div className="complaints-table-container complaints-anim-list">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead>
              <tr className="border-b border-slate-700/30 bg-slate-900/90">
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">ID</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">Signal</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">Department</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">Urgency</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">Confidence</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">Status</th>
                <th className="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-slate-400 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {loading && filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-500" />
                    <p className="text-xs uppercase tracking-widest">Loading Signals...</p>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                    <p className="text-sm font-medium">No signals found matching criteria.</p>
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr 
                    key={c.complaint_id} 
                    className="complaint-table-row group cursor-pointer"
                    onClick={() => onSelectComplaint(c.complaint_id)}
                  >
                    <td className="px-6 py-5">
                      <span className="font-mono text-[10px] text-slate-300 bg-slate-950/60 px-2.5 py-1 rounded border border-slate-700/40 group-hover:border-emerald-500/30 transition-colors">
                        {c.complaint_id.split('-').pop()}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <p className="text-sm text-slate-100 font-semibold line-clamp-1 max-w-xs group-hover:text-emerald-300 transition-colors">{c.summary}</p>
                      <p className="text-[10px] text-slate-400 uppercase tracking-widest mt-1">Via {c.channel}</p>
                    </td>
                    <td className="px-6 py-5">
                      <span className="text-xs font-medium text-slate-300">
                        {DEPT_MAP[c.department] || c.department}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <span className={`inline-flex items-center px-2 py-1 rounded border text-[9px] font-bold uppercase tracking-widest ${getUrgencyColor(c.urgency)}`}>
                        {c.urgency || 'UNKNOWN'}
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <span className="text-xs font-mono font-medium text-slate-300">
                        {((c.routing_confidence ?? c.confidence ?? 0.8) * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-5">
                      <span className={`text-[10px] font-bold uppercase tracking-widest flex items-center ${getStatusColor(c.processing_status)}`}>
                        {c.processing_status?.replace(/_/g, ' ') || 'PENDING'}
                      </span>
                    </td>
                    <td className="px-6 py-5 text-right">
                      <button className="text-xs font-bold uppercase tracking-widest text-[#22c7d8] opacity-0 group-hover:opacity-100 transition-opacity">
                        Review &rarr;
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
