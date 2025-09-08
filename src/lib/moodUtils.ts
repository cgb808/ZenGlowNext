// TODO: Centralize mood mapping and utility functions here.

export type Mood = 'calm' | 'anxious' | 'happy' | 'sad' | 'neutral';

/**
 * Maps a mood string to a corresponding color.
 * @param mood The mood to map.
 * @returns A hex color string.
 */
export const getMoodColor = (mood: Mood): string => {
  const colorMap: Record<Mood, string> = {
    calm: '#AEEEEE',
    anxious: '#FFA07A',
    happy: '#FFD700',
    sad: '#B0C4DE',
    neutral: '#E0E0E0',
  };
  return colorMap[mood] || colorMap.neutral;
};

/**
 * Maps a mood string to an emoji.
 * @param mood The mood to map.
 * @returns An emoji character.
 */
export const getMoodEmoji = (mood: Mood): string => {
  const emojiMap: Record<Mood, string> = {
    calm: '😌',
    anxious: '😟',
    happy: '😊',
    sad: '😢',
    neutral: '😐',
  };
  return emojiMap[mood] || emojiMap.neutral;
};
