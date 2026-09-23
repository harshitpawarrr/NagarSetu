import React, { useState, useEffect, useMemo } from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Search, 
  ShieldAlert, 
  ArrowUpDown, 
  ChevronRight, 
  RefreshCw,
  AlertCircle,
  Layers,
  Zap,
  Target
} from 'lucide-react';
import { fetchComplaints } from '../services/api';

interface TriageQueueProps {
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

export const TriageQueue: React.FC<TriageQueueProps> = ({ onSelectComplaint }) => {
  const [complaints, setComplaints] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters and sorting
  const [departmentFilter, setDepartmentFilter] = useState<string>('');
  const [urgencyFilter, setUrgencyFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortBy, setSortBy] = useState<'confidence_asc' | 'urgency_desc' | 'date_desc'>('confidence_asc');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchComplaints({
        page_size: 100,
        department: departmentFilter || undefined,
        urgency: urgencyFilter || undefined,
        search_query: searchTerm || undefined
      });
      const rawList = Array.isArray(res) ? res : (res?.data || res?.items || []);
      const normalized = rawList.map((c: any) => ({
        ...c,
        channel: c.original_channel || c.channel || 'unknown',
        text: c.original_text || c.text || '',
        summary: c.summary || c.original_text || c.text || 'No description',
        department: c.department || 'Unassigned',
        urgency: c.urgency || 'LOW',
        processing_status: c.processing_status || 'OPERATOR_REVIEW_PENDING',
        routing_confidence: typeof c.routing_confidence === 'number' ? c.routing_confidence : (c.confidence ?? 0.85)
      }));
      setComplaints(normalized);
    } catch (err: any) {
      setError(err.message || 'Failed to load complaints');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [departmentFilter, urgencyFilter]);

