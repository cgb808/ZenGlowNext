/**
 * Design Tokens Snapshot Test
 * 
 * This test ensures that design tokens maintain consistency and detects
 * accidental changes to the token structure or values.
 */

import { tokens, colors, spacing, radii, typography, elevation, zIndices, durations, shadows } from '../../src/theme/tokens';
import { createTheme, lightTheme, darkTheme, highContrastTheme } from '../../src/theme';

describe('Design Tokens', () => {
  describe('Token Structure Snapshots', () => {
    it('should match tokens snapshot', () => {
      expect(tokens).toMatchSnapshot();
    });

    it('should match colors snapshot', () => {
      expect(colors).toMatchSnapshot();
    });

    it('should match spacing snapshot', () => {
      expect(spacing).toMatchSnapshot();
    });

    it('should match radii snapshot', () => {
      expect(radii).toMatchSnapshot();
    });

    it('should match typography snapshot', () => {
      expect(typography).toMatchSnapshot();
    });

    it('should match elevation snapshot', () => {
      expect(elevation).toMatchSnapshot();
    });

    it('should match zIndices snapshot', () => {
      expect(zIndices).toMatchSnapshot();
    });

    it('should match durations snapshot', () => {
      expect(durations).toMatchSnapshot();
    });

    it('should match shadows snapshot', () => {
      expect(shadows).toMatchSnapshot();
    });
  });

  describe('Theme Creation', () => {
    it('should create consistent light theme', () => {
      const theme = createTheme('light');
      expect(theme).toMatchSnapshot();
    });

    it('should create consistent dark theme', () => {
      const theme = createTheme('dark');
      expect(theme).toMatchSnapshot();
    });

    it('should create consistent high contrast theme', () => {
      const theme = createTheme('highContrast');
      expect(theme).toMatchSnapshot();
    });
  });

  describe('Default Theme Instances', () => {
    it('should match lightTheme snapshot', () => {
      expect(lightTheme).toMatchSnapshot();
    });

    it('should match darkTheme snapshot', () => {
      expect(darkTheme).toMatchSnapshot();
    });

    it('should match highContrastTheme snapshot', () => {
      expect(highContrastTheme).toMatchSnapshot();
    });
  });

  describe('Token Validation', () => {
    it('should have all required color categories', () => {
      expect(colors).toHaveProperty('primary');
      expect(colors).toHaveProperty('secondary');
      expect(colors).toHaveProperty('accent');
      expect(colors).toHaveProperty('success');
      expect(colors).toHaveProperty('warning');
      expect(colors).toHaveProperty('error');
      expect(colors).toHaveProperty('neutral');
      expect(colors).toHaveProperty('light');
      expect(colors).toHaveProperty('dark');
      expect(colors).toHaveProperty('highContrast');
    });

    it('should have consistent color scale structure', () => {
      const colorScales = ['primary', 'secondary', 'success', 'warning', 'error'];
      
      colorScales.forEach(scale => {
        expect(colors[scale]).toHaveProperty('50');
        expect(colors[scale]).toHaveProperty('500'); // Main color
        expect(colors[scale]).toHaveProperty('900');
      });
    });

    it('should have all required spacing values', () => {
      expect(spacing).toHaveProperty('xs');
      expect(spacing).toHaveProperty('sm');
      expect(spacing).toHaveProperty('md');
      expect(spacing).toHaveProperty('lg');
      expect(spacing).toHaveProperty('xl');
      expect(spacing).toHaveProperty('component');
    });

    it('should have all required typography properties', () => {
      expect(typography).toHaveProperty('fontFamily');
      expect(typography).toHaveProperty('fontSize');
      expect(typography).toHaveProperty('fontWeight');
      expect(typography).toHaveProperty('lineHeight');
      expect(typography).toHaveProperty('textStyles');
    });

    it('should have ZenGlow-specific tokens', () => {
      // Check for ZenMoon-specific colors
      expect(colors.accent).toHaveProperty('gold');
      expect(colors.accent).toHaveProperty('sky');
      
      // Check for companion z-index
      expect(zIndices).toHaveProperty('companion');
      expect(zIndices.companion).toBe(9999);
      
      // Check for moon glow shadows
      expect(shadows).toHaveProperty('moonGlow');
      expect(shadows.moonGlow).toHaveProperty('calm');
      expect(shadows.moonGlow).toHaveProperty('active');
      
      // Check for security status shadows
      expect(shadows).toHaveProperty('securityStatus');
      expect(shadows.securityStatus).toHaveProperty('valid');
      expect(shadows.securityStatus).toHaveProperty('invalid');
    });

    it('should have valid color values', () => {
      const hexColorRegex = /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/;
      
      // Test primary colors
      Object.values(colors.primary).forEach(color => {
        expect(color).toMatch(hexColorRegex);
      });
      
      // Test accent colors
      Object.values(colors.accent).forEach(color => {
        expect(color).toMatch(hexColorRegex);
      });
    });

    it('should have positive spacing values', () => {
      Object.values(spacing).forEach(value => {
        if (typeof value === 'number') {
          expect(value).toBeGreaterThan(0);
        }
      });
    });

    it('should have positive duration values', () => {
      Object.values(durations).forEach(value => {
        if (typeof value === 'number') {
          expect(value).toBeGreaterThanOrEqual(0);
        }
      });
    });
  });

  describe('Theme Consistency', () => {
    it('should maintain React Navigation theme compatibility', () => {
      const theme = lightTheme;
      
      // Check required React Navigation theme properties
      expect(theme.colors).toHaveProperty('primary');
      expect(theme.colors).toHaveProperty('background');
      expect(theme.colors).toHaveProperty('card');
      expect(theme.colors).toHaveProperty('text');
      expect(theme.colors).toHaveProperty('border');
      expect(theme.colors).toHaveProperty('notification');
      expect(theme).toHaveProperty('dark');
    });

    it('should have all themes with same structure', () => {
      const themes = [lightTheme, darkTheme, highContrastTheme];
      
      themes.forEach(theme => {
        expect(theme).toHaveProperty('colors');
        expect(theme).toHaveProperty('spacing');
        expect(theme).toHaveProperty('radii');
        expect(theme).toHaveProperty('typography');
        expect(theme).toHaveProperty('elevation');
        expect(theme).toHaveProperty('zIndices');
        expect(theme).toHaveProperty('durations');
        expect(theme).toHaveProperty('shadows');
        expect(theme).toHaveProperty('colorScheme');
      });
    });

    it('should have different color values for different themes', () => {
      expect(lightTheme.colors.background.primary).not.toBe(darkTheme.colors.background.primary);
      expect(lightTheme.colors.text.primary).not.toBe(darkTheme.colors.text.primary);
    });
  });
});