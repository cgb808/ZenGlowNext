import { LinearGradient } from 'expo-linear-gradient';
import { MotiView } from 'moti';
import React, { useCallback, useMemo, useState } from 'react';
import {
  Dimensions,
  ImageBackground,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { EnhancedZenMoonAvatar } from '../../components/ZenMoon/EnhancedZenMoonAvatar';

const { width } = Dimensions.get('window');

// Simple color map used by the Bento grid
const zenGlowColors: Record<string, string> = {
  growth: '#00c853',
  calm: '#2a9d8f',
  happy: '#f1c40f',
  curious: '#6c5ce7',
  focused: '#0984e3',
  excited: '#e17055',
};

type ChildInfo = { id: string; name: string; avatar: string };
type ChildActivity = {
  currentMood: string;
  totalMeditation: number;
  recentActivities: string[];
  zenScore: number;
};

const useParentData = () => {
  const [children] = useState<ChildInfo[]>([
    { id: 'child_001', name: 'Alex', avatar: 'Alex' },
    { id: 'child_002', name: 'Bella', avatar: 'Bella' },
  ]);
  const [selectedChildId, setSelectedChildId] = useState('child_001');
  const [activityData] = useState<Record<string, ChildActivity>>({
    child_001: {
      currentMood: 'calm',
      totalMeditation: 25,
      recentActivities: ['Breathing', 'Mindful Walk', 'Sound Scape'],
      zenScore: 82,
    },
    child_002: {
      currentMood: 'curious',
      totalMeditation: 15,
      recentActivities: ['Sound Scape'],
      zenScore: 75,
    },
  });

  const selectedChildData = activityData[selectedChildId];
  const selectedChildInfo = children.find((c) => c.id === selectedChildId);

  return {
    children,
    selectedChildId,
    setSelectedChildId,
    selectedChildData,
    selectedChildInfo,
    allActivityData: activityData,
  };
};

const GlassCard = ({ children, style }: { children: React.ReactNode; style?: object }) => (
  <MotiView
    from={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
    transition={{ type: 'timing', duration: 700 }}
    style={[styles.glassCard, style] as any}
  >
    <LinearGradient
      colors={['rgba(255, 255, 255, 0.25)', 'rgba(255, 255, 255, 0.1)']}
      style={styles.glassGradient}
    >
      {children}
    </LinearGradient>
  </MotiView>
);

const TopLevelCard = React.memo(
  ({
    childInfo,
    childData,
    onDrillDown,
  }: {
    childInfo?: ChildInfo;
    childData?: ChildActivity;
    onDrillDown: () => void;
  }) => (
    <GlassCard>
      <View style={styles.topCardHeader}>
        <Text style={styles.topCardTitle}>{childInfo?.name}'s ZenGlow</Text>
      </View>
      <View style={styles.topCardContent}>
        {/* Use Enhanced avatar; mood maps directly from activity data */}
        <EnhancedZenMoonAvatar
          mood={(childData?.currentMood as any) || 'calm'}
          size={100}
        />
        <View style={styles.topCardMetrics}>
          <Text style={styles.zenScoreLabel}>Zen Score</Text>
          <Text style={styles.zenScoreValue}>{childData?.zenScore}</Text>
        </View>
      </View>
      <TouchableOpacity style={styles.drillDownButton} onPress={onDrillDown}>
        <Text style={styles.drillDownButtonText}>View Details</Text>
      </TouchableOpacity>
    </GlassCard>
  ),
);

const ActivityPill = ({ activity }: { activity: string }) => (
  <View style={styles.activityPill}>
    <Text style={styles.activityText}>{activity}</Text>
  </View>
);

const DetailCard = React.memo(
  ({ childInfo, childData }: { childInfo?: ChildInfo; childData: ChildActivity }) => (
    <View style={styles.detailCard}>
      <View style={styles.detailHeader}>
        <Text style={styles.detailChildName}>{childInfo?.name}'s Day</Text>
      </View>
      <View style={styles.bentoGrid}>
        <View style={[styles.bentoBox, styles.bentoBoxLarge]}>
          <Text style={styles.bentoTitle}>Overall Zen Score</Text>
          <Text style={[styles.bentoLargeText, { color: zenGlowColors.growth }]}>
            {childData.zenScore}
          </Text>
        </View>
        <View style={[styles.bentoBox, styles.bentoBoxSmall]}>
          <Text style={styles.bentoTitle}>Mood</Text>
          <Text
            style={[
              styles.bentoMediumText,
              { color: zenGlowColors[childData.currentMood] || zenGlowColors.calm },
            ]}
          >
            {childData.currentMood}
          </Text>
        </View>
        <View style={[styles.bentoBox, styles.bentoBoxSmall]}>
          <Text style={styles.bentoTitle}>Meditation</Text>
          <Text style={styles.bentoMediumText}>
            {childData.totalMeditation} <Text style={{ fontSize: 16 }}>min</Text>
          </Text>
        </View>
        <View style={[styles.bentoBox, styles.bentoBoxWide]}>
          <Text style={styles.bentoTitle}>Recent Activities</Text>
          <View style={styles.pillsContainer}>
            {childData.recentActivities.map((activity, index) => (
              <ActivityPill key={index} activity={activity} />
            ))}
          </View>
        </View>
      </View>
    </View>
  ),
);

const GlassCardSwiper = React.memo(
  ({
    childrenData,
    allActivityData,
    onClose,
  }: {
    childrenData: ChildInfo[];
    allActivityData: Record<string, ChildActivity>;
    onClose: () => void;
  }) => (
    <MotiView style={styles.swiperContainer} from={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <TouchableOpacity style={styles.closeButton} onPress={onClose}>
        <Text style={styles.closeButtonText}>✕</Text>
      </TouchableOpacity>
      <ScrollView
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        style={{ width, height: '100%' }}
      >
        {childrenData.map((child) => (
          <DetailCard key={child.id} childInfo={child} childData={allActivityData[child.id]} />
        ))}
      </ScrollView>
    </MotiView>
  ),
);

export default function ParentDashboard() {
  const [isDetailedView, setIsDetailedView] = useState(false);
  const { children, selectedChildId, selectedChildData, selectedChildInfo, allActivityData } =
    useParentData();

  const handleDrillDown = useCallback(() => setIsDetailedView(true), []);
  const handleClose = useCallback(() => setIsDetailedView(false), []);

  // Memoize background image
  const bgSource = useMemo(
    () => ({ uri: 'https://www.transparenttextures.com/patterns/soft-wallpaper.png' }),
    [],
  );

  return (
    <ImageBackground source={bgSource} style={styles.safeArea}>
      <LinearGradient colors={['#a8e6cf', '#d7ffde', '#ffaaa5']} style={StyleSheet.absoluteFill} />
      <View style={styles.safeArea}>
        <View style={styles.container}>
          {!isDetailedView ? (
            <TopLevelCard
              childInfo={selectedChildInfo}
              childData={selectedChildData}
              onDrillDown={handleDrillDown}
            />
          ) : (
            <GlassCardSwiper
              childrenData={children}
              allActivityData={allActivityData}
              onClose={handleClose}
            />
          )}
        </View>
      </View>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 },
  glassCard: {
    width: width * 0.9,
    borderRadius: 24,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  glassGradient: { padding: 25, alignItems: 'center' },
  topCardHeader: { marginBottom: 20 },
  topCardTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: 'white',
    textShadowColor: 'rgba(0,0,0,0.2)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  topCardContent: { alignItems: 'center', marginBottom: 30 },
  topCardMetrics: { marginTop: 20, alignItems: 'center' },
  zenScoreLabel: { fontSize: 16, color: 'white', opacity: 0.8 },
  zenScoreValue: {
    fontSize: 52,
    fontWeight: 'bold',
    color: 'white',
    textShadowColor: 'rgba(0,0,0,0.2)',
    textShadowOffset: { width: 2, height: 2 },
    textShadowRadius: 4,
  },
  drillDownButton: {
    backgroundColor: 'rgba(255,255,255,0.3)',
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 25,
  },
  drillDownButtonText: { color: 'white', fontSize: 16, fontWeight: 'bold' },
  swiperContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.1)',
  },
  closeButton: {
    position: 'absolute',
    top: 60,
    right: 20,
    zIndex: 10,
    backgroundColor: 'rgba(0,0,0,0.4)',
    width: 30,
    height: 30,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeButtonText: { color: 'white', fontSize: 18, fontWeight: 'bold' },
  detailCard: { width, justifyContent: 'center', alignItems: 'center', padding: 20 },
  detailHeader: { alignItems: 'center', marginBottom: 20 },
  detailChildName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginTop: 10,
    textShadowColor: 'rgba(0, 0, 0, 0.2)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  bentoGrid: {
    width: '100%',
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  bentoBox: {
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 20,
    padding: 15,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.4)',
  },
  bentoBoxLarge: { width: '100%', height: 150, alignItems: 'center', justifyContent: 'center' },
  bentoBoxSmall: { width: '48%', height: 120, alignItems: 'center', justifyContent: 'center' },
  bentoBoxWide: { width: '100%' },
  bentoTitle: { fontSize: 14, color: 'white', fontWeight: '600', opacity: 0.9, marginBottom: 8 },
  bentoLargeText: { fontSize: 60, fontWeight: 'bold', color: 'white' },
  bentoMediumText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
    textTransform: 'capitalize',
  },
  pillsContainer: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 5 },
  activityPill: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 15,
    paddingHorizontal: 12,
    paddingVertical: 6,
    margin: 4,
  },
  activityText: { color: 'white', fontWeight: '500', fontSize: 12 },
});
