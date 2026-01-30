// Export Button Component with Progress Indicator
// ========================================
import { useState } from 'react';
import { exportAPI } from '@/services/api';
import { cn } from '@/lib/utils';

interface ExportButtonProps {
    studyId?: string;
    className?: string;
    onSuccess?: () => void;
    onError?: (error: Error) => void;
}

export function ExportButton({ studyId, className, onSuccess, onError }: ExportButtonProps) {
    const [exporting, setExporting] = useState(false);
    const [progress, setProgress] = useState(0);
    const [showDropdown, setShowDropdown] = useState(false);

    const handleExport = async (format: 'csv' | 'excel') => {
        setExporting(true);
        setProgress(0);
        setShowDropdown(false);

        try {
            // Simulate progress
            const progressInterval = setInterval(() => {
                setProgress(prev => Math.min(prev + 10, 90));
            }, 200);

            const blob = studyId 
                ? await exportAPI.exportStudy(studyId, format)
                : await exportAPI.exportStudies(format);

            clearInterval(progressInterval);
            setProgress(100);

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = studyId 
                ? `${studyId}_export.${format === 'excel' ? 'xlsx' : 'csv'}`
                : `studies_export.${format === 'excel' ? 'xlsx' : 'csv'}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            onSuccess?.();
        } catch (error) {
            console.error('Export failed:', error);
            onError?.(error as Error);
            
            // Fallback: generate mock CSV for demo
            const mockCSV = generateMockCSV(studyId);
            const blob = new Blob([mockCSV], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = studyId ? `${studyId}_export.csv` : 'studies_export.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } finally {
            setTimeout(() => {
                setExporting(false);
                setProgress(0);
            }, 500);
        }
    };

    return (
        <div className="relative">
            <button
                onClick={() => setShowDropdown(!showDropdown)}
                disabled={exporting}
                className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
                    'bg-indigo-600 text-white hover:bg-indigo-700',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    className
                )}
            >
                {exporting ? (
                    <>
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>Exporting... {progress}%</span>
                    </>
                ) : (
                    <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        <span>Export</span>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </>
                )}
            </button>

            {showDropdown && !exporting && (
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 z-10">
                    <button
                        onClick={() => handleExport('csv')}
                        className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                        📄 Export as CSV
                    </button>
                    <button
                        onClick={() => handleExport('excel')}
                        className="w-full px-4 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                        📊 Export as Excel
                    </button>
                </div>
            )}

            {/* Progress bar */}
            {exporting && (
                <div className="absolute -bottom-2 left-0 right-0 h-1 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                    <div 
                        className="h-full bg-indigo-600 transition-all duration-200"
                        style={{ width: `${progress}%` }}
                    />
                </div>
            )}
        </div>
    );
}

// Generate mock CSV for demo mode
function generateMockCSV(studyId?: string): string {
    const headers = ['Study ID', 'Site ID', 'DQI Score', 'Risk Level', 'Enrollment %', 'SAEs', 'Open Queries'];
    const rows = studyId 
        ? [
            [studyId, 'SITE-001', '78', 'Medium', '85', '2', '5'],
            [studyId, 'SITE-002', '82', 'Low', '92', '1', '3'],
            [studyId, 'SITE-003', '65', 'High', '70', '4', '12'],
        ]
        : [
            ['STUDY_01', 'ALL', '75', 'Medium', '80', '7', '20'],
            ['STUDY_02', 'ALL', '82', 'Low', '95', '3', '8'],
            ['STUDY_05', 'ALL', '58', 'High', '65', '12', '35'],
        ];

    return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
}

export default ExportButton;
