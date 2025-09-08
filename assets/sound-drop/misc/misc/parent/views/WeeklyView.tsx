import React from 'react';
import { Child, DailyData, Supplement } from '../../../types/parentDashboard';

interface WeeklyViewProps {
  selectedChild: string;
  childrenList: Child[];
  dailyData: { [key: string]: DailyData };
  supplements: Supplement[];
}

/**
 * WeeklyView - Dashboard view for 7-day trends and progress.
 */
const WeeklyView: React.FC<WeeklyViewProps> = ({
  selectedChild,
  childrenList,
  dailyData,
  supplements,
}) => {
  // Find the child object
  const child = childrenList.find((c) => c.name === selectedChild);
  // Get last 7 days' keys
  const today = new Date();
  const days: string[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    days.push(d.toISOString().slice(0, 10));
  }

  return (
    <div style={{ padding: 16 }}>
      <h2>Weekly Trends for {selectedChild}</h2>
      {child && (
        <div style={{ marginBottom: 12 }}>
          <strong>Age:</strong> {child.age} &nbsp;|&nbsp; <strong>Device:</strong> {child.device}
        </div>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th>Date</th>
            <th>Screen Time</th>
            <th>Exercise</th>
            <th>Fitness</th>
            <th>Mental</th>
            <th>Breaks</th>
            <th>Supplements</th>
          </tr>
        </thead>
        <tbody>
          {days.map((key) => {
            const data = dailyData[key];
            return (
              <tr key={key} style={{ borderBottom: '1px solid #eee' }}>
                <td>{key}</td>
                <td>{data ? data.screenTime : '-'}</td>
                <td>{data ? data.exercise : '-'}</td>
                <td>{data ? data.fitness : '-'}</td>
                <td>{data ? data.mental : '-'}</td>
                <td>{data ? data.breaks : '-'}</td>
                <td>
                  {data && data.supplements?.length > 0
                    ? data.supplements.map((id) => {
                        const supp = supplements.find((s) => s.id === id);
                        return supp ? <span key={id}>{supp.name} </span> : null;
                      })
                    : '-'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default WeeklyView;
