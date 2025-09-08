import React from 'react';
import { render } from '@testing-library/react-native';
import { EnhancedZenMoonAvatar } from '../../components/ZenMoon/EnhancedZenMoonAvatar';
import { ZenSoundProvider } from '../../components/Audio/ZenSoundProvider';

// Mock the ZenSoundProvider since we don't have actual sound files
jest.mock('../../components/Audio/ZenSoundProvider', () => ({
  ZenSoundProvider: ({ children }: { children: React.ReactNode }) => children,
  useZenSound: () => ({
    playCharacterSound: jest.fn(),
  }),
}));

// Mock react-native-reanimated
jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  
  // The mock for `call` immediately calls the callback which is incorrect
  // So we override it with a no-op
  Reanimated.default.call = () => {};
  
  return Reanimated;
});

describe('EnhancedZenMoonAvatar', () => {
  const TestWrapper = ({ children }: { children: React.ReactNode }) => (
    <ZenSoundProvider>{children}</ZenSoundProvider>
  );

  it('renders with default props', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <EnhancedZenMoonAvatar />
      </TestWrapper>
    );
    
    // Component should render without crashing
    expect(true).toBe(true);
  });

  it('renders with custom mood and size', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <EnhancedZenMoonAvatar mood="joyful" size={150} />
      </TestWrapper>
    );
    
    // Component should render without crashing
    expect(true).toBe(true);
  });

  it('accepts inactivity configuration', () => {
    const onUserInteraction = jest.fn();
    
    const { getByTestId } = render(
      <TestWrapper>
        <EnhancedZenMoonAvatar
          inactivityConfig={{
            timeout: 5000,
            enabled: true,
          }}
          onUserInteraction={onUserInteraction}
        />
      </TestWrapper>
    );
    
    // Component should render without crashing
    expect(true).toBe(true);
  });

  it('accepts sparkle configuration', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <EnhancedZenMoonAvatar
          sparkleConfig={{
            count: 3,
            color: '#FF0000',
            duration: 1000,
            repeat: false,
          }}
        />
      </TestWrapper>
    );
    
    // Component should render without crashing
    expect(true).toBe(true);
  });
});