import React, { useEffect, useState } from 'react';
import { 
  Network, 
  AlertTriangle, 
  ArrowRight,
  Activity,
  Zap,
  Target,
  ShieldCheck,
  Server
} from 'lucide-react';

interface DashboardProps {
  onNavigate: (route: string) => void;
}

import { useScrollReveal } from '../hooks/useScrollReveal';

const RevealSection: React.FC<{ children: React.ReactNode; className?: string; delay?: number }> = ({ children, className = '', delay = 0 }) => {
  const { ref, isVisible } = useScrollReveal();
  return (
    <section
      ref={ref}
      className={`${className} transition-all duration-[800ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </section>
  );
};

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  return (
    <div className="space-y-24 pb-24">
      
      {/* HERO SECTION - Editorial layout */}
      <section className="relative pt-12 pb-20 min-h-[85vh] flex items-center bg-[#080B10] overflow-hidden border border-white/5 rounded-3xl shadow-2xl" style={{ backgroundImage: 'radial-gradient(circle at 75% 50%, rgba(40,199,217,0.03) 0%, transparent 60%), radial-gradient(circle at 25% 30%, rgba(255,255,255,0.02) 0%, transparent 50%)' }}>
        
        {/* Subtle architectural grid background */}
        <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" style={{ backgroundImage: "linear-gradient(to right, rgba(255,255,255,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.05) 1px, transparent 1px)", backgroundSize: "64px 64px" }}></div>
        
        <div className="w-full grid grid-cols-1 lg:grid-cols-[minmax(0,1.15fr)_minmax(380px,0.85fr)] gap-8 xl:gap-12 z-10 px-6 sm:px-10 lg:px-12 items-center">
          
          {/* LEFT CONTENT */}
          <div className="flex flex-col items-start pt-6 lg:pt-0 relative z-20 w-full">
            <div 
              className="inline-flex items-center space-x-3 px-4 py-2 bg-emerald-500/10 text-[10px] font-bold uppercase tracking-widest text-emerald-400 mb-10 border border-emerald-500/20 rounded-full animate-slide-up"
              style={{ animationDelay: '50ms' }}
            >
              <Activity className="w-3.5 h-3.5 mr-2" /> System Online • Municipal Data Sync Active
            </div>
            
            <h1 
              className="font-black flex flex-col w-full max-w-[680px] mb-8 relative z-30"
              style={{
                fontSize: 'clamp(54px, 5vw, 82px)',
                lineHeight: 0.91,
                letterSpacing: '-0.04em'
              }}
            >
              <span className="text-[#F5F7FA] hero-line-anim" style={{ animationDelay: '60ms' }}>CIVIC</span>
              <span className="text-[#F5F7FA] hero-line-anim" style={{ animationDelay: '130ms' }}>OPERATIONS</span>
              <span 
                className="hero-line-anim bg-clip-text text-transparent"
                style={{ 
                  backgroundImage: 'linear-gradient(90deg, #22c7d8, #3b82f6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  animationDelay: '200ms'
                }}
              >
                INTELLIGENCE
              </span>
            </h1>
            
            <p 
              className="text-base sm:text-lg md:text-xl text-[#AAB4C2] font-medium max-w-[560px] leading-relaxed tracking-normal mb-12 animate-slide-up"
              style={{ animationDelay: '250ms' }}
            >
              Turn fragmented citizen signals into structured incidents, explainable routing, and accountable municipal action.
            </p>

            <button 
              onClick={() => onNavigate('triage')}
              className="group px-8 py-4 bg-[#28C7D9] text-white font-bold uppercase tracking-widest text-xs rounded-lg hover:bg-[#34d8eb] hover:-translate-y-[2px] active:scale-[0.98] transition-all duration-300 flex items-center shadow-[0_4px_20px_rgba(40,199,217,0.15)] hover:shadow-[0_8px_30px_rgba(40,199,217,0.25)] animate-slide-up"
              style={{ animationDelay: '300ms' }}
            >
              <span>Open Triage Desk</span>
              <ArrowRight className="w-4 h-4 ml-4 group-hover:translate-x-[4px] transition-transform" />
            </button>
          </div>

          {/* RIGHT VISUAL */}
          <div className="w-full h-[480px] lg:h-[520px] xl:h-[560px] max-w-[500px] justify-self-center lg:justify-self-end relative rounded-2xl overflow-hidden bg-[#0D1118] border border-[rgba(120,140,170,0.16)] shadow-[0_12px_35px_rgba(0,0,0,0.12)] animate-slide-up flex items-center justify-center opacity-85 z-10" style={{ animationDelay: '350ms' }}>
            
            {/* Dark panel internal grid */}
            <div className="absolute inset-0 opacity-[0.15]" style={{ backgroundImage: "linear-gradient(to right, rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.1) 1px, transparent 1px)", backgroundSize: "40px 40px" }}></div>
            
            {/* Architectural Data Visualization */}
            <div className="relative w-[500px] h-[500px]">
               {/* Pathways */}
               <svg className="absolute inset-0 w-full h-full" viewBox="0 0 500 500">
                  <g strokeWidth="1" fill="none">
                     <path d="M 50 150 L 150 250" className="stroke-slate-500/40" />
                     <path d="M 50 350 L 150 250" className="stroke-slate-500/40" />
                     <path d="M 150 250 L 300 250" className="stroke-slate-400/60" />
                     <path d="M 300 250 L 420 150" className="stroke-slate-500/40" />
                     <path d="M 300 250 L 420 350" className="stroke-slate-500/40" />
                     <path d="M 300 250 L 420 250" className="stroke-slate-500/40" />
                  </g>
               </svg>
               
               {/* 1. Signals (Input) */}
               <div className="absolute top-[135px] left-[35px] w-8 h-8 bg-[#111823] border border-slate-700/50 flex items-center justify-center rounded-sm">
                 <div className="w-1.5 h-1.5 bg-[#AAB4C2] opacity-80 animate-pulse"></div>
                 <span className="absolute -left-16 top-2 text-[8px] font-mono text-[#748196] uppercase tracking-widest">Signals</span>
               </div>
               <div className="absolute top-[335px] left-[35px] w-8 h-8 bg-[#111823] border border-slate-700/50 flex items-center justify-center rounded-sm">
                 <div className="w-1.5 h-1.5 bg-[#AAB4C2] opacity-80 animate-pulse" style={{ animationDelay: '1s' }}></div>
               </div>

               {/* 2. Ward Marker (Aggregation) */}
               <div className="absolute top-[225px] left-[125px] w-12 h-12 bg-[#080B10] border border-[#748196]/30 flex items-center justify-center shadow-lg rounded-sm">
                 <div className="w-3 h-3 border border-[#AAB4C2] rotate-45 opacity-60"></div>
                 <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-[8px] font-mono text-[#748196] uppercase tracking-widest whitespace-nowrap">Ward Node</span>
               </div>

               {/* 3. AI Triage Engine (Processing) */}
               <div className="absolute top-[210px] left-[260px] w-20 h-20 bg-[#080B10] border border-[#28C7D9]/40 flex items-center justify-center shadow-[0_0_20px_rgba(40,199,217,0.05)] rounded-sm">
                 <div className="w-8 h-8 border border-[#28C7D9]/30 flex items-center justify-center">
                    <div className="w-2 h-2 bg-[#28C7D9] animate-pulse"></div>
                 </div>
                 <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[9px] font-bold font-mono text-[#28C7D9] uppercase tracking-widest whitespace-nowrap">Triage Engine</span>
               </div>

               {/* 4. Departments (Output) */}
               <div className="absolute top-[135px] left-[405px] w-8 h-8 bg-[#111823] border border-slate-700/50 flex items-center justify-center rounded-sm">
                 <div className="w-1.5 h-1.5 bg-blue-400 opacity-80"></div>
                 <span className="absolute -right-16 top-2 text-[8px] font-mono text-[#748196] uppercase tracking-widest">Dept 1</span>
               </div>
               <div className="absolute top-[235px] left-[405px] w-8 h-8 bg-[#111823] border border-slate-700/50 flex items-center justify-center rounded-sm">
                 <div className="w-1.5 h-1.5 bg-emerald-400 opacity-80"></div>
                 <span className="absolute -right-16 top-2 text-[8px] font-mono text-[#748196] uppercase tracking-widest">Dept 2</span>
               </div>
               <div className="absolute top-[335px] left-[405px] w-8 h-8 bg-[#111823] border border-slate-700/50 flex items-center justify-center rounded-sm">
                 <div className="w-1.5 h-1.5 bg-rose-400 opacity-80"></div>
                 <span className="absolute -right-16 top-2 text-[8px] font-mono text-[#748196] uppercase tracking-widest">Dept 3</span>
               </div>

               {/* Data Packets Ambient Motion & Scoped Animations */}
               <style>{`
                 @keyframes heroHeadingFade {
                   0% {
                     opacity: 0;
                     transform: translateY(14px);
                   }
                   100% {
                     opacity: 1;
                     transform: translateY(0);
                   }
                 }
                 .hero-line-anim {
                   opacity: 0;
                   display: block;
                   animation: heroHeadingFade 580ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
                   will-change: transform, opacity;
                 }
                 @keyframes movePacket1 { 0% { transform: translate(50px, 150px); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { transform: translate(150px, 250px); opacity: 0; } }
                 @keyframes movePacket2 { 0% { transform: translate(150px, 250px); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { transform: translate(300px, 250px); opacity: 0; } }
                 @keyframes movePacket3 { 0% { transform: translate(300px, 250px); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { transform: translate(420px, 150px); opacity: 0; } }
                 .packet-1 { animation: movePacket1 3s linear infinite; }
                 .packet-2 { animation: movePacket2 2.5s linear infinite 1s; }
                 .packet-3 { animation: movePacket3 2.5s linear infinite 2s; }
               `}</style>
               <div className="absolute top-0 left-0 w-1.5 h-1.5 bg-[#AAB4C2] rounded-full packet-1"></div>
               <div className="absolute top-0 left-0 w-1.5 h-1.5 bg-[#28C7D9] rounded-full packet-2 shadow-[0_0_8px_#28C7D9]"></div>
               <div className="absolute top-0 left-0 w-1.5 h-1.5 bg-blue-400 rounded-full packet-3 shadow-[0_0_8px_#60A5FA]"></div>
            </div>
          </div>
        </div>
      </section>

      {/* QUICK METRICS */}
      <RevealSection>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
          {[
            { label: "Total Intake", value: "1,248", icon: Server, color: "text-blue-400", border: "border-blue-500/30", delay: 0 },
            { label: "Active Clusters", value: "34", icon: Network, color: "text-violet-400", border: "border-violet-500/30", delay: 100 },
            { label: "Needs Review", value: "156", icon: Target, color: "text-amber-400", border: "border-amber-500/30", delay: 200 },
            { label: "Critical Cases", value: "12", icon: AlertTriangle, color: "text-rose-400", border: "border-rose-500/30", delay: 300 },
          ].map((m, i) => (
            <div key={i} className={`glass-card p-6 border-l-2 ${m.border} card-hover`} style={{ transitionDelay: `${m.delay}ms` }}>
              <div className="flex justify-between items-start mb-6">
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{m.label}</span>
                <m.icon className={`w-4 h-4 ${m.color}`} />
              </div>
              <p className={`text-4xl font-bold tracking-tight ${m.color}`}>{m.value}</p>
            </div>
          ))}
        </div>
      </RevealSection>

      {/* HOW NAGARSETU WORKS (Editorial Story) */}
      <RevealSection className="py-20 border-y border-white/5 relative">
         <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500 mb-16">How NagarSetu Works</h2>
         <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-6">
            {[
               { num: "01", title: "INTAKE", desc: "Ingest multi-channel civic signals from all endpoints." },
               { num: "02", title: "UNDERSTAND", desc: "Multimodal AI extracts intent, hazard, and sentiment." },
               { num: "03", title: "CLASSIFY", desc: "Determine specific department & resolution urgency." },
               { num: "04", title: "LOCALIZE", desc: "Map precisely to strict municipal ward boundaries." },
               { num: "05", title: "CLUSTER", desc: "Group duplicate complaints into single incidents." },
               { num: "06", title: "REVIEW", desc: "Human operator verifies intelligence via triage desk." },
               { num: "07", title: "ACCOUNT", desc: "Track departmental resolution SLAs." }
            ].map((step, idx) => (
               <div key={idx} className={`group cursor-default relative animate-slide-up stagger-${(idx % 6) + 1}`}>
                  <div className="text-4xl font-bold text-slate-800 group-hover:text-cyan-400 transition-colors duration-300 mb-4">{step.num}</div>
                  <div className="w-full h-px bg-slate-800 mb-6 relative overflow-hidden">
                     <div className="absolute inset-y-0 left-0 bg-cyan-400 w-0 group-hover:w-full transition-all duration-[600ms]"></div>
                  </div>
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-300 mb-3">{step.title}</h3>
                  <p className="text-[11px] text-slate-500 group-hover:text-slate-300 transition-colors leading-relaxed opacity-60 group-hover:opacity-100">{step.desc}</p>
               </div>
            ))}
         </div>
      </RevealSection>

      <RevealSection>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* NEEDS ATTENTION */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center mb-6">
              <Zap className="w-4 h-4 mr-2 text-rose-500" /> Needs Attention
            </h2>
            
            <div className="space-y-3">
              <div className="inner-panel p-5 cursor-pointer border border-rose-500/20 card-hover" onClick={() => onNavigate('triage')}>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-bold text-rose-300">Critical Hazards</span>
                  <span className="text-2xl font-bold text-rose-500">12</span>
                </div>
              </div>
              
              <div className="inner-panel p-5 cursor-pointer border border-amber-500/20 card-hover" onClick={() => onNavigate('triage')}>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-bold text-amber-300">Low Confidence Routing</span>
                  <span className="text-2xl font-bold text-amber-500">47</span>
                </div>
              </div>

              <div className="inner-panel p-5 cursor-pointer card-hover" onClick={() => onNavigate('clusters')}>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-bold text-slate-300">Emerging Clusters</span>
                  <span className="text-2xl font-bold text-violet-400">8</span>
                </div>
              </div>
            </div>
          </div>

          {/* DEPARTMENT PULSE */}
          <div className="lg:col-span-2 space-y-4">
            <h2 className="text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center mb-6">
              <Activity className="w-4 h-4 mr-2 text-cyan-500" /> Department Pulse
            </h2>
            
            <div className="glass-panel p-8">
              <div className="space-y-8">
                {[
                  { name: "Roads & Infrastructure", pending: 45, critical: 3, w: "w-[80%]" },
                  { name: "Water & Sewerage", pending: 82, critical: 7, w: "w-[100%]" },
                  { name: "Sanitation", pending: 24, critical: 0, w: "w-[40%]" },
                  { name: "Electrical Services", pending: 31, critical: 2, w: "w-[60%]" },
                  { name: "Public Health", pending: 15, critical: 0, w: "w-[25%]" }
                ].map((d, i) => (
                  <div key={i} className="relative group">
                    <div className="flex justify-between items-end mb-2">
                      <span className="text-xs font-bold uppercase tracking-widest text-slate-300 group-hover:text-white transition-colors">{d.name}</span>
                      <span className="text-xs font-mono text-slate-500">{d.pending} Active</span>
                    </div>
                    <div className="h-1.5 w-full bg-[#05080E] rounded-full overflow-hidden flex">
                      <div className={`h-full bg-gradient-to-r from-cyan-600 to-blue-500 ${d.w} relative`}>
                        {d.critical > 0 && (
                          <div className="absolute right-0 top-0 bottom-0 bg-rose-500" style={{width: `${(d.critical/d.pending)*100}%`}}></div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </RevealSection>

    </div>
  );
};
