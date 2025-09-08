import { Child, DailyData } from '../../../../types/parentDashboard';

export const testChildren: Child[] = [
  {
    id: 1,
    name: 'Ava',
    age: 8,
    avatar: 'ava.png',
    status: 'active',
    device: 'iPad',
  },
  {
    id: 2,
    name: 'Ben',
    age: 10,
    avatar: 'ben.png',
    status: 'active',
    device: 'Android Tablet',
  },
  {
    id: 3,
    name: 'Mia',
    age: 6,
    avatar: 'mia.png',
    status: 'active',
    device: 'iPad',
  },
];

// Helper to get ISO date string for N days ago
function daysAgo(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

export const testDailyData: { [key: string]: DailyData } = {
  [daysAgo(0)]: {
    supplements: [1, 2],
    fitness: 80,
    mental: 90,
    notes: 'Great day!',
    screenTime: 60,
    exercise: 40,
    breaks: 3,
    achievements: ['Read a book', 'Helped sibling'],
  },
  [daysAgo(1)]: {
    supplements: [2],
    fitness: 70,
    mental: 85,
    notes: '',
    screenTime: 90,
    exercise: 30,
    breaks: 2,
    achievements: ['Did homework'],
  },
  [daysAgo(2)]: {
    supplements: [1],
    fitness: 60,
    mental: 70,
    notes: 'Tired',
    screenTime: 120,
    exercise: 20,
    breaks: 1,
    achievements: [],
  },
  [daysAgo(3)]: {
    supplements: [],
    fitness: 90,
    mental: 95,
    notes: 'Excellent!',
    screenTime: 45,
    exercise: 50,
    breaks: 4,
    achievements: ['Won a game'],
  },
  [daysAgo(4)]: {
    supplements: [1, 2],
    fitness: 85,
    mental: 80,
    notes: 'Good focus',
    screenTime: 70,
    exercise: 35,
    breaks: 2,
    achievements: ['Practiced piano'],
  },
};
