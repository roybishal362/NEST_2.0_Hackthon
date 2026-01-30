import { ReactNode, useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import Sidebar from './Sidebar';

interface LayoutProps {
    children: ReactNode;
}

// Breadcrumb mapping
const getBreadcrumbs = (pathname: string) => {
    const paths = pathname.split('/').filter(Boolean);
    const breadcrumbs = [{ label: 'Home', path: '/' }];
    
    let currentPath = '';
    for (const segment of paths) {
        currentPath += `/${segment}`;
        const label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');
        breadcrumbs.push({ label, path: currentPath });
    }
    
    return breadcrumbs;
};

const Layout = ({ children }: LayoutProps) => {
    const location = useLocation();
    const [darkMode, setDarkMode] = useState(true);
    const [showNotifications, setShowNotifications] = useState(false);
    const breadcrumbs = getBreadcrumbs(location.pathname);

    const toggleDarkMode = () => {
        setDarkMode(!darkMode);
        document.documentElement.classList.toggle('dark');
    };

    return (
        <div className={`min-h-screen ${darkMode ? 'bg-slate-950 text-slate-200' : 'bg-slate-50 text-slate-900'} font-sans selection:bg-indigo-500/30`}>
            <div className="flex">
                <Sidebar />
                <div className="flex-1 ml-64 min-h-screen">
                    {/* Header */}
                    <header className={`sticky top-0 z-40 h-16 ${darkMode ? 'bg-slate-900/80' : 'bg-white/80'} backdrop-blur-md border-b ${darkMode ? 'border-slate-800' : 'border-slate-200'}`}>
                        <div className="h-full px-8 flex items-center justify-between">
                            {/* Breadcrumbs */}
                            <nav className="flex items-center space-x-2 text-sm">
                                {breadcrumbs.map((crumb, index) => (
                                    <div key={crumb.path} className="flex items-center">
                                        {index > 0 && (
                                            <svg className="w-4 h-4 mx-2 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                            </svg>
                                        )}
                                        {index === breadcrumbs.length - 1 ? (
                                            <span className={`font-medium ${darkMode ? 'text-slate-200' : 'text-slate-900'}`}>{crumb.label}</span>
                                        ) : (
                                            <Link 
                                                to={crumb.path} 
                                                className={`${darkMode ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-700'} transition-colors`}
                                            >
                                                {crumb.label}
                                            </Link>
                                        )}
                                    </div>
                                ))}
                            </nav>

                            {/* Right side actions */}
                            <div className="flex items-center gap-4">
                                {/* Search */}
                                <div className={`relative hidden md:block`}>
                                    <input
                                        type="text"
                                        placeholder="Search studies..."
                                        className={`w-64 px-4 py-2 pl-10 text-sm rounded-lg ${
                                            darkMode 
                                                ? 'bg-slate-800 border-slate-700 text-slate-200 placeholder-slate-500' 
                                                : 'bg-slate-100 border-slate-200 text-slate-900 placeholder-slate-400'
                                        } border focus:outline-none focus:ring-2 focus:ring-indigo-500/50`}
                                    />
                                    <svg className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                </div>

                                {/* Theme toggle */}
                                <button
                                    onClick={toggleDarkMode}
                                    className={`p-2 rounded-lg ${darkMode ? 'hover:bg-slate-800' : 'hover:bg-slate-200'} transition-colors`}
                                    title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
                                >
                                    {darkMode ? (
                                        <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                                        </svg>
                                    )}
                                </button>

                                {/* Notifications */}
                                <div className="relative">
                                    <button
                                        onClick={() => setShowNotifications(!showNotifications)}
                                        className={`relative p-2 rounded-lg ${darkMode ? 'hover:bg-slate-800' : 'hover:bg-slate-200'} transition-colors`}
                                    >
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                                        </svg>
                                        {/* Notification badge */}
                                        <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
                                    </button>

                                    {/* Notification dropdown */}
                                    {showNotifications && (
                                        <div className={`absolute right-0 mt-2 w-80 rounded-xl shadow-xl ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'} border overflow-hidden z-50`}>
                                            <div className={`px-4 py-3 ${darkMode ? 'border-slate-700' : 'border-slate-200'} border-b`}>
                                                <h3 className="font-semibold">Notifications</h3>
                                            </div>
                                            <div className="max-h-96 overflow-y-auto">
                                                <div className={`px-4 py-3 ${darkMode ? 'hover:bg-slate-700/50' : 'hover:bg-slate-50'} cursor-pointer`}>
                                                    <div className="flex items-start gap-3">
                                                        <span className="text-red-500">🚨</span>
                                                        <div>
                                                            <p className="text-sm font-medium">SAE Review Overdue</p>
                                                            <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Study 08 - 10 min ago</p>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className={`px-4 py-3 ${darkMode ? 'hover:bg-slate-700/50' : 'hover:bg-slate-50'} cursor-pointer`}>
                                                    <div className="flex items-start gap-3">
                                                        <span className="text-amber-500">⚠️</span>
                                                        <div>
                                                            <p className="text-sm font-medium">Data Entry Lag</p>
                                                            <p className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>Study 05 - 1 hour ago</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <Link 
                                                to="/notifications" 
                                                className={`block px-4 py-3 text-center text-sm font-medium text-indigo-500 ${darkMode ? 'border-slate-700 hover:bg-slate-700/50' : 'border-slate-200 hover:bg-slate-50'} border-t`}
                                                onClick={() => setShowNotifications(false)}
                                            >
                                                View all notifications
                                            </Link>
                                        </div>
                                    )}
                                </div>

                                {/* User profile */}
                                <div className="flex items-center gap-3 pl-4 border-l border-slate-700">
                                    <div className={`w-8 h-8 rounded-full ${darkMode ? 'bg-slate-700' : 'bg-slate-200'} flex items-center justify-center text-xs font-bold`}>
                                        JD
                                    </div>
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Main content */}
                    <main className="p-8 min-h-[calc(100vh-4rem)] overflow-x-hidden">
                        <div className="max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
                            {children}
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
};

export default Layout;
