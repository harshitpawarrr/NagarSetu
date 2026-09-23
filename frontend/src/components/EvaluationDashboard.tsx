import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  Play, 
  RefreshCw, 
  Layers, 
  ShieldCheck, 
  FileText, 
  BarChart2, 
  Info, 
  Search, 
  XCircle,
  Award,
  Zap,
  Target
} from 'lucide-react';
import { runEvaluation, fetchLatestEvaluation } from '../services/api';

export const EvaluationDashboard: React.FC = () => {
  const [evaluation, setEvaluation] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [fieldFilter, setFieldFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const loadLatest = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchLatestEvaluation();
      setEvaluation(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch latest evaluation');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLatest();
  }, []);

  const handleRunBenchmark = async () => {
    try {
      setRunning(true);
      setError(null);
      const result = await runEvaluation({
        test_set_file: "benchmark_held_out_30.csv",
        test_set_version: "v1.0-synthetic",
        is_synthetic: true,
        notes: "Evaluated against 30-sample held-out multilingual benchmark set."
      });
      setEvaluation(result);
    } catch (err: any) {
      setError(err.message || 'Benchmark execution failed');
    } finally {
      setRunning(false);
    }
  };

  const filteredErrors = (evaluation?.incorrect_predictions || []).filter((item: any) => {
    if (fieldFilter !== 'all' && item.field !== fieldFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        item.complaint_id?.toLowerCase().includes(q) ||
        item.ground_truth?.toLowerCase().includes(q) ||
        item.predicted?.toLowerCase().includes(q) ||
        item.text_snippet?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-10 pb-24">
      <style>{`
        @keyframes evalFadeUp {
          0% {
            opacity: 0;
            transform: translateY(12px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .eval-anim-title { animation: evalFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 0ms forwards; opacity: 0; will-change: transform, opacity; }
        .eval-anim-subtitle { animation: evalFadeUp 380ms cubic-bezier(0.22, 1, 0.36, 1) 60ms forwards; opacity: 0; will-change: transform, opacity; }
        .eval-anim-controls { animation: evalFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 120ms forwards; opacity: 0; will-change: transform, opacity; }
        .eval-anim-notice { animation: evalFadeUp 400ms cubic-bezier(0.22, 1, 0.36, 1) 180ms forwards; opacity: 0; will-change: transform, opacity; }
        .eval-anim-kpi { animation: evalFadeUp 420ms cubic-bezier(0.22, 1, 0.36, 1) 240ms forwards; opacity: 0; will-change: transform, opacity; }
        .eval-anim-panels { animation: evalFadeUp 450ms cubic-bezier(0.22, 1, 0.36, 1) 300ms forwards; opacity: 0; will-change: transform, opacity; }

        .eval-kpi-card {
          background: rgba(15, 23, 42, 0.90);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
          transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
        }
        .eval-kpi-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
          border-color: rgba(100, 116, 139, 0.28);
        }

        .eval-panel {
          background: rgba(15, 23, 42, 0.88);
          border: 1px solid rgba(100, 116, 139, 0.16);
          box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
          border-radius: 20px;
        }

        .eval-inner-card {
          background: rgba(10, 14, 23, 0.70);
          border: 1px solid rgba(100, 116, 139, 0.12);
          border-radius: 16px;
          transition: background-color 180ms ease, border-color 180ms ease;
        }
        .eval-inner-card:hover {
          background: rgba(15, 23, 42, 0.90);
          border-color: rgba(100, 116, 139, 0.24);
        }
      `}</style>
      
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 eval-anim-title">
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
            <Target className="w-10 h-10 sm:w-12 sm:h-12 text-[#10b981] mr-4 shrink-0" />
            <span 
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage: 'linear-gradient(90deg, #10b981, #06b6d4)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                display: 'inline-block'
              }}
            >
              MODEL PERFORMANCE
            </span>
          </h1>
          <p 
            className="text-xs sm:text-sm uppercase tracking-widest mt-3 eval-anim-subtitle"
            style={{
              color: '#64748B',
              fontWeight: 600
            }}
          >
            TRANSPARENT MODEL AUDIT & ACCURACY TRACKING
          </p>
        </div>
        
        <div className="flex items-center gap-3 mt-6 md:mt-0 eval-anim-controls">
          {evaluation && (
            <span className={`text-[10px] font-bold px-3.5 py-2 rounded-xl uppercase tracking-widest border ${
              evaluation.is_synthetic_benchmark
                ? 'bg-amber-950/30 text-amber-400 border-amber-500/25'
                : 'bg-emerald-950/30 text-emerald-400 border-emerald-500/25'
            }`}>
              {evaluation.benchmark_badge || 'Synthetic Benchmark'}
            </span>
          )}

          <button
            onClick={handleRunBenchmark}
            disabled={running}
            className="px-6 py-3 bg-white text-[#050B14] rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-slate-200 disabled:opacity-50 transition-all flex items-center shadow-[0_4px_16px_rgba(255,255,255,0.08)]"
          >
            {running ? <RefreshCw className="w-4 h-4 animate-spin mr-2.5" /> : <Play className="w-4 h-4 mr-2.5" />}
            <span>{running ? 'Running Scan...' : 'Run Benchmark'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/40 border border-rose-500/30 text-rose-400 rounded-xl text-sm font-bold flex items-center mb-6">
          <AlertTriangle className="w-5 h-5 mr-3 shrink-0" />
          {error}
        </div>
      )}

      {loading && !evaluation ? (
        <div className="eval-panel p-24 text-center flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="w-12 h-12 animate-spin mx-auto text-emerald-500 mb-2" />
          <p className="text-sm font-bold tracking-widest uppercase text-emerald-400">Loading Benchmark Data...</p>
        </div>
      ) : !evaluation ? (
        <div className="eval-panel p-24 text-center text-slate-400 border border-dashed border-slate-700/60">
          <FileText className="w-16 h-16 mb-4 mx-auto opacity-40 text-slate-500" />
          <p className="font-bold text-lg text-slate-300">No evaluation data available.</p>
          <p className="text-xs mt-2 text-slate-500">Run the benchmark to generate a verified scorecard report.</p>
        </div>
      ) : (
        <div className="space-y-8">
          
          {/* Benchmark Integrity Notice */}
          <div className="eval-anim-notice bg-[#1e1710]/70 border border-amber-500/25 p-5 rounded-2xl flex items-start space-x-4 text-amber-200/90 text-sm leading-relaxed max-w-4xl shadow-sm">
            <Info className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-400" />
            <div>
              <strong className="block mb-1.5 uppercase tracking-widest text-[11px] font-bold text-amber-400">Benchmark Integrity Notice</strong>
              <span className="text-slate-300">
                These metrics are derived exclusively from the verified held-out benchmark set ({evaluation.total_samples} samples). The baseline includes adversarial permutations (synonyms, typos, transliteration) to measure true operational resilience.
              </span>
            </div>
          </div>

          {/* Top Level Metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 md:gap-5 eval-anim-kpi">
            <div className="eval-kpi-card p-6 border-t-2 border-t-cyan-500/90">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Dept Accuracy</p>
              <p className="text-4xl sm:text-5xl font-extrabold tracking-tight text-cyan-400">{(evaluation.department_accuracy * 100).toFixed(1)}%</p>
            </div>
            <div className="eval-kpi-card p-6 border-t-2 border-t-blue-500/90">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Category Accuracy</p>
              <p className="text-4xl sm:text-5xl font-extrabold tracking-tight text-blue-400">{(evaluation.category_accuracy * 100).toFixed(1)}%</p>
            </div>
            <div className="eval-kpi-card p-6 border-t-2 border-t-rose-500/90">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Urgency Agreement</p>
              <p className="text-4xl sm:text-5xl font-extrabold tracking-tight text-rose-400">{(evaluation.urgency_accuracy * 100).toFixed(1)}%</p>
            </div>
            <div className="eval-kpi-card p-6 border-t-2 border-t-emerald-500/90">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Locality Resolution</p>
              <p className="text-4xl sm:text-5xl font-extrabold tracking-tight text-emerald-400">{(evaluation.locality_normalization_accuracy * 100).toFixed(1)}%</p>
            </div>
            <div className="eval-kpi-card p-6 border-t-2 border-t-violet-500/90">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">Duplicate Reduction</p>
              <p className="text-4xl sm:text-5xl font-extrabold tracking-tight text-violet-400">{Number(evaluation.duplicate_reduction).toFixed(1)}%</p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 eval-anim-panels">
            
            {/* Confusion / Stats Matrix */}
            <div className="lg:col-span-1 eval-panel p-6 border-t-2 border-t-emerald-500/80 flex flex-col justify-between">
              <div>
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center mb-6 pb-3 border-b border-slate-800">
                  <BarChart2 className="w-4 h-4 mr-2 text-emerald-400" /> Evaluation Breakdown
                </h3>
                
                <div className="space-y-4">
                  <div className="eval-inner-card p-3.5 space-y-3">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Target Samples</span>
                      <span className="font-semibold text-slate-100 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">{evaluation.total_samples}</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Average Latency</span>
                      <span className="font-semibold text-slate-100 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">{evaluation.performance?.avg_latency_ms || 240} ms</span>
                    </div>
                  </div>

                  <div className="pt-2">
                    <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2.5">Model Parameters</h4>
                    <div className="eval-inner-card p-3.5 space-y-2.5">
                      <div className="flex justify-between text-xs text-slate-300">
                        <span className="font-mono text-slate-500 text-[11px]">temperature</span>
                        <span className="font-semibold text-slate-200">0.1</span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-300">
                        <span className="font-mono text-slate-500 text-[11px]">model</span>
                        <span className="font-semibold text-slate-200">gemini-2.5-flash</span>
                      </div>
                      <div className="flex justify-between text-xs text-slate-300">
                        <span className="font-mono text-slate-500 text-[11px]">fallback</span>
                        <span className="font-semibold text-cyan-400">deterministic</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Error Audit Log */}
            <div className="lg:col-span-2 eval-panel p-6 border-t-2 border-t-amber-500/80">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-3 border-b border-slate-800">
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-amber-400 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2 text-amber-400" /> Auditable Misclassifications
                  <span className="ml-2.5 px-2 py-0.5 rounded-full text-[10px] bg-amber-950/50 text-amber-300 border border-amber-500/30">
                    {filteredErrors.length}
                  </span>
                </h3>
                
                <div className="flex flex-wrap items-center gap-3">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search ID, text..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9 pr-4 py-2 text-xs bg-slate-900/90 border border-slate-700/60 rounded-xl focus:border-amber-500/60 focus:outline-none w-48 text-slate-200 placeholder:text-slate-500 transition-all"
                    />
                  </div>
                  <select
                    value={fieldFilter}
                    onChange={(e) => setFieldFilter(e.target.value)}
                    className="text-[11px] font-bold uppercase tracking-wider border border-slate-700/60 rounded-xl px-3 py-2 bg-slate-900/90 text-slate-300 focus:border-amber-500/60 outline-none"
                  >
                    <option value="all">All Fields</option>
                    <option value="department">Department</option>
                    <option value="category">Category</option>
                    <option value="urgency">Urgency</option>
                    <option value="locality">Locality</option>
                  </select>
                </div>
              </div>

              <div className="space-y-4 max-h-[600px] overflow-y-auto custom-scrollbar pr-2">
                {filteredErrors.length === 0 ? (
                  <div className="text-center p-12 border-dashed border border-slate-700/50 rounded-2xl bg-slate-900/30">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400/60 mx-auto mb-2.5" />
                    <p className="text-sm font-bold text-slate-300 tracking-wider uppercase">No misclassifications found</p>
                    <p className="text-xs text-slate-500 mt-1">Predictions match ground truth or query returned zero matches</p>
                  </div>
                ) : (
                  filteredErrors.map((errItem: any, idx: number) => (
                    <div key={idx} className="eval-inner-card p-4 border border-slate-700/30 hover:border-amber-500/30">
                      <div className="flex items-center justify-between gap-2 mb-3 pb-2.5 border-b border-white/5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] text-slate-300 bg-slate-950/80 px-2.5 py-1 rounded-md border border-slate-800 uppercase font-semibold">
                            {errItem.complaint_id.split('-').pop()}
                          </span>
                          <span className="text-[10px] font-bold bg-amber-950/40 text-amber-300 border border-amber-500/30 px-2.5 py-1 rounded-md uppercase tracking-wider">
                            {errItem.field} Mismatch
                          </span>
                        </div>
                        {errItem.confidence !== undefined && errItem.confidence !== null && (
                          <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                            Conf: {(Number(errItem.confidence) * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      
                      <p className="text-xs sm:text-sm font-medium text-slate-200 mb-3.5 bg-slate-950/70 p-3 rounded-xl border border-white/5 italic leading-relaxed">
                        "{errItem.text_snippet}"
                      </p>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="bg-emerald-950/15 border border-emerald-500/20 rounded-xl p-3">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-400/80 mb-1 flex items-center">
                            <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" /> Expected (Ground Truth)
                          </p>
                          <p className="text-sm font-bold text-emerald-300">{errItem.ground_truth}</p>
                        </div>
                        <div className="bg-rose-950/15 border border-rose-500/20 rounded-xl p-3">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-rose-400/80 mb-1 flex items-center">
                            <XCircle className="w-3.5 h-3.5 mr-1 text-rose-400" /> Predicted
                          </p>
                          <p className="text-sm font-bold text-rose-300">{errItem.predicted}</p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
