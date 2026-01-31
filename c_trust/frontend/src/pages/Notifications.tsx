// Notifications Page - Role-based alerts and notifications
// ========================================
import { useState } from 'react';

type NotificationType = 'critical' | 'warning' | 'info' | 'success';
type UserRole = 'CRA' | 'DataManager' | 'StudyLead' | 'All';

interface Notification {
    id: number;
    type: NotificationType;
    title: string;
    message: string;
    study: string;
    timestamp: string;
    role: UserRole;
    read: boolean;
    acknowledged: boolean;
}

const mockNotifications: Notification[] = [
    {
        id: 1,
        type: 'critical',
        title: 'SAE Review Overdue',
        message: '3 SAEs in Study 08 have exceeded the 48-hour review window. Immediate action required.',
        study: 'STUDY_08',
        timestamp: '10 minutes ago',
        role: 'StudyLead',
        read: false,
        acknowledged: false,
    },
    {
        id: 2,
        type: 'warning',
        title: 'Data Entry Lag Detected',
        message: 'Site SITE-101 shows a 5-day lag in data entry. Consider scheduling a monitoring visit.',
        study: 'STUDY_05',
        timestamp: '1 hour ago',
        role: 'CRA',
        read: false,
        acknowledged: false,
    },
    {
        id: 3,
        type: 'warning',
        title: 'Query Backlog Increasing',
        message: 'Open queries have increased by 25% in the past week. Review query management process.',
        study: 'STUDY_02',
        timestamp: '2 hours ago',
        role: 'DataManager',
        read: true,
        acknowledged: false,
    },
    {
        id: 4,
        type: 'info',
        title: 'DQI Score Improved',
        message: 'Study 11 DQI score improved from 72 to 81 following data cleanup activities.',
        study: 'STUDY_11',
        timestamp: '3 hours ago',
        role: 'All',
        read: true,
        acknowledged: true,
    },
    {
        id: 5,
        type: 'success',
        title: 'Enrollment Target Met',
        message: 'Study 15 has reached 100% enrollment target ahead of schedule.',
        study: 'STUDY_15',
        timestamp: '5 hours ago',
        role: 'StudyLead',
        read: true,
        acknowledged: true,
    },
];

function getTypeStyles(type: NotificationType) {
    switch (type) {
        case 'critical':
            return {
                bg: 'bg-red-50 dark:bg-red-900/20',
                border: 'border-red-200 dark:border-red-800',
                icon: '🚨',
                badge: 'bg-red-500 text-white',
            };
        case 'warning':
            return {
                bg: 'bg-amber-50 dark:bg-amber-900/20',
                border: 'border-amber-200 dark:border-amber-800',
                icon: '⚠️',
                badge: 'bg-amber-500 text-white',
            };
        case 'info':
            return {
                bg: 'bg-blue-50 dark:bg-blue-900/20',
                border: 'border-blue-200 dark:border-blue-800',
                icon: 'ℹ️',
                badge: 'bg-blue-500 text-white',
            };
        case 'success':
            return {
                bg: 'bg-green-50 dark:bg-green-900/20',
                border: 'border-green-200 dark:border-green-800',
                icon: '✅',
                badge: 'bg-green-500 text-white',
            };
    }
}

function getRoleBadge(role: UserRole) {
    switch (role) {
        case 'CRA':
            return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300';
        case 'DataManager':
            return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300';
        case 'StudyLead':
            return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300';
        default:
            return 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300';
    }
}

