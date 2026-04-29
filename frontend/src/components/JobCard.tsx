import { useState, useEffect, useRef } from 'react'
import { ChevronRight } from 'lucide-react'
import { Card, Badge, Button, Spinner } from './ui'
import { getJob, getAuditLog, approveJob, abortJob, type Job } from '../lib/api'
import { statusBadge, formatDate } from '../lib/utils'

interface JobCardProps {
  job: Job
  onUpdated: () => void
}

export function JobCard({ job, onUpdated }: JobCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [auditLog, setAuditLog] = useState<any[]>([])
  const [loadingAudit, setLoadingAudit] = useState(false)
  const [acting, setActing] = useState(false)

  const isRunning = ['profiling', 'engineering', 'qa'].includes(job.status)

  async function loadAudit() {
    if (auditLog.length > 0) { setExpanded(v => !v); return }
    setLoadingAudit(true)
    try {
      const { data } = await getAuditLog(job.job_id)
      setAuditLog(data as any[])
    } catch { /* no-op */ } finally {
      setLoadingAudit(false)
      setExpanded(true)
    }
  }

  async function handleApprove() {
    setActing(true)
    await approveJob(job.job_id).catch(() => {})
    onUpdated(); setActing(false)
  }

  async function handleAbort() {
    setActing(true)
    await abortJob(job.job_id).catch(() => {})
    onUpdated(); setActing(false)
  }

  return (
    <Card className="p-5 animate-slide-up">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-semibold text-gray-900 dark:text-white truncate text-sm">
              {job.job_id}
            </span>
            <Badge label={job.status} className={statusBadge(job.status)} />
            {isRunning && <Spinner size={14} />}
          </div>
          <p className="mt-1 text-xs text-apple-gray1">
            Task: <span className="font-medium text-gray-700 dark:text-gray-300">{job.task_name}</span>
            &nbsp;·&nbsp;{formatDate(job.created_at)}
          </p>
          <p className="mt-1 text-xs text-apple-gray1 truncate">{job.progress_summary}</p>

          {/* Stats row */}
          {(job.rows_before != null) && (
            <div className="mt-3 flex items-center gap-4 text-xs text-apple-gray1">
              <span>Rows: <b className="text-gray-700 dark:text-gray-300">{job.rows_before?.toLocaleString()}</b> → <b className="text-gray-700 dark:text-gray-300">{job.rows_after?.toLocaleString()}</b></span>
              {job.flagged_record_count > 0 && (
                <span className="text-apple-orange">⚑ {job.flagged_record_count.toLocaleString()} flagged</span>
              )}
              <span>Retries: {job.retry_count}</span>
            </div>
          )}

          {job.error_messages?.length > 0 && (
            <p className="mt-2 text-xs text-apple-red truncate">✕ {job.error_messages[0]}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {job.status === 'human_review' && (
            <Button size="sm" variant="primary" onClick={handleApprove} loading={acting}>Approve</Button>
          )}
          {['pending', 'profiling', 'engineering', 'qa'].includes(job.status) && (
            <Button size="sm" variant="danger" onClick={handleAbort} loading={acting}>Abort</Button>
          )}
          <button
            onClick={loadAudit}
            className="p-1.5 rounded-lg text-apple-gray1 hover:text-apple-blue hover:bg-apple-blue/8 transition-colors"
          >
            {loadingAudit ? <Spinner size={16} /> : (
              <ChevronRight size={16} className={`transition-transform ${expanded ? 'rotate-90' : ''}`} />
            )}
          </button>
        </div>
      </div>

      {/* Audit log */}
      {expanded && auditLog.length > 0 && (
        <div className="mt-4 pt-4 border-t border-apple-gray5 dark:border-white/8 space-y-1.5 animate-fade-in">
          <p className="text-xs font-medium text-apple-gray1 mb-2 uppercase tracking-wide">Audit Log</p>
          {auditLog.map((entry: any, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="shrink-0 font-mono text-apple-gray2 w-32 truncate">{entry.node}</span>
              <Badge label={entry.status} className={
                entry.status === 'ok' || entry.status === 'complete' || entry.status === 'pass'
                  ? 'bg-green-50 text-green-700 ring-green-200'
                  : entry.status === 'error' || entry.status === 'fail'
                  ? 'bg-red-50 text-red-700 ring-red-200'
                  : 'bg-blue-50 text-blue-700 ring-blue-200'
              } />
              <span className="text-apple-gray1 truncate flex-1">{entry.detail}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

interface LiveJobProps {
  jobId: string
  onDone?: (job: Job) => void
}

export function LiveJobPoller({ jobId, onDone }: LiveJobProps) {
  const [job, setJob] = useState<Job | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    async function poll() {
      try {
        const { data } = await getJob(jobId)
        setJob(data)
        if (['complete', 'failed', 'aborted', 'human_review'].includes(data.status)) {
          clearInterval(timer.current!)
          onDone?.(data)
        }
      } catch { /* no-op */ }
    }
    poll()
    timer.current = setInterval(poll, 2500)
    return () => clearInterval(timer.current!)
  }, [jobId])

  if (!job) return <div className="flex items-center gap-2 text-sm text-apple-gray1"><Spinner size={16} /> Loading...</div>

  return <JobCard job={job} onUpdated={() => {}} />
}
