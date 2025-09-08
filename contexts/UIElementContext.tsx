import React, { createContext, useContext, useMemo, useState, useCallback } from 'react';

export interface UIElementLayout {
  x: number;
  y: number;
  width: number;
  height: number;
  id?: string;
  type?: 'button' | 'card' | 'input' | 'notification' | 'alert' | 'menu' | 'image' | 'text' | 'other';
  priority?: 'low' | 'medium' | 'high' | 'critical'; // For companion attention priority
  accessible?: boolean; // Whether element supports accessibility
  interactive?: boolean; // Whether element can be interacted with
  metadata?: Record<string, any>; // Additional context for AI
}

interface UIElementContextValue {
  elements: Record<string, UIElementLayout>;
  registerElement: (id: string, layout: UIElementLayout) => void;
  unregisterElement: (id: string) => void;
  updateElement: (id: string, updates: Partial<UIElementLayout>) => void;
  getElementsInArea: (x: number, y: number, radius: number) => UIElementLayout[];
  getHighPriorityElements: () => UIElementLayout[];
  getInteractiveElements: () => UIElementLayout[];
}

// --- Context for UI Element Awareness ---
const UIElementContext = createContext<UIElementContextValue>({
  elements: {},
  registerElement: () => {},
  unregisterElement: () => {},
  updateElement: () => {},
  getElementsInArea: () => [],
  getHighPriorityElements: () => [],
  getInteractiveElements: () => [],
});

export const UIElementProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const [elements, setElements] = useState<Record<string, UIElementLayout>>({});

  const registerElement = useCallback((id: string, layout: UIElementLayout) => {
    setElements((prev) => ({ ...prev, [id]: layout }));
  }, []);

  const unregisterElement = useCallback((id: string) => {
    setElements((prev) => {
      const newElements = { ...prev };
      delete newElements[id];
      return newElements;
    });
  }, []);

  const updateElement = useCallback((id: string, updates: Partial<UIElementLayout>) => {
    setElements((prev) => ({
      ...prev,
      [id]: prev[id] ? { ...prev[id], ...updates } : prev[id],
    }));
  }, []);

  const getElementsInArea = useCallback((x: number, y: number, radius: number): UIElementLayout[] => {
    return Object.values(elements).filter((element) => {
      if (!element) return false;
      const elementCenterX = element.x + element.width / 2;
      const elementCenterY = element.y + element.height / 2;
      const distance = Math.sqrt(
        Math.pow(elementCenterX - x, 2) + Math.pow(elementCenterY - y, 2)
      );
      return distance <= radius;
    });
  }, [elements]);

  const getHighPriorityElements = useCallback((): UIElementLayout[] => {
    return Object.values(elements).filter((element) => 
      element && (element.priority === 'high' || element.priority === 'critical')
    );
  }, [elements]);

  const getInteractiveElements = useCallback((): UIElementLayout[] => {
    return Object.values(elements).filter((element) => 
      element && element.interactive !== false
    );
  }, [elements]);

  const value = useMemo<UIElementContextValue>(
    () => ({ 
      elements, 
      registerElement, 
      unregisterElement, 
      updateElement,
      getElementsInArea,
      getHighPriorityElements,
      getInteractiveElements,
    }),
    [
      elements, 
      registerElement, 
      unregisterElement, 
      updateElement,
      getElementsInArea,
      getHighPriorityElements,
      getInteractiveElements,
    ],
  );

  return <UIElementContext.Provider value={value}>{children}</UIElementContext.Provider>;
};

export const useUIElements = () => useContext(UIElementContext);
