/**
 * ZenGlow Design Tokens
 * 
 * Centralized design system tokens for consistent UI across the application.
 * These tokens define the visual language of ZenGlow including colors, spacing,
 * typography, elevations, and animations.
 * 
 * @version 1.0.0
 * @author ZenGlow Team
 */

/**
 * Color palette tokens organized by semantic meaning
 */
export const colors = {
  // Primary brand colors
  primary: {
    50: '#E3F2FD',
    100: '#BBDEFB', 
    200: '#90CAF9',
    300: '#64B5F6',
    400: '#42A5F5',
    500: '#2196F3', // Main primary
    600: '#1E88E5',
    700: '#1976D2',
    800: '#1565C0',
    900: '#0D47A1',
  },
  
  // Secondary brand colors (zen-inspired blues/teals)
  secondary: {
    50: '#E0F2F1',
    100: '#B2DFDB',
    200: '#80CBC4',
    300: '#4DB6AC',
    400: '#26A69A',
    500: '#009688', // Main secondary
    600: '#00897B',
    700: '#00796B',
    800: '#00695C',
    900: '#004D40',
  },
  
  // Accent colors for special elements
  accent: {
    gold: '#FFD700', // For glowing effects
    sky: '#4A90E2', // For calm states
    sunset: '#FF6B6B', // For energy/playful states
    mint: '#00E676', // For success/growth
  },
  
  // Semantic colors
  success: {
    50: '#F1F8E9',
    100: '#DCEDC8',
    200: '#C5E1A5',
    300: '#AED581',
    400: '#9CCC65',
    500: '#8BC34A', // Main success
    600: '#7CB342',
    700: '#689F38',
    800: '#558B2F',
    900: '#33691E',
  },
  
  warning: {
    50: '#FFF8E1',
    100: '#FFECB3',
    200: '#FFE082',
    300: '#FFD54F',
    400: '#FFCA28',
    500: '#FFC107', // Main warning
    600: '#FFB300',
    700: '#FFA000',
    800: '#FF8F00',
    900: '#FF6F00',
  },
  
  error: {
    50: '#FFEBEE',
    100: '#FFCDD2',
    200: '#EF9A9A',
    300: '#E57373',
    400: '#EF5350',
    500: '#F44336', // Main error
    600: '#E53935',
    700: '#D32F2F',
    800: '#C62828',
    900: '#B71C1C',
  },
  
  // Neutral grays
  neutral: {
    0: '#FFFFFF',
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#EEEEEE',
    300: '#E0E0E0',
    400: '#BDBDBD',
    500: '#9E9E9E',
    600: '#757575',
    700: '#616161',
    800: '#424242',
    900: '#212121',
    1000: '#000000',
  },
  
  // Theme-specific color mappings
  light: {
    background: {
      primary: '#FFFFFF',
      secondary: '#F8F9FA',
      tertiary: '#F5F5F5',
    },
    text: {
      primary: '#11181C',
      secondary: '#687076',
      tertiary: '#9BA1A6',
      inverse: '#FFFFFF',
    },
    border: {
      primary: '#E0E0E0',
      secondary: '#F0F0F0',
      focus: '#2196F3',
    },
    surface: {
      elevated: '#FFFFFF',
      overlay: 'rgba(0, 0, 0, 0.5)',
    },
  },
  
  dark: {
    background: {
      primary: '#121212',
      secondary: '#1E1E1E',
      tertiary: '#2C2C2C',
    },
    text: {
      primary: '#ECEDEE',
      secondary: '#9BA1A6',
      tertiary: '#687076',
      inverse: '#000000',
    },
    border: {
      primary: '#333333',
      secondary: '#404040',
      focus: '#42A5F5',
    },
    surface: {
      elevated: '#2C2C2C',
      overlay: 'rgba(0, 0, 0, 0.7)',
    },
  },
  
  // High contrast theme placeholders
  highContrast: {
    background: {
      primary: '#FFFFFF',
      secondary: '#F0F0F0',
    },
    text: {
      primary: '#000000',
      secondary: '#333333',
    },
    border: {
      primary: '#000000',
      focus: '#0066CC',
    },
  },
} as const;