  const filteredAndSorted = useMemo(() => {
    return complaints
      .filter(c => {
        if (statusFilter && (c.processing_status || '').toUpperCase() !== statusFilter.toUpperCase()) return false;
        if (departmentFilter && (c.department || '').toUpperCase() !== departmentFilter.toUpperCase()) return false;
        if (urgencyFilter && (c.urgency || '').toUpperCase() !== urgencyFilter.toUpperCase()) return false;
        if (searchTerm) {
          const term = searchTerm.toLowerCase().trim();
          const haystack = [
            c.complaint_id,
            c.original_text,
            c.text,
            c.summary,
            c.department,
            c.ward,
            c.normalized_locality
          ].filter(Boolean).join(' ').toLowerCase();
          if (!haystack.includes(term)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === 'confidence_asc') {
          const confA = typeof a.routing_confidence === 'number' ? a.routing_confidence : (a.confidence ?? 0.8);
          const confB = typeof b.routing_confidence === 'number' ? b.routing_confidence : (b.confidence ?? 0.8);
          return confA - confB; 
        }
        if (sortBy === 'urgency_desc') {
          const urgencyWeight: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
          const uA = urgencyWeight[(a.urgency || '').toUpperCase()] || 0;
          const uB = urgencyWeight[(b.urgency || '').toUpperCase()] || 0;
          return uB - uA;
        }
        return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
      });
  }, [complaints, statusFilter, departmentFilter, urgencyFilter, searchTerm, sortBy]);

  const summaryStats = useMemo(() => {
    return {
      critical: complaints.filter(c => c.urgency === 'CRITICAL').length,
      lowConfidence: complaints.filter(c => c.routing_confidence < 0.5).length,
      needsReview: complaints.filter(c => c.processing_status === 'OPERATOR_REVIEW_PENDING').length,
      clustered: complaints.filter(c => c.duplicate_cluster_id).length,
    };
  }, [complaints]);

  const getUrgencyBadge = (urgency?: string) => {
    switch ((urgency || '').toUpperCase()) {
      case 'CRITICAL':
        return <span className="status-critical inline-flex items-center px-2 py-1 rounded text-[10px] font-bold tracking-widest uppercase shadow-sm"><ShieldAlert className="w-3 h-3 mr-1" />CRITICAL</span>;
      case 'HIGH':
        return <span className="status-high inline-flex items-center px-2 py-1 rounded text-[10px] font-bold tracking-widest uppercase shadow-sm"><AlertTriangle className="w-3 h-3 mr-1" />HIGH</span>;
      case 'MEDIUM':
        return <span className="status-medium inline-flex items-center px-2 py-1 rounded text-[10px] font-bold tracking-widest uppercase">MEDIUM</span>;
      default:
        return <span className="status-low inline-flex items-center px-2 py-1 rounded text-[10px] font-bold tracking-widest uppercase">LOW</span>;
    }
  };

  const getConfidenceBadge = (confidence?: number) => {
    const val = typeof confidence === 'number' ? confidence : 0.85;
    if (val >= 0.80) {
      return <span className="inline-flex items-center text-[10px] uppercase font-bold tracking-widest text-emerald-400 bg-emerald-950/30 px-2 py-1 rounded border border-emerald-500/20">NORMAL ({Math.round(val * 100)}%)</span>;
    } else if (val >= 0.50) {
      return <span className="inline-flex items-center text-[10px] uppercase font-bold tracking-widest text-amber-400 bg-amber-950/30 px-2 py-1 rounded border border-amber-500/30">ATTENTION ({Math.round(val * 100)}%)</span>;
    } else {
      return <span className="inline-flex items-center text-[10px] uppercase font-bold tracking-widest text-rose-400 bg-rose-950/40 px-2 py-1 rounded border border-rose-500/40 shadow-[0_0_10px_rgba(225,29,72,0.2)]">MANUAL REVIEW ({Math.round(val * 100)}%)</span>;
    }
  };

  const getStatusBadge = (status?: string) => {
    switch ((status || '').toUpperCase()) {
      case 'OPERATOR_APPROVED':
        return <span className="inline-flex items-center px-2 py-1 text-[10px] uppercase font-bold tracking-widest text-slate-400 bg-slate-800 rounded"><CheckCircle2 className="w-3 h-3 mr-1" />APPROVED</span>;
      case 'MANUAL_REVIEW_FLAGGED':
        return <span className="inline-flex items-center px-2 py-1 rounded text-[10px] uppercase font-bold tracking-widest bg-rose-950/40 text-rose-400 border border-rose-500/30"><AlertTriangle className="w-3 h-3 mr-1" />FLAGGED</span>;
      default:
        return <span className="inline-flex items-center px-2 py-1 rounded text-[10px] uppercase font-bold tracking-widest bg-cyan-950/30 text-cyan-400 border border-cyan-500/20 shadow-sm"><Clock className="w-3 h-3 mr-1" />REVIEW PENDING</span>;
    }
  };

  return (
    <div className="space-y-10 pb-12">
      <style>{`
        @keyframes triageFadeUp {
          0% {
            opacity: 0;
            transform: translateY(12px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .triage-anim-1 { animation: triageFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 0ms forwards; opacity: 0; will-change: transform, opacity; }
        .triage-anim-2 { animation: triageFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 70ms forwards; opacity: 0; will-change: transform, opacity; }
        .triage-anim-3 { animation: triageFadeUp 420ms cubic-bezier(0.22, 1, 0.36, 1) 140ms forwards; opacity: 0; will-change: transform, opacity; }
        .triage-anim-4 { animation: triageFadeUp 420ms cubic-bezier(0.22, 1, 0.36, 1) 210ms forwards; opacity: 0; will-change: transform, opacity; }
        .triage-anim-5 { animation: triageFadeUp 450ms cubic-bezier(0.22, 1, 0.36, 1) 280ms forwards; opacity: 0; will-change: transform, opacity; }

        .triage-kpi-card {
          background: rgba(15, 23, 42, 0.90);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.10);
          border-radius: 20px;
          transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }
        .triage-kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 36px rgba(15, 23, 42, 0.20);
          border-color: rgba(100, 116, 139, 0.28);
        }

        .triage-filter-bar {
          background: rgba(15, 23, 42, 0.88);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.10);
          border-radius: 18px;
          backdrop-filter: blur(8px);
        }

        .triage-complaint-card {
          background: rgba(15, 23, 42, 0.85);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 8px 24px rgba(15, 23, 42, 0.10);
          border-radius: 18px;
          transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease, background-color 220ms ease;
        }
        .triage-complaint-card:hover {
          transform: translateY(-2px);
          background: rgba(22, 33, 56, 0.94);
          border-color: rgba(100, 116, 139, 0.30);
          box-shadow: 0 14px 34px rgba(15, 23, 42, 0.22);
        }
      `}</style>
      
      {/* Top Page Header */}
      <div className="flex flex-col mb-10 triage-anim-1">
        <h1 
          className="flex items-center tracking-tight"
          style={{
            fontWeight: 850,
            letterSpacing: '-0.035em',
            fontSize: 'clamp(52px, 5vw, 78px)',
            lineHeight: 1.05
          }}
        >
          <Target className="w-10 h-10 sm:w-12 sm:h-12 text-[#12b8d4] mr-4 shrink-0" />
          <span 
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage: 'linear-gradient(90deg, #12b8d4, #4f7cff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              display: 'inline-block'
            }}
          >
            OPERATIONS TRIAGE
          </span>
        </h1>
        <p 
          className="text-xs sm:text-sm uppercase tracking-widest mt-3 triage-anim-2"
          style={{
            color: '#64748B',
            fontWeight: 600
          }}
        >
          REVIEW, AUTHORIZE, AND PRIORITIZE CIVIC SIGNALS.
        </p>
      </div>

