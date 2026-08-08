import { useEffect, useLayoutEffect, useState } from 'react';
import { RunFrame } from '@tscircuit/runframe/runner';

export default function CircuitCanvas({ 
  projectId, 
  moduleName, 
  onClose, 
  isEmbedded = false 
}: { 
  projectId: string; 
  moduleName: string; 
  onClose: () => void; 
  isEmbedded?: boolean; 
}) {
  const [fsMap, setFsMap] = useState<Record<string, string> | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fix: RunFrame can apply CSS filters globally (e.g. grayscale) that persist
  // after unmount. This cleanup resets them when the component is removed.
  useLayoutEffect(() => {
    const originalBodyFilter = document.body.style.filter;
    const originalBodyWebkit = (document.body.style as any).webkitFilter;
    const originalHtmlFilter = document.documentElement.style.filter;
    const originalHtmlWebkit = (document.documentElement.style as any).webkitFilter;

    const bodyHadGrayscale = document.body.classList.contains('grayscale');
    const htmlHadGrayscale = document.documentElement.classList.contains('grayscale');

    return () => {
      // Restore original filters
      document.body.style.filter = originalBodyFilter;
      (document.body.style as any).webkitFilter = originalBodyWebkit;
      document.documentElement.style.filter = originalHtmlFilter;
      (document.documentElement.style as any).webkitFilter = originalHtmlWebkit;

      // Force clear any inline grayscale filter
      if (document.body.style.filter && document.body.style.filter.includes('grayscale')) {
        document.body.style.filter = '';
      }
      if (document.documentElement.style.filter && document.documentElement.style.filter.includes('grayscale')) {
        document.documentElement.style.filter = '';
      }

      // Force clear classList grayscale if it wasn't there before
      if (!bodyHadGrayscale) {
        document.body.classList.remove('grayscale');
      }
      if (!htmlHadGrayscale) {
        document.documentElement.classList.remove('grayscale');
      }

      // Remove runframe stylesheet to prevent CSS style leaks
      const runframeStyle = document.querySelector('style[data-styles="tscircuit-runframe"]');
      if (runframeStyle) {
        runframeStyle.remove();
      }
    };
  }, []);

  useEffect(() => {
    const loadCircuit = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`/api/projects/${projectId}/modules/${moduleName}/circuit`);
        if (!response.ok) {
          throw new Error(`Failed to fetch circuit: ${response.statusText}`);
        }
        const data = await response.json();
        setFsMap(data);
      } catch (err: any) {
        console.error('Error rendering circuit:', err);
        setError(err.message || 'Unknown error occurred while fetching circuit files.');
      } finally {
        setLoading(false);
      }
    };

    loadCircuit();
  }, [projectId, moduleName]);

  const containerStyle: React.CSSProperties = isEmbedded 
    ? { display: 'flex', flexDirection: 'column', height: '100%', width: '100%', backgroundColor: '#020617', padding: '0rem' }
    : { position: 'fixed', inset: 0, backgroundColor: '#020617', padding: '0.75rem', display: 'flex', flexDirection: 'column', zIndex: 50 };

  return (
    <div style={containerStyle}>
      {/* Keyframe animation injected for spinner rotation */}
      <style>{`
        @keyframes spinner-rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* Canvas Header - Only rendered when NOT embedded */}
      {!isEmbedded && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            backgroundColor: '#0f172a',
            padding: '0.25rem 0.625rem',
            borderRadius: '0.5rem',
            border: '1px solid #1e293b'
          }}>
            <span style={{ color: '#64748b', fontSize: '0.7rem', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              CIRCUIT VIEW
            </span>
            <span style={{ color: '#334155', fontSize: '0.75rem' }}>/</span>
            <span style={{ color: '#38bdf8', fontSize: '0.75rem', fontWeight: 600, fontFamily: 'monospace' }}>
              {moduleName}
            </span>
          </div>

          <button 
            onClick={onClose}
            style={{
              backgroundColor: '#1e293b',
              color: '#ffffff',
              fontWeight: 600,
              padding: '0.375rem 0.875rem',
              borderRadius: '0.5rem',
              border: '1px solid #334155',
              cursor: 'pointer',
              fontSize: '0.75rem'
            }}
          >
            Close
          </button>
        </div>
      )}

      {/* Main Canvas Frame Container */}
      <div 
        id="circuit-container"
        style={{
          flexGrow: 1,
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '1rem',
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        {/* Loading Overlay */}
        {loading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            backgroundColor: '#0f172a',
            zIndex: 10
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{
                width: '2.5rem',
                height: '2.5rem',
                border: '4px solid #0ea5e9',
                borderTopColor: 'transparent',
                borderRadius: '50%',
                animation: 'spinner-rotate 1s linear infinite',
                marginBottom: '1rem'
              }} />
              <span style={{ color: '#94a3b8', fontWeight: 500, fontSize: '0.875rem' }}>
                Loading circuit preview...
              </span>
            </div>
          </div>
        )}

        {/* Error Overlay */}
        {error && (
          <div style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#f87171',
            backgroundColor: '#0f172a',
            padding: '1rem',
            zIndex: 10
          }}>
            <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
              <p style={{ fontWeight: 600, fontSize: '1.125rem', marginBottom: '0.5rem', color: '#fca5a5' }}>
                Error Loading Circuit
              </p>
              <p style={{ fontSize: '0.875rem', opacity: 0.8, marginBottom: '1rem', color: '#f87171' }}>
                {error}
              </p>
              <button 
                onClick={onClose}
                style={{
                  backgroundColor: 'rgba(127, 29, 29, 0.4)',
                  color: '#fecaca',
                  border: '1px solid rgba(185, 28, 28, 0.6)',
                  fontWeight: 500,
                  padding: '0.5rem 1rem',
                  borderRadius: '0.5rem',
                  cursor: 'pointer'
                }}
              >
                Go Back
              </button>
            </div>
          </div>
        )}

        {/* Circuit Renderer */}
        {!loading && !error && fsMap && (
          <RunFrame
            fsMap={fsMap}
            entrypoint={`${moduleName}.tsx`}
            availableTabs={["pcb", "schematic", "cad"]}
            defaultTab="pcb"
          />
        )}
      </div>
    </div>
  );
}