/**
 * Role Switcher Component
 * =======================
 * Dropdown component for switching between user roles.
 * Provides visual feedback and role descriptions.
 */

import React from 'react';
import { useRole, Role, ROLE_INFO } from '../contexts/RoleContext';

// Role icons (using emoji for simplicity)
const ROLE_ICONS: Record<Role, string> = {
    CRA: '👤',
    DATA_MANAGER: '📊',
    STUDY_LEAD: '👔',
};

// Role colors for visual distinction
const ROLE_COLORS: Record<Role, string> = {
    CRA: '#3B82F6',      // Blue
    DATA_MANAGER: '#10B981', // Green
    STUDY_LEAD: '#8B5CF6',   // Purple
};

interface RoleSwitcherProps {
    className?: string;
    showDescription?: boolean;
    compact?: boolean;
}

export function RoleSwitcher({
    className = '',
    showDescription = true,
    compact = false
}: RoleSwitcherProps) {
    const { currentRole, setCurrentRole, roleInfo } = useRole();
    const [isOpen, setIsOpen] = React.useState(false);
    const dropdownRef = React.useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    React.useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleRoleSelect = (role: Role) => {
        setCurrentRole(role);
        setIsOpen(false);
    };

    return (
        <div className={`role-switcher ${className}`} ref={dropdownRef}>
            <button
                className="role-switcher-button"
                onClick={() => setIsOpen(!isOpen)}
                style={{ borderColor: ROLE_COLORS[currentRole] }}
            >
                <span className="role-icon">{ROLE_ICONS[currentRole]}</span>
                {!compact && (
                    <span className="role-name">{roleInfo.displayName}</span>
                )}
                <span className="dropdown-arrow">{isOpen ? '▲' : '▼'}</span>
            </button>

            {isOpen && (
                <div className="role-dropdown">
                    {(Object.keys(ROLE_INFO) as Role[]).map((role) => (
                        <button
                            key={role}
                            className={`role-option ${role === currentRole ? 'active' : ''}`}
                            onClick={() => handleRoleSelect(role)}
                            style={{
                                borderLeftColor: ROLE_COLORS[role],
                                backgroundColor: role === currentRole ? `${ROLE_COLORS[role]}15` : undefined
                            }}
                        >
                            <div className="role-option-header">
                                <span className="role-icon">{ROLE_ICONS[role]}</span>
                                <span className="role-display-name">{ROLE_INFO[role].displayName}</span>
                                {role === currentRole && <span className="active-badge">Active</span>}
                            </div>
                            {showDescription && (
                                <p className="role-description">{ROLE_INFO[role].description}</p>
                            )}
                            <div className="role-focus-tags">
                                {ROLE_INFO[role].focus.map((focus) => (
                                    <span key={focus} className="focus-tag">{focus}</span>
                                ))}
                            </div>
                        </button>
                    ))}
                </div>
            )}

            <style>{`
        .role-switcher {
          position: relative;
          display: inline-block;
        }

        .role-switcher-button {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          background: linear-gradient(135deg, #1e293b, #0f172a);
          border: 2px solid;
          border-radius: 8px;
          color: white;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s ease;
        }

        .role-switcher-button:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .role-icon {
          font-size: 18px;
        }

        .dropdown-arrow {
          font-size: 10px;
          margin-left: 4px;
          opacity: 0.7;
        }

        .role-dropdown {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          min-width: 320px;
          background: linear-gradient(135deg, #1e293b, #0f172a);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
          z-index: 1000;
          overflow: hidden;
        }

        .role-option {
          display: block;
          width: 100%;
          padding: 16px;
          border: none;
          border-left: 4px solid transparent;
          background: transparent;
          color: white;
          text-align: left;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .role-option:hover {
          background: rgba(255, 255, 255, 0.05);
        }

        .role-option.active {
          border-left-width: 4px;
        }

        .role-option-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }

        .role-display-name {
          font-weight: 600;
          font-size: 15px;
        }

        .active-badge {
          font-size: 10px;
          padding: 2px 8px;
          background: rgba(16, 185, 129, 0.2);
          color: #10B981;
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: 600;
          margin-left: auto;
        }

        .role-description {
          font-size: 12px;
          color: rgba(255, 255, 255, 0.6);
          margin: 4px 0 8px 26px;
          line-height: 1.4;
        }

        .role-focus-tags {
          display: flex;
          gap: 6px;
          margin-left: 26px;
          flex-wrap: wrap;
        }

        .focus-tag {
          font-size: 10px;
          padding: 2px 8px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
          color: rgba(255, 255, 255, 0.7);
        }
      `}</style>
        </div>
    );
}

export default RoleSwitcher;
