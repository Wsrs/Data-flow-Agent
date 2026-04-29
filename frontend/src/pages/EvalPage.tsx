import { useState, useEffect } from 'react'
import { BarChart2, Play, FileText } from 'lucide-react'
import { Card, SectionHeader, Button, Select, EmptyState } from '../components/ui'
import { triggerEval, getEval, listTasks, type EvalResult, type TaskSummary } from '../lib/api'
import { RadialBarChart, RadialBar, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'

export default function EvalPage() {
  const [tasks, setTasks]     = useState<TaskSummary[]>([])
  const [selected, setSelected] = useState('all')
  const [running, setRunning] = useState(false)
  const [evalId, setEvalId]   = useState<string | null>(null)
  const [result, setResult]   = useState<EvalResult | null>(null)
  const [pollTimer, setPollTimer] = useState<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    listTasks().then(r => setTasks(r.data)).catch(() => {})
    return () => { if (pollTimer) clearInterval(pollTimer) }
  }, [])

  async function handleRun() {
    setRunning(true); setResult(null); setEvalId(null)
    try {
      const { data } = await triggerEval(selected)
      setEvalId(data.eval_id)
      const t = setInterval(async () => {
        const { data: r } = await getEval(data.eval_id)
        if (r.status !== 'running') {
          setResult(r); setRunning(false); clearInterval(t)
        }
      }, 2500)
      setPollTimer(t)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Evaluation failed'); setRunning(false)
    }
  }

  const taskOptions = [
    { value: 'all', label: 'All tasks' },
    ...tasks.map(t => ({ value: t.task, label: t.task })),
  ]

  const chartData = result?.results
    ? Object.entries(result.results)
        .filter(([, v]) => typeof v === 'object' && !('error' in v))
        .map(([task, metrics]) => ({
          task,
          score: (metrics as Record<string, number>).weighted_score ?? 0,
        }))
    : []

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Evaluation"
        subtitle="Run harness benchmark against registered tasks"
        action={
          <div className="flex items-center gap-3">
            <Select options={taskOptions} value={selected} onChange={e => setSelected(e.target.value)} />
            <Button onClick={handleRun} loading={running}>
              <Play size={14} />
              Run
            </Button>
          </div>
        }
      />

      {running && !result && (
        <Card className="p-8 flex flex-col items-center gap-3 text-center animate-fade-in">
          <div className="w-8 h-8 border-2 border-apple-blue border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-apple-gray1">Running evaluation {evalId ? `· ${evalId}` : ''}…</p>
        </Card>
      )}

      {result && (
        <div className="space-y-4 animate-slide-up">
          {/* Overall score */}
          <Card className="p-6 flex items-center gap-6">
            <div className="w-20 h-20 shrink-0">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart innerRadius="60%" outerRadius="100%" data={[{ value: (result.overall_weighted_score ?? 0) * 100, fill: '#007AFF' }]} startAngle={90} endAngle={-270}>
                  <RadialBar dataKey="value" background cornerRadius={6} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {((result.overall_weighted_score ?? 0) * 100).toFixed(1)}
                <span className="text-lg font-normal text-apple-gray1 ml-1">/ 100</span>
              </p>
              <p className="text-sm text-apple-gray1 mt-0.5">Overall Weighted Score</p>
              <p className="text-xs text-apple-gray2 mt-1">{result.generated_at?.replace('T', ' ').slice(0, 16)} UTC</p>
            </div>
          </Card>

          {/* Per-task bar chart */}
          {chartData.length > 0 && (
            <Card className="p-6">
              <p className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-4">Task Scores</p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData} barSize={28} margin={{ top: 4, right: 4, bottom: 4, left: -16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e5ea" />
                  <XAxis dataKey="task" tick={{ fontSize: 12, fill: '#8e8e93' }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12, fill: '#8e8e93' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
                  <Bar dataKey="score" fill="#007AFF" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Per-metric details */}
          {Object.entries(result.results ?? {}).map(([task, metrics]) => (
            <Card key={task} className="p-5">
              <p className="font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                <FileText size={14} className="text-apple-blue" />
                {task}
              </p>
              {'error' in (metrics as object) ? (
                <p className="text-sm text-apple-red">{(metrics as any).error}</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {Object.entries(metrics as Record<string, number>).map(([m, v]) => (
                    <div key={m} className="rounded-xl bg-apple-gray6/60 dark:bg-white/5 px-3 py-2">
                      <p className="text-xs text-apple-gray1 truncate">{m}</p>
                      <p className={`text-sm font-semibold mt-0.5 ${m === 'weighted_score' ? 'text-apple-blue' : 'text-gray-800 dark:text-gray-100'}`}>
                        {(v * 100).toFixed(2)}%
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {!running && !result && (
        <EmptyState
          icon={<BarChart2 size={40} strokeWidth={1.2} />}
          title="No evaluation results"
          subtitle="Select tasks and click Run to start a harness evaluation."
        />
      )}
    </div>
  )
}
