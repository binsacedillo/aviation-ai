'use client';

interface MetarData {
  station: string;
  time: string;
  raw: string;
  wind_direction: number | null;
  wind_speed: number | null;
  wind_gust: number | null;
  temperature_c: number | null;
  dewpoint_c: number | null;
  flight_category: string;
  source: string;
}

interface LandingAnalysis {
  runway_number: string;
  runway_heading: number;
  crosswind_kt: number;
  headwind_kt: number;
}

interface MetarDisplayProps {
  metar: MetarData;
  landing?: LandingAnalysis | null;
}

export default function MetarDisplay({ metar, landing }: MetarDisplayProps) {
  const categoryColors: Record<string, string> = {
    VFR: 'bg-green-100 text-green-800 border-green-300',
    MVFR: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    IFR: 'bg-orange-100 text-orange-800 border-orange-300',
    LIFR: 'bg-red-100 text-red-800 border-red-300',
  };

  const categoryEmoji: Record<string, string> = {
    VFR: '✅',
    MVFR: '⚠️',
    IFR: '🔴',
    LIFR: '🚫',
  };

  return (
    <div className="space-y-4">
      {/* Station Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{metar.station}</h2>
          <p className="text-sm text-gray-600">Report: {metar.time}</p>
        </div>
        <div
          className={`px-4 py-2 rounded-lg border-2 font-semibold ${
            categoryColors[metar.flight_category] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {categoryEmoji[metar.flight_category]} {metar.flight_category}
        </div>
      </div>

      {/* Raw METAR */}
      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
        <p className="text-xs text-gray-500 mb-1">RAW METAR</p>
        <p className="font-mono text-sm text-gray-900 break-all">{metar.raw}</p>
      </div>

      {/* Weather Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Wind Card */}
        {metar.wind_direction !== null && metar.wind_speed !== null && (
          <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">💨</span>
              <h3 className="font-semibold text-gray-900">Wind</h3>
            </div>
            <div className="space-y-1">
              <p className="text-lg font-bold text-gray-900">
                {metar.wind_direction.toString().padStart(3, '0')}° at {metar.wind_speed} knots
              </p>
              {metar.wind_gust && metar.wind_gust > metar.wind_speed && (
                <p className="text-sm text-gray-600">
                  Gusting to {metar.wind_gust} knots
                </p>
              )}
            </div>
          </div>
        )}

        {/* Temperature Card */}
        {metar.temperature_c !== null && (
          <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🌡️</span>
              <h3 className="font-semibold text-gray-900">Temperature</h3>
            </div>
            <div className="space-y-1">
              <p className="text-lg font-bold text-gray-900">{metar.temperature_c}°C</p>
              {metar.dewpoint_c !== null && (
                <p className="text-sm text-gray-600">Dewpoint: {metar.dewpoint_c}°C</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Landing Analysis */}
      {landing && (
        <div className="bg-blue-50 p-4 rounded-lg border-2 border-blue-200">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl">🛫</span>
            <h3 className="font-semibold text-gray-900">Landing Analysis</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-xs text-gray-600 mb-1">Runway in Use</p>
              <p className="text-xl font-bold text-blue-900">
                {landing.runway_number} ({landing.runway_heading}°)
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-600 mb-1">Crosswind</p>
              <p className="text-xl font-bold text-orange-900">
                {landing.crosswind_kt} knots
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-600 mb-1">Headwind</p>
              <p className="text-xl font-bold text-green-900">
                {landing.headwind_kt} knots
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Source Badge */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className={metar.source === 'live' ? 'text-green-600' : 'text-orange-600'}>
          {metar.source === 'live' ? '🟢 Live Data' : '🟠 Fallback Data'}
        </span>
      </div>
    </div>
  );
}
