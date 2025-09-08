# ZenGlow Audio Acquisition Guide 🎵

This guide will help you find and organize the perfect royalty-free audio for ZenGlow's child-focused meditation app.

## Quick Start 🚀

1. **Drop & Organize**: Place audio files in `./audio-drop/` folder and run:

   ```cmd
   node organizeAudio.js
   ```

2. **Manual Organization**: Use the detailed organizer:

   ```cmd
   cd scripts
   npx ts-node soundOrganizer.ts
   ```

## Audio Requirements 📋

### 🎯 HIGH PRIORITY (Get these first!)

Essential sounds for core app functionality:

**UI Core Sounds:**

- **zen_chime** - Clear, gentle notification chime (kalimba-like)
- **zen_bell** - Soft meditation bell for important moments
- **zen_click_soft** - Subtle button press feedback

**Character Core Sounds:**

- **moon_happy_giggle** - Cute, child-friendly giggle (0.5-1 second)
- **moon_agree_hum** - Pleasant "mmmm" approval sound
- **moon_focused_breath** - Gentle breathing sound for meditation sync

**Meditation Core:**

- **breathing_in_cue** - Soft "breathe in" audio cue
- **breathing_out_cue** - Gentle "breathe out" audio cue
- **meditation_bell** - Traditional meditation bell strike

### 🎵 MEDIUM PRIORITY

Important for full experience:

**UI Enhancement:**

- zen_whoosh - Smooth transition sound
- zen_bubble_pop - Playful interaction feedback
- zen_detected - Gentle "something happened" notification

**Character Personality:**

- moon_disagree_hum - Gentle "hmm?" questioning sound
- moon_maybe_hum - Uncertain "mm-hmm?" sound

**Meditation Support:**

- meditation_start - Begin session tone
- meditation_end - Complete session chime
- focus_timer_tick - Subtle progress tick

**Ambient Foundation:**

- zen_ambient_hum - Calming background tone (loopable)
- nature_soft_wind - Gentle breeze (loopable)
- quiet_rainfall - Light rain ambience (loopable)

### 🌟 NICE TO HAVE

Polish and delight:

**Lullabies:**

- lullaby_custom_zen - Original peaceful melody
- lullaby_brahms_child - Child-appropriate Brahms adaptation
- sleep_transition - Gentle wind-down sound

**Support & Achievement:**

- help_activated - Supportive "help is here" tone
- calm_down_guide - Soothing reset sound
- progress_milestone - Gentle celebration
- new_level_unlock - Soft achievement fanfare

## Search Terms by Category 🔍

### UI Sounds

```
zen chime, kalimba note, positive bell, notification chime
meditation bell, singing bowl, temple bell, tibetan bell
soft click, gentle tap, button press, UI feedback
whoosh transition, gentle swoosh, air movement
bubble pop, water drop, gentle plop, soft burst
zen detected, gentle alert, soft notification
```

### Character Sounds (Child-Safe)

```
child giggle, baby laugh, cute giggle, happy child
gentle hum, approval mmm, positive vocalization
breathing meditation, calm breath, gentle inhale
questioning hm, uncertain sound, maybe hum
disagreement hm, gentle no, soft questioning
```

### Meditation Cues

```
breathe in cue, meditation inhale, breathing guide
breathe out cue, meditation exhale, breath guidance
meditation start, session begin, peaceful opening
meditation end, session complete, gentle closure
focus timer, mindfulness tick, meditation progress
transition bell, movement cue, stretch sound
```

### Ambient Loops

```
zen ambient, peaceful hum, meditation drone, calming tone
soft wind, gentle breeze, nature wind, peaceful air
light rain, gentle rainfall, soft precipitation, rain meditation
meditation om, peaceful chant, zen background
```

### Lullabies

```
zen lullaby, peaceful melody, meditation music box
brahms lullaby child, baby brahms, gentle classical
sleep transition, wind down, peaceful fade, bedtime sound
goodnight hum, peaceful close, gentle ending
```

### Support Sounds

```
help notification, support alert, caring chime
calm down sound, reset tone, peaceful return, gentle guide
safe space, comfort sound, reassuring tone
```

### Achievement

```
gentle celebration, soft achievement, positive milestone
progress sound, accomplishment chime, gentle success
level unlock, new discovery, gentle fanfare
streak continue, consistency reward, gentle pride
```

## Recommended Sources 🌐

### Free/Royalty-Free Sites

- **Freesound.org** - Great for UI clicks and ambient sounds
- **Zapsplat** - Professional sound library (free with account)
- **BBC Sound Effects** - High-quality, completely free
- **YouTube Audio Library** - Reliable, pre-cleared sounds
- **Incompetech** - Kevin MacLeod's music and sounds

### Premium Options

- **Epidemic Sound** - Professional quality, child-safe
- **AudioJungle** - Individual purchase, high quality
- **Pond5** - Extensive meditation/zen collection

## Technical Specifications 🔧

### File Requirements

- **Format:** MP3 (preferred) or WAV
- **Quality:** 44.1kHz, 16-bit minimum
- **Size:** Keep under 100KB for UI sounds, under 1MB for ambient/lullabies
- **Length:** UI sounds 0.5-2 seconds, ambient 30+ seconds (loopable)

### Volume Guidelines

- UI sounds: 0.6-0.8 (clear but not jarring)
- Character sounds: 0.5-0.7 (gentle and friendly)
- Meditation: 0.4-0.6 (calm and peaceful)
- Ambient: 0.3-0.5 (background presence)

## Child Safety Notes ⚠️

### AVOID

- Sudden loud sounds or sharp attacks
- Scary or unsettling tones
- Adult voices (use child or neutral voices only)
- Complex musical content that might distract
- Sounds that could trigger anxiety

### PREFER

- Gentle, organic sounds
- Predictable, comforting audio
- Nature sounds (rain, wind, gentle water)
- Simple musical tones (bells, chimes, kalimba)
- Warm, friendly character sounds

## Testing Checklist ✅

For each sound you acquire:

1. **Volume Test:** Play at various device volumes - never harsh
2. **Child Test:** Would this comfort or delight a 6-year-old?
3. **Context Test:** Does it fit the zen/meditation theme?
4. **Loop Test:** For ambient sounds, does it loop seamlessly?
5. **Quality Test:** Clear audio without artifacts or noise?

## File Organization 📁

Once you have files, the organizer will sort them into:

```
src/assets/sounds/
├── ui/              (interface sounds)
├── character/       (ZenMoon personality)
├── meditation/      (breathing cues, bells)
├── ambient/         (background loops)
├── lullaby/         (sleep sounds)
├── support/         (help/calm sounds)
└── achievement/     (celebration sounds)
```

## Need Help? 🤝

If you find sounds that almost match but need editing:

- **Audacity** (free) - Basic editing, volume adjustment
- **Reaper** (affordable) - Professional editing
- **Online converters** - For format conversion

Remember: Start with HIGH PRIORITY sounds first. Even just the core 9 sounds will make ZenGlow feel much more engaging for children!

The most important thing is that sounds feel **safe, gentle, and delightful** for young users. 🌙✨
