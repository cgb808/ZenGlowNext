import React from 'react';
import { Child, DailyData, Supplement } from '../../../types/parentDashboard';

interface TrendsViewProps {
  selectedChild: string;
  childrenList: Child[];
  dailyData: { [key: string]: DailyData };
  supplements: Supplement[];
}

/**
 * TrendsView - Dashboard view for analytics and long-term patterns.
 */
const TrendsView: React.FC<TrendsViewProps> = ({
  selectedChild,
  childrenList,
  dailyData,
  supplements,
}) => {
  // Find the child object
  const child = childrenList.find((c) => c.name === selectedChild);
  // Get all available days for this child
  const allDays = Object.keys(dailyData);
  // Calculate averages
  let totalScreen = 0,
    totalExercise = 0,
    totalFitness = 0,
    totalMental = 0,
    totalBreaks = 0,
    count = 0;
  allDays.forEach((key) => {
    const data = dailyData[key];
    if (data) {
      totalScreen += data.screenTime || 0;
      totalExercise += data.exercise || 0;
      totalFitness += data.fitness || 0;
      totalMental += data.mental || 0;
      totalBreaks += data.breaks || 0;
      count++;
    }
  });
  const avg = (val: number) => (count ? (val / count).toFixed(1) : '-');

  return (
    <div style={{ padding: 16 }}>
      <h2>Trends & Analytics for {selectedChild}</h2>
      {child && (
        <div style={{ marginBottom: 12 }}>
          <strong>Age:</strong> {child.age} &nbsp;|&nbsp; <strong>Device:</strong> {child.device}
        </div>
      )}
      <div>
        <strong>Average Screen Time:</strong> {avg(totalScreen)} min
      </div>
      <div>
        <strong>Average Exercise:</strong> {avg(totalExercise)} min
      </div>
      <div>
        <strong>Average Fitness:</strong> {avg(totalFitness)}
      </div>
      <div>
        <strong>Average Mental:</strong> {avg(totalMental)}
      </div>
      <div>
        <strong>Average Breaks:</strong> {avg(totalBreaks)}
      </div>
      <div style={{ marginTop: 12 }}>
        <strong>Most Common Supplements:</strong>
        <ul>
          {/* Simple count of supplement IDs */}
          {(() => {
            const suppCount: { [id: number]: number } = {};
            allDays.forEach((key) => {
              const data = dailyData[key];
              data?.supplements?.forEach((id) => {
                suppCount[id] = (suppCount[id] || 0) + 1;
              });
            });
            const sorted = Object.entries(suppCount).sort((a, b) => b[1] - a[1]);
            return sorted.length > 0 ? (
              sorted.slice(0, 3).map(([id, count]) => {
                const supp = supplements.find((s) => s.id === Number(id));
                return supp ? (
                  <li key={id}>
                    <b>{supp.name}</b> ({count} days)
                  </li>
                ) : null;
              })
            ) : (
              <li>None</li>
            );
          })()}
        </ul>
      </div>
    </div>
  );
};

export default TrendsView;
