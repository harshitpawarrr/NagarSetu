import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  ShieldAlert, 
  Settings, 
  Save, 
  Info,
  Mic,
  Camera,
  MessageSquare,
  ShieldCheck,
  BrainCircuit,
  ArrowRight,
  GitMerge,
  UserCheck,
  MapPin
} from 'lucide-react';
import { 
  fetchComplaint, 
  fetchTriage, 
  fetchAuditTrail, 
  fetchAcknowledgement,
  editAcknowledgement,
  reviewComplaint 
} from '../services/api';
import { CanonicalComplaint } from '../types/complaint';

interface DetailProps {
  complaintId: string;
  onBack: () => void;
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

export const ComplaintDetailWorkbench: React.FC<DetailProps> = ({ complaintId, onBack }) => {
  const [complaint, setComplaint] = useState<any>(null);
  const [triage, setTriage] = useState<CanonicalComplaint | null>(null);
  const [audit, setAudit] = useState<any[]>([]);
  const [ack, setAck] = useState<any>(null);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  
  const [draftContent, setDraftContent] = useState('');
  const [operatorNotes, setOperatorNotes] = useState('');
  const [overrideDept, setOverrideDept] = useState('');

  const loadAll = async () => {
    try {
      setLoading(true);
      setError(null);
      const [cData, tData, aData, ackData] = await Promise.all([
        fetchComplaint(complaintId),
        fetchTriage(complaintId).catch(() => null),
        fetchAuditTrail(complaintId).catch(() => []),
        fetchAcknowledgement(complaintId).catch(() => null)
      ]);
      setComplaint(cData);
      setTriage(tData);
      setAudit(aData);
      setAck(ackData);
      
      if (ackData?.draft_text) setDraftContent(ackData.draft_text);
      if (tData?.department) setOverrideDept(tData.department);
      
    } catch (err: any) {
      setError(err.message || 'Failed to load details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, [complaintId]);

  const handleApprove = async () => {
    try {
      setSaving(true);
      if (draftContent !== ack?.draft_text) {
        await editAcknowledgement(complaintId, { draft_text: draftContent, operator_id: 'OP-ZONE-42' } as any);
      }
      await reviewComplaint(complaintId, {
        action: 'approve',
        operator_id: 'OP-ZONE-42',
        notes: operatorNotes || 'Approved automatically.',
        department: overrideDept !== triage?.department ? overrideDept : undefined
      });
      await loadAll();
    } catch (err: any) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleFlag = async () => {
    try {
      setSaving(true);
      await reviewComplaint(complaintId, {
        action: 'flag_manual_review',
        operator_id: 'OP-ZONE-42',
        reason: 'MANUAL FLAG',
        notes: operatorNotes || 'Needs further investigation.'
      });
      await loadAll();
    } catch (err: any) {
      alert(`Flag failed: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="glass-panel p-24 flex flex-col items-center justify-center space-y-4 animate-in fade-in">
        <BrainCircuit className="w-12 h-12 animate-pulse text-cyan-500" />
        <p className="text-sm font-bold tracking-widest uppercase text-slate-400">Loading civic intelligence...</p>
      </div>
    );
  }

  if (error || !complaint) {
    return (
      <div className="glass-panel p-16 text-center animate-in fade-in">
        <AlertTriangle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
        <h2 className="text-lg font-bold text-rose-400 mb-2">Retrieval Failed</h2>
        <p className="text-sm text-slate-400 mb-6">{error}</p>
        <button onClick={onBack} className="px-6 py-2 bg-slate-800 text-slate-200 text-xs font-bold uppercase tracking-widest rounded-lg hover:bg-slate-700 transition-colors">
          Return to Queue
        </button>
      </div>
    );
  }

  const raw = complaint.raw || complaint;
  const isApproved = triage?.processing_status === 'OPERATOR_APPROVED';
  
  return (
    <div className="space-y-8 pb-24">
      
      {/* Top Header */}
      <div className="flex items-center space-x-4 mb-8">
        <button 
          onClick={onBack}
          className="p-2.5 bg-slate-900/50 hover:bg-slate-800 border border-white/5 rounded-xl transition-all shadow-sm group"
        >
          <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-cyan-400 transition-colors" />
        </button>
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-100 uppercase font-mono">
            {complaintId}
          </h2>
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-0.5">
            Ingested {new Date(raw.created_at).toLocaleString()} • {raw.channel}
          </p>
        </div>
        <div className="ml-auto">
          {isApproved ? (
            <span className="inline-flex items-center px-4 py-1.5 text-xs uppercase font-bold tracking-widest text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 rounded-lg shadow-[0_0_15px_rgba(16,185,129,0.15)]">
              <CheckCircle2 className="w-4 h-4 mr-2" /> Dispatched
            </span>
          ) : (
            <span className="inline-flex items-center px-4 py-1.5 text-xs uppercase font-bold tracking-widest text-cyan-400 bg-cyan-950/30 border border-cyan-500/30 rounded-lg shadow-[0_0_15px_rgba(6,182,212,0.15)]">
              <Clock className="w-4 h-4 mr-2" /> Action Required
            </span>
          )}
        </div>
      </div>

      {/* 2-Column Split: Signal vs AI Interpretation */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        
        {/* LEFT COLUMN: ORIGINAL SIGNAL */}
        <div className="glass-panel p-8 border-t-2 border-t-slate-500 animate-slide-up stagger-2 h-full flex flex-col">
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center mb-6">
            <MessageSquare className="w-4 h-4 mr-2" /> Original Signal
          </h3>
          
          <div className="inner-panel p-6 mb-8 flex-1">
            <p className="text-xl text-slate-100 leading-relaxed font-medium">"{raw.original_text || raw.text}"</p>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-5">
              <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-1">Source Channel</p>
              <p className="text-sm font-bold text-slate-200">{raw.original_channel || raw.channel}</p>
            </div>
            <div className="glass-card p-5">
              <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-1">Reported Language</p>
              <p className="text-sm font-bold text-slate-200 uppercase">{raw.language || 'UNKNOWN'}</p>
            </div>
          </div>
          
          {/* Multimodal Elements */}
          {raw.attachments && raw.attachments.length > 0 && (
            <div className="mt-8 pt-8 border-t border-white/5 space-y-4">
              <h4 className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Multimodal Evidence</h4>
              {raw.attachments.map((att: any, i: number) => (
                <div key={i} className="flex items-start space-x-4 p-5 rounded-xl bg-[#05080E] border border-white/5">
                  <div className="p-3 bg-slate-900 rounded-lg text-cyan-400">
                    {att.modality === 'VOICE' ? <Mic className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">{att.modality}</p>
                    {att.transcription ? (
                      <p className="text-sm text-slate-300 italic">"{att.transcription}"</p>
                    ) : att.caption ? (
                      <p className="text-sm text-slate-300 italic">"{att.caption}"</p>
                    ) : (
                      <p className="text-xs text-slate-600 font-mono">{att.file_uri}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* RIGHT COLUMN: AI INTERPRETATION */}
        <div className="glass-panel p-8 border-t-2 border-t-cyan-500 relative overflow-hidden animate-slide-up stagger-3 h-full flex flex-col">
          <div className="absolute top-0 right-0 p-8 opacity-[0.03]">
            <BrainCircuit className="w-48 h-48" />
          </div>
          
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-cyan-500 flex items-center mb-8">
            <BrainCircuit className="w-4 h-4 mr-2" /> AI Interpretation
          </h3>
          
          {triage ? (
            <div className="space-y-10 relative z-10 flex-1">
              <div>
                <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-3">Predicted Classification</p>
                <div className="flex flex-col gap-4">
                  <div className="flex items-center space-x-4">
                    <span className="text-[10px] font-bold text-slate-500 w-24">DEPARTMENT</span>
                    <span className="px-4 py-2 bg-[#05080E] border border-blue-500/30 text-blue-400 text-xs font-bold uppercase tracking-wider rounded-lg shadow-sm w-full">
                      {DEPT_MAP[triage.department] || triage.department}
                    </span>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className="text-[10px] font-bold text-slate-500 w-24">CATEGORY</span>
                    <span className="px-4 py-2 bg-[#05080E] border border-indigo-500/30 text-indigo-400 text-xs font-bold uppercase tracking-wider rounded-lg shadow-sm w-full">
                      {triage.category}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-3">Locality Extraction</p>
                <div className="glass-card p-5">
                  <div className="flex items-center space-x-3 mb-2">
                    <MapPin className="w-4 h-4 text-cyan-400" />
                    <span className="text-sm font-bold text-slate-200">{triage.normalized_locality || 'Unknown Locality'}</span>
                  </div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest pl-7">
                    {triage.ward ? `${triage.ward} • ${triage.zone}` : 'Unmapped Ward'}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500 italic">Triage record not found.</p>
          )}
        </div>
      </div>

      {/* FULL WIDTH SECTIONS BELOW */}
      {triage && (
        <div className="space-y-8 animate-slide-up stagger-4">
          
          {/* ROUTING EVIDENCE */}
          <div className="glass-panel p-8 border-l-4 border-l-cyan-500">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-6">Routing Evidence</h3>
            <div className="flex flex-col md:flex-row md:items-center space-y-4 md:space-y-0 md:space-x-6">
              <div className="flex-1 bg-slate-900 border border-white/5 rounded-xl px-5 py-4 text-sm text-slate-300 font-mono">
                {triage.routing_evidence || "No evidence extracted"}
              </div>
              <div className="flex items-center justify-center">
                <ArrowRight className="w-5 h-5 text-slate-600 rotate-90 md:rotate-0 hidden md:block" />
              </div>
              <div className="bg-[#05080E] border border-cyan-500/30 rounded-xl px-6 py-4 flex flex-col items-center justify-center min-w-[160px]">
                <p className="text-2xl font-bold text-cyan-400">{(triage.routing_confidence * 100).toFixed(1)}%</p>
                <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mt-1">Confidence</p>
              </div>
            </div>
          </div>

          {/* URGENCY */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className={`col-span-1 md:col-span-3 glass-panel p-8 border-l-4 ${
              triage.urgency === 'CRITICAL' ? 'border-l-rose-500' :
              triage.urgency === 'HIGH' ? 'border-l-amber-500' : 'border-l-slate-500'
            }`}>
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">Urgency Assessment</h3>
                  <p className="text-2xl font-bold text-slate-200">{triage.urgency}</p>
                </div>
                <div className="bg-[#05080E] rounded-xl border border-white/5 p-4 text-sm text-slate-400 italic max-w-lg text-right">
                  "{triage.urgency_reason}"
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass-card p-4">
                  <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest mb-3">
                    <span className="text-slate-400">Public Safety</span>
                    <span className="text-slate-300">{(triage.urgency_score * 40).toFixed(0)}/40</span>
                  </div>
                  <div className="h-1.5 w-full bg-[#05080E] rounded-full overflow-hidden">
                    <div className="h-full bg-rose-500" style={{ width: `${Math.min(100, triage.urgency_score * 100)}%` }}></div>
                  </div>
                </div>
                <div className="glass-card p-4">
                  <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest mb-3">
                    <span className="text-slate-400">Service Outage</span>
                    <span className="text-slate-300">{(triage.urgency_score * 30).toFixed(0)}/30</span>
                  </div>
                  <div className="h-1.5 w-full bg-[#05080E] rounded-full overflow-hidden">
                    <div className="h-full bg-amber-500" style={{ width: `${Math.min(100, triage.urgency_score * 80)}%` }}></div>
                  </div>
                </div>
                <div className="glass-card p-4">
                  <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest mb-3">
                    <span className="text-slate-400">Duration</span>
                    <span className="text-slate-300">{(triage.urgency_score * 30).toFixed(0)}/30</span>
                  </div>
                  <div className="h-1.5 w-full bg-[#05080E] rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: `${Math.min(100, triage.urgency_score * 60)}%` }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* INCIDENT RELATIONSHIP (Clustering) */}
          {triage.duplicate_cluster_id && (
            <div className="glass-panel p-8 border-l-4 border-l-violet-500">
               <h3 className="text-[10px] font-bold uppercase tracking-widest text-violet-400 flex items-center mb-6">
                <GitMerge className="w-4 h-4 mr-2" /> Incident Relationship
              </h3>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-slate-300 font-medium mb-1">Part of larger incident cluster</p>
                  <p className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">{triage.duplicate_cluster_id}</p>
                </div>
                <div className="px-4 py-2 bg-violet-950/30 text-violet-400 border border-violet-500/30 rounded-lg text-xs font-bold uppercase tracking-widest">
                  View Incident
                </div>
              </div>
            </div>
          )}

          {/* OPERATOR DECISION */}
          <div className="glass-panel p-8 border-t-2 border-t-emerald-500 bg-emerald-950/5">
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-emerald-500 flex items-center mb-6">
              <ShieldCheck className="w-4 h-4 mr-2" /> Operator Decision
            </h3>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div>
                  <label className="block text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-3">Override Department</label>
                  <select 
                    value={overrideDept} 
                    onChange={(e) => setOverrideDept(e.target.value)}
                    disabled={isApproved || saving}
                    className="w-full text-sm border border-white/10 rounded-xl px-4 py-3 bg-[#05080E] text-slate-200 focus:ring-1 focus:ring-emerald-500 outline-none disabled:opacity-50 transition-all hover:border-white/20"
                  >
                    <option value="">-- No Override (Keep AI Prediction) --</option>
                    {Object.entries(DEPT_MAP).map(([code, name]) => (
                      <option key={code} value={code}>{name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-3">Operator Notes (Internal Audit)</label>
                  <input 
                    type="text" 
                    value={operatorNotes}
                    onChange={(e) => setOperatorNotes(e.target.value)}
                    disabled={isApproved || saving}
                    placeholder="E.g., Escalated to supervisor due to severity..."
                    className="w-full text-sm border border-white/10 rounded-xl px-4 py-3 bg-[#05080E] text-slate-300 focus:ring-1 focus:ring-emerald-500 outline-none disabled:opacity-50 transition-all hover:border-white/20"
                  />
                </div>
              </div>

              <div className="space-y-6">
                <div>
                  <label className="block text-[9px] font-bold uppercase tracking-widest text-slate-500 mb-3">Citizen Acknowledgement Draft</label>
                  <textarea 
                    value={draftContent}
                    onChange={(e) => setDraftContent(e.target.value)}
                    disabled={isApproved || saving}
                    className="w-full text-sm border border-white/10 rounded-xl px-5 py-4 bg-[#05080E] text-slate-300 focus:ring-1 focus:ring-emerald-500 outline-none h-32 custom-scrollbar disabled:opacity-50 transition-all hover:border-white/20"
                    placeholder="Draft SMS/Email to citizen..."
                  />
                </div>
              </div>
            </div>

            {!isApproved && (
              <div className="flex flex-col sm:flex-row items-center gap-4 pt-8 mt-8 border-t border-white/5">
                <button 
                  onClick={handleApprove}
                  disabled={saving}
                  className="w-full sm:w-auto px-8 py-4 bg-emerald-500 text-white rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-emerald-600 disabled:opacity-50 transition-all flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.2)]"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" /> Approve & Dispatch
                </button>
                <button 
                  onClick={handleFlag}
                  disabled={saving}
                  className="w-full sm:w-auto px-8 py-4 bg-transparent text-rose-400 border border-rose-500/30 rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-rose-500/10 disabled:opacity-50 transition-all flex items-center justify-center"
                >
                  <AlertTriangle className="w-4 h-4 mr-2" /> Flag for Review
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Audit Trail - Placed at bottom */}
      <div className="glass-panel p-8 border-t-2 border-t-slate-700 animate-slide-up stagger-5">
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center mb-6">
          <UserCheck className="w-4 h-4 mr-2" /> Action History
        </h3>
        <div className="space-y-6">
          {audit.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No human interventions recorded.</p>
          ) : (
            audit.map((a, i) => (
              <div key={i} className="relative pl-6 border-l border-white/10 pb-6 last:pb-0">
                <div className="absolute w-2.5 h-2.5 bg-slate-600 rounded-full -left-[5px] top-1"></div>
                <p className="text-sm font-bold text-slate-200">{a.action} <span className="text-slate-500 font-normal">by {a.operator_id}</span></p>
                <p className="text-[9px] uppercase tracking-widest text-slate-500 mt-1">{new Date(a.timestamp).toLocaleString()}</p>
                {a.notes && <p className="text-xs text-emerald-400 mt-3 p-3 bg-emerald-950/20 rounded-lg border border-emerald-500/10 italic">"{a.notes}"</p>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
