import { useState, useEffect, useCallback } from 'react'
import { Plus, Inbox, RefreshCw } from 'lucide-react'
import { Card, SectionHeader, Button, Input, Select, EmptyState, Spinner } from '../components/ui'
import { JobCard } from '../components/JobCard'
import { createJob, listTasks, type Job, type TaskSummary } from '../lib/api'

// Simple in-memory job list (persisted in state)
type JobMeta = Pick<Job, 'job_id' | 'task_name' | 'status' | 'created_at' | 'progress_summary' | 'retry_count' |
  'circuit_breaker_triggered' | 'flagged_record_count' | 'rows_before' | 'rows_after' | 'error_messages' | 'result_path'>

export default function JobsPage() {
  const [tasks, setTasks]         = useState<TaskSummary[]>([])
  const [jobs, setJobs]           = useState<JobMeta[]>([])
  const [showForm, setShowForm]   = useState(false)
  const [loading, setLoading]     = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const [form, setForm] = useState({
    task_name: '',
    data_path: '',
    output_path: '',
  })

  useEffect(() => {
    listTasks().then(r => {
      setTasks(r.data)
      if (r.data.length > 0) setForm(f => ({ ...f, task_name: r.data[0].task }))
    }).catch(() => {})
  }, [])

  // Poll all running jobs
  const refreshJobs = useCallback(async () => {
    setLoading(true)
    const runningIds = jobs.filter(j => ['profiling', 'engineering', 'qa', 'pending'].includes(j.status)).map(j => j.job_id)
    if (runningIds.length === 0) { setLoading(false); return }
    const { getJob } = await import('../lib/api')
    const updated = await Promise.all(runningIds.map(id => getJob(id).then(r => r.data).catch(() => null)))
    setJobs(prev => prev.map(j => {
      const u = updated.find(x => x?.job_id === j.job_id)
      return u ? { ...j, ...u } : j
    }))
    setLoading(false)
  }, [jobs])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    try {
      const { data } = await createJob(form)
      const now = new Date().toISOString()
      setJobs(prev => [{
        job_id: data.job_id,
        task_name: form.task_name,
        status: 'pending',
        created_at: now,
        progress_summary: 'Job queued',
        retry_count: 0,
        circuit_breaker_triggered: false,
        flagged_record_count: 0,
        rows_before: undefined,
        rows_after: undefined,
        error_messages: [],
        result_path: undefined,
      }, ...prev])
      setShowForm(false)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to create job')
    } finally {
      setSubmitting(false)
    }
  }

  const taskOptions = tasks.map(t => ({ value: t.task, label: `${t.task} · ${t.cleaning_strategy_type}` }))

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Jobs"
        subtitle="Submit and monitor cleaning pipeline runs"
        action={
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={refreshJobs} loading={loading}>
              <RefreshCw size={14} />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setShowForm(v => !v)}>
              <Plus size={14} />
              New Job
            </Button>
          </div>
        }
      />

      {/* New Job Form */}
      {showForm && (
        <Card className="p-6 animate-slide-up">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Create Cleaning Job</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Select
              label="Task"
              options={taskOptions}
              value={form.task_name}
              onChange={e => setForm(f => ({ ...f, task_name: e.target.value }))}
            />
            <Input
              label="Input data path"
              placeholder="/data/sample_dirty.parquet"
              value={form.data_path}
              onChange={e => setForm(f => ({ ...f, data_path: e.target.value }))}
              required
            />
            <Input
              label="Output path"
              placeholder="/data/sample_clean.parquet"
              value={form.output_path}
              onChange={e => setForm(f => ({ ...f, output_path: e.target.value }))}
              required
            />
            <div className="flex gap-2 pt-1">
              <Button type="submit" loading={submitting}>Submit</Button>
              <Button type="button" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </form>
        </Card>
      )}

      {/* Job list */}
      {jobs.length === 0 ? (
        <EmptyState
          icon={<Inbox size={40} strokeWidth={1.2} />}
          title="No jobs yet"
          subtitle="Create a new job to start cleaning your data."
        />
      ) : (
        <div className="space-y-3">
          {jobs.map(job => (
            <JobCard
              key={job.job_id}
              job={job as Job}
              onUpdated={refreshJobs}
            />
          ))}
        </div>
      )}
    </div>
  )
}
