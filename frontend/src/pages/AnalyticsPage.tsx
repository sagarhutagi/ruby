import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  Activity,
  HardDrive,
  Cpu,
  Server,
  Zap,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Gauge,
  Thermometer,
} from 'lucide-react';
import { fetchSystemResources, checkModelFit, ModelFitResult } from '../services/api';

const MODEL_PRESETS = [
  'llama3.2:3b',
  'qwen2.5:7b',
  'llama3:8b',
  'deepseek-r1:14b',
  'llama3.3:70b',
];

export const AnalyticsPage: React.FC = () => {
  const [testModel, setTestModel] = useState('llama3.2:3b');
  const [modelFit, setModelFit] = useState<ModelFitResult | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  const { data: metrics, isLoading } = useQuery({
    queryKey: ['system-resources'],
    queryFn: fetchSystemResources,
    refetchInterval: 4000, // Poll hardware metrics every 4s
  });

  const handleEvaluateFit = async (name: string) => {
    setEvaluating(true);
    try {
      const res = await checkModelFit(name);
      setModelFit(res);
    } catch (e: any) {
      console.error(e);
    } finally {
      setEvaluating(false);
    }
  };

  // Run initial model check once
  React.useEffect(() => {
    handleEvaluateFit(testModel);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Hardware Telemetry & Inference Diagnostics
          </h2>
          <p className="text-xs text-zinc-400">
            Real hardware metrics (NVML/nvidia-smi, psutil) and VRAM capacity warnings.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg text-zinc-300">
          <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          Live Sampling (4s)
        </div>
      </div>

      {isLoading || !metrics ? (
        <div className="p-12 text-center text-xs text-zinc-400">Sampling hardware telemetry...</div>
      ) : (
        <>
          {/* Main 4 Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* CPU Card */}
            <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-3">
              <div className="flex items-center justify-between text-zinc-400">
                <span className="text-xs font-medium uppercase tracking-wider">Host CPU</span>
                <Cpu className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-zinc-100 font-mono">
                  {metrics.cpu.percent.toFixed(1)}%
                </div>
                <div className="text-[11px] text-zinc-400 mt-0.5">
                  {metrics.cpu.core_count} Logical Cores {metrics.cpu.frequency_mhz ? `@ ${metrics.cpu.frequency_mhz} MHz` : ''}
                </div>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-indigo-500 h-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, metrics.cpu.percent))}%` }}
                />
              </div>
            </div>

            {/* RAM Card */}
            <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-3">
              <div className="flex items-center justify-between text-zinc-400">
                <span className="text-xs font-medium uppercase tracking-wider">System RAM</span>
                <Activity className="w-4 h-4 text-emerald-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-zinc-100 font-mono">
                  {(metrics.ram.used_mb / 1024).toFixed(1)} / {(metrics.ram.total_mb / 1024).toFixed(1)} GB
                </div>
                <div className="text-[11px] text-zinc-400 mt-0.5">
                  {metrics.ram.percent}% utilized ({(metrics.ram.available_mb / 1024).toFixed(1)} GB available)
                </div>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, metrics.ram.percent))}%` }}
                />
              </div>
            </div>

            {/* GPU & VRAM Card */}
            <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-3">
              <div className="flex items-center justify-between text-zinc-400">
                <span className="text-xs font-medium uppercase tracking-wider">GPU Dedicated VRAM</span>
                <Gauge className="w-4 h-4 text-rose-400" />
              </div>
              {metrics.gpu.available ? (
                <>
                  <div>
                    <div className="text-2xl font-bold text-zinc-100 font-mono">
                      {metrics.gpu.vram_used_mb.toFixed(0)} / {metrics.gpu.vram_total_mb.toFixed(0)} MB
                    </div>
                    <div className="text-[11px] text-zinc-400 mt-0.5 flex items-center justify-between">
                      <span className="truncate max-w-[150px]">{metrics.gpu.name || 'NVIDIA GPU'}</span>
                      {metrics.gpu.temperature_c !== undefined && (
                        <span className="flex items-center gap-0.5 text-zinc-400 font-mono">
                          <Thermometer className="w-3 h-3 text-rose-400" />
                          {metrics.gpu.temperature_c}°C
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-rose-500 h-full transition-all duration-500"
                      style={{
                        width: `${Math.min(
                          100,
                          Math.max(
                            0,
                            (metrics.gpu.vram_used_mb / Math.max(1, metrics.gpu.vram_total_mb)) * 100
                          )
                        )}%`,
                      }}
                    />
                  </div>
                </>
              ) : (
                <div className="text-xs text-zinc-400 pt-2">
                  <div className="font-semibold text-zinc-300">GPU Not Detected</div>
                  <div className="text-[11px] text-zinc-400 mt-1">
                    {metrics.gpu.error || 'Running in CPU-only inference mode.'}
                  </div>
                </div>
              )}
            </div>

            {/* NVMe Storage Card */}
            <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-3">
              <div className="flex items-center justify-between text-zinc-400">
                <span className="text-xs font-medium uppercase tracking-wider">NVMe Storage</span>
                <HardDrive className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <div className="text-2xl font-bold text-zinc-100 font-mono">
                  {metrics.disk.used_gb.toFixed(0)} / {metrics.disk.total_gb.toFixed(0)} GB
                </div>
                <div className="text-[11px] text-zinc-400 mt-0.5 font-mono">
                  {metrics.disk.free_gb.toFixed(0)} GB free ({metrics.disk.percent}%)
                </div>
              </div>
              <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-amber-500 h-full transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(0, metrics.disk.percent))}%` }}
                />
              </div>
            </div>
          </div>

          {/* Ollama Local Status Card */}
          <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-400" />
                <h3 className="font-semibold text-sm text-zinc-100">Ollama Local Inference Daemon</h3>
              </div>
              <span
                className={`text-[11px] font-mono px-2.5 py-0.5 rounded-full flex items-center gap-1.5 ${
                  metrics.ollama.running
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    metrics.ollama.running ? 'bg-emerald-400' : 'bg-rose-400'
                  }`}
                />
                {metrics.ollama.running ? 'Daemon Active' : 'Offline'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs pt-1">
              <div>
                <span className="text-zinc-400 font-medium">Currently Loaded in VRAM:</span>
                {metrics.ollama.running_models.length > 0 ? (
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {metrics.ollama.running_models.map((m) => (
                      <span
                        key={m}
                        className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 rounded font-mono text-[11px]"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-400 mt-1 italic">No models actively cached in GPU VRAM.</p>
                )}
              </div>

              <div>
                <span className="text-zinc-400 font-medium">Installed Local Models:</span>
                {metrics.ollama.installed_models.length > 0 ? (
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {metrics.ollama.installed_models.map((m) => (
                      <span
                        key={m}
                        className="px-2 py-0.5 bg-zinc-800 text-zinc-300 rounded font-mono text-[11px]"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-zinc-400 mt-1 italic">
                    No models downloaded yet. Use 'ollama pull &lt;model&gt;' or Providers page.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Hardware-Aware Model Advisor */}
          <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-4">
            <div>
              <h3 className="font-semibold text-sm text-zinc-100 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-400" />
                Hardware-Aware Model VRAM Advisor
              </h3>
              <p className="text-xs text-zinc-400 mt-0.5">
                Calculate real memory fit on your 6GB RTX 3050 Laptop GPU before pulling or loading models.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-2">
              <input
                type="text"
                value={testModel}
                onChange={(e) => setTestModel(e.target.value)}
                placeholder="Enter model identifier (e.g., llama3.2:3b, qwen2.5:7b)"
                className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={() => handleEvaluateFit(testModel)}
                disabled={evaluating}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                {evaluating ? 'Analyzing...' : 'Analyze Fit'}
              </button>
            </div>

            {/* Quick Preset Buttons */}
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="text-zinc-400 text-[11px] self-center">Try presets:</span>
              {MODEL_PRESETS.map((preset) => (
                <button
                  key={preset}
                  onClick={() => {
                    setTestModel(preset);
                    handleEvaluateFit(preset);
                  }}
                  className={`px-2 py-1 rounded text-[11px] font-mono border transition-colors ${
                    testModel === preset
                      ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-300'
                      : 'bg-zinc-800/60 border-zinc-700/60 text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {preset}
                </button>
              ))}
            </div>

            {/* Evaluation Result Banner */}
            {modelFit && (
              <div
                className={`p-4 rounded-xl border space-y-2 text-xs ${
                  modelFit.fit_tier === 'optimal'
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-200'
                    : modelFit.fit_tier === 'tight'
                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-200'
                    : 'bg-rose-500/10 border-rose-500/20 text-rose-200'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-semibold">
                    {modelFit.fit_tier === 'optimal' && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                    {modelFit.fit_tier === 'tight' && <AlertTriangle className="w-4 h-4 text-amber-400" />}
                    {modelFit.fit_tier === 'exceeds_vram' && <XCircle className="w-4 h-4 text-rose-400" />}
                    <span className="uppercase tracking-wider font-mono text-[11px]">
                      {modelFit.fit_tier === 'optimal' && 'Optimal Fit for 6GB VRAM'}
                      {modelFit.fit_tier === 'tight' && 'Tight Fit — Moderate Context Recommended'}
                      {modelFit.fit_tier === 'exceeds_vram' && 'Exceeds VRAM Capacity'}
                    </span>
                  </div>
                  <span className="font-mono text-[11px]">
                    Est. {modelFit.estimated_vram_needed_mb.toFixed(0)} MB / {modelFit.vram_available_mb.toFixed(0)} MB
                  </span>
                </div>

                <p className="leading-relaxed text-zinc-300">{modelFit.recommendation}</p>

                {modelFit.warning && (
                  <div className="pt-1 text-[11px] font-semibold text-amber-300">
                    Caution: {modelFit.warning}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