export default function Notifications() {
    const [notifications, setNotifications] = useState(mockNotifications);
    const [filter, setFilter] = useState<'all' | 'unread' | 'critical'>('all');
    const [roleFilter, setRoleFilter] = useState<UserRole | 'All'>('All');

    const filteredNotifications = notifications.filter(n => {
        if (filter === 'unread' && n.read) return false;
        if (filter === 'critical' && n.type !== 'critical') return false;
        if (roleFilter !== 'All' && n.role !== roleFilter && n.role !== 'All') return false;
        return true;
    });

    const handleMarkRead = (id: number) => {
        setNotifications(prev =>
            prev.map(n => n.id === id ? { ...n, read: true } : n)
        );
    };

    const handleAcknowledge = (id: number) => {
        setNotifications(prev =>
            prev.map(n => n.id === id ? { ...n, acknowledged: true, read: true } : n)
        );
    };

    const handleMarkAllRead = () => {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    };

    const unreadCount = notifications.filter(n => !n.read).length;
    const criticalCount = notifications.filter(n => n.type === 'critical' && !n.acknowledged).length;

    return (
        <div className="space-y-6">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Notifications</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">Role-based alerts and system notifications.</p>
                </div>
                <button
                    onClick={handleMarkAllRead}
                    className="px-4 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                >
                    Mark all as read
                </button>
            </header>

            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="text-sm text-slate-500 dark:text-slate-400">Unread</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{unreadCount}</div>
                </div>
                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="text-sm text-slate-500 dark:text-slate-400">Critical Pending</div>
                    <div className="text-2xl font-bold text-red-600">{criticalCount}</div>
                </div>
                <div className="bg-white dark:bg-slate-800 p-4 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="text-sm text-slate-500 dark:text-slate-400">Total</div>
                    <div className="text-2xl font-bold text-slate-900 dark:text-white">{notifications.length}</div>
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-4">
                <div className="flex gap-2">
                    {(['all', 'unread', 'critical'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                                filter === f
                                    ? 'bg-indigo-600 text-white'
                                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300'
                            }`}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </button>
                    ))}
                </div>
                <div className="flex gap-2">
                    {(['All', 'CRA', 'DataManager', 'StudyLead'] as const).map(r => (
                        <button
                            key={r}
                            onClick={() => setRoleFilter(r)}
                            className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                                roleFilter === r
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300'
                            }`}
                        >
                            {r === 'DataManager' ? 'Data Manager' : r === 'StudyLead' ? 'Study Lead' : r}
                        </button>
                    ))}
                </div>
            </div>

            {/* Notification List */}
            <div className="space-y-3">
                {filteredNotifications.length === 0 ? (
                    <div className="text-center py-12 text-slate-500 dark:text-slate-400">
                        No notifications match your filters.
                    </div>
                ) : (
                    filteredNotifications.map(notification => {
                        const styles = getTypeStyles(notification.type);
                        return (
                            <div
                                key={notification.id}
                                className={`p-4 rounded-xl border ${styles.bg} ${styles.border} ${
                                    !notification.read ? 'ring-2 ring-indigo-500/20' : ''
                                }`}
                            >
                                <div className="flex items-start gap-4">
                                    <span className="text-2xl">{styles.icon}</span>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`px-2 py-0.5 text-xs font-semibold rounded ${styles.badge}`}>
                                                {notification.type.toUpperCase()}
                                            </span>
                                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${getRoleBadge(notification.role)}`}>
                                                {notification.role === 'DataManager' ? 'Data Manager' : notification.role === 'StudyLead' ? 'Study Lead' : notification.role}
                                            </span>
                                            <span className="text-xs text-slate-500 dark:text-slate-400">{notification.study}</span>
                                            {!notification.read && (
                                                <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                                            )}
                                        </div>
                                        <h3 className="font-semibold text-slate-900 dark:text-white">{notification.title}</h3>
                                        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{notification.message}</p>
                                        <div className="text-xs text-slate-500 dark:text-slate-500 mt-2">{notification.timestamp}</div>
                                    </div>
                                    <div className="flex flex-col gap-2">
                                        {!notification.read && (
                                            <button
                                                onClick={() => handleMarkRead(notification.id)}
                                                className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400"
                                            >
                                                Mark read
                                            </button>
                                        )}
                                        {!notification.acknowledged && (
                                            <button
                                                onClick={() => handleAcknowledge(notification.id)}
                                                className="px-3 py-1.5 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-700 transition-colors"
                                            >
                                                Acknowledge
                                            </button>
                                        )}
                                        {notification.acknowledged && (
                                            <span className="text-xs text-green-600 font-medium">✓ Acknowledged</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
