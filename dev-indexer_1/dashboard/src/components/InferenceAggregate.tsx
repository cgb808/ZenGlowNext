import React, { useEffect, useState } from 'react';

type AggregateWindow = {
  window: string;
  available: boolean;
  models?: {
    model: string;
    events: number;
    avg_prob: number;
    avg_avg_logprob: number;
    avg_entropy: number;
    avg_top1_prob: number;
    avg_latency_ms: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    decisions: Record<string, number>;
  }[];
};

export const InferenceAggregate: React.FC = () => {
  const [data, setData] = useState<AggregateWindow[]>([]);

  const fetchAgg = async () => {
    try {
      const res = await fetch('/inference/aggregate?windows=1 hour,24 hours');
      const j = await res.json();
      setData(j.windows || []);
    } catch (e) {
      // swallow
    }
  };

  useEffect(() => {
    fetchAgg();
    const id = setInterval(fetchAgg, 15000);
    return () => clearInterval(id);
  }, []);

  return (
    <div style={{ border: '1px solid #333', borderRadius: 6 }}>
      <div style={{ background: '#111', color: '#eee', padding: '0.5rem 0.75rem', fontSize: 14, fontWeight: 600 }}>Inference Aggregates</div>
      <div style={{ display: 'flex', gap: '1.5rem', padding: '0.75rem', flexWrap: 'wrap' }}>
        {data.map((w, wi) => (
          <div key={wi} style={{ minWidth: 260 }}>
            <h4 style={{ margin: '0 0 0.25rem 0', fontSize: 13, color: '#ccc' }}>{w.window}</h4>
            {!w.available && <div style={{ fontSize: 12, color: '#888' }}>n/a</div>}
            {w.available && (w.models || []).map((m, mi) => (
              <div key={mi} style={{ fontSize: 12, padding: '0.25rem 0', borderBottom: '1px solid #222' }}>
                <strong>{m.model}</strong> ({m.events}) p~{m.avg_prob.toFixed(3)} H {m.avg_entropy.toFixed(2)} L {m.avg_latency_ms.toFixed(0)}ms
                <div style={{ marginTop: 2 }}>
                  {Object.entries(m.decisions).map(([d, c]) => (
                    <span key={d} style={{ marginRight: 6 }}>{d}:{c}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};
