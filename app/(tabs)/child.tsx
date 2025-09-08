import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FlatList,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type PressableStateCallbackType,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle } from 'react-native-svg';
import { ZenMoonAvatar } from '../../components/ZenMoon/ZenMoonAvatar';

type Theme = {
  background: string;
  primary: string;
  text: string;
  accent: string;
};

const palettes: Record<string, Theme> = {
  earlyMorning: {
    background: '#2c3e50',
    primary: '#34495e',
    text: '#bdc3c7',
    accent: '#f1c40f',
  },
  morning: {
    background: '#fdf6e3',
    primary: '#a3b899',
    text: '#586e75',
    accent: '#85c1e9',
  },
  afternoon: {
    background: '#f4a261',
    primary: '#e76f51',
    text: '#2a9d8f',
    accent: '#ffffff',
  },
  evening: {
    background: '#e5989b',
    primary: '#6d6875',
    text: '#ffcdb2',
    accent: '#4b4453',
  },
  lateNight: {
    background: '#343a40',
    primary: '#495057',
    text: '#adb5bd',
    accent: '#66a5ad',
  },
};

const getThemeByTime = (): Theme => {
  const hour = new Date().getHours();
  if (hour >= 4 && hour < 7) return palettes.earlyMorning;
  if (hour >= 7 && hour < 12) return palettes.morning;
  if (hour >= 12 && hour < 17) return palettes.afternoon;
  if (hour >= 17 && hour < 22) return palettes.evening;
  return palettes.lateNight;
};

type Activity = { id: string; icon: string; title: string; color: string };

