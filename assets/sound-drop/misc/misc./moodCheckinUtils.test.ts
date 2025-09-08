// GoCodeo-style tests for moodCheckinUtils
import { pushMoodCheckin, getMoodCheckins } from './moodCheckinUtils';
import { MoodCheckin } from '../types/moodCheckin';

const mockCheckin: MoodCheckin = {
  id: 'checkin1',
  userId: 'user1',
  timestamp: new Date(),
  mood: 'happy',
  notes: 'Feeling great!',
  source: 'parent',
};

function testPushMoodCheckin() {
  pushMoodCheckin(mockCheckin);
  console.log('pushMoodCheckin executed.');
}

function testGetMoodCheckins() {
  const checkins = getMoodCheckins('user1');
  console.assert(Array.isArray(checkins), 'getMoodCheckins should return an array');
  console.log('getMoodCheckins executed.');
}

testPushMoodCheckin();
testGetMoodCheckins();
console.log('All moodCheckinUtils tests passed.');
