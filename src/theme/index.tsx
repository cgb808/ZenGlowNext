/**
 * ZenGlow Theme System
 * 
 * Central theme provider and utilities for accessing design tokens throughout the application.
 * Builds on the existing React Navigation theme system while extending it with comprehensive tokens.
 * 
 * @version 1.0.0
 * @author ZenGlow Team
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { Theme as NavigationTheme } from '@react-navigation/native';
import { tokens, colors, spacing, radii, typography, elevation, zIndices, durations, shadows } from './tokens';

/**
 * Color scheme type definition
 */
export type ColorScheme = 'light' | 'dark' | 'highContrast';

/**
 * Extended theme interface that includes all design tokens
 */
export interface Theme {
  // React Navigation theme compatibility
  dark: boolean;
  colors: NavigationTheme['colors'] & {
    // Extended color tokens
    primary: typeof colors.primary;
    secondary: typeof colors.secondary;
    accent: typeof colors.accent;
    success: typeof colors.success;
    warning: typeof colors.warning;
    error: typeof colors.error;
    neutral: typeof colors.neutral;
    
    // Theme-specific colors
    background: typeof colors.light.background | typeof colors.dark.background | typeof colors.highContrast.background;
    text: typeof colors.light.text | typeof colors.dark.text | typeof colors.highContrast.text;
    border: typeof colors.light.border | typeof colors.dark.border | typeof colors.highContrast.border;
    surface: typeof colors.light.surface | typeof colors.dark.surface;
  };
  
  // Design token categories
  spacing: typeof spacing;
  radii: typeof radii;
  typography: typeof typography;
  elevation: typeof elevation;
  zIndices: typeof zIndices;
  durations: typeof durations;
  shadows: typeof shadows;
  
  // Theme metadata
  colorScheme: ColorScheme;
}

/**
 * Create theme object based on color scheme
 */
export function createTheme(colorScheme: ColorScheme): Theme {
  const isDark = colorScheme === 'dark';
  const isHighContrast = colorScheme === 'highContrast';
  
  // Select appropriate color mappings
  let themeColors;
  if (isHighContrast) {
    themeColors = colors.highContrast;
  } else if (isDark) {
    themeColors = colors.dark;
  } else {
    themeColors = colors.light;
  }
  
  return {
    dark: isDark,
    colors: {
      // React Navigation compatibility
      primary: colors.primary[500],
      background: themeColors.background.primary,
      card: themeColors.background.secondary,
      text: themeColors.text.primary,
      border: themeColors.border.primary,
      notification: colors.error[500],
      
      // Extended token colors
      primary: colors.primary,
      secondary: colors.secondary,
      accent: colors.accent,
      success: colors.success,
      warning: colors.warning,
      error: colors.error,
      neutral: colors.neutral,
      
      // Theme-specific colors
      background: themeColors.background,
      text: themeColors.text,
      border: themeColors.border,
      surface: themeColors.surface || { elevated: themeColors.background.primary, overlay: 'rgba(0, 0, 0, 0.5)' },
    },
    
    // Include all design tokens
    spacing,
    radii,
    typography,
    elevation,
    zIndices,
    durations,
    shadows,
    
    // Theme metadata
    colorScheme,
  };
}

/**
 * Default theme instances
 */
export const lightTheme = createTheme('light');
export const darkTheme = createTheme('dark');
export const highContrastTheme = createTheme('highContrast');

/**
 * Theme context for provider pattern
 */
const ThemeContext = createContext<Theme>(lightTheme);

/**
 * Theme provider component props
 */
export interface ZenThemeProviderProps {
  children: ReactNode;
  theme?: Theme;
  forcedColorScheme?: ColorScheme;
}

/**
 * ZenGlow Theme Provider Component
 * 
 * Provides theme context to the entire application.
 * Automatically detects system color scheme unless forced.
 * 
 * @param children - React children components
 * @param theme - Optional custom theme object
 * @param forcedColorScheme - Optional forced color scheme override
 */
export function ZenThemeProvider({ 
  children, 
  theme,
  forcedColorScheme 
}: ZenThemeProviderProps) {
  const systemColorScheme = useColorScheme();
  
  // Determine the active color scheme
  const activeColorScheme: ColorScheme = 
    forcedColorScheme || 
    (systemColorScheme === 'dark' ? 'dark' : 'light');
  
  // Use provided theme or create one based on color scheme
  const activeTheme = theme || createTheme(activeColorScheme);
  
  return (
    <ThemeContext.Provider value={activeTheme}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Hook to access the current theme
 * 
 * Provides access to all design tokens and theme-aware colors.
 * 
 * @returns Current theme object with all design tokens
 * 
 * @example
 * ```tsx
 * const theme = useTheme();
 * 
 * const styles = StyleSheet.create({
 *   container: {
 *     backgroundColor: theme.colors.background.primary,
 *     padding: theme.spacing.md,
 *     borderRadius: theme.radii.lg,
 *   },
 *   text: {
 *     color: theme.colors.text.primary,
 *     fontSize: theme.typography.fontSize.base,
 *   },
 * });
 * ```
 */
export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  
  if (!theme) {
    throw new Error('useTheme must be used within a ZenThemeProvider');
  }
  
  return theme;
}

/**
 * Hook to access specific color tokens with theme awareness
 * 
 * Provides semantic color access with automatic theme switching.
 * 
 * @param colorPath - Dot notation path to color token
 * @returns Color value for current theme
 * 
 * @example
 * ```tsx
 * const backgroundColor = useThemeColor('background.primary');
 * const textColor = useThemeColor('text.secondary');
 * const primaryColor = useThemeColor('primary.500');
 * ```
 */
export function useThemeColor(colorPath: string): string {
  const theme = useTheme();
  
  // Split the path and traverse the color object
  const pathSegments = colorPath.split('.');
  let colorValue: any = theme.colors;
  
  for (const segment of pathSegments) {
    if (colorValue && typeof colorValue === 'object' && segment in colorValue) {
      colorValue = colorValue[segment];
    } else {
      console.warn(`Color path "${colorPath}" not found in theme`);
      return theme.colors.text.primary; // Fallback
    }
  }
  
  if (typeof colorValue === 'string') {
    return colorValue;
  }
  
  console.warn(`Color path "${colorPath}" does not resolve to a string value`);
  return theme.colors.text.primary; // Fallback
}

/**
 * Hook to access spacing tokens
 * 
 * @param size - Spacing size key
 * @returns Spacing value in pixels
 */
export function useSpacing(size: keyof typeof spacing): number {
  const theme = useTheme();
  return theme.spacing[size];
}

/**
 * Hook to access typography tokens
 * 
 * @param styleKey - Typography style key
 * @returns Typography style object
 */
export function useTextStyle(styleKey: keyof typeof typography.textStyles) {
  const theme = useTheme();
  return theme.typography.textStyles[styleKey];
}

/**
 * Utility function to check if current theme is dark
 * 
 * @returns True if current theme is dark mode
 */
export function useIsDarkTheme(): boolean {
  const theme = useTheme();
  return theme.dark;
}

/**
 * Utility function to get current color scheme
 * 
 * @returns Current color scheme identifier
 */
export function useColorSchemeType(): ColorScheme {
  const theme = useTheme();
  return theme.colorScheme;
}

// Re-export tokens for direct access when needed
export { tokens };
export * from './tokens';

// Default export for convenience
export default {
  ZenThemeProvider,
  useTheme,
  useThemeColor,
  useSpacing,
  useTextStyle,
  useIsDarkTheme,
  useColorSchemeType,
  lightTheme,
  darkTheme,
  highContrastTheme,
  createTheme,
  tokens,
};