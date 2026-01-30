// DQI Score Gauge Component
// ========================================
import { useEffect, useState } from 'react';

interface DQIGaugeProps {
    score: number;
    size?: 'sm' | 'md' | 'lg';
    showLabel?: boolean;
    animated?: boolean;
}

export function DQIGauge({ score, size = 'md', showLabel = true, animated = true }: DQIGaugeProps) {
    const [displayScore, setDisplayScore] = useState(animated ? 0 : score);
    
    // Animate score on mount
    useEffect(() => {
        if (!animated) return;
        
        const duration = 1000;
        const steps = 60;
        const increment = score / steps;
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= score) {
                setDisplayScore(score);
                clearInterval(timer);
            } else {
                setDisplayScore(Math.round(current));
            }
        }, duration / steps);
        
        return () => clearInterval(timer);
    }, [score, animated]);

    // Size configurations
    const sizes = {
        sm: { width: 80, strokeWidth: 6, fontSize: 'text-lg' },
        md: { width: 120, strokeWidth: 8, fontSize: 'text-2xl' },
        lg: { width: 160, strokeWidth: 10, fontSize: 'text-4xl' },
    };
    
    const config = sizes[size];
    const radius = (config.width - config.strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = (displayScore / 100) * circumference;
    
    // Color based on score
    const getColor = (s: number) => {
        if (s >= 85) return { stroke: '#22c55e', bg: 'bg-green-500/10', text: 'text-green-500' };
        if (s >= 65) return { stroke: '#f59e0b', bg: 'bg-amber-500/10', text: 'text-amber-500' };
        if (s >= 40) return { stroke: '#f97316', bg: 'bg-orange-500/10', text: 'text-orange-500' };
        return { stroke: '#ef4444', bg: 'bg-red-500/10', text: 'text-red-500' };
    };
    
    const colors = getColor(displayScore);
    
    // Band label
    const getBandLabel = (s: number) => {
        if (s >= 85) return 'Green';
        if (s >= 65) return 'Amber';
        if (s >= 40) return 'Orange';
        return 'Red';
    };

    return (
        <div className="flex flex-col items-center">
            <div className="relative" style={{ width: config.width, height: config.width }}>
                <svg
                    className="transform -rotate-90"
                    width={config.width}
                    height={config.width}
                >
                    {/* Background circle */}
                    <circle
                        cx={config.width / 2}
                        cy={config.width / 2}
                        r={radius}
                        fill="none"
                        stroke="currentColor"
                        strokeWidth={config.strokeWidth}
                        className="text-slate-200 dark:text-slate-700"
                    />
                    {/* Progress circle */}
                    <circle
                        cx={config.width / 2}
                        cy={config.width / 2}
                        r={radius}
                        fill="none"
                        stroke={colors.stroke}
                        strokeWidth={config.strokeWidth}
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={circumference - progress}
                        className="transition-all duration-1000 ease-out"
                    />
                </svg>
                {/* Score text */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={`${config.fontSize} font-bold ${colors.text}`}>
                        {Math.round(displayScore)}
                    </span>
                    {showLabel && (
                        <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                            {getBandLabel(displayScore)}
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

export default DQIGauge;
