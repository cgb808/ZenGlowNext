import React from 'react';
import { Child, DailyData, Supplement } from '../../../types/parentDashboard';

interface DailyViewProps {
  selectedChild: string;
  childrenList: Child[];
  dailyData: { [key: string]: DailyData };
  supplements: Supplement[];
}

/**
 * DailyView - Dashboard view for daily metrics, supplements, and activity summary.
 */
const DailyView: React.FC<DailyViewProps> = ({
  selectedChild,
  childrenList,
  dailyData,
  supplements,
}) => {
  // Find the child object
  const child = childrenList.find((c) => c.name === selectedChild);
  // Get today's date key
  const todayKey = new Date().toISOString().slice(0, 10);
  const todayData = dailyData[todayKey];

  return (
    <div style={{ padding: 16 }}>
      <h2>Daily Summary for {selectedChild}</h2>
      {child && (
        <div style={{ marginBottom: 12 }}>
          <strong>Age:</strong> {child.age} &nbsp;|&nbsp; <strong>Device:</strong> {child.device}
        </div>
      )}
      {todayData ? (
        <>
          <div>
            <strong>Screen Time:</strong> {todayData.screenTime} min
          </div>
          <div>
            <strong>Exercise:</strong> {todayData.exercise} min
          </div>
          <div>
            <strong>Fitness:</strong> {todayData.fitness}
          </div>
          <div>
            <strong>Mental:</strong> {todayData.mental}
          </div>
          <div>
            <strong>Breaks:</strong> {todayData.breaks}
          </div>
          <div>
            <strong>Achievements:</strong> {todayData.achievements?.join(', ') || 'None'}
          </div>
          <div>
            <strong>Notes:</strong> {todayData.notes || '-'}
          </div>
          <div style={{ marginTop: 12 }}>
            <strong>Supplements Taken:</strong>
            <ul>
              {todayData.supplements?.length > 0 ? (
                todayData.supplements.map((id) => {
                  const supp = supplements.find((s) => s.id === id);
                  return supp ? (
                    <li key={id}>
                      <b>{supp.name}</b> ({supp.dosage}) - {supp.benefits?.[0] || ''}
                    </li>
                  ) : null;
                })
              ) : (
                <li>None</li>
              )}
            </ul>
          </div>
        </>
      ) : (
        <div>No data for today.</div>
      )}
    </div>
  );
};

export default DailyView;
