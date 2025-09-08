/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { ThemedText } from '../../components/ThemedText';

// Mock the useThemeColor hook
jest.mock('../../hooks/useThemeColor', () => ({
  useThemeColor: jest.fn(() => '#000000'),
}));

describe('ThemedText', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders text content correctly', () => {
    const { getByText } = render(
      <ThemedText>Hello World</ThemedText>
    );
    
    expect(getByText('Hello World')).toBeTruthy();
  });

  it('applies default type styling by default', () => {
    const { getByText } = render(
      <ThemedText>Default Text</ThemedText>
    );
    
    const textElement = getByText('Default Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          fontSize: 16,
          lineHeight: 24,
        })
      ])
    );
  });

  it('applies title type styling correctly', () => {
    const { getByText } = render(
      <ThemedText type="title">Title Text</ThemedText>
    );
    
    const textElement = getByText('Title Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          fontSize: 32,
          fontWeight: 'bold',
          lineHeight: 32,
        })
      ])
    );
  });

  it('applies subtitle type styling correctly', () => {
    const { getByText } = render(
      <ThemedText type="subtitle">Subtitle Text</ThemedText>
    );
    
    const textElement = getByText('Subtitle Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          fontSize: 20,
          fontWeight: 'bold',
        })
      ])
    );
  });

  it('applies defaultSemiBold type styling correctly', () => {
    const { getByText } = render(
      <ThemedText type="defaultSemiBold">Semi Bold Text</ThemedText>
    );
    
    const textElement = getByText('Semi Bold Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          fontSize: 16,
          lineHeight: 24,
          fontWeight: '600',
        })
      ])
    );
  });

  it('applies link type styling correctly', () => {
    const { getByText } = render(
      <ThemedText type="link">Link Text</ThemedText>
    );
    
    const textElement = getByText('Link Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          lineHeight: 30,
          fontSize: 16,
          color: '#0a7ea4',
        })
      ])
    );
  });

  it('merges custom styles with type styles', () => {
    const customStyle = { marginTop: 10, padding: 5 };
    const { getByText } = render(
      <ThemedText type="default" style={customStyle}>
        Styled Text
      </ThemedText>
    );
    
    const textElement = getByText('Styled Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining(customStyle),
        expect.objectContaining({
          fontSize: 16,
          lineHeight: 24,
        })
      ])
    );
  });

  it('passes through additional Text props', () => {
    const { getByText } = render(
      <ThemedText
        numberOfLines={2}
        ellipsizeMode="tail"
        testID="themed-text"
      >
        Props Test
      </ThemedText>
    );
    
    const textElement = getByText('Props Test');
    expect(textElement.props.numberOfLines).toBe(2);
    expect(textElement.props.ellipsizeMode).toBe('tail');
    expect(textElement.props.testID).toBe('themed-text');
  });

  it('applies themed color correctly', () => {
    const mockUseThemeColor = require('../../hooks/useThemeColor').useThemeColor;
    mockUseThemeColor.mockReturnValue('#123456');
    
    const { getByText } = render(
      <ThemedText>Themed Color Text</ThemedText>
    );
    
    const textElement = getByText('Themed Color Text');
    expect(textElement.props.style).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          color: '#123456'
        })
      ])
    );
  });

  it('passes light and dark colors to useThemeColor hook', () => {
    const mockUseThemeColor = require('../../hooks/useThemeColor').useThemeColor;
    
    render(
      <ThemedText lightColor="#ffffff" darkColor="#000000">
        Color Theme Test
      </ThemedText>
    );
    
    expect(mockUseThemeColor).toHaveBeenCalledWith(
      { light: '#ffffff', dark: '#000000' },
      'text'
    );
  });
});