import React, { useState, useEffect } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  X,
  Database,
  Users,
  Speech,
  Cpu,
  Workflow,
  GitBranch,
  Box,
  ShieldCheck,
  Zap,
  Factory,
  Microscope,
  Code2,
  Search,
  PenTool,
  Monitor,
  Activity,
  FileText,
  Layers,
  Boxes
} from 'lucide-react';

interface PresentationProps {
  onClose: () => void;
}

// NOTE ON FIXES:
// This environment renders Tailwind with a fixed, precompiled stylesheet — there is
// no JIT compiler available, so arbitrary bracket-value classes like `h-[400px]`,
// `top-[30%]`, `backdrop-blur-[2px]` etc. are silently dropped (they never make it
// into the stylesheet). That was the root cause of almost every layout bug in the
// original file: boxes lost their height, radially-positioned nodes collapsed to
// the container's top-left corner, and blur/opacity modifiers were ignored.
// Fix: every arbitrary value below is now either a core Tailwind class or an
// inline `style` object. SVG `<path>` elements that used percentage coordinates
// (invalid — path data must be numeric) were replaced with `<line>` elements,
// which do support percentage attributes. Radial ticks around circles now use a
// proper `viewBox` so the rotation center actually matches the visual center.
// Low-contrast elements (module squares, decomposition lines) were given visible
// fills/borders so they don't blend into the background.

const RADIAL_POS: { top: string; left: string }[] = [
  { top: '15%', left: '20%' },
  { top: '15%', left: '80%' },
  { top: '85%', left: '20%' },
  { top: '85%', left: '80%' }
];

