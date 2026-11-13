import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  Plus,
  Shield,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Lock,
  Layers,
  Zap,
} from 'lucide-react';
import {
  fetchProviders,
  createProvider,
  deleteProvider,
  testProvider,
  fetchProviderModels,
  ProviderCreateModel,
  TestResult,
  DiscoveredModel,
} from '../services/api';

const PROVIDER_PRESETS: Record<string, { base_url: string; model_name: string; label: string }> = {
  ollama: { base_url: 'http://127.0.0.1:11434', model_name: 'llama3.2:latest', label: 'Ollama (Local)' },
  openai: { base_url: 'https://api.openai.com/v1', model_name: 'gpt-4o-mini', label: 'OpenAI Cloud' },
  gemini: { base_url: 'https://generativelanguage.googleapis.com/v1beta', model_name: 'gemini-1.5-flash', label: 'Google Gemini' },
  anthropic: { base_url: 'https://api.anthropic.com/v1', model_name: 'claude-3-5-sonnet-20241022', label: 'Anthropic Claude' },
  openrouter: { base_url: 'https://openrouter.ai/api/v1', model_name: 'meta-llama/llama-3.3-70b-instruct', label: 'OpenRouter' },
  generic: { base_url: 'http://127.0.0.1:1234/v1', model_name: 'local-model', label: 'Generic OpenAI Compatible' },
};

