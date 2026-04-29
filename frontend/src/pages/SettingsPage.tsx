import { useState, useEffect } from 'react'
import { Cpu, CheckCircle, XCircle, RefreshCw, Save } from 'lucide-react'
import { Card, SectionHeader, Button, Input, Select } from '../components/ui'
import { getLLMStatus, type LLMStatus } from '../lib/api'

const STORAGE_KEY = 'dataflow_llm_config'

interface LLMConfig {
  provider: string
  model: string
  base_url: string
  api_key: string
}

const PROVIDER_DEFAULTS: Record<string, Omit<LLMConfig, 'api_key'>> = {
  openai: {
    provider: 'openai',
    model: 'gpt-4o',
    base_url: 'https://api.openai.com/v1',
  },
  ollama: {
    provider: 'ollama',
    model: 'qwen3-vl:8b',
    base_url: 'http://localhost:11434/v1',
  },
  dashscope: {
    provider: 'openai',
    model: 'qwen2.5-coder-32b-instruct',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  },
}

function loadConfig(): LLMConfig {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch { /* no-op */ }
  return { ...PROVIDER_DEFAULTS.ollama, api_key: 'ollama' }
}

export default function SettingsPage() {
  const [config, setConfig]     = useState<LLMConfig>(loadConfig)
  const [status, setStatus]     = useState<LLMStatus | null>(null)
  const [testing, setTesting]   = useState(false)
  const [saved, setSaved]       = useState(false)
  const [preset, setPreset]     = useState('ollama')

  useEffect(() => {
    getLLMStatus().then(r => setStatus(r.data)).catch(() => {})
  }, [])

  function applyPreset(key: string) {
    setPreset(key)
    const def = PROVIDER_DEFAULTS[key]
    setConfig(c => ({ ...c, ...def, api_key: key === 'ollama' ? 'ollama' : '' }))
  }

  function handleSave() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  async function handleTest() {
    setTesting(true)
    setStatus(null)
    await getLLMStatus().then(r => setStatus(r.data)).catch(() => {})
    setTesting(false)
  }

  const providerOptions = [
    { value: 'openai', label: 'OpenAI / compatible' },
    { value: 'ollama', label: 'Ollama (local)' },
  ]

  const presetOptions = [
    { value: 'openai',     label: 'OpenAI GPT-4o' },
    { value: 'ollama',     label: 'Ollama – qwen3-vl:8b' },
    { value: 'dashscope',  label: 'DashScope – Qwen2.5-Coder' },
  ]

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Settings"
        subtitle="LLM provider configuration — changes apply to new jobs"
      />

      {/* Live status card */}
      <Card className="p-5">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${
              status?.reachable ? 'bg-green-50 dark:bg-green-950/40' : 'bg-red-50 dark:bg-red-950/40'
            }`}>
              {status?.reachable
                ? <CheckCircle size={18} className="text-apple-green" />
                : <XCircle size={18} className="text-apple-red" />}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">
                {status ? `${status.provider} · ${status.model}` : 'Checking…'}
              </p>
              <p className="text-xs text-apple-gray1 mt-0.5">
                {status?.reachable
                  ? `Connected · ${status.base_url}`
                  : status ? 'Unreachable — check service' : 'Loading status…'}
              </p>
              {status?.available_models && status.available_models.length > 1 && (
                <p className="text-xs text-apple-gray2 mt-0.5">
                  Available: {status.available_models.join(', ')}
                </p>
              )}
            </div>
          </div>
          <Button size="sm" variant="secondary" onClick={handleTest} loading={testing}>
            <RefreshCw size={13} />
            Test connection
          </Button>
        </div>
      </Card>

      {/* Quick presets */}
      <Card className="p-5 space-y-4">
        <p className="text-sm font-semibold text-gray-900 dark:text-white">Quick Presets</p>
        <div className="flex flex-wrap gap-2">
          {presetOptions.map(p => (
            <button
              key={p.value}
              onClick={() => applyPreset(p.value)}
              className={`px-3.5 py-1.5 rounded-xl text-sm font-medium border transition-all ${
                preset === p.value
                  ? 'bg-apple-blue text-white border-apple-blue shadow-sm'
                  : 'bg-white dark:bg-white/5 border-apple-gray4 dark:border-white/10 text-gray-700 dark:text-gray-300 hover:border-apple-blue/50'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </Card>

      {/* Manual config */}
      <Card className="p-5 space-y-4">
        <p className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Cpu size={14} className="text-apple-blue" />
          Manual Configuration
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Select
            label="Provider"
            options={providerOptions}
            value={config.provider}
            onChange={e => setConfig(c => ({ ...c, provider: e.target.value }))}
          />
          <Input
            label="Model name"
            value={config.model}
            onChange={e => setConfig(c => ({ ...c, model: e.target.value }))}
            placeholder="gpt-4o / qwen3-vl:8b"
          />
          <Input
            label="Base URL"
            value={config.base_url}
            onChange={e => setConfig(c => ({ ...c, base_url: e.target.value }))}
            placeholder="https://api.openai.com/v1"
          />
          <Input
            label="API Key"
            type="password"
            value={config.api_key}
            onChange={e => setConfig(c => ({ ...c, api_key: e.target.value }))}
            placeholder="sk-… or 'ollama' for local"
          />
        </div>

        <div className="pt-1 flex items-center gap-3">
          <Button onClick={handleSave}>
            <Save size={13} />
            Save to browser
          </Button>
          {saved && (
            <span className="text-sm text-apple-green flex items-center gap-1 animate-fade-in">
              <CheckCircle size={13} /> Saved
            </span>
          )}
        </div>

        <p className="text-xs text-apple-gray1 leading-relaxed">
          These settings are stored locally in your browser. To persist them server-side, update the
          <code className="mx-1 px-1 py-0.5 rounded bg-apple-gray5 dark:bg-white/10 font-mono text-[11px]">.env</code>
          file and restart the API server.
        </p>
      </Card>

      {/* .env snippet */}
      <Card className="p-5">
        <p className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Server .env snippet</p>
        <pre className="p-4 rounded-xl bg-gray-950 text-gray-100 text-xs overflow-x-auto leading-relaxed">
{`LLM_PROVIDER=${config.provider}
LLM_MODEL=${config.model}
LLM_BASE_URL=${config.base_url}
LLM_API_KEY=${config.api_key || '<your-key>'}`}
        </pre>
      </Card>
    </div>
  )
}
