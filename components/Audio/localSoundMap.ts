import type { SoundName } from './ZenSoundProvider';

// Map sound names to locally bundled modules (optional).
// Drop tiny UI sounds into assets/sounds/ui and uncomment examples below.
// Example:
//  export default {
//    zen_click_soft: require('../../assets/sounds/ui/zen_click_soft.mp3'),
//    zen_chime: require('../../assets/sounds/ui/zen_chime.mp3'),
//  } satisfies Partial<Record<SoundName, any>>;

const localSoundMap: Partial<Record<SoundName, any>> = {};

export default localSoundMap;
