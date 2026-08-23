import { useRef, useEffect } from 'react';
import PropTypes from 'prop-types';
import './LogSheet.css';
import {
  CANVAS_W,
  CANVAS_H,
  COLORS,
  DPR,
  buildSegments,
  drawGrid,
  drawHeader,
  drawHourLabels,
  drawRemarks,
  drawRowLabels,
  drawStatusBars,
  drawTotalsBar,
  drawTotalsColumn,
  drawTransitionLines,
} from './logSheetDraw';

/**
 * FMCSA Daily Log Sheet — Canvas-rendered grid.
 *
 * Draws: 24-hour grid, 4 status rows, status bars with color coding,
 * vertical transition lines, hour labels, tick marks, header, totals, remarks.
 *
 * Props:
 *   log — a daily log object from the HOS calculator:
 *         { day, date, events, totals, miles_today, remarks }
 */
export default function LogSheet({ log }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!log) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');

    // Set canvas size for high-DPI
    canvas.width = CANVAS_W * DPR;
    canvas.height = CANVAS_H * DPR;
    canvas.style.width = `${CANVAS_W}px`;
    canvas.style.height = `${CANVAS_H}px`;
    ctx.scale(DPR, DPR);

    // Clear
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

    const segments = buildSegments(log.events);

    drawHeader(ctx, log);
    drawGrid(ctx);
    drawHourLabels(ctx);
    drawRowLabels(ctx);
    drawStatusBars(ctx, segments);
    drawTransitionLines(ctx, segments);
    drawTotalsColumn(ctx, log.totals);
    drawTotalsBar(ctx, log.totals);
    drawRemarks(ctx, log.remarks);
  }, [log]);

  if (!log) return null;

  return (
    <div className="log-sheet" id={`log-sheet-day-${log.day}`}>
      <canvas ref={canvasRef} className="log-sheet__canvas" />
    </div>
  );
}

LogSheet.propTypes = {
  log: PropTypes.object.isRequired,
};
