import React, { useState, useEffect, useMemo } from 'react';
import { Heart, Zap, Brain, Sparkles, Wind, Sun, Star, Moon } from 'lucide-react';

// Enhanced Zen color palette with more depth
const zenColors = {
  calm: {
    primary: '#4A90E2', 
    secondary: '#7BB3F0', 
    accent: '#A8D0F7',
    glow: '#2E86DE',
    particle: '#6FAADB',
    texture: '#3498DB',
    shadow: '#2980B9'
  },
  curious: {
    primary: '#E67E22', 
    secondary: '#F39C12', 
    accent: '#F7DC6F',
    glow: '#D35400',
    particle: '#F39C12',
    texture: '#FF8C42',
    shadow: '#C0392B'
  },
  joyful: {
    primary: '#27AE60', 
    secondary: '#58D68D', 
    accent: '#85E085',
    glow: '#229954',
    particle: '#48C9B0',
    texture: '#2ECC71',
    shadow: '#1E8449'
  },
  focused: {
    primary: '#8E44AD', 
    secondary: '#BB8FCE', 
    accent: '#D7BDE2',
    glow: '#7D3C98',
    particle: '#A569BD',
    texture: '#9B59B6',
    shadow: '#6C3483'
  },
  playful: {
    primary: '#E91E63', 
    secondary: '#F06292', 
    accent: '#F8BBD9',
    glow: '#C2185B',
    particle: '#EC407A',
    texture: '#FF6B9D',
    shadow: '#AD1457'
  },
  sleepy: {
    primary: '#5D4E75', 
    secondary: '#8E7CC3', 
    accent: '#B39DDB',
    glow: '#512DA8',
    particle: '#7E57C2',
    texture: '#673AB7',
    shadow: '#4A148C'
  }
};

// Dramatic expressions with exaggerated features
const expressions = {
  calm: { 
    eyeScale: 0.9, 
    eyeAngle: 0, 
    mouthScale: 1.1, 
    mouthCurve: 15,
    cheekSize: 1.2,
    eyebrowAngle: -5,
    specialEffect: 'gentle-glow'
  },
  curious: { 
    eyeScale: 1.4, 
    eyeAngle: 3, 
    mouthScale: 0.8, 
    mouthCurve: 8,
    cheekSize: 1.0,
    eyebrowAngle: 15,
    specialEffect: 'sparkle-eyes'
  },
  joyful: { 
    eyeScale: 1.2, 
    eyeAngle: -8, 
    mouthScale: 1.8, 
    mouthCurve: 25,
    cheekSize: 1.6,
    eyebrowAngle: -10,
    specialEffect: 'joy-burst'
  },
  focused: { 
    eyeScale: 0.7, 
    eyeAngle: 0, 
    mouthScale: 0.6, 
    mouthCurve: 2,
    cheekSize: 0.8,
    eyebrowAngle: 25,
    specialEffect: 'laser-focus'
  },
  playful: { 
    eyeScale: 1.3, 
    eyeAngle: 5, 
    mouthScale: 1.4, 
    mouthCurve: 20,
    cheekSize: 1.4,
    eyebrowAngle: -15,
    specialEffect: 'mischief-sparkle'
  },
  sleepy: { 
    eyeScale: 0.4, 
    eyeAngle: 0, 
    mouthScale: 1.2, 
    mouthCurve: -5,
    cheekSize: 1.1,
    eyebrowAngle: -20,
    specialEffect: 'dream-drift'
  }
};

