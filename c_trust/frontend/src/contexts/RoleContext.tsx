/**
 * Role Context for C-TRUST Dashboard
 * ===================================
 * Provides role-based access control context for the application.
 * Allows switching between CRA, Data Manager, and Study Lead views.
 */

import React, { createContext, useContext, useState, ReactNode } from 'react';

// Define role types
export type Role = 'CRA' | 'DATA_MANAGER' | 'STUDY_LEAD';

// Role display names and descriptions
export const ROLE_INFO: Record<Role, { displayName: string; description: string; focus: string[] }> = {
  CRA: {
    displayName: 'Clinical Research Associate',
    description: 'Focuses on site-level data quality and patient safety monitoring',
    focus: ['Site Performance', 'Data Completeness', 'Query Resolution'],
  },
  DATA_MANAGER: {
    displayName: 'Data Manager',
    description: 'Focuses on overall data quality, coding, and database lock readiness',
    focus: ['DQI Scores', 'Coding Progress', 'Data Integrity'],
  },
  STUDY_LEAD: {
    displayName: 'Study Lead',
    description: 'Executive overview of study health and risk assessment',
    focus: ['Portfolio Overview', 'Risk Assessment', 'Strategic Decisions'],
  },
};

// Role-specific settings
export const ROLE_SETTINGS: Record<Role, { 
  primaryMetrics: string[];
  alertPriority: string[];
  dashboardDefault: string;
}> = {
  CRA: {
    primaryMetrics: ['site_performance', 'query_aging', 'form_completion'],
    alertPriority: ['safety', 'query', 'completeness'],
    dashboardDefault: 'study-details',
  },
  DATA_MANAGER: {
    primaryMetrics: ['dqi_score', 'coding_completion', 'data_integrity'],
    alertPriority: ['coding', 'completeness', 'cross_evidence'],
    dashboardDefault: 'analytics',
  },
  STUDY_LEAD: {
    primaryMetrics: ['portfolio_risk', 'dqi_trends', 'milestone_status'],
    alertPriority: ['critical', 'high', 'safety'],
    dashboardDefault: 'portfolio',
  },
};

// Context type
interface RoleContextType {
  currentRole: Role;
  setCurrentRole: (role: Role) => void;
  roleInfo: typeof ROLE_INFO[Role];
  roleSettings: typeof ROLE_SETTINGS[Role];
  isRoleAllowed: (allowedRoles: Role[]) => boolean;
}

// Create context with default value
const RoleContext = createContext<RoleContextType | null>(null);

// Provider props
interface RoleProviderProps {
  children: ReactNode;
  defaultRole?: Role;
}

/**
 * Role Context Provider
 * Wraps the application to provide role-based access control
 */
export function RoleProvider({ children, defaultRole = 'STUDY_LEAD' }: RoleProviderProps) {
  const [currentRole, setCurrentRole] = useState<Role>(defaultRole);

  // Check if current role is in allowed list
  const isRoleAllowed = (allowedRoles: Role[]): boolean => {
    return allowedRoles.includes(currentRole);
  };

  const value: RoleContextType = {
    currentRole,
    setCurrentRole,
    roleInfo: ROLE_INFO[currentRole],
    roleSettings: ROLE_SETTINGS[currentRole],
    isRoleAllowed,
  };

  return (
    <RoleContext.Provider value={value}>
      {children}
    </RoleContext.Provider>
  );
}

/**
 * Hook to access role context
 * @throws Error if used outside RoleProvider
 */
export function useRole(): RoleContextType {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
}

/**
 * HOC to restrict component to certain roles
 */
export function withRoleAccess<P extends object>(
  Component: React.ComponentType<P>,
  allowedRoles: Role[],
  fallback?: React.ReactNode
) {
  return function RoleRestrictedComponent(props: P) {
    const { isRoleAllowed } = useRole();
    
    if (!isRoleAllowed(allowedRoles)) {
      return fallback || null;
    }
    
    return <Component {...props} />;
  };
}

export { RoleContext };
export default RoleProvider;
