import { Button, StyleSheet, Text, View } from 'react-native';
import { useCompanionAI } from '../../hooks/useCompanionAI';

export default function Index() {
  // Use the hook to get the action functions
  // TODO: Get actual familyId and childId from user context/navigation
  const { mood, nextAction, decideNextAction } = useCompanionAI('default-family', 'default-child');

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Companion Test Controls</Text>
      <View style={styles.buttonContainer}>
        <Button
          title={`Mood: ${mood} (Tap to Idle)`}
          onPress={() => decideNextAction({ trigger: 'idle' })}
        />
      </View>
      <View style={styles.buttonContainer}>
        <Button
          title="🤔 Look At Center"
          onPress={() =>
            decideNextAction({
              trigger: 'user_tap',
              targetElement: { x: 180, y: 350, width: 50, height: 50 },
            })
          }
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#f0f4f8',
  },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 20, color: '#333' },
  buttonContainer: { marginVertical: 10, width: '80%' },
});
