import { useRef, useEffect } from 'react';
import './LogSheet.css';

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

// ─── Layout Constants ───────────────────────────────────────────────────────

const CANVAS_W = 1100;
const CANVAS_H = 520;
const DPR = typeof window !== 'undefined' ? (window.devicePixelRatio || 1) : 1;

// Margins
const LEFT_MARGIN = 90;       // Row labels
const RIGHT_MARGIN = 90;      // Totals column
const TOP_MARGIN = 70;        // Header area
const HOUR_LABEL_H = 28;      // Hour label row height
const ROW_H = 52;             // Each status row height
const GRID_TOP = TOP_MARGIN + HOUR_LABEL_H;
const GRID_W = CANVAS_W - LEFT_MARGIN - RIGHT_MARGIN;
const GRID_H = ROW_H * 4;
const REMARKS_TOP = GRID_TOP + GRID_H + 16;

// Status row indices (top to bottom)
const STATUS_ROWS = ['off_duty', 'sleeper_berth', 'driving', 'on_duty_not_driving'];
const STATUS_LABELS = ['Off Duty', 'Sleeper', 'Driving', 'On Duty'];
const STATUS_SHORT = ['OFF', 'SB', 'D', 'ON'];

// Colors
const COLORS = {
  bg:           '#1c110b',
  gridLine:     '#3d2c22',
  gridLineMajor:'#4a362a',
  hourLabel:    '#8a7060',
  rowLabel:     '#c4a48e',
  text:         '#f5e6dc',
  textMuted:    '#8a7060',
  textSecondary:'#c4a48e',
  accent:       '#ffb690',
  driving:      '#F97316',
  on_duty_not_driving: '#EAB308',
  sleeper_berth:'#8B5CF6',
  off_duty:     '#6B7280',
  statusBar:    {
    driving:             'rgba(249, 115, 22, 0.85)',
    on_duty_not_driving: 'rgba(234, 179, 8, 0.85)',
    sleeper_berth:       'rgba(139, 92, 246, 0.85)',
    off_duty:            'rgba(107, 114, 128, 0.50)',
  },
  transition:   '#ffb690',
};

// Hour labels: M 1 2 3 ... 11 N 1 2 3 ... 11
const HOUR_LABELS = [
  'M','1','2','3','4','5','6','7','8','9','10','11',
  'N','1','2','3','4','5','6','7','8','9','10','11',
];


// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Parse "HH:MM" time string to decimal hours.
 * e.g. "08:30" → 8.5, "13:45" → 13.75
 */
function parseTime(timeStr) {
  if (!timeStr || typeof timeStr !== 'string') return 0;
  const [h, m] = timeStr.split(':').map(Number);
  return h + (m || 0) / 60;
}

/**
 * Build a normalized segments array from events.
 * Each segment: { startHour, endHour, status, rowIndex }
 * Includes implicit off-duty for gaps.
 */
function buildSegments(events) {
  if (!events || events.length === 0) {
    return [{ startHour: 0, endHour: 24, status: 'off_duty', rowIndex: 0 }];
  }

  const segments = [];
  let cursor = 0; // tracks where we are in the day

  // Off-duty before first event
  const firstStart = parseTime(events[0].time);
  if (firstStart > 0.01) {
    segments.push({
      startHour: 0,
      endHour: firstStart,
      status: 'off_duty',
      rowIndex: 0,
    });
    cursor = firstStart;
  }

  // Process each event
  events.forEach((event) => {
    const startHour = parseTime(event.time);
    const endHour = Math.min(startHour + event.hours, 24);
    const rowIndex = STATUS_ROWS.indexOf(event.status);
    if (rowIndex === -1) return;

    // Gap between cursor and this event's start → implicit off-duty
    if (startHour > cursor + 0.01) {
      segments.push({
        startHour: cursor,
        endHour: startHour,
        status: 'off_duty',
        rowIndex: 0,
      });
    }

    segments.push({ startHour, endHour, status: event.status, rowIndex });
    cursor = endHour;
  });

  // Off-duty after last event
  if (cursor < 23.99) {
    segments.push({
      startHour: cursor,
      endHour: 24,
      status: 'off_duty',
      rowIndex: 0,
    });
  }

  return segments;
}


// ─── Component ──────────────────────────────────────────────────────────────

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


// ─── Drawing Functions ──────────────────────────────────────────────────────

