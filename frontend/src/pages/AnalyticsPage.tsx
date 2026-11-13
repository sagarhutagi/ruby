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
  GraduationCap,
  Files,
  Coins,
  ShieldCheck,
  Download,
  Database,
  Layers,
  Clock,
  Award,
} from 'lucide-react';
import {
  fetchSystemResources,
  checkModelFit,
  ModelFitResult,
  fetchAnalyticsOverview,
  fetchDiagnosticReport,
  getDiagnosticExportUrl,
} from '../services/api';

const MODEL_PRESETS = [
  'llama3.2:3b',
  'qwen2.5:7b',
  'llama3:8b',
  'deepseek-r1:14b',
  'llama3.3:70b',
];

export const AnalyticsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'hardware' | 'study' | 'library' | 'tokens' | 'diagnostics'>('hardware');

  // Hardware Model Fit state
  const [testModel, setTestModel] = useState('llama3.2:3b');
  const [modelFit, setModelFit] = useState<ModelFitResult | null>(null);

  // Queries
  const { data: metrics, isLoading: loadingHardware } = useQuery({
    queryKey: ['system-resources'],
    queryFn: fetchSystemResources,
    refetchInterval: 4000,
  });

  const { data: analytics, isLoading: loadingAnalytics } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: fetchAnalyticsOverview,
  });

  const { data: diagnostics, isLoading: loadingDiagnostics } = useQuery({
    queryKey: ['diagnostic-report'],
    queryFn: fetchDiagnosticReport,
    enabled: activeTab === 'diagnostics',
  });

  const handleEvaluateFit = async (name: string) => {
    try {
      const res = await checkModelFit(name);
      setModelFit(res);
    } catch (e: any) {
      console.error(e);
    }
  };

  React.useEffect(() => {
    handleEvaluateFit(testModel);
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Analytics & System Diagnostics
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Measured study retention, document storage telemetry, AI token expenditure, and hardware diagnostics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {activeTab === 'hardware' && (
            <div className="flex items-center gap-2 text-xs font-mono bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-lg text-zinc-300">
              <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
              Live Hardware (4s)
            </div>
          )}
          {activeTab === 'diagnostics' && (
            <a
              href={getDiagnosticExportUrl()}
              download="ruby_sanitized_diagnostics.json"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg shadow transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              Export Sanitized Report
            </a>
          )}
        </div>
      </div>

      {/* Tabs Row */}
      <div className="flex items-center gap-2 border-b border-zinc-800 pb-3 overflow-x-auto scrollbar-thin">
        {[
          { id: 'hardware', label: 'Hardware Telemetry', icon: Gauge },
          { id: 'study', label: 'Study & Retention', icon: GraduationCap },
          { id: 'library', label: 'Library & Documents', icon: Files },
          { id: 'tokens', label: 'AI Tokens & Cost', icon: Coins },
          { id: 'diagnostics', label: 'System Diagnostics & Audit', icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-zinc-800 text-zinc-100 border border-zinc-700 shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/50'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-zinc-500'}`} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ==================== 1. HARDWARE TELEMETRY ==================== */}
      {activeTab === 'hardware' && (
        <div className="space-y-6">
          {loadingHardware || !metrics ? (
            <div className="p-12 text-center text-xs text-zinc-400">Sampling hardware telemetry...</div>
          ) : (
            <>
              {/* 4 Primary Hardware Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* CPU */}
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

                {/* RAM */}
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
                      {metrics.ram.percent}% utilized ({(metrics.ram.available_mb / 1024).toFixed(1)} GB free)
                    </div>
                  </div>
                  <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full transition-all duration-500"
                      style={{ width: `${Math.min(100, Math.max(0, metrics.ram.percent))}%` }}
                    />
                  </div>
                </div>

                {/* GPU */}
                <div className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 space-y-3">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs font-medium uppercase tracking-wider">Dedicated VRAM</span>
                    <Gauge className="w-4 h-4 text-rose-400" />
                  </div>
                  {metrics.gpu.available ? (
                    <>
                      <div>
                        <div className="text-2xl font-bold text-zinc-100 font-mono">
                          {metrics.gpu.vram_used_mb.toFixed(0)} / {metrics.gpu.vram_total_mb.toFixed(0)} MB
                        </div>
                        <div className="text-[11px] text-zinc-400 mt-0.5 flex items-center justify-between">
                          <span className="truncate max-w-[140px]">{metrics.gpu.name || 'NVIDIA GPU'}</span>
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
                    <div className="text-xs text-zinc-400 pt-1">
                      <div className="font-semibold text-zinc-300">GPU Not Detected</div>
                      <div className="text-[11px] text-zinc-400 mt-0.5">CPU-only inference mode.</div>
                    </div>
                  )}
                </div>

                {/* NVMe */}
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

              {/* Ollama Daemon & Model Fit Evaluator */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Ollama Status */}
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
                      <span className={`w-1.5 h-1.5 rounded-full ${metrics.ollama.running ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                      {metrics.ollama.running ? 'Daemon Active' : 'Offline'}
                    </span>
                  </div>

                  <div className="text-xs space-y-2 pt-1">
                    <div>
                      <span className="text-zinc-400 font-medium">Currently Cached in VRAM:</span>
                      {metrics.ollama.running_models.length > 0 ? (
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {metrics.ollama.running_models.map((m) => (
                            <span key={m} className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 rounded font-mono text-[11px]">
                              {m}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-zinc-500 mt-0.5 italic">No models actively cached in GPU VRAM.</p>
                      )}
                    </div>
                    <div>
                      <span className="text-zinc-400 font-medium">Installed Local Models:</span>
                      {metrics.ollama.installed_models.length > 0 ? (
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {metrics.ollama.installed_models.map((m) => (
                            <span key={m} className="px-2 py-0.5 bg-zinc-800 text-zinc-300 rounded font-mono text-[11px]">
                              {m}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-zinc-500 mt-0.5 italic">No local models installed yet.</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Model Capacity Evaluator */}
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-3">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    <h3 className="font-semibold text-sm text-zinc-100">Model VRAM Capacity Evaluator</h3>
                  </div>
                  <div className="flex gap-2">
                    <select
                      value={testModel}
                      onChange={(e) => {
                        setTestModel(e.target.value);
                        handleEvaluateFit(e.target.value);
                      }}
                      className="flex-1 px-3 py-1.5 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
                    >
                      {MODEL_PRESETS.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>

                  {modelFit && (
                    <div
                      className={`p-3.5 rounded-xl border space-y-1.5 text-xs ${
                        modelFit.fit_tier === 'optimal'
                          ? 'bg-emerald-950/20 border-emerald-900/40 text-emerald-300'
                          : modelFit.fit_tier === 'tight'
                          ? 'bg-amber-950/20 border-amber-900/40 text-amber-300'
                          : 'bg-rose-950/20 border-rose-900/40 text-rose-300'
                      }`}
                    >
                      <div className="flex items-center gap-2 font-semibold">
                        {modelFit.fit_tier === 'optimal' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : modelFit.fit_tier === 'tight' ? (
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400" />
                        )}
                        <span className="uppercase tracking-wider">{modelFit.fit_tier.replace('_', ' ')}</span>
                      </div>
                      <p className="text-[11px] leading-relaxed opacity-90">{modelFit.recommendation}</p>
                      <div className="text-[10px] text-zinc-400 pt-1">
                        Est. VRAM Needed: {modelFit.estimated_vram_needed_mb.toFixed(0)} MB | Available:{' '}
                        {modelFit.vram_available_mb.toFixed(0)} MB
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ==================== 2. STUDY & RETENTION ==================== */}
      {activeTab === 'study' && (
        <div className="space-y-6">
          {loadingAnalytics || !analytics ? (
            <div className="p-12 text-center text-xs text-zinc-500">Loading academic analytics...</div>
          ) : (
            <>
              {/* Study Metric Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs uppercase font-medium">Flashcards in Decks</span>
                    <Layers className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-zinc-100">
                    {analytics.study.flashcards.total_cards}
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    {analytics.study.flashcards.total_reviews} total reviews logged
                  </div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs uppercase font-medium">Memory Stability</span>
                    <Clock className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    {analytics.study.flashcards.average_stability_days} days
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    Avg Difficulty: {analytics.study.flashcards.average_difficulty} / 10
                  </div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs uppercase font-medium">Examination Accuracy</span>
                    <Award className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-amber-400">
                    {analytics.study.quizzes.average_score_percentage.toFixed(0)}%
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    {analytics.study.quizzes.total_quizzes_taken} exams completed
                  </div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <div className="flex items-center justify-between text-zinc-400">
                    <span className="text-xs uppercase font-medium">Knowledge Concepts</span>
                    <GraduationCap className="w-4 h-4 text-purple-400" />
                  </div>
                  <div className="text-2xl font-bold font-mono text-purple-400">
                    {analytics.study.knowledge_graph.total_concepts}
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    {analytics.study.knowledge_graph.verified_concepts} verified by user
                  </div>
                </div>
              </div>

              {/* Detailed Breakdown */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Flashcard Recall Distribution */}
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
                  <span className="text-xs font-semibold text-zinc-300">FSRS Review Recall Distribution</span>
                  <div className="space-y-2 pt-1">
                    {['Again', 'Hard', 'Good', 'Easy'].map((rating) => {
                      const count = analytics.study.flashcards.ratings_distribution[rating] || 0;
                      const total = analytics.study.flashcards.total_reviews || 1;
                      const pct = Math.round((count / total) * 100);

                      return (
                        <div key={rating} className="space-y-1">
                          <div className="flex justify-between text-xs text-zinc-300">
                            <span>{rating}</span>
                            <span className="font-mono text-zinc-400">
                              {count} ({pct}%)
                            </span>
                          </div>
                          <div className="w-full bg-zinc-800 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                rating === 'Good'
                                  ? 'bg-emerald-500'
                                  : rating === 'Easy'
                                  ? 'bg-blue-500'
                                  : rating === 'Hard'
                                  ? 'bg-amber-500'
                                  : 'bg-rose-500'
                              }`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Exam Breakdown */}
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
                  <span className="text-xs font-semibold text-zinc-300">Examination Performance</span>
                  <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800/80 space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Questions Answered:</span>
                      <span className="font-mono text-zinc-200">{analytics.study.quizzes.total_questions_answered}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Correct Answers:</span>
                      <span className="font-mono text-emerald-400">{analytics.study.quizzes.correct_answers}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-400">Historical Accuracy:</span>
                      <span className="font-mono font-bold text-zinc-100">
                        {analytics.study.quizzes.accuracy_percentage}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ==================== 3. LIBRARY & DOCUMENTS ==================== */}
      {activeTab === 'library' && (
        <div className="space-y-6">
          {loadingAnalytics || !analytics ? (
            <div className="p-12 text-center text-xs text-zinc-500">Loading library analytics...</div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <span className="text-xs uppercase text-zinc-400 font-medium">Indexed Documents</span>
                  <div className="text-2xl font-bold font-mono text-zinc-100">
                    {analytics.documents.total_documents}
                  </div>
                  <div className="text-[11px] text-zinc-500">Across all academic subjects</div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <span className="text-xs uppercase text-zinc-400 font-medium">Text Storage Size</span>
                  <div className="text-2xl font-bold font-mono text-indigo-400">
                    {analytics.documents.total_storage_mb} MB
                  </div>
                  <div className="text-[11px] text-zinc-500">
                    {analytics.documents.total_storage_bytes.toLocaleString()} bytes
                  </div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <span className="text-xs uppercase text-zinc-400 font-medium">Structure-Aware Chunks</span>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    {analytics.documents.total_chunks}
                  </div>
                  <div className="text-[11px] text-zinc-500">Preserving code fences & tables</div>
                </div>
              </div>

              {/* Formats and Subjects */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
                  <span className="text-xs font-semibold text-zinc-300">File Format Distribution</span>
                  <div className="space-y-1.5 pt-1">
                    {Object.entries(analytics.documents.by_file_type).map(([ext, count]) => (
                      <div key={ext} className="flex justify-between items-center text-xs p-2 rounded bg-zinc-950 border border-zinc-800/80">
                        <span className="font-mono text-zinc-300 uppercase">.{ext}</span>
                        <span className="font-semibold text-zinc-200">{count} file{count === 1 ? '' : 's'}</span>
                      </div>
                    ))}
                    {Object.keys(analytics.documents.by_file_type).length === 0 && (
                      <div className="text-xs text-zinc-500 italic">No documents imported yet.</div>
                    )}
                  </div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
                  <span className="text-xs font-semibold text-zinc-300">Subject Distribution</span>
                  <div className="space-y-1.5 pt-1">
                    {Object.entries(analytics.documents.by_subject).map(([subj, count]) => (
                      <div key={subj} className="flex justify-between items-center text-xs p-2 rounded bg-zinc-950 border border-zinc-800/80">
                        <span className="text-zinc-300">{subj}</span>
                        <span className="font-semibold text-zinc-200">{count} item{count === 1 ? '' : 's'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* ==================== 4. AI TOKENS & COST ==================== */}
      {activeTab === 'tokens' && (
        <div className="space-y-6">
          {loadingAnalytics || !analytics ? (
            <div className="p-12 text-center text-xs text-zinc-500">Loading token analytics...</div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <span className="text-xs uppercase text-zinc-400 font-medium">Total Messages</span>
                  <div className="text-2xl font-bold font-mono text-zinc-100">
                    {analytics.tokens.total_messages}
                  </div>
                  <div className="text-[11px] text-zinc-500">Across all chat sessions</div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <span className="text-xs uppercase text-zinc-400 font-medium">Tokens Tracked</span>
                  <div className="text-2xl font-bold font-mono text-indigo-400">
                    {analytics.tokens.total_tokens_consumed.toLocaleString()}
                  </div>
                  <div className="text-[11px] text-zinc-500">Local & Cloud LLMs</div>
                </div>

                <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-2">
                  <span className="text-xs uppercase text-zinc-400 font-medium">Estimated Cloud Cost</span>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    ${analytics.tokens.total_estimated_cost_usd.toFixed(4)}
                  </div>
                  <div className="text-[11px] text-emerald-400/80">Local Ollama inference is $0.00</div>
                </div>
              </div>

              {/* By Provider Table */}
              <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
                <span className="text-xs font-semibold text-zinc-300">Provider Usage & Pricing Breakdown</span>
                <table className="w-full text-left text-xs border border-zinc-800 rounded-lg overflow-hidden">
                  <thead className="bg-zinc-900 text-zinc-400 text-[10px] uppercase">
                    <tr>
                      <th className="p-2.5">Provider</th>
                      <th className="p-2.5">Messages</th>
                      <th className="p-2.5">Tokens</th>
                      <th className="p-2.5">Est. Cost (USD)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {Object.entries(analytics.tokens.by_provider).map(([pName, pData]) => (
                      <tr key={pName} className="text-zinc-200">
                        <td className="p-2.5 font-semibold text-indigo-400 uppercase">{pName}</td>
                        <td className="p-2.5">{pData.message_count}</td>
                        <td className="p-2.5 font-mono">{pData.tokens.toLocaleString()}</td>
                        <td className="p-2.5 font-mono text-emerald-400">
                          {pName.toLowerCase() === 'ollama' ? '$0.0000 (Free Local)' : `$${pData.estimated_cost_usd.toFixed(4)}`}
                        </td>
                      </tr>
                    ))}
                    {Object.keys(analytics.tokens.by_provider).length === 0 && (
                      <tr>
                        <td colSpan={4} className="p-4 text-center text-zinc-500 italic">
                          No conversation token metrics logged yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* ==================== 5. SYSTEM DIAGNOSTICS & AUDIT ==================== */}
      {activeTab === 'diagnostics' && (
        <div className="space-y-6">
          {loadingDiagnostics || !diagnostics ? (
            <div className="p-12 text-center text-xs text-zinc-500">Generating diagnostic health report...</div>
          ) : (
            <div className="space-y-5">
              {/* Compliance Badges */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-xs space-y-1">
                  <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4" />
                    Zero Cloud Leakage
                  </div>
                  <p className="text-[11px] text-zinc-400">Local-only default. Cloud requests require explicit opt-in.</p>
                </div>

                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-xs space-y-1">
                  <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4" />
                    Keyring Secret Protection
                  </div>
                  <p className="text-[11px] text-zinc-400">Keys encrypted or sealed; never stored or exported in plaintext.</p>
                </div>

                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-xs space-y-1">
                  <div className="font-semibold text-emerald-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4" />
                    AST Code Execution Sandbox
                  </div>
                  <p className="text-[11px] text-zinc-400">Python AST static check rejects filesystem and socket access.</p>
                </div>
              </div>

              {/* Database Tables Summary */}
              <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
                  <Database className="w-4 h-4 text-indigo-400" />
                  SQLite Relational Store Telemetry
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  {Object.entries(diagnostics.storage_diagnostics.database_tables).map(([table, count]) => (
                    <div key={table} className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                      <div className="text-[10px] text-zinc-500 uppercase">{table}</div>
                      <div className="font-mono font-bold text-zinc-200">{Number(count).toLocaleString()}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Environment Information */}
              <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-3 text-xs">
                <span className="font-semibold text-zinc-300">Environment & Host Specifications</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-zinc-300 font-mono text-[11px]">
                  <div>Python Version: <span className="text-zinc-100">{diagnostics.environment.python_version}</span></div>
                  <div>Platform: <span className="text-zinc-100">{diagnostics.environment.platform}</span></div>
                  <div>Localhost Enforced: <span className="text-emerald-400">True (127.0.0.1)</span></div>
                  <div>Data Directory: <span className="text-zinc-100">{diagnostics.environment.data_directory}</span></div>
                  <div>ChromaDB Storage: <span className="text-zinc-100">{diagnostics.storage_diagnostics.chromadb_size_mb} MB</span></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;
