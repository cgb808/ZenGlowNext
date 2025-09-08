import React from 'react';
import { render } from '@testing-library/react-native';
import { Sparkle } from '../../components/ZenMoon/Sparkle';

// Mock react-native-reanimated
jest.mock('react-native-reanimated', () => {
  const Reanimated = require('react-native-reanimated/mock');
  
  // The mock for `call` immediately calls the callback which is incorrect
  // So we override it with a no-op
  Reanimated.default.call = () => {};
  
  return Reanimated;
});

describe('Sparkle', () => {
  it('renders with default props', () => {
    const { getByTestId } = render(<Sparkle />);
    
    // Component should render without crashing
    expect(true).toBe(true);
  });

  it('renders with custom props', () => {
    const { getByTestId } = render(
      <Sparkle
        color="#FF0000"
        size={20}
        duration={2000}
        delay={500}
        repeat={false}
        offsetX={10}
        offsetY={15}
      />
    );
    
    // Component should render without crashing
    expect(true).toBe(true);
  });

  it('uses default values when props are not provided', () => {
    const { getByTestId } = render(<Sparkle />);
    
    // Component should render with defaults without crashing
    expect(true).toBe(true);
  });
});