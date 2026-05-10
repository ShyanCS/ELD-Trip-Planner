/**
 * Mock API response — matches the exact structure returned by /api/trip/plan/
 * Used for visual testing of TripSummary + LogSheet + MapView without a live API.
 */
const MOCK_TRIP_RESULT = {
  route: {
    total_distance_miles: 1745.3,
    total_duration_hours: 31.7,
    geometry: {
      type: 'LineString',
      coordinates: [
        // Chicago → Kansas City → Tulsa → Amarillo → Flagstaff → LA (simplified)
        [-87.6298, 41.8781],  // Chicago
        [-88.3, 41.5],
        [-89.6, 40.7],
        [-90.2, 39.8],
        [-91.4, 39.1],
        [-92.5, 38.6],
        [-93.5, 38.2],
        [-94.5, 39.0],
        [-94.5781, 39.0997],  // Kansas City
        [-95.3, 38.4],
        [-95.9, 37.5],
        [-96.0, 36.7],
        [-95.9928, 36.1540],  // Tulsa
        [-97.0, 36.0],
        [-98.0, 35.8],
        [-99.5, 35.4],
        [-100.7, 35.2],
        [-101.8312, 35.2220], // Amarillo
        [-103.0, 35.2],
        [-104.5, 35.1],
        [-106.0, 35.0],
        [-107.5, 35.0],
        [-109.0, 35.1],
        [-110.5, 35.1],
        [-111.6513, 35.1983], // Flagstaff
        [-112.5, 35.0],
        [-113.5, 34.8],
        [-114.5, 34.7],
        [-115.5, 34.8],
        [-116.5, 34.9],
        [-117.0, 34.9],
        [-117.0382, 34.9005], // Barstow
        [-117.5, 34.3],
        [-118.0, 34.1],
        [-118.2437, 34.0522], // Los Angeles
      ],
    },
    waypoints: [
      { type: 'start',   name: 'Chicago, IL',        lat: 41.8781, lon: -87.6298, miles_from_start: 0 },
      { type: 'pickup',  name: 'Kansas City, MO',     lat: 39.0997, lon: -94.5781, miles_from_start: 500 },
      { type: 'rest',    name: 'Tulsa, OK',           lat: 36.1540, lon: -95.9928, miles_from_start: 550 },
      { type: 'fuel',    name: 'Amarillo, TX',        lat: 35.2220, lon: -101.8312, miles_from_start: 1000 },
      { type: 'rest',    name: 'Flagstaff, AZ',       lat: 35.1983, lon: -111.6513, miles_from_start: 1155 },
      { type: 'dropoff', name: 'Los Angeles, CA',     lat: 34.0522, lon: -118.2437, miles_from_start: 1745 },
    ],
  },
  daily_logs: [
    {
      day: 1,
      date: '2026-05-07',
      miles_today: 550,
      totals: {
        off_duty: 10.77,
        sleeper_berth: 0,
        driving: 10.0,
        on_duty_not_driving: 3.23,
      },
      events: [
        { time: '08:00', status: 'on_duty_not_driving', hours: 0.5,  location: 'Chicago, IL', miles: 0 },
        { time: '08:30', status: 'driving',             hours: 5.45, location: 'Chicago, IL', miles: 300 },
        { time: '13:57', status: 'on_duty_not_driving', hours: 0.5,  location: 'Kansas City, MO', miles: 0 },
        { time: '14:27', status: 'on_duty_not_driving', hours: 1.0,  location: 'Kansas City, MO', miles: 0 },
        { time: '15:27', status: 'driving',             hours: 4.55, location: 'Kansas City, MO', miles: 250 },
        { time: '20:00', status: 'on_duty_not_driving', hours: 0.73, location: 'Tulsa, OK', miles: 0 },
        { time: '20:44', status: 'on_duty_not_driving', hours: 0.5,  location: 'Tulsa, OK', miles: 0 },
      ],
      remarks: [
        '08:00 Chicago, IL - Pre-trip inspection',
        '08:30 Chicago, IL - Driving to Kansas City',
        '13:57 Kansas City, MO - 30-min mandatory break',
        '14:27 Kansas City, MO - Pickup (loading)',
        '15:27 Kansas City, MO - Driving to Tulsa',
        '20:00 Tulsa, OK - Dropoff (unloading)',
        '20:44 Tulsa, OK - Post-trip inspection',
      ],
    },
    {
      day: 2,
      date: '2026-05-08',
      miles_today: 605,
      totals: {
        off_duty: 13.0,
        sleeper_berth: 0,
        driving: 9.5,
        on_duty_not_driving: 1.5,
      },
      events: [
        { time: '08:00', status: 'on_duty_not_driving', hours: 0.5,  location: 'Tulsa, OK', miles: 0 },
        { time: '08:30', status: 'driving',             hours: 5.0,  location: 'Tulsa, OK', miles: 275 },
        { time: '13:30', status: 'on_duty_not_driving', hours: 0.5,  location: 'Amarillo, TX', miles: 0 },
        { time: '14:00', status: 'driving',             hours: 4.5,  location: 'Amarillo, TX', miles: 330 },
        { time: '18:30', status: 'on_duty_not_driving', hours: 0.5,  location: 'Flagstaff, AZ', miles: 0 },
      ],
      remarks: [
        '08:00 Tulsa, OK - Pre-trip inspection',
        '08:30 Tulsa, OK - Driving to Amarillo',
        '13:30 Amarillo, TX - 30-min mandatory break',
        '14:00 Amarillo, TX - Driving to Flagstaff',
        '18:30 Flagstaff, AZ - Post-trip inspection',
      ],
    },
    {
      day: 3,
      date: '2026-05-09',
      miles_today: 590,
      totals: {
        off_duty: 12.27,
        sleeper_berth: 0,
        driving: 10.23,
        on_duty_not_driving: 1.5,
      },
      events: [
        { time: '08:00', status: 'on_duty_not_driving', hours: 0.5,  location: 'Flagstaff, AZ', miles: 0 },
        { time: '08:30', status: 'driving',             hours: 5.0,  location: 'Flagstaff, AZ', miles: 275 },
        { time: '13:30', status: 'on_duty_not_driving', hours: 0.5,  location: 'Barstow, CA', miles: 0 },
        { time: '14:00', status: 'driving',             hours: 5.23, location: 'Barstow, CA', miles: 315 },
        { time: '19:14', status: 'on_duty_not_driving', hours: 0.5,  location: 'Los Angeles, CA', miles: 0 },
      ],
      remarks: [
        '08:00 Flagstaff, AZ - Pre-trip inspection',
        '08:30 Flagstaff, AZ - Driving to Barstow',
        '13:30 Barstow, CA - 30-min mandatory break',
        '14:00 Barstow, CA - Driving to Los Angeles',
        '19:14 Los Angeles, CA - Post-trip inspection',
      ],
    },
  ],
  stop_events: [
    { type: 'fuel', location_name: 'Amarillo, TX', total_miles_at_stop: 1000 },
    { type: 'rest', location_name: 'Tulsa, OK', total_miles_at_stop: 550 },
    { type: 'rest', location_name: 'Flagstaff, AZ', total_miles_at_stop: 1155 },
  ],
};

export default MOCK_TRIP_RESULT;
