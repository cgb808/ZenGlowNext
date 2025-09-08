import React, { useEffect, useRef, useState } from 'react';

type TickerEvent = {
  ts: string;
  model: string;
  decision: string;
  avg_prob: number;
  avg_logprob: number;
  top1_pct: number;
  entropy: number;
  latency_ms: number;
  color: string;
  tokens: { prompt: number; completion: number };
};

export const InferenceTicker: React.FC = () => {
  const [events, setEvents] = useState<TickerEvent[]>([]);
  const [available, setAvailable] = useState(true);
  const timer = useRef<number | null>(null);

  const fetchData = async () => {
    try {
      const res = await fetch('/inference/ticker?limit=30');
      const j = await res.json();
      if (!j.available) {
        setAvailable(false);
        return;
      }
      setAvailable(true);
      setEvents(j.events || []);
    } catch (e) {
      setAvailable(false);
    }
  };

  useEffect(() => {
    fetchData();
    timer.current = window.setInterval(fetchData, 4000);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, []);

  if (!available) {
    return <div style={{ padding: '0.5rem', background: '#222', color: '#ccc' }}>Inference ticker unavailable</div>;
  }

  return (
    <div style={{ border: '1px solid #333', borderRadius: 6, overflow: 'hidden' }}>
      <div style={{ background: '#111', color: '#eee', padding: '0.5rem 0.75rem', fontSize: 14, fontWeight: 600 }}>Inference Ticker</div>
      <div style={{ display: 'flex', gap: '2rem', animation: 'scroll-left 30s linear infinite', whiteSpace: 'nowrap', padding: '0.5rem' }}>
        {events.map((e, i) => (
          <div key={i} style={{ color: e.color, display: 'flex', flexDirection: 'column', fontSize: 12 }}>
            <span style={{ fontWeight: 600 }}>{e.model}</span>
            <span>{e.decision}</span>
            <span>p~{e.avg_prob.toFixed(3)} top1 {e.top1_pct.toFixed(1)}%</span>
            <span>H {e.entropy.toFixed(2)} L {e.latency_ms}ms</span>
          </div>
        ))}
      </div>
      <style>{`@keyframes scroll-left { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }`}</style>
    </div>
  );
};