// Optimized particle system with performance improvements
const ParticleSystem = ({ mood, zenScore, behavior, count = 12 }) => {
  const colors = zenColors[mood];
  const [particles, setParticles] = useState([]);

  const particleCount = useMemo(() => Math.min(count, 8 + Math.floor(zenScore / 10)), [count, zenScore]);

  useEffect(() => {
    const newParticles = Array.from({ length: particleCount }, (_, i) => ({
      id: i,
      x: 30 + (Math.random() * 40),
      y: 20 + (Math.random() * 60),
      size: 2 + Math.random() * 4,
      speed: 0.5 + Math.random() * 1.5,
      direction: Math.random() * Math.PI * 2,
      opacity: 0.3 + Math.random() * 0.7,
      type: ['sparkle', 'glow', 'star', 'dot'][Math.floor(Math.random() * 4)]
    }));
    setParticles(newParticles);
  }, [mood, zenScore, particleCount]);

  const getParticleStyle = (particle) => {
    const intensity = zenScore / 100;
    const behaviorMultiplier = behavior === 'celebrating' ? 2 : behavior === 'meditation' ? 1.5 : 1;
    
    return {
      position: 'absolute',
      left: `${particle.x}%`,
      top: `${particle.y}%`,
      width: particle.size * intensity * behaviorMultiplier,
      height: particle.size * intensity * behaviorMultiplier,
      opacity: particle.opacity * intensity,
      animation: `particle-${particle.type}-${behavior} ${2 + particle.speed}s infinite ease-in-out`,
      animationDelay: `${particle.id * 0.2}s`
    };
  };

  const renderParticle = (particle) => {
    const style = { filter: `drop-shadow(0 0 4px ${colors.glow})` };
    
    switch(particle.type) {
      case 'sparkle':
        return <Sparkles className="text-yellow-300" style={style} />;
      case 'star':
        return <Star className="text-white" style={{ color: colors.accent, ...style }} />;
      case 'glow':
        return <div className="rounded-full" style={{ backgroundColor: colors.particle, boxShadow: `0 0 8px ${colors.glow}` }} />;
      default:
        return <div className="rounded-full" style={{ backgroundColor: colors.primary }} />;
    }
  };

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      {particles.map(particle => (
        <div key={particle.id} style={getParticleStyle(particle)}>
          {renderParticle(particle)}
        </div>
      ))}
    </div>
  );
};

// Textured moon base with craters and surface features
const TexturedMoonBase = ({ mood, size, zenScore, behavior }) => {
  const colors = zenColors[mood];
  const intensity = zenScore / 100;

  const craters = useMemo(() => 
    Array.from({ length: 8 }, (_, i) => ({
      x: 15 + (Math.random() * 70),
      y: 15 + (Math.random() * 70),
      size: 8 + Math.random() * 15,
      depth: 0.3 + Math.random() * 0.4
    })), [mood]
  );

  const getBehaviorTransform = () => {
    switch(behavior) {
      case 'celebrating': return 'scale(1.1) rotate(5deg)';
      case 'meditation': return 'scale(1.05)';
      case 'thinking': return 'rotate(2deg)';
      case 'responding': return 'scale(1.08)';
      default: return 'scale(1)';
    }
  };

  return (
    <div 
      className="relative rounded-full transition-all duration-1000 ease-in-out"
      style={{
        width: size,
        height: size,
        background: `
          radial-gradient(circle at 30% 30%, ${colors.accent} 0%, transparent 50%),
          radial-gradient(circle at 70% 20%, ${colors.secondary}60 0%, transparent 40%),
          radial-gradient(circle at 20% 80%, ${colors.primary}40 0%, transparent 30%),
          linear-gradient(135deg, ${colors.primary} 0%, ${colors.secondary} 50%, ${colors.accent} 100%)
        `,
        boxShadow: `
          0 0 ${20 + intensity * 30}px ${colors.glow}${Math.floor(intensity * 80 + 20).toString(16)},
          inset 0 0 ${30 + intensity * 20}px ${colors.accent}60,
          inset ${5 + intensity * 10}px ${5 + intensity * 10}px ${20 + intensity * 10}px ${colors.shadow}30,
          0 ${8 + intensity * 12}px ${32 + intensity * 20}px rgba(0,0,0,0.3)
        `,
        transform: getBehaviorTransform(),
        filter: `saturate(${1 + intensity * 0.5}) brightness(${0.9 + intensity * 0.3})`
      }}
    >
      {/* Surface craters and texture */}
      {craters.map((crater, i) => (
        <div
          key={i}
          className="absolute rounded-full transition-all duration-700"
          style={{
            left: `${crater.x}%`,
            top: `${crater.y}%`,
            width: `${crater.size}%`,
            height: `${crater.size}%`,
            background: `radial-gradient(circle, ${colors.shadow}${Math.floor(crater.depth * 100)} 0%, transparent 70%)`,
            transform: `scale(${0.8 + intensity * 0.4})`
          }}
        />
      ))}
      
      {/* Zen score glow ring */}
      <div 
        className="absolute inset-0 rounded-full"
        style={{
          background: `conic-gradient(${colors.glow} ${zenScore * 3.6}deg, transparent 0deg)`,
          mask: 'radial-gradient(circle, transparent 85%, black 87%, black 95%, transparent 97%)',
          opacity: 0.8,
          animation: `zen-pulse 3s infinite ease-in-out`
        }}
      />
      
      {/* Surface shimmer effect */}
      <div 
        className="absolute inset-0 rounded-full opacity-40"
        style={{
          background: `linear-gradient(45deg, transparent 0%, ${colors.accent}80 50%, transparent 100%)`,
          animation: `surface-shimmer 4s infinite ease-in-out`
        }}
      />
    </div>
  );
};

