// Settings Page - System configuration and user preferences
// ========================================
import { useState } from 'react';

export default function Settings() {
    const [notifications, setNotifications] = useState({
        email: true,
        push: true,
        critical: true,
        weekly: false,
    });

    return (
        <div className="space-y-8 max-w-3xl">
            <header>
                <h1 className="text-3xl font-bold text-white tracking-tight">Settings</h1>
                <p className="text-slate-400 mt-2">Manage your preferences and system configuration.</p>
            </header>

            {/* Notifications */}
            <section className="bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-700">
                <h2 className="text-lg font-semibold text-white mb-4">Notifications</h2>
                <div className="space-y-4">
                    {[
                        { key: 'email', label: 'Email Notifications', desc: 'Receive alerts via email' },
                        { key: 'push', label: 'Push Notifications', desc: 'Browser push notifications' },
                        { key: 'critical', label: 'Critical Alerts Only', desc: 'Only notify for critical issues' },
                        { key: 'weekly', label: 'Weekly Digest', desc: 'Receive weekly summary reports' },
                    ].map(item => (
                        <div key={item.key} className="flex items-center justify-between py-2">
                            <div>
                                <div className="font-medium text-white">{item.label}</div>
                                <div className="text-sm text-slate-400">{item.desc}</div>
                            </div>
                            <button
                                onClick={() => setNotifications(prev => ({ ...prev, [item.key]: !prev[item.key as keyof typeof prev] }))}
                                className={`relative w-14 h-8 rounded-full transition-colors ${
                                    notifications[item.key as keyof typeof notifications] ? 'bg-indigo-600' : 'bg-slate-600'
                                }`}
                            >
                                <span
                                    className={`absolute top-1 w-6 h-6 bg-white rounded-full shadow transition-transform ${
                                        notifications[item.key as keyof typeof notifications] ? 'translate-x-7' : 'translate-x-1'
                                    }`}
                                />
                            </button>
                        </div>
                    ))}
                </div>
            </section>

            {/* DQI Configuration */}
            <section className="bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-700">
                <h2 className="text-lg font-semibold text-white mb-4">DQI Configuration</h2>
                <p className="text-sm text-slate-400 mb-4">
                    Current DQI weights (read-only). Changes require administrator approval.
                </p>
                <div className="space-y-3">
                    {[
                        { name: 'Safety', weight: 35, color: 'bg-red-500' },
                        { name: 'Compliance', weight: 25, color: 'bg-amber-500' },
                        { name: 'Completeness', weight: 20, color: 'bg-blue-500' },
                        { name: 'Operations', weight: 15, color: 'bg-green-500' },
                    ].map(dim => (
                        <div key={dim.name} className="flex items-center gap-4">
                            <div className="w-32 text-sm font-medium text-slate-300">{dim.name}</div>
                            <div className="flex-1 bg-slate-700 rounded-full h-3 overflow-hidden">
                                <div className={`h-full ${dim.color}`} style={{ width: `${dim.weight}%` }} />
                            </div>
                            <div className="w-12 text-right text-sm font-semibold text-white">{dim.weight}%</div>
                        </div>
                    ))}
                </div>
            </section>

            {/* System Info */}
            <section className="bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-700">
                <h2 className="text-lg font-semibold text-white mb-4">System Information</h2>
                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <div className="text-slate-400">Version</div>
                        <div className="font-medium text-white">C-TRUST v1.0.0</div>
                    </div>
                    <div>
                        <div className="text-slate-400">Environment</div>
                        <div className="font-medium text-white">Development</div>
                    </div>
                    <div>
                        <div className="text-slate-400">API Status</div>
                        <div className="font-medium text-green-600">Connected</div>
                    </div>
                    <div>
                        <div className="text-slate-400">Last Data Refresh</div>
                        <div className="font-medium text-white">2 hours ago</div>
                    </div>
                </div>
            </section>
        </div>
    );
}
