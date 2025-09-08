import React from 'react';
import { render, screen } from '@testing-library/react';
import ZenScoreView from '../ZenScoreView';
import { testChildren, testDailyData } from './zenScoreTestData';

describe('ZenScoreView', () => {
  it('renders Zen Score for all periods with test data', () => {
    render(<ZenScoreView childrenList={testChildren} dailyData={testDailyData} />);
    // Check table headers
    expect(screen.getByText('Period')).toBeInTheDocument();
    expect(screen.getByText('Zen Score')).toBeInTheDocument();
    expect(screen.getByText('Entries')).toBeInTheDocument();
    // Check all periods
    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('This Week')).toBeInTheDocument();
    expect(screen.getByText('This Month')).toBeInTheDocument();
    expect(screen.getByText('Year to Date')).toBeInTheDocument();
    // Check that a Zen Score is rendered for today (should be a number)
    const todayScore = screen.getAllByText(/^[0-9]+$/)[0];
    expect(todayScore).toBeInTheDocument();
  });
});