export const ProvidersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [discoveredModels, setDiscoveredModels] = useState<Record<string, DiscoveredModel[]>>({});
  const [loadingModelsId, setLoadingModelsId] = useState<string | null>(null);

  // Form State
  const [formType, setFormType] = useState('ollama');
  const [formName, setFormName] = useState(PROVIDER_PRESETS.ollama.label);
  const [formBaseUrl, setFormBaseUrl] = useState(PROVIDER_PRESETS.ollama.base_url);
  const [formModel, setFormModel] = useState(PROVIDER_PRESETS.ollama.model_name);
  const [formApiKey, setFormApiKey] = useState('');
  const [formIsDefault, setFormIsDefault] = useState(false);
  const [formTemperature, setFormTemperature] = useState(0.7);
  const [formError, setFormError] = useState<string | null>(null);

  const { data: providers, isLoading } = useQuery({
    queryKey: ['providers'],
    queryFn: fetchProviders,
  });

  const createMutation = useMutation({
    mutationFn: (data: ProviderCreateModel) => createProvider(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      setShowAddModal(false);
      resetForm();
    },
    onError: (err: Error) => {
      setFormError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProvider(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });

  const resetForm = () => {
    setFormType('ollama');
    setFormName(PROVIDER_PRESETS.ollama.label);
    setFormBaseUrl(PROVIDER_PRESETS.ollama.base_url);
    setFormModel(PROVIDER_PRESETS.ollama.model_name);
    setFormApiKey('');
    setFormIsDefault(false);
    setFormTemperature(0.7);
    setFormError(null);
  };

  const handleTypeChange = (type: string) => {
    setFormType(type);
    const preset = PROVIDER_PRESETS[type];
    if (preset) {
      setFormName(preset.label);
      setFormBaseUrl(preset.base_url);
      setFormModel(preset.model_name);
    }
  };

  const handleTest = async (id: string) => {
    setTestingId(id);
    try {
      const res = await testProvider(id);
      setTestResults((prev) => ({ ...prev, [id]: res }));
    } catch (e: any) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: false, latency_ms: 0, message: e.message },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleDiscoverModels = async (id: string) => {
    setLoadingModelsId(id);
    try {
      const models = await fetchProviderModels(id);
      setDiscoveredModels((prev) => ({ ...prev, [id]: models }));
    } catch (e: any) {
      alert(`Model discovery error: ${e.message}`);
    } finally {
      setLoadingModelsId(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    createMutation.mutate({
      name: formName,
      provider_type: formType,
      base_url: formBaseUrl,
      model_name: formModel,
      api_key: formApiKey ? formApiKey : undefined,
      is_enabled: true,
      is_default: formIsDefault,
      timeout_seconds: 60,
      temperature: formTemperature,
    });
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" />
            AI Providers & Inference Manager
          </h2>
          <p className="text-xs text-zinc-400">
            Configure local Ollama, cloud endpoints (OpenAI, Gemini, Claude, OpenRouter), and enforce secret sealing.
          </p>
        </div>
        <button
          onClick={() => {
            resetForm();
            setShowAddModal(true);
          }}
          className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Add Provider
        </button>
      </div>

      {/* Security Banner */}
      <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 flex items-start gap-3">
        <Shield className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <span className="font-semibold text-zinc-200">Zero Cloud Leakage & Hardware-Aware Policy</span>
          <p className="text-zinc-400 leading-relaxed">
            Local Ollama inference is default. Requests never leave this workstation unless you explicitly select a cloud provider. API keys are sealed in the OS keyring or encrypted storage; plaintext secrets are never returned in API payloads or saved in database records.
          </p>
        </div>
      </div>

      {/* Providers Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-zinc-400">Loading AI providers...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers?.map((provider) => {
            const testResult = testResults[provider.id];
            const isTesting = testingId === provider.id;
            const models = discoveredModels[provider.id];
            const isLoadingModels = loadingModelsId === provider.id;

            return (
              <div
                key={provider.id}
                className="p-5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 hover:border-zinc-700/80 transition-all flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`w-2.5 h-2.5 rounded-full ${
                          provider.is_enabled ? 'bg-emerald-500' : 'bg-zinc-600'
                        }`}
                      />
                      <h3 className="font-semibold text-sm text-zinc-100">{provider.name}</h3>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {provider.is_default && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          Default
                        </span>
                      )}
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700/60">
                        {provider.provider_type}
                      </span>
                    </div>
                  </div>

                  <div className="mt-3 space-y-1 text-xs">
                    <div className="text-zinc-400 flex items-center justify-between">
                      <span>Base URL:</span>
                      <span className="font-mono text-zinc-300">{provider.base_url || 'Default'}</span>
                    </div>
                    <div className="text-zinc-400 flex items-center justify-between">
                      <span>Active Model:</span>
                      <span className="font-mono text-indigo-300">{provider.model_name}</span>
                    </div>
                    {provider.has_api_key && (
                      <div className="text-zinc-400 flex items-center justify-between">
                        <span className="flex items-center gap-1">
                          <Lock className="w-3 h-3 text-emerald-400" />
                          Key Preview:
                        </span>
                        <span className="font-mono text-emerald-400">{provider.masked_key}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Test Result Message */}
                {testResult && (
                  <div
                    className={`p-2.5 rounded-lg text-xs flex items-center justify-between border ${
                      testResult.success
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {testResult.success ? (
                        <CheckCircle2 className="w-4 h-4 shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 shrink-0" />
                      )}
                      <span className="truncate max-w-[280px]">{testResult.message}</span>
                    </div>
                    {testResult.success && (
                      <span className="font-mono text-[11px] font-semibold">
                        {testResult.latency_ms}ms
                      </span>
                    )}
                  </div>
                )}

                {/* Discovered Models Dropdown / Summary */}
                {models && models.length > 0 && (
                  <div className="p-3 bg-zinc-950/60 border border-zinc-800 rounded-lg text-xs space-y-1">
                    <div className="flex items-center justify-between font-semibold text-zinc-300">
                      <span>Available Models ({models.length}):</span>
                    </div>
                    <div className="max-h-24 overflow-y-auto space-y-1 pr-1 font-mono text-[11px] text-zinc-400">
                      {models.slice(0, 10).map((m) => (
                        <div key={m.id} className="flex justify-between items-center py-0.5">
                          <span>{m.name}</span>
                          <span className="text-[10px] text-zinc-400">{m.is_local ? 'Local' : 'Cloud'}</span>
                        </div>
                      ))}
                      {models.length > 10 && <div className="text-[10px] text-zinc-400">...and {models.length - 10} more</div>}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex items-center justify-between pt-3 border-t border-zinc-800/60 text-xs">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleTest(provider.id)}
                      disabled={isTesting}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-[11px] font-medium transition-colors"
                    >
                      <Zap className={`w-3.5 h-3.5 ${isTesting ? 'animate-pulse text-amber-400' : 'text-amber-400'}`} />
                      {isTesting ? 'Testing...' : 'Test'}
                    </button>

                    <button
                      onClick={() => handleDiscoverModels(provider.id)}
                      disabled={isLoadingModels}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-[11px] font-medium transition-colors"
                    >
                      <Layers className={`w-3.5 h-3.5 ${isLoadingModels ? 'animate-spin' : ''}`} />
                      {isLoadingModels ? 'Fetching...' : 'Models'}
                    </button>
                  </div>

                  {!provider.is_default && (
                    <button
                      onClick={() => {
                        if (confirm(`Delete provider '${provider.name}'?`)) {
                          deleteMutation.mutate(provider.id);
                        }
                      }}
                      className="p-1.5 text-zinc-400 hover:text-rose-400 transition-colors"
                      title="Delete Provider"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add Provider Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <h3 className="font-semibold text-zinc-100 text-sm flex items-center gap-2">
                <Plus className="w-4 h-4 text-indigo-400" />
                Add AI Model Provider
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-zinc-400 hover:text-zinc-200 text-sm"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              {/* Provider Preset Selector */}
              <div>
                <label className="block text-zinc-400 mb-1.5 font-medium">Provider Platform</label>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(PROVIDER_PRESETS).map(([key, preset]) => (
                    <button
                      type="button"
                      key={key}
                      onClick={() => handleTypeChange(key)}
                      className={`p-2 rounded-lg border text-left transition-all ${
                        formType === key
                          ? 'border-indigo-500 bg-indigo-500/10 text-indigo-300 font-medium'
                          : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700'
                      }`}
                    >
                      <div className="capitalize font-semibold text-[11px]">{key}</div>
                      <div className="text-[10px] text-zinc-400 truncate">{preset.model_name}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Name */}
              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Display Name</label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Base URL */}
              <div>
                <label className="block text-zinc-400 mb-1 font-medium">API Base URL</label>
                <input
                  type="text"
                  value={formBaseUrl}
                  onChange={(e) => setFormBaseUrl(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Default Model */}
              <div>
                <label className="block text-zinc-400 mb-1 font-medium">Model Identifier</label>
                <input
                  type="text"
                  required
                  value={formModel}
                  onChange={(e) => setFormModel(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* API Key */}
              {formType !== 'ollama' && (
                <div>
                  <label className="block text-zinc-400 mb-1 font-medium flex items-center justify-between">
                    <span>API Key</span>
                    <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-normal">
                      <Lock className="w-3 h-3" /> Sealed in OS Keyring
                    </span>
                  </label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={formApiKey}
                    onChange={(e) => setFormApiKey(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {/* Is Default Checkbox */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formIsDefault}
                  onChange={(e) => setFormIsDefault(e.target.checked)}
                  className="rounded border-zinc-700 bg-zinc-950 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="is_default" className="text-zinc-300 select-none">
                  Set as primary default provider for new conversations
                </label>
              </div>

              {/* Modal Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-sm transition-colors"
                >
                  {createMutation.isPending ? 'Saving...' : 'Save Provider'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
