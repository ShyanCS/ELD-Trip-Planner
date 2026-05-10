import { useState } from 'react';
import { jsPDF } from 'jspdf';
import './ExportPdfButton.css';

export default function ExportPdfButton() {
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);

    // Yield to the event loop so React can render the 'Generating PDF...' state
    await new Promise((resolve) => setTimeout(resolve, 50));

    try {
      // Find all log sheet canvases
      const canvases = document.querySelectorAll('.log-sheet__canvas');
      
      if (canvases.length === 0) {
        alert('No log sheets found to export.');
        setIsExporting(false);
        return;
      }

      // Initialize jsPDF in landscape with the exact dimensions of our canvas
      // CANVAS_W = 1100, CANVAS_H = 520 from LogSheet.jsx
      const doc = new jsPDF({
        orientation: 'landscape',
        unit: 'px',
        format: [1100, 520]
      });

      canvases.forEach((canvas, index) => {
        if (index > 0) {
          doc.addPage([1100, 520], 'landscape');
        }
        
        // The canvas is rendered at high DPI, but toDataURL gets the pixel data
        // We render it onto the 1100x520 PDF canvas size.
        const imgData = canvas.toDataURL('image/png');
        doc.addImage(imgData, 'PNG', 0, 0, 1100, 520);
      });

      doc.save('eld-daily-logs.pdf');
    } catch (err) {
      console.error('Failed to export PDF:', err);
      alert('Failed to generate PDF. Check console for details.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <button 
      className={`btn-export-pdf ${isExporting ? 'exporting' : ''}`} 
      onClick={handleExport}
      disabled={isExporting}
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      {isExporting ? 'Generating PDF...' : 'Download Logs (PDF)'}
    </button>
  );
}
