// Mood Check-in API endpoint stub
// TODO: Connect to Supabase and implement real check-in logic
import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'POST') {
    // const { childId, message } = req.body;
    // TODO: Store check-in request in Supabase
    res.status(200).json({
      status: 'success',
      message: 'Mood check-in request sent to Alex.',
      checkinId: 'checkin-abc-987',
    });
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}