const ProgressRing = ({
  progress,
  size = 70,
  strokeWidth = 8,
  color = '#00b894',
}: {
  progress: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - progress * circumference;

  return (
    <View style={{ width: size, height: size }}>
      <Svg width={size} height={size} style={{ transform: [{ rotate: '-90deg' }] }}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={`${color}66`}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
        />
      </Svg>
      <View style={styles.ringCenter}>
        <Text style={{ color, fontWeight: 'bold' }}>{Math.round(progress * 100)}%</Text>
      </View>
    </View>
  );
};

const MoodSelector = ({
  currentMood,
  onMoodSelect,
  theme,
}: {
  currentMood: string;
  onMoodSelect: (mood: string) => void;
  theme: Theme;
}) => {
  const moods = [
    { name: 'calm', emoji: '😌', color: theme.primary },
    { name: 'happy', emoji: '😊', color: theme.accent },
    { name: 'curious', emoji: '🤔', color: theme.text },
    { name: 'focused', emoji: '🎯', color: theme.primary },
    { name: 'excited', emoji: '🤩', color: theme.accent },
  ];

  return (
    <View
      style={[
        styles.card,
        { borderColor: `${theme.accent}33`, backgroundColor: `${theme.text}22` },
      ]}
    >
      <Text style={[styles.cardTitle, { color: theme.text }]}>How are you feeling?</Text>
      <View style={styles.moodsRow}>
        {moods.map((m) => {
          const active = currentMood === m.name;
          return (
            <Pressable
              key={m.name}
              onPress={() => onMoodSelect(m.name)}
              style={({ pressed }: PressableStateCallbackType) => [
                styles.moodItem,
                {
                  backgroundColor: active ? m.color : `${theme.text}33`,
                  transform: [{ scale: pressed || active ? 1.06 : 1 }],
                },
              ]}
            >
              <Text style={styles.moodEmoji}>{m.emoji}</Text>
              <Text
                style={[
                  styles.moodLabel,
                  { color: theme.text, fontWeight: active ? ('700' as const) : '400' },
                ]}
              >
                {m.name}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
};

const ActivityButton = ({
  icon,
  title,
  color,
  onPress,
  completed,
  theme,
}: {
  icon: string;
  title: string;
  color: string;
  onPress: () => void;
  completed: boolean;
  theme: Theme;
}) => {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }: PressableStateCallbackType) => [
        styles.activity,
        {
          backgroundColor: completed ? theme.accent : color,
          borderColor: `${theme.text}22`,
          transform: [{ scale: pressed ? 0.97 : 1 }],
          opacity: pressed ? 0.9 : 1,
          shadowColor: Platform.OS === 'ios' ? '#000' : 'transparent',
        },
      ]}
    >
      <Text style={styles.activityIcon}>{completed ? '✅' : icon}</Text>
      <Text style={[styles.activityTitle, { color: theme.text }]}>{title}</Text>
      {completed && <Text style={[styles.activityDone, { color: theme.text }]}>Complete!</Text>}
    </Pressable>
  );
};

export default function ChildDashboard() {
  const [currentMood, setCurrentMood] = useState<string>('calm');
  const [meditationProgress, setMeditationProgress] = useState<number>(0.3);
  const [completedActivities, setCompletedActivities] = useState<Set<string>>(new Set());
  const [zenScore, setZenScore] = useState<number>(75);
  const [dailyGoals, setDailyGoals] = useState({
    meditation: 0.6,
    exercise: 0.8,
    mindfulness: 0.4,
  });
  const [loaded, setLoaded] = useState<boolean>(false);
  const [theme, setTheme] = useState<Theme>(getThemeByTime());

  useEffect(() => {
    setLoaded(true);
    const id = setInterval(() => setTheme(getThemeByTime()), 60000);
    return () => clearInterval(id);
  }, []);

  const activities: Activity[] = useMemo(
    () => [
      { id: 'breathing', icon: '🫁', title: 'Breathing Exercise', color: theme.primary },
      { id: 'walk', icon: '🚶‍♀️', title: 'Mindful Walk', color: theme.accent },
      { id: 'sounds', icon: '🎵', title: 'Sound Scape', color: theme.text },
      { id: 'journal', icon: '📝', title: 'Feelings Journal', color: theme.primary },
      { id: 'gratitude', icon: '🙏', title: 'Gratitude Time', color: theme.accent },
      { id: 'family', icon: '👨‍👩‍👧‍👦', title: 'Family Chat', color: theme.text },
    ],
    [theme],
  );

  const handleMoodSelect = useCallback((mood: string) => setCurrentMood(mood), []);

  const handleActivityPress = useCallback(
    (activityId: string) => {
      if (completedActivities.has(activityId)) return;
      setCompletedActivities((prev) => new Set([...prev, activityId]));
      setMeditationProgress((p) => Math.min(p + 0.15, 1));
      setZenScore((p) => Math.min(p + 5, 100));
    },
    [completedActivities],
  );

  const getTimeBasedGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 4 && hour < 7) return 'Good early morning! 🌅';
    if (hour >= 7 && hour < 12) return 'Good morning! ☀️';
    if (hour >= 12 && hour < 17) return 'Good afternoon! 🌞';
    if (hour >= 17 && hour < 22) return 'Good evening! 🌇';
    return 'Good night! 🌙';
  };

  const encouragementMessages = [
    "You're doing great! 🌟",
    'Keep up the zen vibes! ✨',
    'Your inner peace is growing! 🌱',
    'Awesome mindfulness today! 🧘‍♀️',
  ];
  const currentMessage =
    encouragementMessages[Math.floor(zenScore / 25) % encouragementMessages.length];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.background }}>
      <ScrollView contentContainerStyle={styles.container}>
        <View
          style={[
            styles.headerCard,
            {
              borderColor: `${theme.accent}33`,
              backgroundColor: `${theme.text}22`,
              opacity: loaded ? 1 : 0,
              transform: [{ translateY: loaded ? 0 : -30 }],
            },
          ]}
        >
          <Text style={[styles.greeting, { color: theme.text }]}>{getTimeBasedGreeting()}</Text>
          <Text style={[styles.subGreeting, { color: theme.accent }]}>Hi Alex! 👋</Text>
          <ZenMoonAvatar mood="calm" enableAura enableInteraction meditationProgress={meditationProgress} />
          <Text style={[styles.encouragement, { color: theme.text }]}>{currentMessage}</Text>
        </View>

        <View style={{ opacity: loaded ? 1 : 0, transform: [{ translateX: loaded ? 0 : -30 }] }}>
          <MoodSelector currentMood={currentMood} onMoodSelect={handleMoodSelect} theme={theme} />
        </View>

        <View
          style={[
            styles.card,
            {
              borderColor: `${theme.accent}33`,
              backgroundColor: `${theme.text}22`,
              opacity: loaded ? 1 : 0,
              transform: [{ translateX: loaded ? 0 : 30 }],
            },
          ]}
        >
          <Text style={[styles.cardTitle, { color: theme.text }]}>Today's Zen Journey</Text>
          <View style={styles.progressRow}>
            <View style={styles.progressItem}>
              <ProgressRing progress={dailyGoals.meditation} color={theme.accent} />
              <Text style={[styles.progressLabel, { color: theme.text }]}>Meditation</Text>
            </View>
            <View style={styles.progressItem}>
              <ProgressRing progress={dailyGoals.exercise} color={theme.primary} />
              <Text style={[styles.progressLabel, { color: theme.text }]}>Movement</Text>
            </View>
            <View style={styles.progressItem}>
              <ProgressRing progress={dailyGoals.mindfulness} color={theme.text} />
              <Text style={[styles.progressLabel, { color: theme.text }]}>Mindfulness</Text>
            </View>
          </View>
          <View
            style={[
              styles.zenScore,
              { backgroundColor: `${theme.accent}22`, borderColor: `${theme.accent}33` },
            ]}
          >
            <Text style={[styles.zenScoreLabel, { color: theme.text }]}>Zen Score</Text>
            <Text style={[styles.zenScoreValue, { color: theme.accent }]}>{zenScore}</Text>
          </View>
        </View>

        <View style={{ opacity: loaded ? 1 : 0, transform: [{ translateY: loaded ? 0 : 30 }] }}>
          <Text
            style={[styles.cardTitle, { color: theme.text, textAlign: 'center', marginBottom: 10 }]}
          >
            Today's Activities
          </Text>
          <FlatList
            data={activities}
            keyExtractor={(item) => item.id}
            numColumns={2}
            columnWrapperStyle={{ gap: 12 }}
            contentContainerStyle={{ gap: 12 }}
            renderItem={({ item }) => (
              <View style={{ flex: 1 }}>
                <ActivityButton
                  icon={item.icon}
                  title={item.title}
                  color={item.color}
                  onPress={() => handleActivityPress(item.id)}
                  completed={completedActivities.has(item.id)}
                  theme={theme}
                />
              </View>
            )}
          />
        </View>

        <View style={{ height: 24 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
  },
  headerCard: {
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    alignItems: 'center',
    marginBottom: 16,
  },
  greeting: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
  },
  subGreeting: {
    fontSize: 16,
    marginTop: 4,
    marginBottom: 12,
  },
  encouragement: {
    fontSize: 16,
    marginTop: 12,
    opacity: 0.9,
    textAlign: 'center',
  },
  card: {
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    marginBottom: 16,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 12,
    textAlign: 'center',
  },
  moodsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around',
    gap: 10,
  },
  moodItem: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 50,
    minWidth: 56,
    alignItems: 'center',
    marginVertical: 4,
  },
  moodEmoji: {
    fontSize: 24,
  },
  moodLabel: {
    fontSize: 10,
    marginTop: 4,
    textTransform: 'capitalize',
  },
  progressRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  progressItem: {
    alignItems: 'center',
  },
  progressLabel: {
    fontSize: 12,
    marginTop: 8,
  },
  zenScore: {
    marginTop: 16,
    paddingVertical: 12,
    borderRadius: 16,
    alignItems: 'center',
    borderWidth: 1,
  },
  zenScoreLabel: {
    fontSize: 14,
    opacity: 0.8,
  },
  zenScoreValue: {
    fontSize: 32,
    fontWeight: '800',
    marginTop: 4,
  },
  activity: {
    flex: 1,
    minHeight: 120,
    borderRadius: 18,
    padding: 16,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    ...Platform.select({
      ios: {
        shadowOpacity: 0.15,
        shadowRadius: 6,
        shadowOffset: { width: 0, height: 4 },
      },
      android: { elevation: 2 },
      default: {},
    }),
  },
  activityIcon: { fontSize: 36, marginBottom: 6 },
  activityTitle: { fontSize: 14, fontWeight: '700', textAlign: 'center' },
  activityDone: { fontSize: 12, marginTop: 4 },
  ringCenter: {
    position: 'absolute',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