const Presentation: React.FC<PresentationProps> = ({ onClose }) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides = [
    // Introduction
    {
      title: null,
      content: (
        <div className="flex flex-col items-center justify-center w-full h-full text-center space-y-8 md:space-y-12">
          <h1 className="text-5xl md:text-7xl font-bold bg-gradient-to-r from-white to-violet-400 bg-clip-text text-transparent leading-tight">
            Virtual Hardware Laboratory
          </h1>
          <p className="text-xl md:text-3xl text-slate-400 max-w-3xl mx-auto font-bold leading-relaxed">
            A New Way of Hardware Engineering
          </p>
          <p className="text-xl md:text-2xl text-slate-400 max-w-4xl mx-auto italic font-light leading-relaxed">
            "Traditional hardware engineering relies on conversations between experts.
            VHL augments those conversations with a persistent engineering system.
            The project itself becomes a continuously growing repository of engineering knowledge."
          </p>
          <div className="pt-6 md:pt-12">
            <div className="inline-block px-6 py-2 border border-violet-500/30 rounded-full text-violet-400 font-mono tracking-widest text-sm uppercase">
              2027
            </div>
          </div>
        </div>
      )
    },
    // Act I
    {
      title: 'Why a new engineering model?',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-8 md:mb-12 text-center text-white w-full">
            Engineering is Entering a New Era
          </h3>
          <div className="flex-1 flex items-center w-full">
            <div className="grid md:grid-cols-2 gap-10 md:gap-20 items-center w-full">
              <div className="text-lg md:text-2xl text-slate-300 space-y-4 md:space-y-8 leading-relaxed">
                <p>Software engineering evolved from individual programmers to collaborative development platforms.</p>
                <p>
                  Hardware engineering is now undergoing a similar transition—from isolated engineering activities to{' '}
                  <span className="text-violet-400 font-semibold underline decoration-violet-500/30 underline-offset-8">
                    persistent engineering systems
                  </span>
                  .
                </p>
              </div>
              <div className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-6 md:p-10 flex items-center justify-center overflow-hidden">
                <div className="w-full max-w-full">
                  <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-8">
                    {[
                      { label: 'Drafting Board', icon: PenTool, opacity: 'opacity-40' },
                      { label: 'CAD', icon: Monitor, opacity: 'opacity-60' },
                      { label: 'Simulation', icon: Activity, opacity: 'opacity-80' },
                      { label: 'Persistent Engineering', icon: Database, opacity: 'opacity-100', active: true }
                    ].map((step, i, arr) => (
                      <React.Fragment key={step.label}>
                        <div
                          className={`flex flex-col items-center gap-4 transition-all duration-700 shrink-0 ${step.opacity} ${
                            step.active ? 'scale-110' : ''
                          }`}
                          style={{ width: 120 }}
                        >
                          <div
                            className={`p-4 rounded-2xl bg-slate-900 border ${
                              step.active ? 'border-violet-500 shadow-lg shadow-violet-500/20' : 'border-slate-800'
                            }`}
                          >
                            <step.icon className={`w-8 h-8 ${step.active ? 'text-violet-400' : 'text-slate-500'}`} />
                          </div>
                          <span
                            className={`text-sm font-mono text-center leading-snug ${
                              step.active ? 'text-violet-400 font-bold' : 'text-slate-500'
                            }`}
                          >
                            {step.label}
                          </span>
                        </div>
                        {i < arr.length - 1 && (
                          <ChevronRight className="hidden md:block text-slate-800 w-6 h-6 shrink-0" />
                        )}
                      </React.Fragment>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    // Act II - Slide 1
    {
      title: 'How VHL thinks about projects',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-4xl md:text-5xl font-bold mb-8 md:mb-16 text-center text-white w-full">
            A New Engineering Model
          </h3>
          <div className="flex-1 flex items-center w-full">
            <div className="grid md:grid-cols-2 gap-8 md:gap-16 w-full max-w-6xl mx-auto">
              {/* Left Side: Traditional */}
              <div className="flex flex-col gap-6">
                <h4 className="text-xl md:text-2xl font-semibold text-slate-500 text-center uppercase tracking-widest">
                  Traditional
                </h4>
                <div
                  className="bg-slate-950/30 border border-slate-800 border-dashed rounded-3xl flex items-center justify-center p-8 relative overflow-hidden"
                  style={{ height: 400 }}
                >
                  <div className="grid grid-cols-2 gap-x-16 gap-y-10 relative z-10">
                    <div className="flex flex-col items-center gap-2 opacity-40 animate-pulse">
                      <Users size={40} className="text-slate-500" />
                      <Speech size={20} className="text-slate-600" />
                    </div>
                    <div className="flex flex-col items-center gap-2 opacity-30 animate-pulse" style={{ animationDelay: '0.5s' }}>
                      <Speech size={24} className="text-slate-600" />
                      <Users size={32} className="text-slate-500" />
                    </div>
                    <div className="flex flex-col items-center gap-2 opacity-50 animate-pulse" style={{ animationDelay: '1s' }}>
                      <Users size={32} className="text-slate-500" />
                      <Speech size={24} className="text-slate-600" />
                    </div>
                    <div className="flex flex-col items-center gap-2 opacity-20 animate-pulse" style={{ animationDelay: '1.5s' }}>
                      <Speech size={20} className="text-slate-600" />
                      <Users size={40} className="text-slate-500" />
                    </div>
                  </div>

                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950/80 backdrop-blur-sm z-20">
                    <div className="w-20 h-20 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center text-slate-500 shadow-xl">
                      <Users size={40} />
                    </div>
                    <div className="text-xs font-mono text-slate-500 text-center mt-4 font-bold uppercase tracking-wider">
                      Ephemeral Conversations
                      <br />
                      &amp; Individual Memory
                    </div>
                  </div>

                  {/* Leaky lines */}
                  <svg className="absolute inset-0 w-full h-full opacity-10" preserveAspectRatio="none">
                    <line x1="0" y1="0" x2="100%" y2="100%" stroke="white" strokeWidth="1" strokeDasharray="10 10" />
                    <line x1="100%" y1="0" x2="0" y2="100%" stroke="white" strokeWidth="1" strokeDasharray="10 10" />
                  </svg>
                </div>
              </div>

              {/* Right Side: VHL */}
              <div className="flex flex-col gap-6">
                <h4 className="text-xl md:text-2xl font-semibold text-violet-400 text-center uppercase tracking-widest">
                  VHL
                </h4>
                <div
                  className="bg-violet-950/10 border border-violet-500/20 border-dashed rounded-3xl flex items-center justify-center p-8 relative overflow-hidden"
                  style={{ height: 400 }}
                >
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div
                      className="rounded-full border border-violet-500/10 animate-spin"
                      style={{ width: 256, height: 256, animationDuration: '10s' }}
                    />
                    <div
                      className="absolute rounded-full border border-violet-500/10 animate-spin"
                      style={{ width: 192, height: 192, animationDuration: '15s', animationDirection: 'reverse' }}
                    />
                  </div>

                  <div className="flex flex-col items-center gap-6 z-10">
                    <div className="w-24 h-24 rounded-3xl bg-violet-600 border border-violet-400 flex items-center justify-center text-white shadow-2xl shadow-violet-500/40 relative group">
                      <div className="absolute inset-0 bg-white/20 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
                      <Database size={48} />
                    </div>
                    <div className="text-center">
                      <div className="text-sm font-black text-violet-400 font-mono uppercase tracking-widest">
                        Persistent Engineering
                        <br />
                        System (AOSM)
                      </div>
                      <div className="text-xs text-violet-500/70 font-mono mt-2">AUTONOMOUS PROJECT STATE</div>
                    </div>
                  </div>

                  {/* Radial ticks — proper viewBox so rotation center matches the visual center */}
                  <svg
                    className="absolute inset-0 w-full h-full pointer-events-none opacity-20 text-violet-400"
                    viewBox="0 0 400 400"
                    preserveAspectRatio="xMidYMid meet"
                  >
                    <circle cx="200" cy="200" r="120" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 4" />
                    {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
                      <g key={angle} transform={`rotate(${angle} 200 200)`}>
                        <line x1="200" y1="80" x2="200" y2="50" stroke="currentColor" strokeWidth="3" />
                      </g>
                    ))}
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    // Act II - Slide 2
    {
      title: 'How VHL thinks about projects',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-6 md:mb-10 text-center text-white w-full">The Project Blueprint</h3>
          <div className="flex-1 flex flex-col justify-center w-full gap-6 md:gap-8 max-w-6xl mx-auto">
            <div className="grid md:grid-cols-2 gap-8 md:gap-16 items-center w-full">
              {/* Diagram: the four documents that make up the Stable Core */}
              <div
                className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-6 flex items-center justify-center relative overflow-hidden"
                style={{ height: 320 }}
              >
                <div className="relative w-full h-full flex items-center justify-center">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="bg-violet-500/5 rounded-full animate-pulse" style={{ width: '65%', height: '65%' }} />
                  </div>

                  {/* Connection lines — real <line> elements (percentage path "d" data is invalid) */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" preserveAspectRatio="none">
                    <defs>
                      <marker id="dot" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4">
                        <circle cx="5" cy="5" r="5" fill="#8b5cf6" />
                      </marker>
                    </defs>
                    {RADIAL_POS.map((pos, i) => (
                      <line
                        key={i}
                        x1="50%"
                        y1="50%"
                        x2={pos.left}
                        y2={pos.top}
                        stroke="#8b5cf6"
                        strokeWidth="2"
                        strokeDasharray="4 4"
                        className="opacity-30"
                        markerEnd="url(#dot)"
                      />
                    ))}
                  </svg>

                  {/* Central Node */}
                  <div className="z-20 p-5 rounded-3xl bg-slate-900 border-2 border-violet-500 shadow-2xl shadow-violet-500/20 text-center">
                    <Workflow className="w-10 h-10 text-violet-400 mx-auto mb-2" />
                    <div className="text-xs font-bold text-white font-mono uppercase tracking-widest">Stable Core</div>
                  </div>

                  {/* Radial Components — the four documents */}
                  {[
                    { icon: FileText, label: 'Assembly SCUD' },
                    { icon: Layers, label: 'Module SCUDs' },
                    { icon: ShieldCheck, label: 'System Boundary Doc' },
                    { icon: Boxes, label: 'Module Boundary Docs' }
                  ].map((item, i) => (
                    <div
                      key={item.label}
                      className="absolute z-10 flex flex-col items-center gap-2 -translate-x-1/2 -translate-y-1/2"
                      style={{ top: RADIAL_POS[i].top, left: RADIAL_POS[i].left, width: 116 }}
                    >
                      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 shadow-lg">
                        <item.icon size={20} />
                      </div>
                      <span className="text-xs font-mono font-bold text-slate-400 uppercase text-center leading-snug">
                        {item.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="text-lg md:text-xl text-slate-300 space-y-3 md:space-y-5 leading-relaxed">
                <p className="font-bold text-violet-400 text-3xl md:text-4xl">Stable Core</p>
                <p>
                  Everything else derives from a small set of living documents — the{' '}
                  <span className="text-white font-semibold">source of truth</span> that defines the system's DNA.
                </p>
                <p className="text-slate-500 text-base md:text-lg">
                  SCUD = Shared Circuit Understanding Document. Boundary docs exist at both the system and module level.
                  Changes to any of these ripple through the entire engineering stack.
                </p>
              </div>
            </div>

            {/* Bootstrap strip */}
            <div className="w-full bg-slate-950/40 border border-slate-800 rounded-2xl p-5 md:p-6 flex flex-col md:flex-row items-center gap-5 md:gap-8">
              <div className="flex items-center gap-4 md:w-72 shrink-0">
                <div className="p-3 rounded-xl bg-violet-600/10 border border-violet-500/30 text-violet-400 shrink-0">
                  <Microscope size={24} />
                </div>
                <div>
                  <div className="text-white font-bold text-base md:text-lg leading-tight">Bootstrapped by Architects</div>
                  <div className="text-slate-500 text-xs md:text-sm">A high-level design doc kicks off every project</div>
                </div>
              </div>
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
                {[
                  'Module responsibilities & boundaries',
                  'Preferred ASIC components',
                  'High-level system description'
                ].map((chip) => (
                  <div
                    key={chip}
                    className="px-4 py-2.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 text-center leading-snug"
                  >
                    {chip}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )
    },
    // Act III - Slide 1
    {
      title: 'How engineering happens',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-6 md:mb-10 text-center text-white w-full">Divide the Problem: Modules</h3>
          <div className="flex-1 flex flex-col justify-center w-full gap-6 md:gap-8 max-w-6xl mx-auto">
            <div className="grid md:grid-cols-2 gap-8 md:gap-16 items-center w-full">
              <div className="text-base md:text-lg text-slate-300 space-y-3 md:space-y-4 leading-relaxed">
                {/* <p className="text-slate-500 text-xs font-mono uppercase tracking-widest">VHL Terminology</p> */}
                <p className="text-3xl md:text-4xl font-bold text-white">Module</p>
                <p>
                  A self-contained, isolated functional building block — <span className="text-slate-400">not</span> a single
                  component like an IC or resistor, but a set of components organized to deliver{' '}
                  <span className="text-white font-semibold">one engineering capability</span>.
                </p>
                {/* <div className="flex flex-wrap gap-2 pt-1">
                  {['Current Sensing', 'Power Supply', 'Battery Monitoring', 'Gate Driver'].map((ex) => (
                    <span key={ex} className="px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-slate-400">
                      {ex}
                    </span>
                  ))}
                </div> */}
                <p className="text-xl md:text-2xl font-medium pt-2">
                  Defined by its{' '}
                  <span className="text-violet-400 font-bold underline underline-offset-8 decoration-violet-500/30">Function</span> and
                  its <span className="text-violet-400 font-bold underline underline-offset-8 decoration-violet-500/30">Ports</span>.
                </p>
                <p className="text-slate-500 text-sm md:text-base italic">Nothing else — implementation stays internal.</p>
              </div>
              <div
                className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-6 md:p-10 flex items-center justify-center relative overflow-hidden"
                style={{ height: 300 }}
              >
                <div className="relative w-full h-full flex flex-col items-center">
                  {/* Parent Box */}
                  <div
                    className="z-20 w-48 bg-slate-900 border-2 border-slate-700 rounded-2xl flex items-center justify-center shadow-2xl relative mt-4"
                    style={{ height: 64 }}
                  >
                    <span className="font-bold text-slate-300 font-mono tracking-widest uppercase text-xs">BMS Assembly</span>
                    <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-slate-700 rotate-45" />
                  </div>

                  {/* Decomposition Lines — real <line> elements instead of invalid percentage path data */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-30" preserveAspectRatio="none">
                    <line x1="50%" y1="25%" x2="50%" y2="45%" stroke="white" strokeWidth="2" />
                    <line x1="12.5%" y1="45%" x2="87.5%" y2="45%" stroke="white" strokeWidth="2" />
                    <line x1="12.5%" y1="45%" x2="12.5%" y2="65%" stroke="white" strokeWidth="2" />
                    <line x1="37.5%" y1="45%" x2="37.5%" y2="65%" stroke="white" strokeWidth="2" />
                    <line x1="62.5%" y1="45%" x2="62.5%" y2="65%" stroke="white" strokeWidth="2" />
                    <line x1="87.5%" y1="45%" x2="87.5%" y2="65%" stroke="white" strokeWidth="2" />
                  </svg>

                  {/* Modules */}
                  <div className="absolute bottom-6 grid grid-cols-4 gap-3 w-full px-4">
                    {[
                      { label: 'Monitoring', icon: Activity },
                      { label: 'Switching', icon: Zap },
                      { label: 'LV Supply', icon: Cpu },
                      { label: 'HV Supply', icon: Box }
                    ].map((mod) => (
                      <div key={mod.label} className="flex flex-col items-center gap-3 group">
                        <div className="w-full h-16 bg-slate-800 border border-violet-500/30 rounded-xl flex items-center justify-center transition-all group-hover:border-violet-500 group-hover:bg-violet-500/10 group-hover:-translate-y-2 shadow-lg">
                          <mod.icon className="w-6 h-6 text-violet-400" />
                        </div>
                        <span className="text-xs font-mono font-bold text-slate-400 group-hover:text-violet-400 text-center uppercase tracking-tighter">
                          {mod.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Core Characteristics */}
            <div className="w-full grid sm:grid-cols-3 gap-4 md:gap-6">
              {[
                {
                  icon: Zap,
                  title: 'Functionality',
                  desc: 'What the module does — the engineering capability it provides, independent of how it\u2019s implemented.'
                },
                {
                  icon: GitBranch,
                  title: 'Interfaces (Ports)',
                  desc: 'How other modules interact with it — abstract exchange points, not physical pins or connectors.'
                },
                {
                  icon: FileText,
                  title: 'Summary Info',
                  desc: 'Name, purpose, design intent, key capabilities, assumptions & constraints at a glance.'
                }
              ].map((c) => (
                <div key={c.title} className="bg-slate-950/40 border border-slate-800 rounded-2xl p-5 flex flex-col gap-3">
                  <div className="w-10 h-10 rounded-lg bg-violet-600/10 border border-violet-500/30 flex items-center justify-center text-violet-400">
                    <c.icon size={18} />
                  </div>
                  <div className="text-white font-bold text-sm">{c.title}</div>
                  <div className="text-slate-500 text-xs leading-relaxed">{c.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )
    },
    // Act III - Slide 2
    {
      title: 'How engineering happens',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-3 text-center text-white w-full">Compose Larger Systems: Assemblies</h3>
          <p className="text-slate-400 text-base md:text-lg text-center max-w-3xl mx-auto mb-6 md:mb-10 leading-relaxed">
            A higher-level construct that interconnects multiple modules to realize a system objective —{' '}
            <span className="text-violet-400 font-semibold">composition, not new circuitry</span>.
          </p>
          <div className="flex-1 flex flex-col justify-center w-full gap-6 md:gap-8 max-w-6xl mx-auto">
            <div
              className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-6 md:p-10 flex items-center justify-center w-full"
              style={{ height: 280 }}
            >
              <div className="flex items-center justify-around w-full gap-4 md:gap-10">
                {/* Small Modules — raised contrast so squares are actually visible against the background */}
                <div className="flex flex-col items-center gap-3">
                  <div className="grid grid-cols-2 gap-2">
                    {[0, 0.2, 0.4, 0.6].map((delay, i) => (
                      <div
                        key={i}
                        className="w-7 h-7 md:w-9 md:h-9 bg-slate-700 border border-slate-500 rounded shadow-lg animate-bounce"
                        style={{ animationDelay: `${delay}s` }}
                      />
                    ))}
                  </div>
                  <div className="text-xs font-mono text-slate-500 uppercase font-bold tracking-widest">Modules</div>
                </div>

                <ChevronRight className="text-slate-700" size={28} />

                {/* Assembly */}
                <div className="flex flex-col items-center gap-3">
                  <div className="w-20 h-20 md:w-28 md:h-28 bg-slate-900 border-2 border-violet-500/50 rounded-2xl shadow-xl flex items-center justify-center relative overflow-hidden group">
                    <div className="absolute inset-0 bg-violet-500/10 animate-pulse" />
                    <div className="grid grid-cols-2 gap-1.5 p-3 z-10 w-full h-full">
                      <div className="w-full h-full bg-violet-500/40 border border-violet-400/60 rounded" />
                      <div className="w-full h-full bg-violet-500/40 border border-violet-400/60 rounded" />
                      <div className="w-full h-full bg-violet-500/40 border border-violet-400/60 rounded" />
                      <div className="w-full h-full bg-violet-500/40 border border-violet-400/60 rounded" />
                    </div>
                  </div>
                  <div className="text-xs font-mono text-violet-400 uppercase font-bold tracking-widest">Assembly</div>
                </div>

                <ChevronRight className="text-slate-700" size={28} />

                {/* Complete Product */}
                <div className="flex flex-col items-center gap-3">
                  <div className="w-24 h-24 md:w-36 md:h-36 bg-slate-900 border-2 border-violet-500 rounded-3xl shadow-2xl shadow-violet-500/30 flex items-center justify-center relative group overflow-hidden">
                    <div className="absolute inset-0 bg-violet-600/10 animate-pulse" />
                    <Cpu size={48} className="text-violet-400 z-10" />
                    <div className="absolute top-2 right-2 w-7 h-7 rounded-full bg-violet-600 border border-violet-400 flex items-center justify-center text-white shadow-xl rotate-12">
                      <ShieldCheck size={14} />
                    </div>
                  </div>
                  <div className="text-xs font-mono text-white font-black tracking-widest uppercase bg-violet-600/40 px-3 py-1.5 rounded-full border border-violet-400">
                    Complete Product
                  </div>
                </div>
              </div>
            </div>

            {/* Assembly Assets */}
            <div className="w-full grid sm:grid-cols-2 gap-4 md:gap-6">
              {[
                {
                  icon: FileText,
                  title: 'SCUD Document',
                  desc: 'Assembly objective, constituent modules, interconnections, interfaces, assumptions & constraints — the primary spec.'
                },
                {
                  icon: Code2,
                  title: 'Subcircuit (.tsx)',
                  desc: 'Describes how modules are wired together to form the subsystem — composition, not new electronic functionality.'
                }
              ].map((c) => (
                <div key={c.title} className="bg-slate-950/40 border border-slate-800 rounded-2xl p-5 flex items-start gap-4">
                  <div className="w-10 h-10 shrink-0 rounded-lg bg-violet-600/10 border border-violet-500/30 flex items-center justify-center text-violet-400">
                    <c.icon size={18} />
                  </div>
                  <div>
                    <div className="text-white font-bold text-sm mb-1">{c.title}</div>
                    <div className="text-slate-500 text-xs leading-relaxed">{c.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )
    },
    // Act IV - Slide 1
    {
      title: 'Why this scales',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-8 md:mb-12 text-center text-white w-full">Boundaries Enable Parallel Engineering</h3>
          <div className="flex-1 flex items-center w-full">
            <div className="grid md:grid-cols-2 gap-10 md:gap-20 items-center w-full">
              <div className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-6 md:p-12 flex items-center justify-center">
                <div className="w-full space-y-8">
                  {[
                    { label: 'Module A', progress: 100, agent: 'Archy' },
                    { label: 'Module B', progress: 85, agent: 'ANA' },
                    { label: 'Module C', progress: 60, agent: 'Librarian' },
                    { label: 'Module D', progress: 40, agent: 'ANA' }
                  ].map((task) => (
                    <div key={task.label} className="flex items-center gap-6">
                      <div className="w-24 font-mono text-sm text-slate-500">{task.label}</div>
                      <div className="flex-1 h-3 bg-slate-900 rounded-full border border-slate-800 overflow-hidden relative">
                        <div
                          className="h-full bg-violet-600 rounded-full transition-all duration-1000 ease-out"
                          style={{ width: `${task.progress}%` }}
                        />
                        {task.progress < 100 && (
                          <div className="absolute top-0 right-0 h-full w-24 bg-gradient-to-l from-violet-500/20 to-transparent animate-pulse" />
                        )}
                      </div>
                      <div className="w-24 text-right">
                        <span className="px-2 py-1 rounded-md bg-violet-500/10 border border-violet-500/20 text-xs font-mono text-violet-400">
                          {task.agent} Active
                        </span>
                      </div>
                    </div>
                  ))}
                  <div className="pt-6 flex justify-between items-center border-t border-slate-800">
                    <div className="flex items-center gap-2 text-slate-500 font-mono text-xs uppercase">
                      <div className="w-2 h-2 rounded-full bg-violet-500 animate-ping" />
                      Independent Progress
                    </div>
                    <div className="text-slate-500 font-mono text-xs uppercase">Shared Interfaces (Blueprint)</div>
                  </div>
                </div>
              </div>
              <div className="text-lg md:text-2xl text-slate-300 space-y-4 md:space-y-8 leading-relaxed">
                <p>
                  Well-defined boundaries allow engineering to proceed independently{' '}
                  <span className="text-white font-semibold">without losing system coherence</span>.
                </p>
                <p>Each team (or agent) can work on their module with full confidence in the interfaces.</p>
              </div>
            </div>
          </div>
        </div>
      )
    },
    // Act IV - Slide 2
    {
      title: 'Why this scales',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-8 md:mb-12 text-center text-white w-full">Every Module Has an Engineering Team</h3>
          <div className="flex-1 flex items-center w-full">
            <div className="grid md:grid-cols-2 gap-10 md:gap-20 items-center w-full">
              <div className="text-lg md:text-2xl text-slate-300 space-y-4 md:space-y-8 leading-relaxed">
                <p className="text-2xl md:text-3xl font-semibold text-white">Engineers remain the decision makers.</p>
                <p>VHL provides persistent architectural reasoning, analysis, and knowledge management throughout development.</p>
              </div>
              <div className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-6 md:p-12 flex items-center justify-center">
                <div className="relative w-full flex items-center justify-center" style={{ height: 350 }}>
                  {/* Engineer Node */}
                  <div className="z-20 p-6 rounded-3xl bg-white border-2 border-slate-200 shadow-2xl text-center scale-110">
                    <Users className="w-12 h-12 text-slate-800 mx-auto mb-2" />
                    <div className="text-sm font-black text-slate-900 font-mono uppercase">Engineer</div>
                    <div className="text-xs font-bold text-slate-500 uppercase tracking-tighter">Decision Maker</div>
                  </div>

                  {/* Agent Nodes — inline style for the pixel offset instead of a bracket class */}
                  {[
                    { label: 'Archy Agent', icon: Microscope, x: -150, y: -80, sub: 'Analysis' },
                    { label: 'ANA Agent', icon: Code2, x: 150, y: -80, sub: 'Synthesis' },
                    { label: 'Librarian', icon: Search, x: 0, y: 150, sub: 'Resolution' }
                  ].map((agent) => (
                    <div
                      key={agent.label}
                      className="absolute z-10 flex flex-col items-center gap-3"
                      style={{ transform: `translate(${agent.x}px, ${agent.y}px)` }}
                    >
                      <div className="p-5 rounded-2xl bg-violet-600 border border-violet-400 text-white shadow-xl shadow-violet-500/20">
                        <agent.icon size={32} />
                      </div>
                      <div className="text-center">
                        <div className="text-xs font-bold text-violet-400 font-mono uppercase">{agent.label}</div>
                        <div className="text-xs text-slate-500 font-mono uppercase">{agent.sub}</div>
                      </div>
                    </div>
                  ))}

                  {/* Connecting Paths — numeric coordinates matching the viewBox, not percentages */}
                  <svg
                    className="absolute inset-0 w-full h-full pointer-events-none text-violet-500/30"
                    viewBox="0 0 400 350"
                    preserveAspectRatio="xMidYMid meet"
                  >
                    <line x1="200" y1="175" x2="80" y2="105" stroke="currentColor" strokeWidth="2" strokeDasharray="5 5" />
                    <line x1="200" y1="175" x2="320" y2="105" stroke="currentColor" strokeWidth="2" strokeDasharray="5 5" />
                    <line x1="200" y1="175" x2="200" y2="315" stroke="currentColor" strokeWidth="2" strokeDasharray="5 5" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      )
    },
    // Act V - Slide 1
    {
      title: 'What becomes possible',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-8 md:mb-12 text-center text-white w-full">Knowledge Never Disappears</h3>
          <div className="flex-1 flex flex-col items-center justify-center w-full space-y-8 md:space-y-12">
            <div className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-8 md:p-16 flex items-center justify-center w-full max-w-6xl mx-auto">
              <div className="w-full">
                <div className="grid grid-cols-2 gap-10 md:gap-20">
                  {/* Traditional: Leaky / Memory loss */}
                  <div className="flex flex-col items-center gap-8">
                    <div
                      className="relative w-32 md:w-40 bg-slate-900 border-x-2 border-b-2 border-slate-700 rounded-b-3xl overflow-hidden shadow-inner"
                      style={{ height: 256 }}
                    >
                      {/* Water/Data level low */}
                      <div className="absolute bottom-0 w-full h-12 bg-slate-600/40 animate-pulse" />
                      {/* Leaks */}
                      <div className="absolute bottom-16 -left-1 w-6 h-1 bg-slate-400 rounded-full animate-ping" />
                      <div className="absolute bottom-24 -right-1 w-4 h-1 bg-slate-400 rounded-full animate-ping" style={{ animationDuration: '3s' }} />
                      <div className="absolute bottom-32 -left-1 w-3 h-1 bg-slate-400 rounded-full animate-ping" style={{ animationDuration: '1.5s' }} />
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-slate-500 uppercase tracking-widest mb-2 flex items-center justify-center gap-2">
                        <Users size={20} /> Traditional
                      </div>
                      <div className="text-sm font-mono text-slate-600 uppercase">Fragmented &amp; Ephemeral</div>
                    </div>
                  </div>

                  {/* VHL: Accumulating / Growth */}
                  <div className="flex flex-col items-center gap-8">
                    <div
                      className="relative w-32 md:w-40 bg-slate-900 border-x-2 border-b-2 border-violet-500 rounded-b-3xl overflow-hidden shadow-2xl shadow-violet-500/10"
                      style={{ height: 256 }}
                    >
                      {/* Growing level */}
                      <div className="absolute bottom-0 w-full bg-violet-600/40 animate-pulse" style={{ height: '75%' }} />
                      {/* Inbound data particles */}
                      <div className="absolute top-4 left-1/4 w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }} />
                      <div className="absolute top-8 left-1/2 w-3 h-3 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                      <div className="absolute top-12 right-1/4 w-2 h-2 bg-violet-300 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }} />
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-violet-400 uppercase tracking-widest mb-2 flex items-center justify-center gap-2">
                        <Database size={20} /> VHL
                      </div>
                      <div className="text-sm font-mono text-violet-500 font-bold uppercase tracking-wider">Persistent &amp; Cumulative</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <p className="text-xl md:text-3xl text-slate-400 font-medium text-center max-w-5xl leading-relaxed">
              Persistence matters: everything is connected, from the first idea to the next project.
            </p>
          </div>
        </div>
      )
    },
    // Act V - Slide 2 (Research Frontiers)
    {
      title: 'Current Research Frontiers',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-8 md:mb-16 text-center text-white w-full max-w-5xl mx-auto leading-tight">
            The Vision is Clear. The Architecture is Still Evolving.
          </h3>
          <div className="flex-1 flex items-center w-full">
            <div className="grid md:grid-cols-3 gap-6 md:gap-8 w-full max-w-7xl mx-auto">
              {/* Mature */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 space-y-6 relative overflow-hidden group hover:border-violet-500/50 transition-colors">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-2xl font-black text-white uppercase tracking-wider">Mature</h4>
                  <div className="w-10 h-10 rounded-full bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center">
                    <ShieldCheck size={20} className="text-emerald-400" />
                  </div>
                </div>
                <ul className="text-slate-400 space-y-4 font-mono text-sm">
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> Project decomposition
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> Module abstraction
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> Assembly abstraction
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> Persistent module engineering
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> Recursive composition
                  </li>
                </ul>
              </div>

              {/* Active Research */}
              <div className="bg-violet-900/10 border border-violet-500/30 rounded-3xl p-8 space-y-6 relative overflow-hidden group hover:border-violet-500 transition-colors">
                <div className="absolute top-0 right-0 w-24 h-24 bg-violet-500/10 blur-3xl" />
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-2xl font-black text-violet-400 uppercase tracking-wider">Active Research</h4>
                  <div className="w-10 h-10 rounded-full bg-violet-500/20 border border-violet-500/50 flex items-center justify-center">
                    <Activity size={20} className="text-violet-400 animate-pulse" />
                  </div>
                </div>
                <ul className="text-slate-300 space-y-4 font-mono text-sm">
                  <li className="flex items-center gap-3 font-bold">
                    <div className="w-1.5 h-1.5 bg-violet-500 rounded-full animate-ping" /> Architectural State Manager
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-violet-500 rounded-full" /> Boundary Documentation
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-violet-500 rounded-full" /> Boundary reconciliation
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-violet-500 rounded-full" /> Assembly synthesis
                  </li>
                  <li className="flex items-center gap-3">
                    <div className="w-1.5 h-1.5 bg-violet-500 rounded-full" /> PCB workflow
                  </li>
                </ul>
              </div>

              {/* Future */}
              <div className="bg-slate-950 border border-slate-800 border-dashed rounded-3xl p-8 space-y-6 opacity-60 hover:opacity-100 transition-opacity">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-2xl font-black text-slate-500 uppercase tracking-wider">Future</h4>
                  <div className="w-10 h-10 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
                    <Search size={20} className="text-slate-600" />
                  </div>
                </div>
                <ul className="text-slate-500 space-y-4 font-mono text-sm">
                  <li>• Verification</li>
                  <li>• Manufacturing</li>
                  <li>• Testing</li>
                  <li>• Firmware co-design</li>
                  <li>• Scientific workflows</li>
                </ul>
              </div>
            </div>
          </div>
          <p className="mt-12 text-lg text-slate-500 italic text-center max-w-4xl">
            VHL is evolving by discovering the minimal abstractions required for engineering rather than prescribing them upfront.
          </p>
        </div>
      )
    },
    // Act VI - Closing
    {
      title: 'What becomes possible',
      content: (
        <div className="flex flex-col items-center w-full h-full text-center">
          <h3 className="text-4xl md:text-6xl font-black text-white w-full mb-8 md:mb-12">The Future</h3>
          <div className="flex-1 flex flex-col items-center justify-center w-full space-y-8 md:space-y-12">
            <div className="bg-slate-950/50 border border-slate-800 border-dashed rounded-3xl p-8 md:p-12 w-full flex items-center justify-center">
              <div className="relative w-full flex items-center justify-center" style={{ height: 320 }}>
                {/* Circular Ecosystem */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div
                    className="rounded-full border border-violet-500/10 animate-spin"
                    style={{ width: 350, height: 350, animationDuration: '20s' }}
                  />
                </div>

                {/* Nodes on the loop */}
                <div className="relative z-10 w-full flex items-center justify-around gap-4">
                  {[
                    { label: 'Engineers', icon: Users, sub: 'Human Intent' },
                    { label: 'Living Project', icon: GitBranch, sub: 'Continuous Evolution' },
                    { label: 'Living Platform', icon: Factory, sub: 'Recursive Knowledge' }
                  ].map((node, i) => (
                    <React.Fragment key={node.label}>
                      <div className="flex flex-col items-center gap-6 group">
                        <div className="p-8 rounded-3xl bg-slate-900 border-2 border-violet-500/30 group-hover:border-violet-500 shadow-2xl transition-all group-hover:-translate-y-2">
                          <node.icon size={48} className="text-violet-400" />
                        </div>
                        <div className="text-center">
                          <div className="text-xl font-black text-white uppercase tracking-wider">{node.label}</div>
                          <div className="text-xs font-mono text-slate-500 uppercase mt-1">{node.sub}</div>
                        </div>
                      </div>
                      {i < 2 && <ChevronRight className="text-violet-500/30" size={40} />}
                    </React.Fragment>
                  ))}
                </div>

                {/* Floating particles */}
                <div className="absolute top-8 left-8 w-2 h-2 bg-violet-500 rounded-full animate-ping" />
                <div className="absolute bottom-8 right-8 w-3 h-3 bg-violet-400 rounded-full animate-pulse" />
              </div>
            </div>
            <div className="space-y-4 md:space-y-6">
              <p className="text-2xl md:text-3xl font-bold text-white max-w-5xl mx-auto leading-tight">
                "Every project strengthens the engineering ecosystem that builds the next project."
              </p>
              {/* <p className="text-slate-500 text-xl md:text-2xl font-light">VHL SYSTEM • 2026</p> */}
            </div>
          </div>
        </div>
      )
    },
    // Closing - Technology Stack
    {
      title: 'Built On',
      content: (
        <div className="flex flex-col items-center w-full h-full">
          <h3 className="text-3xl md:text-5xl font-bold mb-4 text-center text-white w-full">Technology Stack for VHL</h3>
          <p className="text-slate-500 font-mono text-sm uppercase tracking-widest mb-8 md:mb-14 text-center">
            Built in the open, on open foundations
          </p>
          <div className="flex-1 flex items-center w-full">
            <div className="grid md:grid-cols-3 gap-6 md:gap-8 w-full max-w-6xl mx-auto">
              {[
                {
                  name: 'tscircuit',
                  desc: 'Code-first circuit design and schematic/PCB primitives',
                  icon: Cpu,
                  license: 'MIT License'
                },
                {
                  name: 'OpenHands Software Agent SDK',
                  desc: 'Agent framework powering VHL\u2019s autonomous engineering workflows',
                  icon: Workflow,
                  license: 'MIT License'
                },
                {
                  name: 'Unified Runtime Primitive',
                  desc: 'Shared execution layer underlying the persistent engineering system',
                  icon: Box,
                  license: 'MIT License'
                }
              ].map((tech) => (
                <div
                  key={tech.name}
                  className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8 flex flex-col gap-6 relative overflow-hidden group hover:border-violet-500/50 transition-colors"
                >
                  <div className="w-14 h-14 rounded-2xl bg-violet-600/10 border border-violet-500/30 flex items-center justify-center text-violet-400 group-hover:bg-violet-600 group-hover:text-white transition-colors">
                    <tech.icon size={28} />
                  </div>
                  <div className="flex-1">
                    <div className="text-xl font-bold text-white mb-2">{tech.name}</div>
                    <div className="text-slate-400 text-sm leading-relaxed">{tech.desc}</div>
                  </div>
                  <div className="inline-flex self-start items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                    <ShieldCheck size={14} className="text-emerald-400" />
                    <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider">{tech.license}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <p className="mt-10 text-lg text-slate-500 italic text-center max-w-3xl">
            Open-source foundations, permissively licensed, so the ecosystem can grow with everyone who builds on it.
          </p>
        </div>
      )
    }
  ];

  const nextSlide = () => setCurrentSlide((prev) => Math.min(prev + 1, slides.length - 1));
  const prevSlide = () => setCurrentSlide((prev) => Math.max(prev - 1, 0));

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
      if (e.key === 'ArrowLeft') prevSlide();
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="fixed inset-0 bg-slate-950 z-50 flex flex-col p-8 overflow-hidden">
      {/* Top Bar */}
      <div className="flex items-center justify-between mb-4 md:mb-8">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-violet-600 rounded-xl flex items-center justify-center font-bold text-xl">V</div>
          <div>
            <div className="text-sm font-bold text-white uppercase tracking-wider">Virtual Hardware Laboratory</div>
            {slides[currentSlide].title && (
              <div className="text-xs font-mono text-violet-400 uppercase tracking-widest mt-0.5 opacity-80">
                {slides[currentSlide].title}
              </div>
            )}
          </div>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-slate-900 rounded-full transition-colors text-slate-500 hover:text-white">
          <X size={24} />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col items-center relative group overflow-hidden min-h-0">
        <div className="w-full max-w-6xl h-full flex flex-col transition-all duration-500 ease-in-out">
          <div className="flex-1 flex items-center justify-center bg-slate-900/40 border border-slate-800 rounded-3xl p-8 md:p-12 shadow-2xl shadow-violet-900/10 overflow-auto min-h-0">
            <div className="w-full h-full">{slides[currentSlide].content}</div>
          </div>
        </div>

        {/* Navigation Overlays */}
        {currentSlide > 0 && (
          <button
            onClick={prevSlide}
            className="absolute left-0 top-1/2 -translate-y-1/2 p-4 bg-slate-900/50 hover:bg-slate-900 rounded-full opacity-0 group-hover:opacity-100 transition-opacity z-10 text-slate-400 hover:text-white"
          >
            <ChevronLeft size={32} />
          </button>
        )}
        {currentSlide < slides.length - 1 && (
          <button
            onClick={nextSlide}
            className="absolute right-0 top-1/2 -translate-y-1/2 p-4 bg-slate-900/50 hover:bg-slate-900 rounded-full opacity-0 group-hover:opacity-100 transition-opacity z-10 text-slate-400 hover:text-white"
          >
            <ChevronRight size={32} />
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mt-8 flex gap-2">
        {slides.map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all duration-500 ${
              i === currentSlide ? 'bg-violet-500' : i < currentSlide ? 'bg-violet-900/50' : 'bg-slate-900'
            }`}
          />
        ))}
      </div>

      {/* Controls Hint */}
      <div className="mt-4 flex justify-center gap-8 text-xs font-mono text-slate-600 uppercase tracking-widest">
        <span>[Space / Arrow Right] Next</span>
        <span>[Arrow Left] Prev</span>
        <span>[Esc] Close</span>
      </div>
    </div>
  );
};

export default Presentation;