/**
 * KpiHeader — Mini KPI bar for the AI Training Interface
 * Shows: %HIGH / %MEDIUM / %LOW tier distribution + corrections today
 * Polls GET /api/v1/corrections/stats every 15 s
 */
import { useQuery } from '@tanstack/react-query'
import { Brain, TrendingUp, TrendingDown, Activity, Wrench } from 'lucide-react'
import { fetchCorrectionStats } from '@/services/correctionService'
import { runMaintenance } from '@/services/correctionService'
import { useState } from 'react'

interface TierPillProps {
  label: string
  count: number
  total: number
  color: string
  bgColor: string
  textColor: string
  borderColor: string
}

const TierPill = ({ label, count, total, bgColor, textColor, borderColor }: TierPillProps) => {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${bgColor} ${borderColor}`}>
      <span className={`text-xs font-bold ${textColor}`}>{label}</span>
      <span className={`text-sm font-bold ${textColor}`}>{pct}%</span>
      <span className="text-xs text-gray-400 font-mono">({count})</span>
    </div>
  )
}

export default function KpiHeader() {
  const [maintenanceRunning, setMaintenanceRunning] = useState(false)
  const [maintenanceDone, setMaintenanceDone] = useState(false)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['correctionStats'],
    queryFn: fetchCorrectionStats,
    refetchInterval: 15_000,
  })

  const dist = stats?.tier_distribution ?? { HIGH: 0, MEDIUM: 0, LOW: 0 }
  const total = (dist.HIGH ?? 0) + (dist.MEDIUM ?? 0) + (dist.LOW ?? 0)
  const todayCount = stats?.today_count ?? 0
  const totalCorrections = stats?.total ?? 0

  const handleMaintenance = async () => {
    setMaintenanceRunning(true)
    try {
      await runMaintenance(false)
      setMaintenanceDone(true)
      setTimeout(() => setMaintenanceDone(false), 4000)
    } finally {
      setMaintenanceRunning(false)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm px-5 py-3">
      <div className="flex flex-wrap items-center gap-4 justify-between">
        {/* Left: branding + tier pills */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Brain size={18} className="text-indigo-600" />
            <span className="text-sm font-semibold text-gray-700 dark:text-gray-200">
              Qualité IA
            </span>
          </div>

          {isLoading ? (
            <div className="flex gap-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse h-7 w-20 bg-gray-100 rounded-full" />
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <TierPill
                label="HIGH"
                count={dist.HIGH ?? 0}
                total={total}
                color=""
                bgColor="bg-green-50"
                textColor="text-green-700"
                borderColor="border-green-200"
              />
              <TierPill
                label="MEDIUM"
                count={dist.MEDIUM ?? 0}
                total={total}
                color=""
                bgColor="bg-yellow-50"
                textColor="text-yellow-700"
                borderColor="border-yellow-200"
              />
              <TierPill
                label="LOW"
                count={dist.LOW ?? 0}
                total={total}
                color=""
                bgColor="bg-red-50"
                textColor="text-red-700"
                borderColor="border-red-200"
              />
            </div>
          )}
        </div>

        {/* Right: stats + maintenance button */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-sm text-gray-500">
            <Activity size={14} className="text-indigo-400" />
            <span>
              <span className="font-semibold text-gray-700 dark:text-gray-200">{todayCount}</span>{' '}
              correction{todayCount !== 1 ? 's' : ''} aujourd'hui
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-sm text-gray-500">
            {totalCorrections > 0 ? (
              <TrendingUp size={14} className="text-green-500" />
            ) : (
              <TrendingDown size={14} className="text-gray-400" />
            )}
            <span>
              <span className="font-semibold text-gray-700 dark:text-gray-200">{totalCorrections}</span>{' '}
              total
            </span>
          </div>

          <button
            onClick={handleMaintenance}
            disabled={maintenanceRunning}
            title="Lancer la maintenance IA (decay, rebalance, compact)"
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition
              ${maintenanceDone
                ? 'bg-green-50 border-green-300 text-green-700'
                : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700'
              }
              ${maintenanceRunning ? 'opacity-60 cursor-wait' : ''}
            `}
          >
            <Wrench size={12} className={maintenanceRunning ? 'animate-spin' : ''} />
            {maintenanceDone ? 'Maintenance OK ✓' : maintenanceRunning ? 'En cours…' : 'Maintenance IA'}
          </button>
        </div>
      </div>
    </div>
  )
}