      {/* Attention Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 triage-anim-3">
        <div className="triage-kpi-card p-6 border-l-4 border-l-rose-500 flex items-center justify-between group">
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-2">Critical Actions</p>
            <p className="text-4xl md:text-5xl font-bold text-slate-100 group-hover:text-rose-400 transition-colors">{summaryStats.critical}</p>
          </div>
          <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-2xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-500 shadow-[inset_0_0_20px_rgba(244,63,94,0.1)]">
            <ShieldAlert className="w-6 h-6 sm:w-7 sm:h-7" />
          </div>
        </div>
        <div className="triage-kpi-card p-6 border-l-4 border-l-amber-500 flex items-center justify-between group">
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-2">Low Confidence</p>
            <p className="text-4xl md:text-5xl font-bold text-slate-100 group-hover:text-amber-400 transition-colors">{summaryStats.lowConfidence}</p>
          </div>
          <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500 shadow-[inset_0_0_20px_rgba(245,158,11,0.1)]">
            <AlertCircle className="w-6 h-6 sm:w-7 sm:h-7" />
          </div>
        </div>
        <div className="triage-kpi-card p-6 border-l-4 border-l-cyan-500 flex items-center justify-between group">
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-2">Needs Review</p>
            <p className="text-4xl md:text-5xl font-bold text-slate-100 group-hover:text-cyan-400 transition-colors">{summaryStats.needsReview}</p>
          </div>
          <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-500 shadow-[inset_0_0_20px_rgba(6,182,212,0.1)]">
            <Clock className="w-6 h-6 sm:w-7 sm:h-7" />
          </div>
        </div>
        <div className="triage-kpi-card p-6 border-l-4 border-l-violet-500 flex items-center justify-between group">
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mb-2">Clustered</p>
            <p className="text-4xl md:text-5xl font-bold text-slate-100 group-hover:text-violet-400 transition-colors">{summaryStats.clustered}</p>
          </div>
          <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-500 shadow-[inset_0_0_20px_rgba(139,92,246,0.1)]">
            <Layers className="w-6 h-6 sm:w-7 sm:h-7" />
          </div>
        </div>
      </div>

      {/* Top Filter & Control Toolbar */}
      <div className="triage-filter-bar p-4 flex flex-wrap gap-4 items-center justify-between triage-anim-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search ID, keyword..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-2 text-xs bg-slate-900/60 border border-slate-700/40 rounded-lg focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 focus:outline-none w-64 text-slate-200 transition-all placeholder:text-slate-500"
            />
          </div>

          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="text-xs font-bold uppercase tracking-wider border border-slate-700/40 rounded-lg px-3 py-2.5 bg-slate-900/60 text-slate-300 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition-all outline-none"
          >
            <option value="">All Departments</option>
            {Object.entries(DEPT_MAP).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>

          <select
            value={urgencyFilter}
            onChange={(e) => setUrgencyFilter(e.target.value)}
            className="text-xs font-bold uppercase tracking-wider border border-slate-700/40 rounded-lg px-3 py-2.5 bg-slate-900/60 text-slate-300 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition-all outline-none"
          >
            <option value="">All Urgencies</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs font-bold uppercase tracking-wider border border-slate-700/40 rounded-lg px-3 py-2.5 bg-slate-900/60 text-slate-300 focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 transition-all outline-none"
          >
            <option value="">All Statuses</option>
            <option value="OPERATOR_REVIEW_PENDING">Review Pending</option>
            <option value="OPERATOR_APPROVED">Approved</option>
            <option value="MANUAL_REVIEW_FLAGGED">Flagged</option>
          </select>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={sortBy}
              onChange={(e: any) => setSortBy(e.target.value)}
              className="text-[10px] font-bold tracking-widest uppercase border border-slate-700/40 rounded-md px-2 py-1.5 bg-slate-900/80 text-cyan-400 focus:ring-1 focus:ring-cyan-500 outline-none"
            >
              <option value="confidence_asc">Lowest Confidence First</option>
              <option value="urgency_desc">Highest Urgency First</option>
              <option value="date_desc">Newest First</option>
            </select>
          </div>

          <button
            onClick={loadData}
            title="Refresh Queue"
            className="p-2 text-slate-400 hover:text-cyan-400 bg-slate-900/60 border border-slate-700/40 rounded-md hover:border-cyan-500/30 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Triage Queue Hybrid List */}
      <div className="space-y-3 triage-anim-5">
        {loading ? (
          <div className="triage-filter-bar p-20 text-center flex flex-col items-center justify-center space-y-4">
            <RefreshCw className="w-10 h-10 animate-spin text-cyan-500" />
            <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Compiling Queue...</p>
          </div>
        ) : error ? (
          <div className="triage-filter-bar p-16 text-center border-rose-500/30">
            <div className="w-16 h-16 rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-rose-500" />
            </div>
            <p className="text-lg font-bold text-rose-400">{error}</p>
            <button onClick={loadData} className="mt-6 px-6 py-2 bg-rose-500/20 text-xs font-bold tracking-widest uppercase text-rose-300 border border-rose-500/30 rounded-lg hover:bg-rose-500/30 transition-colors">Try Again</button>
          </div>
        ) : filteredAndSorted.length === 0 ? (
          <div className="triage-filter-bar p-24 text-center">
            <div className="w-20 h-20 rounded-full bg-slate-800/80 border border-white/5 flex items-center justify-center mx-auto mb-6 shadow-inner">
              <CheckCircle2 className="w-10 h-10 text-slate-500" />
            </div>
            <p className="text-2xl font-bold text-slate-300 mb-2 tracking-tight">Inbox Zero</p>
            <p className="text-sm text-slate-500 font-medium">No complaints match the current triage criteria.</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {filteredAndSorted.map((c) => {
              const railColor = c.urgency === 'CRITICAL' ? 'bg-rose-500' : c.urgency === 'HIGH' ? 'bg-amber-500' : c.urgency === 'MEDIUM' ? 'bg-cyan-500' : 'bg-slate-600';

              return (
                <div 
                  key={c.complaint_id} 
                  onClick={() => onSelectComplaint(c.complaint_id)}
                  className="triage-complaint-card p-0 flex flex-col md:flex-row cursor-pointer group relative overflow-hidden"
                >
                  {/* Color Coded Left Rail */}
                  <div className={`absolute left-0 top-0 bottom-0 w-1 ${railColor}`}></div>
                  
                  <div className="flex-1 p-6 pl-8 md:pl-10 border-b md:border-b-0 md:border-r border-slate-700/20">
                    <div className="flex flex-wrap items-center gap-3 mb-4">
                      <span className="font-mono text-[10px] bg-slate-950/60 text-slate-300 px-2.5 py-1 rounded-md uppercase tracking-widest border border-slate-700/40 group-hover:border-cyan-500/40 transition-colors">
                        {c.complaint_id.split('-').pop()}
                      </span>
                      {getUrgencyBadge(c.urgency)}
                      {getConfidenceBadge(c.routing_confidence)}
                    </div>
                    
                    <h3 className="text-lg font-medium text-slate-100 line-clamp-2 leading-relaxed group-hover:text-white transition-colors">
                      {c.summary}
                    </h3>
                    
                    <div className="flex flex-wrap items-center gap-4 mt-5 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                      <span className="flex items-center text-cyan-400">
                        <ArrowUpDown className="w-3.5 h-3.5 mr-1.5" />
                        {DEPT_MAP[c.department] || c.department}
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="text-slate-300">Locality: {c.normalized_locality || 'Unknown'}</span>
                    </div>
                  </div>

                  <div className="w-full md:w-72 p-6 flex flex-col justify-center items-start md:items-end bg-slate-950/20">
                    <div className="mb-3">
                      {getStatusBadge(c.processing_status)}
                    </div>
                    {c.duplicate_cluster_id && (
                      <div className="mb-3">
                        <span className="inline-flex items-center text-[9px] font-bold tracking-widest uppercase px-2 py-1 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">
                          <Layers className="w-3 h-3 mr-1" /> CLUSTERED
                        </span>
                      </div>
                    )}
                    <p className="text-[9px] uppercase tracking-widest font-mono text-slate-500 mt-auto">
                      {new Date(c.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
