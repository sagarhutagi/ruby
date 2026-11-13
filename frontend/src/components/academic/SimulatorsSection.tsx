import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Cpu,
  Calculator,
  Terminal,
  Network,
  Binary,
  Layers,
  ShieldAlert,
  Play,
  ChevronRight,
  ChevronLeft,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import {
  solveMathEquation,
  differentiateMath,
  integrateMath,
  simplifyMath,
  computeMatrix,
  runSandboxCode,
  traceAlgorithm,
  simulateCPUScheduler,
  simulateBankers,
  simulatePageReplacement,
  calculateSubnet,
  generateTruthTable,
  DSATraceResult,
  CPUScheduleResult,
  BankerResult,
  PageReplacementResult,
  SubnetResult,
  TruthTableResult,
  CodeRunResult,
} from '../../services/api';
import { MarkdownRenderer } from '../MarkdownRenderer';

export const SimulatorsSection: React.FC = () => {
  const [subTab, setSubTab] = useState<
    'math' | 'sandbox' | 'dsa' | 'cpu' | 'banker' | 'page' | 'subnet' | 'dlcd'
  >('math');

  // ==================== 1. MATH & SYMPY STATE ====================
  const [mathOp, setMathOp] = useState<'solve' | 'diff' | 'integrate' | 'simplify' | 'matrix'>('solve');
  const [mathInput, setMathInput] = useState('x**2 - 5*x + 6 = 0');
  const [mathVar, setMathVar] = useState('x');
  const [mathOrder, setMathOrder] = useState(1);
  const [mathLower, setMathLower] = useState('');
  const [mathUpper, setMathUpper] = useState('');
  const [matrixOp, setMatrixOp] = useState<'determinant' | 'inverse' | 'eigenvalues' | 'rref'>('determinant');
  const [matrixData, setMatrixData] = useState<number[][]>([
    [1, 2],
    [3, 4],
  ]);
  const [mathResult, setMathResult] = useState<any>(null);

  const mathMutation = useMutation({
    mutationFn: async () => {
      if (mathOp === 'solve') return solveMathEquation(mathInput, mathVar);
      if (mathOp === 'diff') return differentiateMath(mathInput, mathVar, mathOrder);
      if (mathOp === 'integrate') return integrateMath(mathInput, mathVar, mathLower, mathUpper);
      if (mathOp === 'simplify') return simplifyMath(mathInput);
      if (mathOp === 'matrix') return computeMatrix(matrixData, matrixOp);
    },
    onSuccess: (data) => setMathResult(data),
    onError: (err: any) => setMathResult({ error: err.message }),
  });

  // ==================== 2. SANDBOX STATE ====================
  const [codeSnippet, setCodeSnippet] = useState(
    '# Safe execution sandbox\ndef fibonacci(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n\nprint("Fibonacci(10) =", fibonacci(10))\n'
  );
  const [codeResult, setCodeResult] = useState<CodeRunResult | null>(null);

  const runCodeMutation = useMutation({
    mutationFn: () => runSandboxCode(codeSnippet, 2.5),
    onSuccess: (data) => setCodeResult(data),
  });

  // ==================== 3. DSA TRACER STATE ====================
  const [dsaAlgo, setDsaAlgo] = useState<'binary_search' | 'bubble_sort'>('binary_search');
  const [dsaArrayStr, setDsaArrayStr] = useState('2, 5, 8, 12, 16, 23, 38, 56, 72, 91');
  const [dsaTarget, setDsaTarget] = useState<number>(23);
  const [dsaResult, setDsaResult] = useState<DSATraceResult | null>(null);
  const [dsaStepIndex, setDsaStepIndex] = useState(0);

  const dsaMutation = useMutation({
    mutationFn: () => {
      const arr = dsaArrayStr.split(',').map((s) => parseInt(s.trim())).filter((n) => !isNaN(n));
      return traceAlgorithm(dsaAlgo, arr, dsaAlgo === 'binary_search' ? dsaTarget : undefined);
    },
    onSuccess: (data) => {
      setDsaResult(data);
      setDsaStepIndex(0);
    },
  });

  // ==================== 4. CPU SCHEDULER STATE ====================
  const [cpuAlgo, setCpuAlgo] = useState<'fcfs' | 'round_robin'>('round_robin');
  const [cpuQuantum, setCpuQuantum] = useState(2);
  const [cpuProcesses, setCpuProcesses] = useState([
    { pid: 'P1', arrival: 0, burst: 5 },
    { pid: 'P2', arrival: 1, burst: 3 },
    { pid: 'P3', arrival: 2, burst: 8 },
    { pid: 'P4', arrival: 3, burst: 6 },
  ]);
  const [cpuResult, setCpuResult] = useState<CPUScheduleResult | null>(null);

  const cpuMutation = useMutation({
    mutationFn: () => simulateCPUScheduler(cpuAlgo, cpuProcesses, cpuQuantum),
    onSuccess: (data) => setCpuResult(data),
  });

  // ==================== 5. BANKER'S STATE ====================
  const [bankerAvailable, setBankerAvailable] = useState('3, 3, 2');
  const [bankerAlloc, setBankerAlloc] = useState('0,1,0\n2,0,0\n3,0,2\n2,1,1\n0,0,2');
  const [bankerMax, setBankerMax] = useState('7,5,3\n3,2,2\n9,0,2\n2,2,2\n4,3,3');
  const [bankerResult, setBankerResult] = useState<BankerResult | null>(null);

  const bankerMutation = useMutation({
    mutationFn: () => {
      const avail = bankerAvailable.split(',').map((x) => parseInt(x.trim())).filter((x) => !isNaN(x));
      const parseMat = (str: string) =>
        str
          .trim()
          .split('\n')
          .map((row) => row.split(',').map((x) => parseInt(x.trim())).filter((x) => !isNaN(x)));
      return simulateBankers(avail, parseMat(bankerAlloc), parseMat(bankerMax));
    },
    onSuccess: (data) => setBankerResult(data),
  });

  // ==================== 6. PAGE REPLACEMENT STATE ====================
  const [pageAlgo, setPageAlgo] = useState<'fifo' | 'lru'>('fifo');
  const [numFrames, setNumFrames] = useState(3);
  const [pageString, setPageString] = useState('7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2');
  const [pageResult, setPageResult] = useState<PageReplacementResult | null>(null);

  const pageMutation = useMutation({
    mutationFn: () => {
      const pages = pageString.split(',').map((x) => parseInt(x.trim())).filter((x) => !isNaN(x));
      return simulatePageReplacement(pageAlgo, pages, numFrames);
    },
    onSuccess: (data) => setPageResult(data),
  });

  // ==================== 7. SUBNET CALCULATOR STATE ====================
  const [subnetIP, setSubnetIP] = useState('192.168.1.145');
  const [subnetPrefix, setSubnetPrefix] = useState(26);
  const [subnetResult, setSubnetResult] = useState<SubnetResult | null>(null);

  const subnetMutation = useMutation({
    mutationFn: () => calculateSubnet(subnetIP, subnetPrefix),
    onSuccess: (data) => setSubnetResult(data),
    onError: (err: any) => alert(err.message),
  });

  // ==================== 8. DLCD TRUTH TABLE STATE ====================
  const [dlcdExpr, setDlcdExpr] = useState('(A and B) or not C');
  const [dlcdResult, setDlcdResult] = useState<TruthTableResult | null>(null);

  const dlcdMutation = useMutation({
    mutationFn: () => generateTruthTable(dlcdExpr),
    onSuccess: (data) => setDlcdResult(data),
    onError: (err: any) => alert(err.message),
  });

  return (
    <div className="space-y-6">
      {/* Simulator Nav Subtabs */}
      <div className="flex items-center gap-1 overflow-x-auto pb-2 border-b border-zinc-800 scrollbar-thin">
        {[
          { id: 'math', label: 'Math & SymPy', icon: Calculator },
          { id: 'sandbox', label: 'Python Sandbox', icon: Terminal },
          { id: 'dsa', label: 'DSA Visual Tracer', icon: Binary },
          { id: 'cpu', label: 'CPU Scheduler', icon: Cpu },
          { id: 'banker', label: "Banker's Deadlock", icon: ShieldAlert },
          { id: 'page', label: 'Page Replacement', icon: Layers },
          { id: 'subnet', label: 'Subnet Calculator', icon: Network },
          { id: 'dlcd', label: 'DLCD Truth Table', icon: Binary },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = subTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setSubTab(tab.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-colors ${
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

      {/* ==================== 1. MATH SOLVER ==================== */}
      {subTab === 'math' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">SymPy Symbolic Mathematics Engine</h4>
              <p className="text-xs text-zinc-400">
                Rigorous algebraic solver, calculus (differentiation, definite integrals), and matrix linear algebra.
              </p>
            </div>
            <div className="flex gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800 text-xs">
              {(['solve', 'diff', 'integrate', 'simplify', 'matrix'] as const).map((op) => (
                <button
                  key={op}
                  onClick={() => {
                    setMathOp(op);
                    setMathResult(null);
                    if (op === 'solve') setMathInput('x**2 - 5*x + 6 = 0');
                    if (op === 'diff') setMathInput('sin(x)*cos(x)');
                    if (op === 'integrate') {
                      setMathInput('x**2');
                      setMathLower('0');
                      setMathUpper('3');
                    }
                    if (op === 'simplify') setMathInput('(x**2 - 1)/(x - 1)');
                  }}
                  className={`px-2.5 py-1 rounded capitalize text-xs transition-colors ${
                    mathOp === op ? 'bg-indigo-600 text-white font-medium' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {op}
                </button>
              ))}
            </div>
          </div>

          {mathOp !== 'matrix' ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="sm:col-span-2 space-y-1">
                <label className="text-[11px] text-zinc-400">Mathematical Expression / Equation</label>
                <input
                  type="text"
                  value={mathInput}
                  onChange={(e) => setMathInput(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
                  placeholder="e.g. 2*x + 5 = 15 or sin(x)*exp(x)"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] text-zinc-400">Target Variable</label>
                <input
                  type="text"
                  value={mathVar}
                  onChange={(e) => setMathVar(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              {mathOp === 'diff' && (
                <div className="space-y-1">
                  <label className="text-[11px] text-zinc-400">Derivative Order</label>
                  <input
                    type="number"
                    min={1}
                    max={5}
                    value={mathOrder}
                    onChange={(e) => setMathOrder(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
                  />
                </div>
              )}
              {mathOp === 'integrate' && (
                <>
                  <div className="space-y-1">
                    <label className="text-[11px] text-zinc-400">Lower Limit (Optional)</label>
                    <input
                      type="text"
                      value={mathLower}
                      onChange={(e) => setMathLower(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[11px] text-zinc-400">Upper Limit (Optional)</label>
                    <input
                      type="text"
                      value={mathUpper}
                      onChange={(e) => setMathUpper(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
                    />
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-400">Matrix Operation:</span>
                {(['determinant', 'inverse', 'eigenvalues', 'rref'] as const).map((op) => (
                  <button
                    key={op}
                    onClick={() => setMatrixOp(op)}
                    className={`px-2 py-1 rounded text-xs capitalize ${
                      matrixOp === op ? 'bg-indigo-600 text-white' : 'bg-zinc-800 text-zinc-400'
                    }`}
                  >
                    {op}
                  </button>
                ))}
              </div>
              <div className="p-3 bg-zinc-950 rounded-xl border border-zinc-800 space-y-2">
                <span className="text-[11px] text-zinc-500">2x2 Matrix Entries:</span>
                <div className="grid grid-cols-2 gap-2 max-w-xs">
                  {matrixData.map((row, rIdx) =>
                    row.map((val, cIdx) => (
                      <input
                        key={`${rIdx}-${cIdx}`}
                        type="number"
                        value={val}
                        onChange={(e) => {
                          const valNum = parseFloat(e.target.value) || 0;
                          const next = matrixData.map((r, ri) =>
                            r.map((c, ci) => (ri === rIdx && ci === cIdx ? valNum : c))
                          );
                          setMatrixData(next);
                        }}
                        className="px-2 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-center text-xs font-mono text-zinc-100"
                      />
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end">
            <button
              onClick={() => mathMutation.mutate()}
              disabled={mathMutation.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50 transition-colors"
            >
              {mathMutation.isPending ? 'Computing...' : 'Execute Symbolic Math'}
            </button>
          </div>

          {mathResult && (
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-2">
              <span className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider">Computed Result</span>
              {mathResult.latex ? (
                <div className="text-sm font-mono text-zinc-100">
                  <MarkdownRenderer content={`$$${mathResult.latex}$$`} />
                </div>
              ) : (
                <pre className="text-xs font-mono text-zinc-300 overflow-x-auto">
                  {JSON.stringify(mathResult, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      {/* ==================== 2. PYTHON SANDBOX ==================== */}
      {subTab === 'sandbox' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">Restricted Execution Sandbox</h4>
              <p className="text-xs text-zinc-400">
                Safe AST static analysis prevents filesystem/network tampering with a 2.5s execution timeout.
              </p>
            </div>
            <button
              onClick={() => runCodeMutation.mutate()}
              disabled={runCodeMutation.isPending}
              className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg disabled:opacity-50 transition-colors"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {runCodeMutation.isPending ? 'Running...' : 'Run Code'}
            </button>
          </div>

          <textarea
            rows={8}
            value={codeSnippet}
            onChange={(e) => setCodeSnippet(e.target.value)}
            className="w-full p-4 bg-zinc-950 border border-zinc-800 rounded-xl font-mono text-xs text-zinc-200 focus:outline-none focus:border-emerald-500 leading-relaxed"
          />

          {codeResult && (
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-2 font-mono text-xs">
              <div className="flex items-center justify-between text-[11px] pb-2 border-b border-zinc-800">
                <span className={codeResult.success ? 'text-emerald-400' : 'text-rose-400'}>
                  {codeResult.success ? '✓ Execution Succeeded' : '✗ Execution Failed / Security Violation'}
                </span>
                <span className="text-zinc-500">Duration: {codeResult.duration_ms}ms</span>
              </div>
              {codeResult.stdout && (
                <div>
                  <div className="text-[10px] text-zinc-500">STDOUT:</div>
                  <pre className="text-zinc-300 whitespace-pre-wrap">{codeResult.stdout}</pre>
                </div>
              )}
              {codeResult.stderr && (
                <div>
                  <div className="text-[10px] text-rose-400">STDERR:</div>
                  <pre className="text-rose-300 whitespace-pre-wrap">{codeResult.stderr}</pre>
                </div>
              )}
              {codeResult.error && (
                <div className="text-rose-400 font-semibold">{codeResult.error}</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ==================== 3. DSA VISUAL TRACER ==================== */}
      {subTab === 'dsa' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">DSA Step-by-Step Visual Tracer</h4>
              <p className="text-xs text-zinc-400">
                Inspect array state modifications and search pointer intervals at each algorithmic step.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={dsaAlgo}
                onChange={(e) => {
                  setDsaAlgo(e.target.value as any);
                  setDsaResult(null);
                }}
                className="px-3 py-1.5 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200"
              >
                <option value="binary_search">Binary Search</option>
                <option value="bubble_sort">Bubble Sort</option>
              </select>
              <button
                onClick={() => dsaMutation.mutate()}
                disabled={dsaMutation.isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
              >
                {dsaMutation.isPending ? 'Tracing...' : 'Trace Algorithm'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="sm:col-span-2 space-y-1">
              <label className="text-[11px] text-zinc-400">Initial Array (Comma-Separated)</label>
              <input
                type="text"
                value={dsaArrayStr}
                onChange={(e) => setDsaArrayStr(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
              />
            </div>
            {dsaAlgo === 'binary_search' && (
              <div className="space-y-1">
                <label className="text-[11px] text-zinc-400">Search Target</label>
                <input
                  type="number"
                  value={dsaTarget}
                  onChange={(e) => setDsaTarget(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
                />
              </div>
            )}
          </div>

          {dsaResult && dsaResult.steps.length > 0 && (
            <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-5">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <div className="text-xs font-semibold text-zinc-300">
                  Step {dsaStepIndex + 1} of {dsaResult.steps.length}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDsaStepIndex((prev) => Math.max(0, prev - 1))}
                    disabled={dsaStepIndex === 0}
                    className="p-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 disabled:opacity-40"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setDsaStepIndex((prev) => Math.min(dsaResult.steps.length - 1, prev + 1))}
                    disabled={dsaStepIndex === dsaResult.steps.length - 1}
                    className="p-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 disabled:opacity-40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Step Description */}
              <div className="text-xs text-indigo-300 bg-indigo-950/30 p-3 rounded-lg border border-indigo-900/40">
                {dsaResult.steps[dsaStepIndex].description}
              </div>

              {/* Visual Array Blocks */}
              <div className="flex items-center justify-center gap-2 overflow-x-auto py-4">
                {dsaResult.steps[dsaStepIndex].array_state.map((val, idx) => {
                  const pointers = dsaResult.steps[dsaStepIndex].pointers || {};
                  const isMid = pointers.mid === idx;
                  const isLow = pointers.low === idx;
                  const isHigh = pointers.high === idx;
                  const isTarget = val === dsaTarget && isMid;

                  return (
                    <div key={idx} className="flex flex-col items-center gap-1.5 flex-shrink-0">
                      <div
                        className={`w-12 h-12 rounded-xl flex items-center justify-center font-mono font-bold text-sm border transition-all ${
                          isTarget
                            ? 'bg-emerald-500/20 border-emerald-400 text-emerald-300 scale-105'
                            : isMid
                            ? 'bg-amber-500/20 border-amber-400 text-amber-300 scale-105'
                            : isLow || isHigh
                            ? 'bg-indigo-950 border-indigo-500 text-indigo-200'
                            : 'bg-zinc-900 border-zinc-700 text-zinc-200'
                        }`}
                      >
                        {val}
                      </div>
                      <div className="text-[10px] font-mono text-zinc-500">[{idx}]</div>
                      <div className="text-[10px] font-bold text-amber-400 h-3">
                        {isMid && 'MID'}
                        {isLow && !isMid && 'LOW'}
                        {isHigh && !isMid && 'HIGH'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== 4. CPU SCHEDULER ==================== */}
      {subTab === 'cpu' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">CPU Scheduling Simulator & Gantt Chart</h4>
              <p className="text-xs text-zinc-400">
                Compare First-Come First-Served (FCFS) and preemptive Round Robin execution with metrics.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={cpuAlgo}
                onChange={(e) => setCpuAlgo(e.target.value as any)}
                className="px-3 py-1.5 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200"
              >
                <option value="fcfs">First-Come First-Served (FCFS)</option>
                <option value="round_robin">Round Robin</option>
              </select>
              {cpuAlgo === 'round_robin' && (
                <div className="flex items-center gap-1.5 text-xs text-zinc-400">
                  <span>Quantum:</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={cpuQuantum}
                    onChange={(e) => setCpuQuantum(parseInt(e.target.value) || 2)}
                    className="w-14 px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-center text-xs text-zinc-100"
                  />
                </div>
              )}
              <button
                onClick={() => cpuMutation.mutate()}
                disabled={cpuMutation.isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
              >
                {cpuMutation.isPending ? 'Simulating...' : 'Simulate'}
              </button>
            </div>
          </div>

          {/* Processes Input Table */}
          <div className="p-4 bg-zinc-950 rounded-xl border border-zinc-800 space-y-3">
            <span className="text-xs font-semibold text-zinc-300">Process Configuration</span>
            <div className="grid grid-cols-4 gap-2 text-[11px] font-semibold text-zinc-400 uppercase">
              <div>PID</div>
              <div>Arrival Time</div>
              <div>Burst Time</div>
              <div />
            </div>
            {cpuProcesses.map((p, idx) => (
              <div key={idx} className="grid grid-cols-4 gap-2 items-center">
                <input
                  type="text"
                  value={p.pid}
                  onChange={(e) => {
                    const next = [...cpuProcesses];
                    next[idx].pid = e.target.value;
                    setCpuProcesses(next);
                  }}
                  className="px-2.5 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-xs text-zinc-200"
                />
                <input
                  type="number"
                  value={p.arrival}
                  onChange={(e) => {
                    const next = [...cpuProcesses];
                    next[idx].arrival = parseInt(e.target.value) || 0;
                    setCpuProcesses(next);
                  }}
                  className="px-2.5 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-xs text-zinc-200"
                />
                <input
                  type="number"
                  value={p.burst}
                  onChange={(e) => {
                    const next = [...cpuProcesses];
                    next[idx].burst = parseInt(e.target.value) || 1;
                    setCpuProcesses(next);
                  }}
                  className="px-2.5 py-1.5 bg-zinc-900 border border-zinc-700 rounded text-xs text-zinc-200"
                />
                <button
                  onClick={() => setCpuProcesses(cpuProcesses.filter((_, i) => i !== idx))}
                  disabled={cpuProcesses.length <= 1}
                  className="text-xs text-rose-400 hover:text-rose-300 disabled:opacity-30"
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              onClick={() =>
                setCpuProcesses([
                  ...cpuProcesses,
                  { pid: `P${cpuProcesses.length + 1}`, arrival: cpuProcesses.length, burst: 4 },
                ])
              }
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium pt-1"
            >
              + Add Process
            </button>
          </div>

          {/* Results: Gantt Chart and Metrics */}
          {cpuResult && (
            <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-5">
              <div>
                <span className="text-xs font-semibold text-zinc-300">Execution Gantt Chart</span>
                <div className="flex items-center overflow-x-auto py-3">
                  {cpuResult.timeline.map((block, bIdx) => (
                    <div key={bIdx} className="flex flex-col items-center flex-shrink-0">
                      <div className="h-10 min-w-[48px] px-2 bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-xs font-semibold text-indigo-200">
                        {block.pid}
                      </div>
                      <div className="flex justify-between w-full text-[10px] text-zinc-500 px-0.5">
                        <span>{block.start}</span>
                        <span>{block.end}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Metrics Table */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-zinc-300">Metrics Breakdown</span>
                <table className="w-full text-left text-xs border border-zinc-800 rounded-lg overflow-hidden">
                  <thead className="bg-zinc-900 text-zinc-400 text-[10px] uppercase">
                    <tr>
                      <th className="p-2.5">PID</th>
                      <th className="p-2.5">Arrival</th>
                      <th className="p-2.5">Burst</th>
                      <th className="p-2.5">Completion</th>
                      <th className="p-2.5">Turnaround</th>
                      <th className="p-2.5">Waiting</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {cpuResult.process_metrics.map((m) => (
                      <tr key={m.pid} className="text-zinc-200">
                        <td className="p-2.5 font-semibold text-indigo-400">{m.pid}</td>
                        <td className="p-2.5">{m.arrival}</td>
                        <td className="p-2.5">{m.burst}</td>
                        <td className="p-2.5">{m.completion_time}</td>
                        <td className="p-2.5">{m.turnaround_time}</td>
                        <td className="p-2.5">{m.waiting_time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center gap-4 text-xs font-medium text-emerald-400 pt-2 border-t border-zinc-800">
                <span>Average Waiting Time: {cpuResult.average_waiting_time.toFixed(2)} ms</span>
                <span>•</span>
                <span>Average Turnaround Time: {cpuResult.average_turnaround_time.toFixed(2)} ms</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== 5. BANKER'S DEADLOCK ==================== */}
      {subTab === 'banker' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-zinc-200">Banker's Algorithm: Deadlock Avoidance</h4>
            <p className="text-xs text-zinc-400">
              Evaluates system resource safety sequence across Allocation, Max, and Available vectors.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] text-zinc-400">Available Resources Vector</label>
              <input
                type="text"
                value={bankerAvailable}
                onChange={(e) => setBankerAvailable(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
                placeholder="3, 3, 2"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-zinc-400">Allocation Matrix (row/process)</label>
              <textarea
                rows={4}
                value={bankerAlloc}
                onChange={(e) => setBankerAlloc(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-zinc-400">Max Matrix (row/process)</label>
              <textarea
                rows={4}
                value={bankerMax}
                onChange={(e) => setBankerMax(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => bankerMutation.mutate()}
              disabled={bankerMutation.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
            >
              {bankerMutation.isPending ? 'Checking Safety...' : 'Run Safety Algorithm'}
            </button>
          </div>

          {bankerResult && (
            <div
              className={`p-4 rounded-xl border ${
                bankerResult.is_safe
                  ? 'bg-emerald-950/20 border-emerald-900/40'
                  : 'bg-rose-950/20 border-rose-900/40'
              } space-y-2`}
            >
              <div className="flex items-center gap-2 text-xs font-semibold">
                {bankerResult.is_safe ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-300">System is in a SAFE State!</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                    <span className="text-rose-300">DEADLOCK DETECTED: System is in an Unsafe State.</span>
                  </>
                )}
              </div>
              {bankerResult.safe_sequence && (
                <div className="text-xs text-zinc-300">
                  <span className="font-semibold text-zinc-100">Safe Execution Sequence: </span>
                  <span className="font-mono text-emerald-400">{bankerResult.safe_sequence.join(' ➔ ')}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ==================== 6. PAGE REPLACEMENT ==================== */}
      {subTab === 'page' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">Virtual Memory: Page Replacement</h4>
              <p className="text-xs text-zinc-400">
                Visualize memory frame cache hits, page faults, and miss rate under FIFO and LRU strategies.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={pageAlgo}
                onChange={(e) => setPageAlgo(e.target.value as any)}
                className="px-3 py-1.5 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200"
              >
                <option value="fifo">FIFO (First-In First-Out)</option>
                <option value="lru">LRU (Least Recently Used)</option>
              </select>
              <div className="flex items-center gap-1 text-xs text-zinc-400">
                <span>Frames:</span>
                <input
                  type="number"
                  min={1}
                  max={6}
                  value={numFrames}
                  onChange={(e) => setNumFrames(parseInt(e.target.value) || 3)}
                  className="w-12 px-2 py-1 bg-zinc-950 border border-zinc-700 rounded text-center text-xs text-zinc-100"
                />
              </div>
              <button
                onClick={() => pageMutation.mutate()}
                disabled={pageMutation.isPending}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
              >
                {pageMutation.isPending ? 'Simulating...' : 'Simulate'}
              </button>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] text-zinc-400">Page Reference String</label>
            <input
              type="text"
              value={pageString}
              onChange={(e) => setPageString(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
            />
          </div>

          {pageResult && (
            <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 space-y-4">
              <div className="flex items-center gap-4 text-xs font-medium pb-3 border-b border-zinc-800">
                <span className="text-rose-400 font-semibold">Total Faults: {pageResult.page_faults}</span>
                <span className="text-emerald-400 font-semibold">Total Hits: {pageResult.hits}</span>
                <span className="text-zinc-300">Fault Rate: {(pageResult.fault_rate * 100).toFixed(1)}%</span>
              </div>

              {/* Steps frame matrix */}
              <div className="overflow-x-auto">
                <div className="inline-flex gap-2 pb-2">
                  {pageResult.steps.map((st) => (
                    <div key={st.step} className="flex flex-col items-center gap-1 flex-shrink-0">
                      <div className="text-[11px] font-bold text-zinc-300">P{st.page}</div>
                      <div className="flex flex-col gap-1 p-1 bg-zinc-900 rounded-lg border border-zinc-800">
                        {st.frames.map((f, fi) => (
                          <div
                            key={fi}
                            className="w-8 h-8 flex items-center justify-center font-mono text-xs rounded bg-zinc-950 border border-zinc-700 text-zinc-200"
                          >
                            {f !== null ? f : '-'}
                          </div>
                        ))}
                      </div>
                      <span
                        className={`text-[9px] font-bold uppercase px-1 rounded ${
                          st.status === 'HIT' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}
                      >
                        {st.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== 7. SUBNET CALCULATOR ==================== */}
      {subTab === 'subnet' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-zinc-200">Computer Networks: IPv4 Subnet Calculator</h4>
            <p className="text-xs text-zinc-400">
              Calculate CIDR boundaries, netmasks, broadcast addresses, and valid host assignable ranges.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] text-zinc-400">IPv4 Address</label>
              <input
                type="text"
                value={subnetIP}
                onChange={(e) => setSubnetIP(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[11px] text-zinc-400">CIDR Prefix (/{subnetPrefix})</label>
              <input
                type="range"
                min={8}
                max={30}
                value={subnetPrefix}
                onChange={(e) => setSubnetPrefix(parseInt(e.target.value))}
                className="w-full h-2 bg-zinc-700 rounded-lg cursor-pointer"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => subnetMutation.mutate()}
              disabled={subnetMutation.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
            >
              {subnetMutation.isPending ? 'Calculating...' : 'Calculate Subnet'}
            </button>
          </div>

          {subnetResult && (
            <div className="p-5 rounded-xl bg-zinc-950 border border-zinc-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-[10px] text-zinc-500 uppercase">Network Address</span>
                <div className="font-mono font-semibold text-zinc-200">{subnetResult.network_address}</div>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase">Broadcast Address</span>
                <div className="font-mono font-semibold text-zinc-200">{subnetResult.broadcast_address}</div>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase">Subnet Mask</span>
                <div className="font-mono font-semibold text-zinc-200">{subnetResult.netmask}</div>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase">Wildcard Mask</span>
                <div className="font-mono font-semibold text-zinc-200">{subnetResult.wildcard_mask}</div>
              </div>
              <div className="sm:col-span-2">
                <span className="text-[10px] text-zinc-500 uppercase">Usable Host Range</span>
                <div className="font-mono font-semibold text-emerald-400">
                  {subnetResult.usable_host_range[0]} ➔ {subnetResult.usable_host_range[1]}
                </div>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase">Usable Hosts</span>
                <div className="font-mono font-semibold text-zinc-200">{subnetResult.usable_hosts.toLocaleString()}</div>
              </div>
              <div>
                <span className="text-[10px] text-zinc-500 uppercase">Scope</span>
                <div className="font-semibold text-indigo-400">
                  {subnetResult.is_private ? 'RFC 1918 Private' : 'Public Internet'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ==================== 8. DLCD TRUTH TABLE ==================== */}
      {subTab === 'dlcd' && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-4">
          <div>
            <h4 className="text-sm font-semibold text-zinc-200">DLCD: Boolean Logic Truth Table Generator</h4>
            <p className="text-xs text-zinc-400">
              Evaluates arbitrary boolean expressions with AND, OR, NOT, and XOR operator logic.
            </p>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] text-zinc-400">Boolean Expression (e.g., (A and B) or not C)</label>
            <input
              type="text"
              value={dlcdExpr}
              onChange={(e) => setDlcdExpr(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs font-mono text-zinc-200"
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={() => dlcdMutation.mutate()}
              disabled={dlcdMutation.isPending}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
            >
              {dlcdMutation.isPending ? 'Generating...' : 'Generate Truth Table'}
            </button>
          </div>

          {dlcdResult && (
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 space-y-2">
              <span className="text-xs font-semibold text-zinc-300">
                Truth Table ({dlcdResult.total_rows} rows)
              </span>
              <div className="overflow-x-auto">
                <table className="w-full text-center text-xs font-mono border border-zinc-800 rounded-lg overflow-hidden">
                  <thead className="bg-zinc-900 text-zinc-400 text-[11px]">
                    <tr>
                      {dlcdResult.variables.map((v) => (
                        <th key={v} className="p-2 border-r border-zinc-800">{v}</th>
                      ))}
                      <th className="p-2 text-indigo-400">OUTPUT</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800">
                    {dlcdResult.table.map((row, rIdx) => {
                      const isTrue = row.OUTPUT === 1 || row.OUTPUT === true;
                      return (
                        <tr key={rIdx} className={isTrue ? 'bg-emerald-950/20' : ''}>
                          {dlcdResult.variables.map((v) => (
                            <td key={v} className="p-2 border-r border-zinc-800 text-zinc-300">
                              {row[v] ? '1' : '0'}
                            </td>
                          ))}
                          <td className={`p-2 font-bold ${isTrue ? 'text-emerald-400' : 'text-zinc-500'}`}>
                            {isTrue ? '1' : '0'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
