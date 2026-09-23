import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  RefreshCw, 
  TrendingDown, 
  FileText, 
  MapPin, 
  CheckCircle2, 
  XCircle, 
  Info, 
  ChevronRight, 
  AlertCircle,
  Network,
  Edit3,
  Server,
  Crosshair
} from 'lucide-react';
import { 
  fetchClusters, 
  fetchClusterDetail, 
  detectClusters, 
  reviewCluster 
} from '../services/api';
import type { ClusterSummary, ClusterDetailResponse, ClusterAnalytics } from '../types/cluster';

interface ClusterWorkbenchProps {
  onSelectComplaint?: (complaintId: string) => void;
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

export const ClusterWorkbench: React.FC<ClusterWorkbenchProps> = ({ onSelectComplaint }) => {
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [analytics, setAnalytics] = useState<ClusterAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [clusterDetail, setClusterDetail] = useState<ClusterDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [operatorNotes, setOperatorNotes] = useState<string>('');
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadClusters = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchClusters();
      setClusters(res.clusters || []);
      setAnalytics(res.analytics || null);
    } catch (err: any) {
      setError(err.message || 'Failed to load clusters');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClusters();
  }, []);

  const handleRunDetection = async () => {
    try {
      setLoading(true);
      setActionMessage(null);
      const res = await detectClusters({ recluster: true });
      setActionMessage(`Clustering completed: ${res.clusters_created} clusters created from ${res.total_complaints_clustered} complaints.`);
      await loadClusters();
    } catch (err: any) {
      setError(err.message || 'Cluster detection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCluster = async (clusterId: string) => {
    try {
      setSelectedClusterId(clusterId);
      setDetailLoading(true);
      const detail = await fetchClusterDetail(clusterId);
      setClusterDetail(detail);
      setOperatorNotes(detail.operator_notes || '');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleRemoveMember = async (complaintId: string) => {
    if (!selectedClusterId) return;
    try {
      setDetailLoading(true);
      await reviewCluster(selectedClusterId, {
        action: 'remove_member',
        complaint_id: complaintId,
        operator_id: 'OP-ZONE-42',
        notes: 'Member confirmed as false positive and removed by operator.'
      });
      setActionMessage(`Complaint ${complaintId} removed from cluster.`);
      const updated = await fetchClusterDetail(selectedClusterId);
      setClusterDetail(updated);
      await loadClusters();
    } catch (err: any) {
      setError(err.message);
      setDetailLoading(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!selectedClusterId) return;
    try {
      setDetailLoading(true);
      await reviewCluster(selectedClusterId, {
        action: 'add_notes',
        operator_id: 'OP-ZONE-42',
        notes: operatorNotes
      });
      setActionMessage(`Operator notes saved for cluster ${selectedClusterId.split('-').pop()}.`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading && !clusters.length) {
    return (
      <div className="glass-panel p-24 text-center text-slate-500 flex flex-col items-center justify-center space-y-4">
        <Network className="w-12 h-12 animate-pulse text-violet-500 mb-2" />
        <p className="text-sm font-bold tracking-widest uppercase text-violet-400">Analyzing Spatial-Temporal Patterns...</p>
      </div>
    );
  }

  return (
    <div className="space-y-10 pb-24">
      <style>{`
        @keyframes clusterFadeUp {
          0% {
            opacity: 0;
            transform: translateY(12px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .cluster-anim-title { animation: clusterFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 0ms forwards; opacity: 0; will-change: transform, opacity; }
        .cluster-anim-subtitle { animation: clusterFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 60ms forwards; opacity: 0; will-change: transform, opacity; }
        .cluster-anim-btn { animation: clusterFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 120ms forwards; opacity: 0; will-change: transform, opacity; }
        .cluster-anim-kpi { animation: clusterFadeUp 420ms cubic-bezier(0.22, 1, 0.36, 1) 180ms forwards; opacity: 0; will-change: transform, opacity; }
        .cluster-anim-workspace { animation: clusterFadeUp 440ms cubic-bezier(0.22, 1, 0.36, 1) 240ms forwards; opacity: 0; will-change: transform, opacity; }

        .cluster-kpi-card {
          background: rgba(15, 23, 42, 0.90);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
          transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }
        .cluster-kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
          border-color: rgba(100, 116, 139, 0.28);
        }

        .cluster-item-card {
          background: rgba(15, 23, 42, 0.88);
          border: 1px solid rgba(100, 116, 139, 0.14);
          box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
          border-radius: 18px;
          transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease, background-color 200ms ease;
        }
        .cluster-item-card:hover {
          transform: translateY(-2px);
          background: rgba(22, 33, 56, 0.94);
          border-color: rgba(124, 92, 255, 0.35);
          box-shadow: 0 14px 32px rgba(15, 23, 42, 0.20);
        }
        .cluster-item-selected {
          background: rgba(30, 27, 75, 0.60);
          border: 1px solid rgba(124, 92, 255, 0.65);
          box-shadow: 0 12px 30px rgba(124, 92, 255, 0.15);
          border-radius: 18px;
        }

        .cluster-workspace-panel {
          background: rgba(15, 23, 42, 0.90);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.10);
          border-radius: 20px;
        }

        .cluster-member-card {
          background: rgba(10, 14, 23, 0.70);
          border: 1px solid rgba(100, 116, 139, 0.12);
          border-radius: 16px;
          transition: background-color 180ms ease, border-color 180ms ease;
        }
        .cluster-member-card:hover {
          background: rgba(15, 23, 42, 0.90);
          border-color: rgba(100, 116, 139, 0.24);
        }
      `}</style>
      
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 cluster-anim-title">
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
            <Network className="w-10 h-10 sm:w-12 sm:h-12 text-[#7c5cff] mr-4 shrink-0" />
            <span 
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage: 'linear-gradient(90deg, #7c5cff, #22c7d8)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                display: 'inline-block'
              }}
            >
              INCIDENT INTELLIGENCE
            </span>
          </h1>
          <p 
            className="text-xs sm:text-sm uppercase tracking-widest mt-3 cluster-anim-subtitle"
            style={{
              color: '#64748B',
              fontWeight: 600
            }}
          >
            COLLAPSE DUPLICATE SIGNALS INTO ACTIONABLE CIVIC INCIDENTS
          </p>
        </div>
        
        <div className="flex items-center gap-4 mt-6 md:mt-0 cluster-anim-btn">
           <button 
             onClick={handleRunDetection}
             disabled={loading}
             className="px-6 py-3.5 bg-[#7c5cff] hover:bg-[#6b46ff] text-white rounded-xl font-bold text-xs uppercase tracking-widest disabled:opacity-50 transition-all duration-200 flex items-center shadow-[0_4px_16px_rgba(124,92,255,0.25)] hover:shadow-[0_8px_24px_rgba(124,92,255,0.35)] hover:-translate-y-[2px] active:scale-[0.98]"
           >
             <RefreshCw className={`w-4 h-4 mr-2.5 ${loading ? 'animate-spin' : ''}`} />
             <span>Run Detection Scan</span>
           </button>
        </div>
      </div>

      {actionMessage && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 rounded-lg text-sm font-bold uppercase tracking-widest flex items-center shadow-[0_0_15px_rgba(16,185,129,0.1)]">
          <CheckCircle2 className="w-4 h-4 mr-2 flex-shrink-0" />
          {actionMessage}
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/30 text-rose-400 rounded-lg text-sm font-bold flex items-center shadow-[0_0_15px_rgba(225,29,72,0.1)]">
          <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Analytics Summary */}
      {analytics && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 md:gap-6 cluster-anim-kpi">
          <div className="cluster-kpi-card p-6 border-t-2 border-t-blue-500">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Total Ingested</p>
            <p className="text-4xl md:text-5xl font-bold tracking-tight text-blue-400">{analytics.raw_complaint_count}</p>
          </div>
          <div className="cluster-kpi-card p-6 border-t-2 border-t-violet-500">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Active Clusters</p>
            <p className="text-4xl md:text-5xl font-bold tracking-tight text-violet-400">{analytics.unique_cluster_count}</p>
          </div>
          <div className="cluster-kpi-card p-6 border-t-2 border-t-emerald-500">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Singletons</p>
            <p className="text-4xl md:text-5xl font-bold tracking-tight text-emerald-400">{analytics.unclustered_complaint_count}</p>
          </div>
          <div className="cluster-kpi-card p-6 border-t-2 border-t-amber-500">
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">Duplicates</p>
            <p className="text-4xl md:text-5xl font-bold tracking-tight text-amber-400">{analytics.duplicate_or_related_count}</p>
          </div>
          <div className="cluster-kpi-card p-6 border-t-2 border-t-indigo-500 bg-indigo-950/20">
            <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 mb-2 flex items-center">
              <TrendingDown className="w-4 h-4 mr-1" /> Reduction
            </p>
            <p className="text-4xl md:text-5xl font-bold tracking-tight text-indigo-300">{Math.round(analytics.ticket_reduction_percentage)}%</p>
          </div>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 cluster-anim-workspace">
        
        {/* Left Column: Cluster List */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 flex items-center mb-4 pl-1">
            <Layers className="w-4 h-4 mr-2 text-violet-400" /> Active Incidents ({clusters.length})
          </h3>
          
          <div className="space-y-3 pr-2 h-[800px] overflow-y-auto custom-scrollbar">
            {clusters.length === 0 ? (
              <p className="text-sm text-slate-500 italic p-4 text-center">No clusters detected.</p>
            ) : (
              clusters.map((cluster) => {
                const isSelected = selectedClusterId === cluster.cluster_id;
                return (
                  <div 
                    key={cluster.cluster_id}
                    onClick={() => handleSelectCluster(cluster.cluster_id)}
                    className={`p-5 cursor-pointer ${
                      isSelected ? 'cluster-item-selected' : 'cluster-item-card'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <span className={`text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-md font-mono ${isSelected ? 'bg-violet-500/20 text-violet-300 border border-violet-500/40' : 'bg-slate-900/80 text-slate-400 border border-slate-700/40'}`}>
                        {cluster.cluster_id.split('-').pop()}
                      </span>
                      <span className="flex items-center text-xs font-bold text-slate-200 bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-700/40">
                        <FileText className="w-3.5 h-3.5 mr-1.5 text-cyan-400" /> {cluster.complaint_count} Signals
                      </span>
                    </div>
                    
                    <h4 className={`text-sm font-semibold mb-3.5 line-clamp-2 leading-relaxed ${isSelected ? 'text-white' : 'text-slate-200 group-hover:text-violet-300'}`}>
                      {cluster.representative_summary}
                    </h4>
                    
                    <div className="flex flex-wrap items-center gap-3 pt-2 text-[10px] font-bold uppercase tracking-widest border-t border-slate-700/20">
                      <span className="flex items-center text-emerald-400">
                        <MapPin className="w-3 h-3 mr-1" /> {cluster.canonical_locality || 'Unknown'}
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="flex items-center text-cyan-400">
                        <Crosshair className="w-3 h-3 mr-1" /> {cluster.department ? (DEPT_MAP[cluster.department] || cluster.department) : 'Unassigned'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
        
        {/* Right Column: Cluster Detail & Inspection */}
        <div className="lg:col-span-2">
          {!selectedClusterId ? (
             <div className="cluster-workspace-panel min-h-[520px] flex flex-col items-center justify-center p-12 text-center border-dashed border border-slate-700/50">
               <div className="w-20 h-20 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mb-6">
                 <Layers className="w-10 h-10 text-violet-400" />
               </div>
               <p className="text-xl font-bold text-slate-200 mb-2 uppercase tracking-wide">Select an Incident</p>
               <p className="text-sm text-slate-400 max-w-sm font-medium">Review duplicate civic complaints aggregated into a single actionable incident.</p>
             </div>
          ) : detailLoading && !clusterDetail ? (
             <div className="cluster-workspace-panel min-h-[520px] flex flex-col items-center justify-center p-12 text-slate-400">
               <RefreshCw className="w-10 h-10 animate-spin mb-4 text-violet-400" />
               <p className="text-sm font-bold uppercase tracking-widest">Loading Incident Intelligence...</p>
             </div>
          ) : clusterDetail ? (
            <div className="space-y-6">
              {/* Detail Header */}
              <div className="cluster-workspace-panel p-6 border-t-4 border-t-violet-500 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 opacity-5 pointer-events-none">
                  <Network className="w-48 h-48" />
                </div>
                
                <div className="flex justify-between items-start mb-4 relative z-10">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                       <span className="text-[10px] font-bold uppercase tracking-widest bg-violet-500/20 text-violet-400 px-3 py-1 rounded-full border border-violet-500/30">
                         CLUSTER {clusterDetail.cluster_id.split('-').pop()}
                       </span>
                       <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-widest ${clusterDetail.is_active ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}`}>
                         {clusterDetail.is_active ? 'ACTIVE' : 'RESOLVED'}
                       </span>
                    </div>
                    <h3 className="text-xl font-bold text-slate-100 mt-4 leading-relaxed">{clusterDetail.representative_summary}</h3>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 relative z-10 border-t border-slate-700/25 pt-6">
                   <div>
                     <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">Locality</p>
                     <p className="text-sm font-bold text-emerald-400">{clusterDetail.canonical_locality || 'Unknown'}</p>
                   </div>
                   <div>
                     <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">Ward</p>
                     <p className="text-sm font-bold text-slate-300">{clusterDetail.ward || 'Unknown'}</p>
                   </div>
                   <div className="md:col-span-2">
                     <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-1">Assigned Department</p>
                     <p className="text-sm font-bold text-cyan-400 bg-cyan-950/20 inline-block px-2.5 py-0.5 rounded border border-cyan-500/20">{clusterDetail.department ? (DEPT_MAP[clusterDetail.department] || clusterDetail.department) : 'Unassigned'}</p>
                   </div>
                </div>
              </div>
              
              {/* Member Complaints Timeline */}
              <div className="cluster-workspace-panel p-6">
                <div className="flex items-center justify-between mb-6">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-slate-300 flex items-center">
                    <FileText className="w-4 h-4 mr-2 text-violet-400" /> Member Complaints ({clusterDetail.members.length})
                  </h4>
                </div>
                
                <div className="space-y-4">
                  {clusterDetail.members.map((m) => (
                    <div key={m.complaint_id} className="cluster-member-card p-4 flex flex-col sm:flex-row gap-4 group">
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-[9px] font-bold text-slate-400 uppercase font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-700/40">
                            {m.complaint_id.split('-').pop()}
                          </span>
                          <span className="text-[9px] font-bold uppercase tracking-widest text-cyan-400">
                            Similarity: {((m.similarity_score || 0) * 100).toFixed(0)}%
                          </span>
                        </div>
                        <p className="text-sm text-slate-200 font-medium mb-3">{m.summary}</p>
                        
                        <div className="flex flex-wrap gap-2 text-[9px] font-bold uppercase tracking-widest text-slate-400">
                          <span className="px-2 py-1 bg-slate-800/80 rounded border border-slate-700/30">{m.channel}</span>
                          <span className="px-2 py-1 bg-slate-800/80 rounded border border-slate-700/30">{new Date(m.added_at).toLocaleString()}</span>
                        </div>
                      </div>

                      <div className="flex flex-col justify-between sm:items-end sm:w-48 border-t sm:border-t-0 sm:border-l border-slate-700/25 pt-3 sm:pt-0 sm:pl-4">
                        <button 
                          onClick={() => onSelectComplaint && onSelectComplaint(m.complaint_id)}
                          className="text-[9px] font-bold uppercase tracking-widest text-cyan-400 hover:text-cyan-300 flex items-center mb-3"
                        >
                          View Detail <ChevronRight className="w-3 h-3 ml-1" />
                        </button>
                        
                        {clusterDetail.members.length > 1 && (
                          <button 
                            onClick={() => handleRemoveMember(m.complaint_id)}
                            className="text-[9px] font-bold uppercase tracking-widest text-rose-400/80 hover:text-rose-400 flex items-center"
                          >
                            <XCircle className="w-3 h-3 mr-1" /> Remove (False Positive)
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Operator Notes / Resolution */}
              <div className="cluster-workspace-panel p-6 bg-slate-900/40">
                <h4 className="text-xs font-bold uppercase tracking-widest text-slate-300 flex items-center mb-4">
                  <Edit3 className="w-4 h-4 mr-2 text-indigo-400" /> Incident Audit Notes
                </h4>
                <div className="space-y-3">
                  <textarea
                    value={operatorNotes}
                    onChange={(e) => setOperatorNotes(e.target.value)}
                    placeholder="Document root causes, public updates, or internal routing decisions..."
                    className="w-full text-xs border border-slate-700/50 rounded-lg px-4 py-3 bg-slate-950/80 text-slate-200 focus:ring-1 focus:ring-violet-500 outline-none h-24 custom-scrollbar placeholder:text-slate-500"
                  />
                  <div className="flex justify-end">
                    <button 
                      onClick={handleSaveNotes}
                      disabled={detailLoading}
                      className="px-6 py-2 bg-slate-800 text-slate-200 font-bold uppercase tracking-widest text-[10px] rounded-lg border border-slate-700 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-50"
                    >
                      {detailLoading ? 'Saving...' : 'Save Notes'}
                    </button>
                  </div>
                </div>
              </div>

            </div>
          ) : null}
        </div>
        
      </div>
    </div>
  );
};
