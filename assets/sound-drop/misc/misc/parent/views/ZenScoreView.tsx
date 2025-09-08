import React from 'react';
import { Child, DailyData } from '../../../types/parentDashboard';

interface ZenScoreViewProps {
  childrenList: Child[];
  dailyData: { [key: string]: DailyData };
}

/**
 * ZenScoreView - Aggregated Zen Score view for daily, weekly, monthly, and YTD periods.
 * Combines all children and metrics into a single score and summary.
 */
const periods = [
  { label: 'Today', days: 1 },
  { label: 'This Week', days: 7 },
  { label: 'This Month', days: 30 },
  { label: 'Year to Date', days: 365 },
];

function computeZenScore(data: DailyData[]): number {
  // Example: simple average of normalized metrics (0-100 scale)
  if (!data.length) return 0;
  let total = 0;
  data.forEach((d) => {
    // Normalize each metric to 0-100, then average
    const metrics = [
      Math.min(100, d.fitness || 0),
      Math.min(100, d.mental || 0),
      Math.min(100, d.screenTime ? 100 - d.screenTime : 100), // less screen time = higher score
      Math.min(100, d.exercise || 0),
      Math.min(100, d.breaks || 0),
    ];
    total += metrics.reduce((a, b) => a + b, 0) / metrics.length;
  });
  return Math.round(total / data.length);
}

const ZenScoreView: React.FC<ZenScoreViewProps> = ({ childrenList, dailyData }) => {
  const today = new Date();
  // For each period, aggregate all children and all days in range
  const periodScores = periods.map(({ label, days }) => {
    const start = new Date(today);
    start.setDate(today.getDate() - days + 1);
    const allData: DailyData[] = [];
    Object.entries(dailyData).forEach(([dateStr, data]) => {
      const date = new Date(dateStr);
      if (date >= start && date <= today) {
        allData.push(data);
      }
    });
    return { label, score: computeZenScore(allData), count: allData.length };
  });

  return (
    <div style={{ padding: 16 }}>
      <h2>Zen Score (Aggregated)</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>Period</th>
            <th>Zen Score</th>
            <th>Entries</th>
          </tr>
        </thead>
        <tbody>
          {periodScores.map(({ label, score, count }) => (
            <tr key={label} style={{ borderBottom: '1px solid #eee' }}>
              <td>{label}</td>
              <td
                style={{
                  fontWeight: 'bold',
                  color: score > 80 ? '#22c55e' : score > 60 ? '#eab308' : '#ef4444',
                }}
              >
                {score}
              </td>
              <td>{count}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 16, fontSize: 14, color: '#64748b' }}>
        <b>How is Zen Score calculated?</b> It is an average of fitness, mental, exercise, breaks,
        and (inverted) screen time, normalized to a 0-100 scale.
      </div>
    </div>
  );
};

export default ZenScoreView;
