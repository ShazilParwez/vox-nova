'use client';

export function FintechBackground() {
  return (
    <div className="fixed inset-0 z-[-1] overflow-hidden bg-slate-950 selection:bg-primary/30">
      {/* Soft Ambient Radial Glows */}
      <div className="absolute -top-40 -left-40 h-[500px] w-[500px] rounded-full bg-emerald-500/10 mix-blend-screen blur-[120px] animate-pulse-slow" />
      <div className="absolute top-1/3 -right-40 h-[600px] w-[600px] rounded-full bg-teal-500/10 mix-blend-screen blur-[150px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
      <div className="absolute -bottom-40 left-1/4 h-[400px] w-[400px] rounded-full bg-emerald-700/10 mix-blend-screen blur-[100px] animate-pulse-slow" style={{ animationDelay: '4s' }} />

      {/* Subtle Abstract Financial Curves (SVG) */}
      <div className="absolute inset-0 opacity-[0.04] animate-float">
        <svg
          className="h-full w-full"
          viewBox="0 0 1440 800"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="none"
        >
          {/* Upward trending curve 1 */}
          <path
            d="M-100 800 C 200 700, 400 500, 600 600 C 800 700, 1000 400, 1440 200"
            stroke="white"
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
          {/* Upward trending curve 2 */}
          <path
            d="M-100 800 C 300 750, 500 550, 700 500 C 900 450, 1200 300, 1440 100"
            stroke="url(#paint0_linear)"
            strokeWidth="4"
            vectorEffect="non-scaling-stroke"
          />
          {/* Subtle grid lines matching the curve nodes */}
          <line x1="600" y1="0" x2="600" y2="800" stroke="white" strokeWidth="1" strokeDasharray="5 5" />
          <line x1="700" y1="0" x2="700" y2="800" stroke="white" strokeWidth="1" strokeDasharray="5 5" />
          
          <defs>
            <linearGradient id="paint0_linear" x1="0" y1="800" x2="1440" y2="100" gradientUnits="userSpaceOnUse">
              <stop stopColor="#10b981" />
              <stop offset="1" stopColor="#0f766e" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Atmospheric Glass Overlay to push lines back further */}
      <div className="absolute inset-0 bg-slate-950/50 backdrop-blur-[2px]" />
    </div>
  );
}
