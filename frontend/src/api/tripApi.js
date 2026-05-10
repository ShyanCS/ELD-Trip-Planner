/**
 * tripApi.js — API client for the ELD Trip Planner backend.
 *
 * Communicates with POST /api/trip/plan/ to get HOS-compliant
 * daily logs, route geometry, and waypoints.
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s — routing + HOS calc can take time
});

/**
 * Plan a trip with full HOS compliance.
 *
 * @param {Object} tripData
 * @param {string} tripData.current_location  - Driver's current city/address
 * @param {string} tripData.pickup_location   - Load pickup city/address
 * @param {string} tripData.dropoff_location  - Load dropoff city/address
 * @param {number} tripData.current_cycle_used - Hours used in 70hr window (0-70)
 * @param {string} [tripData.start_date]      - Optional YYYY-MM-DD
 *
 * @returns {Promise<Object>} { route, daily_logs, stop_events }
 */
export async function planTrip(tripData) {
  const response = await api.post('/trip/plan/', tripData);
  return response.data;
}

export default api;