// Optimized eyes with dramatic animations
const DramaticEye = ({ mood, expression, isBlinking, side = 'left' }) => {
  const colors = zenColors[mood];
  const [isSpecialEffect, setIsSpecialEffect] = useState(false);

  useEffect(() => {
    if (expression.specialEffect === 'sparkle-eyes' || expression.specialEffect === 'mischief-sparkle') {
      const interval = setInterval(() => {
        setIsSpecialEffect(true);
        setTimeout(() => setIsSpecialEffect(false), 200);
      }, 1000 + Math.random() * 2000);
      return () => clearInterval(interval);
    }
  }, [expression.specialEffect]);

  const eyeStyle = {
    width: 16 * expression.eyeScale,
    height: 16 * expression.eyeScale,
    transform: `rotate(${expression.eyeAngle * (side === 'left' ? 1 : -1)}deg) ${isBlinking ? 'scaleY(0.1)' : 'scaleY(1)'}`,
    background: `radial-gradient(circle, ${colors.primary} 20%, ${colors.secondary} 60%, ${colors.accent} 100%)`,
    boxShadow: `0 0 10px ${colors.glow}80, inset 0 0 8px ${colors.shadow}40`,
    animation: isSpecialEffect ? 'eye-flash 0.2s ease-in-out' : 'none'
  };

  return (
    <div className="relative">
      {/* Eyebrow */}
      <div 
        className="absolute -top-3 w-6 h-1 rounded-full transition-all duration-500"
        style={{
          backgroundColor: colors.primary,
          transform: `rotate(${expression.eyebrowAngle * (side === 'left' ? 1 : -1)}deg)`,
          boxShadow: `0 0 4px ${colors.glow}60`
        }}
      />
      
      {/* Main eye */}
      <div className="rounded-full relative transition-all duration-500 ease-in-out" style={eyeStyle}>
        {/* Pupil */}
        <div style={{
          width: '40%',
          height: '40%',
          backgroundColor: colors.shadow,
          borderRadius: '50%',
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          boxShadow: `0 0 6px ${colors.glow}60`
        }} />
        
        {/* Highlight */}
        <div style={{
          width: '25%',
          height: '25%',
          backgroundColor: 'white',
          borderRadius: '50%',
          position: 'absolute',
          top: '25%',
          left: '30%',
          opacity: 0.9,
          filter: `drop-shadow(0 0 2px ${colors.accent})`
        }} />
        
        {/* Special effects */}
        {isSpecialEffect && (
          <div className="absolute -inset-2">
            <Sparkles className="absolute top-0 right-0 text-yellow-400 animate-ping" size={12} />
            <Star className="absolute bottom-0 left-0 text-white animate-pulse" size={8} />
          </div>
        )}
      </div>
    </div>
  );
};