function drawHeader(ctx, data) {
  const y = 20;

  // Day number
  ctx.font = `700 18px Inter, sans-serif`;
  ctx.fillStyle = COLORS.accent;
  ctx.textAlign = 'left';
  ctx.fillText(`Day ${data.day}`, LEFT_MARGIN, y + 4);

  // Date
  ctx.font = `500 14px 'JetBrains Mono', monospace`;
  ctx.fillStyle = COLORS.text;
  ctx.fillText(data.date, LEFT_MARGIN + 70, y + 4);

  // Miles
  ctx.textAlign = 'right';
  ctx.font = `600 14px Inter, sans-serif`;
  ctx.fillStyle = COLORS.textSecondary;
  ctx.fillText(`${data.miles_today} miles`, CANVAS_W - RIGHT_MARGIN, y + 4);

  // Divider line under header
  ctx.strokeStyle = COLORS.gridLineMajor;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(LEFT_MARGIN, TOP_MARGIN - 14);
  ctx.lineTo(CANVAS_W - RIGHT_MARGIN, TOP_MARGIN - 14);
  ctx.stroke();

  // Grid title labels
  ctx.textAlign = 'center';
  ctx.font = `500 10px Inter, sans-serif`;
  ctx.fillStyle = COLORS.textMuted;
  ctx.fillText('GRAPH GRID', LEFT_MARGIN + GRID_W / 2, TOP_MARGIN - 4);

  ctx.textAlign = 'center';
  ctx.fillText('TOTAL', CANVAS_W - RIGHT_MARGIN / 2, TOP_MARGIN - 4);
}


function drawGrid(ctx) {
  ctx.strokeStyle = COLORS.gridLine;
  ctx.lineWidth = 0.5;

  // Horizontal row dividers
  for (let i = 0; i <= 4; i++) {
    const y = GRID_TOP + i * ROW_H;
    ctx.beginPath();
    ctx.moveTo(LEFT_MARGIN, y);
    ctx.lineTo(CANVAS_W - RIGHT_MARGIN, y);
    ctx.stroke();

    // Extend to totals column
    ctx.beginPath();
    ctx.moveTo(CANVAS_W - RIGHT_MARGIN, y);
    ctx.lineTo(CANVAS_W, y);
    ctx.stroke();
  }

  // Vertical hour lines + tick marks
  for (let h = 0; h <= 24; h++) {
    const x = LEFT_MARGIN + (h / 24) * GRID_W;

    // Major hour line
    ctx.strokeStyle = h === 0 || h === 12 || h === 24 ? COLORS.gridLineMajor : COLORS.gridLine;
    ctx.lineWidth = h === 0 || h === 12 || h === 24 ? 1 : 0.5;
    ctx.beginPath();
    ctx.moveTo(x, GRID_TOP);
    ctx.lineTo(x, GRID_TOP + GRID_H);
    ctx.stroke();

    // 15-minute tick marks (except at hour boundaries)
    if (h < 24) {
      ctx.strokeStyle = COLORS.gridLine;
      ctx.lineWidth = 0.3;
      for (let q = 1; q <= 3; q++) {
        const tx = x + (q / 4) * (GRID_W / 24);
        const tickLen = q === 2 ? 8 : 5; // Half-hour tick is longer

        for (let row = 0; row < 4; row++) {
          const ry = GRID_TOP + row * ROW_H;
          ctx.beginPath();
          ctx.moveTo(tx, ry);
          ctx.lineTo(tx, ry + tickLen);
          ctx.stroke();

          // Bottom ticks
          ctx.beginPath();
          ctx.moveTo(tx, ry + ROW_H);
          ctx.lineTo(tx, ry + ROW_H - tickLen);
          ctx.stroke();
        }
      }
    }
  }

  // Left border
  ctx.strokeStyle = COLORS.gridLineMajor;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(LEFT_MARGIN, GRID_TOP);
  ctx.lineTo(LEFT_MARGIN, GRID_TOP + GRID_H);
  ctx.stroke();

  // Right border (grid)
  ctx.beginPath();
  ctx.moveTo(CANVAS_W - RIGHT_MARGIN, GRID_TOP);
  ctx.lineTo(CANVAS_W - RIGHT_MARGIN, GRID_TOP + GRID_H);
  ctx.stroke();
}


function drawHourLabels(ctx) {
  ctx.font = `500 11px 'JetBrains Mono', monospace`;
  ctx.fillStyle = COLORS.hourLabel;
  ctx.textAlign = 'center';

  for (let h = 0; h < 24; h++) {
    const x = LEFT_MARGIN + (h / 24) * GRID_W + (GRID_W / 48);
    ctx.fillText(HOUR_LABELS[h], x, TOP_MARGIN + HOUR_LABEL_H - 6);
  }
}