/**
 * Spacing tokens based on 8px grid system
 */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
  
  // Component-specific spacing
  component: {
    padding: {
      xs: 8,
      sm: 12,
      md: 16,
      lg: 20,
      xl: 24,
    },
    margin: {
      xs: 4,
      sm: 8,
      md: 16,
      lg: 24,
      xl: 32,
    },
    gap: {
      xs: 4,
      sm: 8,
      md: 12,
      lg: 16,
      xl: 20,
    },
  },
} as const;

/**
 * Border radius tokens for consistent rounded corners
 */
export const radii = {
  none: 0,
  xs: 2,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  xxl: 24,
  full: 999,
  
  // Component-specific radii
  button: 8,
  card: 12,
  modal: 16,
  avatar: 999,
} as const;

/**
 * Typography scale and font definitions
 */
export const typography = {
  fontFamily: {
    primary: 'System', // Platform default
    mono: 'Courier New',
  },
  
  fontSize: {
    xs: 12,
    sm: 14,
    base: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
    '4xl': 36,
    '5xl': 48,
    '6xl': 60,
  },
  
  fontWeight: {
    light: '300' as const,
    normal: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
    extrabold: '800' as const,
  },
  
  lineHeight: {
    none: 1,
    tight: 1.25,
    snug: 1.375,
    normal: 1.5,
    relaxed: 1.625,
    loose: 2,
  },
  
  // Pre-defined text styles
  textStyles: {
    h1: {
      fontSize: 32,
      fontWeight: '700' as const,
      lineHeight: 1.25,
    },
    h2: {
      fontSize: 24,
      fontWeight: '600' as const,
      lineHeight: 1.375,
    },
    h3: {
      fontSize: 20,
      fontWeight: '600' as const,
      lineHeight: 1.5,
    },
    body: {
      fontSize: 16,
      fontWeight: '400' as const,
      lineHeight: 1.5,
    },
    bodySmall: {
      fontSize: 14,
      fontWeight: '400' as const,
      lineHeight: 1.375,
    },
    caption: {
      fontSize: 12,
      fontWeight: '400' as const,
      lineHeight: 1.25,
    },
    button: {
      fontSize: 16,
      fontWeight: '600' as const,
      lineHeight: 1.25,
    },
  },
} as const;

/**
 * Elevation/shadow tokens for depth and layering
 */
export const elevation = {
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
  xl: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 16,
  },
} as const;

/**
 * Z-index tokens for consistent layering
 */
export const zIndices = {
  base: 0,
  raised: 1,
  overlay: 10,
  dropdown: 100,
  modal: 1000,
  toast: 2000,
  tooltip: 3000,
  companion: 9999, // ZenGlow floating companion
} as const;

/**
 * Animation duration tokens for consistent timing
 */
export const durations = {
  instant: 0,
  fast: 150,
  normal: 300,
  slow: 500,
  slower: 750,
  slowest: 1000,
  
  // Component-specific durations
  component: {
    tooltip: 200,
    modal: 300,
    page: 500,
    companion: 300, // ZenMoon animations
  },
} as const;

/**
 * Custom shadow presets for ZenGlow components
 */
export const shadows = {
  // Zen moon glow effects
  moonGlow: {
    calm: {
      shadowColor: '#4A90E2',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.3,
      shadowRadius: 10,
      elevation: 10,
    },
    active: {
      shadowColor: '#FFD700',
      shadowOffset: { width: 0, height: 0 },
      shadowOpacity: 0.8,
      shadowRadius: 20,
      elevation: 15,
    },
  },
  
  // Security indicator shadows
  securityStatus: {
    valid: {
      shadowColor: '#27AE60',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.3,
      shadowRadius: 4,
      elevation: 4,
    },
    invalid: {
      shadowColor: '#E74C3C',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.3,
      shadowRadius: 4,
      elevation: 4,
    },
  },
} as const;

/**
 * Combined design tokens object
 */
export const tokens = {
  colors,
  spacing,
  radii,
  typography,
  elevation,
  zIndices,
  durations,
  shadows,
} as const;

export default tokens;