// Optimized mouth with dramatic curves
const DramaticMouth = ({ mood, expression }) => {
  const colors = zenColors[mood];
  
  const mouthPath = `M ${24 - expression.mouthCurve} ${16 - expression.mouthCurve/2} Q 24 ${16 + expression.mouthCurve} ${24 + expression.mouthCurve} ${16 - expression.mouthCurve/2}`;

  return (
    <div className="relative">
      <svg width="48" height="32" className="transition-all duration-700 ease-in-out">
        {/* Main mouth curve */}
        <path
          d={mouthPath}
          stroke={colors.primary}
          strokeWidth={3 * expression.mouthScale}
          strokeLinecap="round"
          fill="none"
          style={{
            filter: `drop-shadow(0 0 6px ${colors.glow}80)`,
            transform: `scale(${expression.mouthScale})`
          }}
        />
        
        {/* Mouth highlight */}
        <path
          d={mouthPath}
          stroke={colors.accent}
          strokeWidth={1}
          strokeLinecap="round"
          fill="none"
          opacity="0.8"
          style={{
            transform: `scale(${expression.mouthScale}) translateY(-1px)`
          }}
        />
      </svg>
      
      {/* Smile lines for joyful expressions */}
      {expression.mouthCurve > 15 && (
        <>
          <div 
            className="absolute w-4 h-1 rounded-full opacity-60"
            style={{
              backgroundColor: colors.secondary,
              left: '10%',
              top: '40%',
              transform: 'rotate(-20deg)',
              filter: 'blur(1px)'
            }}
          />
          <div 
            className="absolute w-4 h-1 rounded-full opacity-60"
            style={{
              backgroundColor: colors.secondary,
              right: '10%',
              top: '40%',
              transform: 'rotate(20deg)',
              filter: 'blur(1px)'
            }}
          />
        </>
      )}
    </div>
  );
};

// Optimized cheeks with dynamic glow
const DramaticCheek = ({ mood, expression, side = 'left' }) => {
  const colors = zenColors[mood];
  
  return (
    <div 
      className="absolute rounded-full transition-all duration-700 ease-in-out"
      style={{
        width: 12 * expression.cheekSize,
        height: 8 * expression.cheekSize,
        backgroundColor: colors.particle,
        [side]: '15%',
        top: '65%',
        opacity: 0.7,
        filter: `blur(${1 + expression.cheekSize}px)`,
        boxShadow: `0 0 ${8 * expression.cheekSize}px ${colors.glow}60`,
        animation: `cheek-glow 2s infinite ease-in-out`
      }}
    />
  );
};