function drawRowLabels(ctx) {
  ctx.textAlign = 'right';

  for (let i = 0; i < 4; i++) {
    const y = GRID_TOP + i * ROW_H + ROW_H / 2;

    // Short label
    ctx.font = `700 13px Inter, sans-serif`;
    ctx.fillStyle = COLORS[STATUS_ROWS[i]] || COLORS.rowLabel;
    ctx.fillText(STATUS_SHORT[i], LEFT_MARGIN - 12, y - 6);

    // Full label
    ctx.font = `400 9px Inter, sans-serif`;
    ctx.fillStyle = COLORS.textMuted;
    ctx.fillText(STATUS_LABELS[i], LEFT_MARGIN - 12, y + 8);
  }
}


function drawStatusBars(ctx, segments) {
  const barH = 4;

  segments.forEach((seg) => {
    const x1 = LEFT_MARGIN + (seg.startHour / 24) * GRID_W;
    const x2 = LEFT_MARGIN + (seg.endHour / 24) * GRID_W;
    const y = GRID_TOP + seg.rowIndex * ROW_H;
    const barY = y + ROW_H / 2 - barH / 2;

    ctx.fillStyle = COLORS.statusBar[seg.status] || COLORS.statusBar.off_duty;
    ctx.fillRect(x1, barY, x2 - x1, barH);
  });
}


function drawTransitionLines(ctx, segments) {
  ctx.strokeStyle = COLORS.transition;
  ctx.lineWidth = 1.5;
  ctx.setLineDash([]);

  for (let i = 1; i < segments.length; i++) {
    const prev = segments[i - 1];
    const curr = segments[i];

    if (prev.rowIndex !== curr.rowIndex) {
      const x = LEFT_MARGIN + (curr.startHour / 24) * GRID_W;
      const fromY = GRID_TOP + prev.rowIndex * ROW_H + ROW_H / 2;
      const toY = GRID_TOP + curr.rowIndex * ROW_H + ROW_H / 2;

      ctx.beginPath();
      ctx.moveTo(x, fromY);
      ctx.lineTo(x, toY);
      ctx.stroke();
    }
  }
}


function drawTotalsColumn(ctx, totals) {
  const colX = CANVAS_W - RIGHT_MARGIN + 8;

  for (let i = 0; i < 4; i++) {
    const y = GRID_TOP + i * ROW_H + ROW_H / 2;
    const status = STATUS_ROWS[i];
    const value = totals[status] || 0;

    ctx.font = `600 14px 'JetBrains Mono', monospace`;
    ctx.fillStyle = value > 0 ? COLORS.text : COLORS.textMuted;
    ctx.textAlign = 'left';
    ctx.fillText(value.toFixed(1), colX + 4, y + 5);
  }
}


function drawTotalsBar(ctx, totals) {
  // Stacked horizontal bar showing time distribution
  const barX = LEFT_MARGIN;
  const barY = GRID_TOP + GRID_H + 4;
  const barH = 6;
  const totalHours = 24;

  let offset = 0;
  STATUS_ROWS.forEach((status) => {
    const hours = totals[status] || 0;
    const width = (hours / totalHours) * GRID_W;

    ctx.fillStyle = COLORS.statusBar[status];
    ctx.fillRect(barX + offset, barY, width, barH);
    offset += width;
  });

  // Total label
  ctx.font = `500 10px Inter, sans-serif`;
  ctx.fillStyle = COLORS.textMuted;
  ctx.textAlign = 'right';
  const totalSum = Object.values(totals).reduce((a, b) => a + b, 0);
  ctx.fillText(`${totalSum.toFixed(1)}h`, CANVAS_W - RIGHT_MARGIN + RIGHT_MARGIN / 2 + 20, barY + barH);
}


function drawRemarks(ctx, remarks) {
  if (!remarks || remarks.length === 0) return;

  const x = LEFT_MARGIN;
  let y = REMARKS_TOP + 8;

  // Section title
  ctx.font = `600 10px Inter, sans-serif`;
  ctx.fillStyle = COLORS.textMuted;
  ctx.textAlign = 'left';
  ctx.fillText('REMARKS', x, y);
  y += 16;

  // Remarks text
  ctx.font = `400 11px Inter, sans-serif`;
  ctx.fillStyle = COLORS.textSecondary;

  const maxRemarks = Math.min(remarks.length, 5); // Limit to 5 to fit
  for (let i = 0; i < maxRemarks; i++) {
    let text = remarks[i];
    if (text.length > 90) text = text.substring(0, 87) + '…';

    ctx.fillText(text, x + 4, y);
    y += 16;
  }

  if (remarks.length > 5) {
    ctx.fillStyle = COLORS.textMuted;
    ctx.fillText(`+ ${remarks.length - 5} more…`, x + 4, y);
  }
}
