/** If true, will generate random metrics locally in JS */
const TEST = false;

const VERSION = '1.0.1';

/** Ordered by rank, will attempt to use first then second etc. */

const API = [
    "/heed_interface",
    "",
    "http://localhost:80",
    "http://127.0.0.1:80",
];

/** Maximum thresholds (%) for setting battery charge indicator CSS colour. Must be ordered. */
const CHARGE_COLORS = [
    [25, '#ff5a5a'],
    [50, '#f5ae2e'],
    [100, '#4ee64e']
];

/** Number of metrics to display in UI */
const NUM_METRICS = 4;

/** Default selected metrics.
    These are expected to be found in metrics returned by API, hence the lower-case w.
*/
const DEFAULT_METRICS = [
    'solar pv energy generation 24h (kwh)',
    'solar pv energy generation 30days (kwh)',
    'energy consumption 24h (kwh)',
    'energy consumption 30days (kwh)',
];

/** These are hidden from metric selection e.g. for booleans that cannot be displayed in LCD screens */
const HIDE_METRICS = new Set(['system state (charging)']);

/** Whether or not to append unit of measurement, as returned by API, to metric display. */
const APPEND_UNITS = true;

/** In milliseconds. Defines period of time with no response from API after which values in UI are reset. */
const CLEAR_VALUES_TIMEOUT = 5*60*1000;

/** In milliseconds. How often the API is queried for metric values and current priorities. */
const METRIC_POLL_RATE = 5000;

/** In milliseconds. How long page will wait for response from API before assuming it has timed out. */
const API_TIMEOUT = 10000;

const SIMPLE_PRIORITIES = true;
/** Simple shows Low/High, otherwise numeric priority */

/** Metric to use for battery SoC indicator */
const CHARGE_KEY = 'battery state of charge (percentage)';

/** Metric to use for battery charging/discharging indicator */
const CHARGING_KEY = 'system state (charging)';

