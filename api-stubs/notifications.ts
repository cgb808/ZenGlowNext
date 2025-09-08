// Notifications API endpoint stub
// TODO: Connect to Supabase and implement real notification logic
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // TODO: Query Supabase for parent notifications
  res.status(200).json([
    {
      id: 'notif-1',
      type: 'MOOD_SHIFT_ALERT',
      message: "Alex's mood has shifted to Anxious. You might want to check in.",
      timestamp: '2023-10-27T09:30:00Z',
      read: false,
    },
  ]);
}
