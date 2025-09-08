/**
 * Custom Hook for Audio Playback Management
 * Manages audio loading, playback state, and controls for ZenGlow
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Audio } from 'expo-av';

export function useAudio() {
  const [isLoading, setIsLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [position, setPosition] = useState(0);
  const [error, setError] = useState(null);
  const soundRef = useRef(null);

  // Clean up sound on unmount
  useEffect(() => {
    return () => {
      if (soundRef.current) {
        soundRef.current.unloadAsync();
      }
    };
  }, []);

  // Load audio file
  const loadAudio = useCallback(async (audioUri) => {
    try {
      setIsLoading(true);
      setError(null);

      // Unload previous sound if exists
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }

      // Create new sound
      const { sound } = await Audio.Sound.createAsync(
        { uri: audioUri },
        { shouldPlay: false }
      );

      soundRef.current = sound;

      // Get duration
      const status = await sound.getStatusAsync();
      if (status.isLoaded) {
        setDuration(status.durationMillis || 0);
      }

      setIsLoading(false);
      return true;
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      return false;
    }
  }, []);

  // Play audio
  const play = useCallback(async () => {
    try {
      if (!soundRef.current) {
        throw new Error('No audio loaded');
      }

      await soundRef.current.playAsync();
      setIsPlaying(true);
      setError(null);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  // Pause audio
  const pause = useCallback(async () => {
    try {
      if (!soundRef.current) {
        throw new Error('No audio loaded');
      }

      await soundRef.current.pauseAsync();
      setIsPlaying(false);
      setError(null);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  // Stop audio
  const stop = useCallback(async () => {
    try {
      if (!soundRef.current) {
        throw new Error('No audio loaded');
      }

      await soundRef.current.stopAsync();
      setIsPlaying(false);
      setPosition(0);
      setError(null);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  // Seek to position
  const seekTo = useCallback(async (positionMillis) => {
    try {
      if (!soundRef.current) {
        throw new Error('No audio loaded');
      }

      await soundRef.current.setPositionAsync(positionMillis);
      setPosition(positionMillis);
      setError(null);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  // Set volume
  const setVolume = useCallback(async (volume) => {
    try {
      if (!soundRef.current) {
        throw new Error('No audio loaded');
      }

      // Ensure volume is between 0 and 1
      const clampedVolume = Math.max(0, Math.min(1, volume));
      await soundRef.current.setVolumeAsync(clampedVolume);
      setError(null);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    }
  }, []);

  // Update position (call this periodically when playing)
  const updatePosition = useCallback(async () => {
    try {
      if (!soundRef.current) {
        return;
      }

      const status = await soundRef.current.getStatusAsync();
      if (status.isLoaded) {
        setPosition(status.positionMillis || 0);
        setIsPlaying(status.isPlaying || false);
        
        // If audio finished playing
        if (status.didJustFinish) {
          setIsPlaying(false);
          setPosition(0);
        }
      }
    } catch (err) {
      setError(err.message);
    }
  }, []);

  return {
    // State
    isLoading,
    isPlaying,
    duration,
    position,
    error,

    // Actions
    loadAudio,
    play,
    pause,
    stop,
    seekTo,
    setVolume,
    updatePosition,

    // Computed values
    progress: duration > 0 ? position / duration : 0,
    hasAudio: !!soundRef.current,
    isLoaded: !isLoading && !!soundRef.current,
  };
}