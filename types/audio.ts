// Audio Types and Sound Management

export interface AudioTrack {
  id: string;
  name: string;
  url: string;
  duration: number;
  category: 'meditation' | 'nature' | 'white-noise' | 'music';
  volume?: number;
}

export interface PlaybackState {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
}

export interface AudioPlayerConfig {
  autoPlay?: boolean;
  loop?: boolean;
  volume?: number;
  preload?: boolean;
}

export interface SoundEffect {
  id: string;
  name: string;
  url: string;
  volume?: number;
  category: 'ui' | 'notification' | 'feedback' | 'ambient';
}

export interface AudioContext {
  currentTrack: AudioTrack | null;
  playbackState: PlaybackState;
  playlist: AudioTrack[];
  soundEffects: SoundEffect[];
  play: (track: AudioTrack) => Promise<void>;
  pause: () => void;
  stop: () => void;
  setVolume: (volume: number) => void;
  playSound: (soundId: string) => Promise<void>;
  loadPlaylist: (tracks: AudioTrack[]) => void;
}

export type AudioEvent = 
  | 'trackStart'
  | 'trackEnd'
  | 'trackPause'
  | 'trackResume'
  | 'volumeChange'
  | 'playlistChange'
  | 'error';

export interface AudioEventPayload {
  event: AudioEvent;
  track?: AudioTrack;
  error?: Error;
  data?: any;
}