// Main enhanced avatar component
export const EnhancedZenMoonAvatar = ({ 
  mood = 'calm', 
  size = 120, 
  enableAura = true, 
  zenScore = 75,
  behavior = 'idle',
  showMoodIcon = true,
  interactive = true
}) => {
  const [isBlinking, setIsBlinking] = useState(false);
  const [currentBehavior, setCurrentBehavior] = useState(behavior);
  const [lastInteraction, setLastInteraction] = useState(0);
  
  const colors = zenColors[mood];
  const expression = expressions[mood];

  // Enhanced blinking with personality
  useEffect(() => {
    const getBlinkInterval = () => {
      switch(mood) {
        case 'sleepy': return 1000 + Math.random() * 1000;
        case 'curious': return 4000 + Math.random() * 2000;
        case 'focused': return 6000 + Math.random() * 3000;
        default: return 3000 + Math.random() * 2000;
      }
    };

    const blinkInterval = setInterval(() => {
      setIsBlinking(true);
      const blinkDuration = mood === 'sleepy' ? 300 : 150;
      setTimeout(() => setIsBlinking(false), blinkDuration);
    }, getBlinkInterval());
    
    return () => clearInterval(blinkInterval);
  }, [mood]);

  // Behavior changes based on zen score
  useEffect(() => {
    if (zenScore >= 90) setCurrentBehavior('celebrating');
    else if (zenScore >= 75) setCurrentBehavior('meditation');
    else if (zenScore >= 60) setCurrentBehavior('thinking');
    else if (zenScore <= 30) setCurrentBehavior('sleepy');
    else setCurrentBehavior('idle');
  }, [zenScore]);

  const handleClick = () => {
    if (interactive) {
      setCurrentBehavior('responding');
      setLastInteraction(Date.now());
      setTimeout(() => {
        if (Date.now() - lastInteraction > 1400) {
          setCurrentBehavior('idle');
        }
      }, 1500);
    }
  };

  const getMoodIcon = () => {
    const iconProps = { size: 16, style: { color: colors.primary } };
    switch(mood) {
      case 'calm': return <Wind {...iconProps} />;
      case 'curious': return <Sparkles {...iconProps} />;
      case 'joyful': return <Heart {...iconProps} />;
      case 'focused': return <Brain {...iconProps} />;
      case 'playful': return <Zap {...iconProps} />;
      case 'sleepy': return <Moon {...iconProps} />;
      default: return <Sun {...iconProps} />;
    }
  };

  return (
    <div 
      className={`relative flex items-center justify-center ${interactive ? 'cursor-pointer' : ''} transition-all duration-500`}
      style={{ width: size + 80, height: size + 80 }}
      onClick={handleClick}
    >
      {/* Enhanced particle system */}
      <ParticleSystem 
        mood={mood} 
        zenScore={zenScore} 
        behavior={currentBehavior} 
        count={Math.floor(8 + zenScore / 10)}
      />
      
      {/* Dynamic aura with zen score influence */}
      {enableAura && (
        <div 
          className="absolute rounded-full transition-all duration-1000"
          style={{
            width: size + 40 + (zenScore / 5),
            height: size + 40 + (zenScore / 5),
            background: `radial-gradient(circle, ${colors.glow}${Math.floor(zenScore/2)} 0%, ${colors.secondary}30 40%, transparent 70%)`,
            opacity: 0.4 + (zenScore / 200),
            animation: `aura-${currentBehavior} 3s infinite ease-in-out`,
            filter: 'blur(2px)'
          }}
        />
      )}
      
      {/* Main textured moon */}
      <TexturedMoonBase 
        mood={mood} 
        size={size} 
        zenScore={zenScore} 
        behavior={currentBehavior}
      />
      
      {/* Face overlay with dramatic features */}
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        {/* Eyes with dramatic expressions */}
        <div className="flex space-x-8 mb-4" style={{ transform: `translateY(-${size * 0.1}px)` }}>
          <DramaticEye mood={mood} expression={expression} isBlinking={isBlinking} side="left" />
          <DramaticEye mood={mood} expression={expression} isBlinking={isBlinking} side="right" />
        </div>
        
        {/* Dramatic mouth */}
        <div style={{ transform: `translateY(${size * 0.05}px)` }}>
          <DramaticMouth mood={mood} expression={expression} />
        </div>
        
        {/* Exaggerated cheeks */}
        <DramaticCheek mood={mood} expression={expression} side="left" />
        <DramaticCheek mood={mood} expression={expression} side="right" />
      </div>
      
      {/* Zen score indicator */}
      <div className="absolute -bottom-4 text-center">
        <div 
          className="text-xs font-bold px-2 py-1 rounded-full"
          style={{ 
            backgroundColor: colors.primary, 
            color: 'white',
            boxShadow: `0 0 10px ${colors.glow}60`
          }}
        >
          {zenScore}
        </div>
      </div>
      
      {/* Mood icon with enhanced styling */}
      {showMoodIcon && (
        <div 
          className="absolute -top-4 -right-4 p-2 rounded-full"
          style={{
            backgroundColor: colors.secondary,
            boxShadow: `0 0 12px ${colors.glow}80`
          }}
        >
          {getMoodIcon()}
        </div>
      )}
      
      <style jsx>{`
        @keyframes zen-pulse {
          0%, 100% { opacity: 0.6; transform: rotate(0deg); }
          50% { opacity: 1; transform: rotate(1deg); }
        }
        
        @keyframes surface-shimmer {
          0%, 100% { opacity: 0.2; transform: translateX(-100%); }
          50% { opacity: 0.6; transform: translateX(100%); }
        }
        
        @keyframes eye-flash {
          0%, 100% { transform: scale(1); filter: brightness(1); }
          50% { transform: scale(1.2); filter: brightness(1.5); }
        }
        
        @keyframes particle-sparkle-idle {
          0%, 100% { transform: translateY(0px) rotate(0deg) scale(1); opacity: 0.6; }
          25% { transform: translateY(-15px) rotate(90deg) scale(1.2); opacity: 0.9; }
          50% { transform: translateY(-8px) rotate(180deg) scale(0.8); opacity: 0.7; }
          75% { transform: translateY(-20px) rotate(270deg) scale(1.1); opacity: 0.8; }
        }
        
        @keyframes particle-glow-celebrating {
          0%, 100% { transform: translateY(0px) scale(1); opacity: 0.8; }
          33% { transform: translateY(-25px) scale(1.5); opacity: 1; }
          66% { transform: translateY(-10px) scale(1.2); opacity: 0.9; }
        }
        
        @keyframes particle-star-meditation {
          0%, 100% { transform: scale(1) rotate(0deg); opacity: 0.7; }
          50% { transform: scale(1.3) rotate(180deg); opacity: 1; }
        }
        
        @keyframes particle-dot-thinking {
          0%, 100% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.2); opacity: 0.8; }
        }
        
        @keyframes aura-celebrating {
          0%, 100% { transform: scale(1) rotate(0deg); opacity: 0.6; }
          25% { transform: scale(1.2) rotate(5deg); opacity: 0.9; }
          50% { transform: scale(1.3) rotate(0deg); opacity: 1; }
          75% { transform: scale(1.2) rotate(-5deg); opacity: 0.9; }
        }
        
        @keyframes aura-meditation {
          0%, 100% { transform: scale(1); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 0.8; }
        }
        
        @keyframes aura-idle {
          0%, 100% { transform: scale(1); opacity: 0.4; }
          50% { transform: scale(1.05); opacity: 0.6; }
        }
        
        @keyframes aura-thinking {
          0%, 100% { transform: scale(1) rotate(0deg); opacity: 0.4; }
          50% { transform: scale(1.08) rotate(1deg); opacity: 0.7; }
        }
        
        @keyframes aura-responding {
          0%, 100% { transform: scale(1.1); opacity: 0.8; }
          50% { transform: scale(1.15); opacity: 1; }
        }
        
        @keyframes cheek-glow {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
};

// Enhanced showcase with zen score control
export default function EnhancedZenShowcase() {
  const [selectedMood, setSelectedMood] = useState('joyful');
  const [zenScore, setZenScore] = useState(85);

  const moods = Object.keys(zenColors);

  const getCurrentBehavior = (score) => {
    if (score >= 90) return 'Enlightened';
    if (score >= 75) return 'Focused';
    if (score >= 60) return 'Contemplative';
    if (score <= 30) return 'Restless';
    return 'Peaceful';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-5xl font-bold text-center mb-4 text-white">
          Enhanced ZenMoon Avatar
        </h1>
        <p className="text-center text-gray-200 text-lg mb-12">
          Dramatically expressive • Richly textured • Behaviorally intelligent
        </p>
        
        {/* Main showcase */}
        <div className="flex justify-center mb-12">
          <EnhancedZenMoonAvatar
            mood={selectedMood}
            size={160}
            enableAura={true}
            zenScore={zenScore}
            showMoodIcon={true}
            interactive={true}
          />
        </div>
        
        {/* Enhanced controls */}
        <div className="bg-black bg-opacity-30 backdrop-blur-lg rounded-3xl p-8 mb-12 border border-white border-opacity-20">
          {/* Mood selector */}
          <div className="mb-8">
            <h3 className="text-2xl font-bold mb-4 text-white">Emotional State</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {moods.map(mood => (
                <button
                  key={mood}
                  onClick={() => setSelectedMood(mood)}
                  className={`p-4 rounded-2xl transition-all duration-300 ${
                    selectedMood === mood 
                      ? 'scale-105 shadow-2xl' 
                      : 'hover:scale-102 opacity-80 hover:opacity-100'
                  }`}
                  style={selectedMood === mood ? {
                    backgroundColor: zenColors[mood].primary,
                    boxShadow: `0 0 30px ${zenColors[mood].glow}60`,
                    color: 'white'
                  } : {
                    backgroundColor: 'rgba(255,255,255,0.1)',
                    color: 'rgba(255,255,255,0.8)'
                  }}
                >
                  <div className="text-lg font-bold capitalize">{mood}</div>
                </button>
              ))}
            </div>
          </div>
          
          {/* Zen score control */}
          <div className="mb-8">
            <h3 className="text-2xl font-bold mb-4 text-white">
              Zen Score: {zenScore}/100 - {getCurrentBehavior(zenScore)}
            </h3>
            <div className="relative">
              <input
                type="range"
                min="0"
                max="100"
                step="1"
                value={zenScore}
                onChange={(e) => setZenScore(parseInt(e.target.value))}
                className="w-full h-4 bg-gray-700 rounded-full appearance-none cursor-pointer slider"
                style={{
                  background: `linear-gradient(to right, 
                    ${zenColors[selectedMood].shadow} 0%, 
                    ${zenColors[selectedMood].primary} ${zenScore}%, 
                    rgba(255,255,255,0.2) ${zenScore}%, 
                    rgba(255,255,255,0.2) 100%)`
                }}
              />
              <div className="flex justify-between text-sm text-gray-300 mt-2">
                <span>Restless</span>
                <span>Balanced</span>
                <span>Enlightened</span>
              </div>
            </div>
          </div>
          
          {/* Behavior indicators */}
          <div>
            <h3 className="text-2xl font-bold mb-4 text-white">Current Behavior</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { behavior: 'idle', label: 'Peaceful', range: '31-59', active: zenScore >= 31 && zenScore <= 59 },
                { behavior: 'thinking', label: 'Contemplative', range: '60-74', active: zenScore >= 60 && zenScore <= 74 },
                { behavior: 'meditation', label: 'Focused', range: '75-89', active: zenScore >= 75 && zenScore <= 89 },
                { behavior: 'celebrating', label: 'Enlightened', range: '90-100', active: zenScore >= 90 }
              ].map(({ behavior, label, range, active }) => (
                <div 
                  key={behavior}
                  className={`p-3 rounded-xl text-center transition-all ${
                    active
                      ? 'bg-white bg-opacity-20 text-white border-2 border-white border-opacity-40' 
                      : 'bg-white bg-opacity-5 text-gray-400'
                  }`}
                >
                  <div className="font-semibold">{label}</div>
                  <div className="text-xs opacity-70">{range}</div>
                </div>
              ))}
            </div>
            {zenScore <= 30 && (
              <div className="mt-3 p-3 rounded-xl text-center bg-red-500 bg-opacity-20 text-red-200 border border-red-500 border-opacity-30">
                <div className="font-semibold">Restless</div>
                <div className="text-xs opacity-70">0-30</div>
              </div>
            )}
          </div>
        </div>
        
        {/* Mood gallery */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          {moods.map(mood => (
            <div 
              key={mood} 
              className="bg-black bg-opacity-20 backdrop-blur-sm rounded-2xl p-6 text-center border border-white border-opacity-10 hover:border-opacity-30 transition-all cursor-pointer"
              onClick={() => setSelectedMood(mood)}
            >
              <EnhancedZenMoonAvatar
                mood={mood}
                size={80}
                enableAura={true}
                zenScore={75}
                showMoodIcon={false}
                interactive={false}
              />
              <h3 className="mt-4 font-bold text-white capitalize text-sm">{mood}</h3>
              <div 
                className="mt-2 mx-auto w-8 h-1 rounded-full"
                style={{ backgroundColor: zenColors[mood].primary }}
              />
            </div>
          ))}
        </div>
        
        {/* Feature highlights */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <Sparkles className="text-yellow-400 mb-4" size={32} />
            <h3 className="text-xl font-bold text-white mb-2">Dramatic Expressions</h3>
            <p className="text-gray-200">Exaggerated facial features that truly convey emotion with dynamic eyebrows, dramatic mouth curves, and expressive cheek glow.</p>
          </div>
          
          <div className="bg-gradient-to-br from-green-500/20 to-teal-500/20 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <Brain className="text-green-400 mb-4" size={32} />
            <h3 className="text-xl font-bold text-white mb-2">Rich Textures</h3>
            <p className="text-gray-200">Textured moon surface with realistic craters, surface shimmer effects, and multi-layered gradients for depth and realism.</p>
          </div>
          
          <div className="bg-gradient-to-br from-pink-500/20 to-red-500/20 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <Zap className="text-pink-400 mb-4" size={32} />
            <h3 className="text-xl font-bold text-white mb-2">Dynamic Particles</h3>
            <p className="text-gray-200">Intelligent particle system with sparkles, stars, and glowing orbs that respond to zen score and behavior changes.</p>
          </div>
        </div>
        
        {/* Usage guide */}
        <div className="mt-16 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 backdrop-blur-lg rounded-2xl p-8 border border-white/10">
          <h3 className="text-2xl font-bold text-white mb-6 text-center">🎮 Interactive Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-gray-200">
            <div>
              <h4 className="font-bold text-white mb-2">🎚️ Zen Score Effects</h4>
              <ul className="space-y-1 text-sm">
                <li>• <strong>0-30:</strong> Restless behavior with minimal particles</li>
                <li>• <strong>31-59:</strong> Peaceful idle state with gentle animations</li>
                <li>• <strong>60-74:</strong> Contemplative thinking with focused particles</li>
                <li>• <strong>75-89:</strong> Meditative glow with rhythmic breathing</li>
                <li>• <strong>90-100:</strong> Enlightened celebration with particle bursts</li>
              </ul>
            </div>
            <div>
              <h4 className="font-bold text-white mb-2">🎭 Mood Personalities</h4>
              <ul className="space-y-1 text-sm">
                <li>• <strong>Calm:</strong> Gentle expressions with soft blue tones</li>
                <li>• <strong>Curious:</strong> Wide eyes with sparkle effects</li>
                <li>• <strong>Joyful:</strong> Big smile with vibrant green energy</li>
                <li>• <strong>Focused:</strong> Intense concentration with purple aura</li>
                <li>• <strong>Playful:</strong> Mischievous grin with pink sparkles</li>
                <li>• <strong>Sleepy:</strong> Droopy eyes with dreamy purple hues</li>
              </ul>
            </div>
          </div>
          <div className="mt-6 text-center text-gray-300">
            <p>✨ Click the avatar to see responsive interactions! ✨</p>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: ${zenColors[selectedMood]?.primary || '#4A90E2'};
          cursor: pointer;
          box-shadow: 0 0 10px ${zenColors[selectedMood]?.glow || '#2E86DE'}80;
          border: 2px solid white;
        }
        
        .slider::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: ${zenColors[selectedMood]?.primary || '#4A90E2'};
          cursor: pointer;
          border: 2px solid white;
          box-shadow: 0 0 10px ${zenColors[selectedMood]?.glow || '#2E86DE'}80;
        }
      `}</style>
    </div>
  );
}
