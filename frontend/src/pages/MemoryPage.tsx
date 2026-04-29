import { useState, useEffect } from 'react'
import { Brain, Search, Star, Trash2, BookOpen, Zap } from 'lucide-react'
import { Card, SectionHeader, Button, Input, Badge, EmptyState, Spinner } from '../components/ui'
import { listMemories, searchMemory, listTemplates, deleteMemory, type MemoryEntry, type TemplateEntry } from '../lib/api'
import { formatDate } from '../lib/utils'

export default function MemoryPage() {
  const [tab, setTab]               = useState<'memories' | 'templates'>('memories')
  const [memories, setMemories]     = useState<MemoryEntry[]>([])
  const [templates, setTemplates]   = useState<TemplateEntry[]>([])
  const [query, setQuery]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [typeFilter, setTypeFilter] = useState<'all' | 'short' | 'long'>('all')

  async function loadMemories() {
    setLoading(true)
    try {
      const { data } = await (query.trim()
        ? searchMemory(query)
        : listMemories(typeFilter === 'all' ? undefined : typeFilter))
      setMemories(data)
    } catch { setMemories([]) }
    setLoading(false)
  }

  async function loadTemplates() {
    setLoading(true)
    try { const { data } = await listTemplates(); setTemplates(data) }
    catch { setTemplates([]) }
    setLoading(false)
  }

  useEffect(() => {
    if (tab === 'memories') loadMemories()
    else loadTemplates()
  }, [tab, typeFilter])

  async function handleDelete(id: string) {
    await deleteMemory(id).catch(() => {})
    setMemories(prev => prev.filter(m => m.id !== id))
  }

  const TypePill = ({ label, value }: { label: string; value: 'all' | 'short' | 'long' }) => (
    <button
      onClick={() => setTypeFilter(value)}
      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
        typeFilter === value
          ? 'bg-apple-blue text-white shadow-sm'
          : 'bg-apple-gray5 text-gray-600 dark:bg-white/10 dark:text-gray-300 hover:bg-apple-gray4'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Memory"
        subtitle="Long &amp; short-term memory with template matching"
      />

      {/* Tabs */}
      <div className="flex items-center gap-1 p-1 bg-apple-gray5/60 dark:bg-white/5 rounded-2xl w-fit">
        {(['memories', 'templates'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-xl text-sm font-medium capitalize transition-all ${
              tab === t ? 'bg-white dark:bg-white/10 shadow-sm text-gray-900 dark:text-white' : 'text-apple-gray1 hover:text-gray-700'
            }`}
          >
            {t === 'memories' ? <><Brain size={13} className="inline mr-1.5" />Memories</> : <><BookOpen size={13} className="inline mr-1.5" />Templates</>}
          </button>
        ))}
      </div>

      {tab === 'memories' && (
        <>
          {/* Search + filter */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex-1 min-w-48 relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-apple-gray2" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && loadMemories()}
                placeholder="Search memories…"
                className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-apple-gray4 bg-white/80 text-sm outline-none focus:border-apple-blue focus:ring-2 focus:ring-apple-blue/20 dark:bg-white/5 dark:border-white/10 dark:text-white"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <TypePill label="All" value="all" />
              <TypePill label="Short-term" value="short" />
              <TypePill label="Long-term" value="long" />
            </div>
            <Button size="sm" variant="secondary" onClick={loadMemories} loading={loading}>
              <Search size={13} /> Search
            </Button>
          </div>

          {loading ? (
            <div className="flex justify-center py-12"><Spinner size={28} /></div>
          ) : memories.length === 0 ? (
            <EmptyState icon={<Brain size={40} strokeWidth={1.2} />} title="No memories" subtitle="Past job patterns and insights will appear here." />
          ) : (
            <div className="space-y-2.5">
              {memories.map(m => (
                <Card key={m.id} className="p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge
                          label={m.type === 'long' ? 'Long-term' : 'Short-term'}
                          className={m.type === 'long' ? 'bg-purple-50 text-purple-700 ring-purple-200' : 'bg-blue-50 text-blue-700 ring-blue-200'}
                        />
                        <Badge label={m.category} className="bg-apple-gray5 text-gray-600 ring-apple-gray4" />
                        <span className="text-xs text-apple-gray1 font-medium">{m.task_name}</span>
                      </div>
                      <p className="mt-2 text-sm text-gray-700 dark:text-gray-200 line-clamp-2">{m.summary}</p>
                      <div className="mt-2 flex items-center gap-3 text-xs text-apple-gray1">
                        <span className="flex items-center gap-1"><Star size={10} />{m.score.toFixed(2)}</span>
                        <span>Used {m.use_count}×</span>
                        <span>{formatDate(m.last_used)}</span>
                        <div className="flex gap-1 flex-wrap">
                          {m.tags.map(tag => (
                            <span key={tag} className="px-1.5 py-0.5 rounded-full bg-apple-gray5 text-gray-500 text-[11px]">#{tag}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                    <button onClick={() => handleDelete(m.id)} className="shrink-0 p-1.5 rounded-lg text-apple-gray2 hover:text-apple-red hover:bg-red-50 transition-colors">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'templates' && (
        <>
          {loading ? (
            <div className="flex justify-center py-12"><Spinner size={28} /></div>
          ) : templates.length === 0 ? (
            <EmptyState icon={<BookOpen size={40} strokeWidth={1.2} />} title="No templates" subtitle="Reusable task configurations will appear here as you run jobs." />
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {templates.map(t => (
                <Card key={t.id} className="p-5" hover>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Zap size={14} className="text-apple-yellow shrink-0" />
                        <span className="font-semibold text-sm text-gray-900 dark:text-white truncate">{t.name}</span>
                      </div>
                      <p className="mt-1 text-xs text-apple-gray1 line-clamp-2">{t.description}</p>
                      <div className="mt-2.5 flex items-center gap-2 flex-wrap">
                        <Badge label={t.task_name} className="bg-apple-blue/10 text-apple-blue ring-apple-blue/20" />
                        {t.tags.map(tag => (
                          <span key={tag} className="text-[11px] text-apple-gray1">#{tag}</span>
                        ))}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs font-medium text-apple-green">★ {t.score.toFixed(1)}</p>
                      <p className="text-[11px] text-apple-gray2 mt-0.5">{t.use_count} uses</p>
                    </div>
                  </div>
                  <details className="mt-3">
                    <summary className="text-xs text-apple-blue cursor-pointer select-none">Config snippet</summary>
                    <pre className="mt-2 p-2.5 rounded-xl bg-apple-gray6/60 dark:bg-white/5 text-xs overflow-x-auto text-gray-700 dark:text-gray-300">
                      {JSON.stringify(t.config_snippet, null, 2)}
                    </pre>
                  </details>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
