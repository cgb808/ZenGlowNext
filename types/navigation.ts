// Navigation Types for Expo Router

import { NavigatorScreenParams } from '@react-navigation/native';

export type RootStackParamList = {
  '(tabs)': NavigatorScreenParams<TabParamList>;
  ParentDashboardScreen: undefined;
  RoutineBuilderScreen: undefined;
  '+not-found': undefined;
};

export type TabParamList = {
  index: undefined;
  explore: undefined;
  child: undefined;
  parent: undefined;
  routine: undefined;
};

export type StackScreenProps<T extends keyof RootStackParamList> = {
  route: { params: RootStackParamList[T] };
  navigation: any; // TODO: Add proper navigation types
};

export type TabScreenProps<T extends keyof TabParamList> = {
  route: { params: TabParamList[T] };
  navigation: any; // TODO: Add proper navigation types
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}