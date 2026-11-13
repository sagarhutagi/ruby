import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileQuestion,
  Plus,
  CheckCircle2,
  XCircle,
  Clock,
  Award,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import {
  fetchQuizzes,
  generateQuiz,
  fetchQuiz,
  submitQuiz,
  QuizSubmissionResult,
} from '../../services/api';
import { MarkdownRenderer } from '../MarkdownRenderer';

export const QuizSection: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeQuizId, setActiveQuizId] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  // Form state
  const [quizTitle, setQuizTitle] = useState('Operating Systems & Algorithms Midterm');
  const [quizDifficulty, setQuizDifficulty] = useState('medium');
  const [quizCount, setQuizCount] = useState(5);
  const [timeLimit, setTimeLimit] = useState(15);

  // Taking state
  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({});
  const [submissionResult, setSubmissionResult] = useState<QuizSubmissionResult | null>(null);

  // Fetch list of quizzes
  const { data: quizzes = [], isLoading: loadingQuizzes } = useQuery({
    queryKey: ['quizzes'],
    queryFn: fetchQuizzes,
  });

  // Fetch active quiz details
  const { data: activeQuiz, isLoading: loadingActiveQuiz } = useQuery({
    queryKey: ['quiz', activeQuizId],
    queryFn: () => (activeQuizId ? fetchQuiz(activeQuizId) : Promise.resolve(null)),
    enabled: !!activeQuizId,
  });

  const generateMutation = useMutation({
    mutationFn: generateQuiz,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['quizzes'] });
      setActiveQuizId(data.id);
      setIsGenerating(false);
      setCurrentQIndex(0);
      setUserAnswers({});
      setSubmissionResult(null);
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => {
      if (!activeQuizId) throw new Error('No quiz active');
      return submitQuiz(activeQuizId, userAnswers);
    },
    onSuccess: (result) => {
      setSubmissionResult(result);
      queryClient.invalidateQueries({ queryKey: ['quizzes'] });
      queryClient.invalidateQueries({ queryKey: ['quiz', activeQuizId] });
    },
  });

  const handleSelectOption = (questionId: string, optionText: string) => {
    setUserAnswers((prev) => ({
      ...prev,
      [questionId]: optionText,
    }));
  };

  const isCompleted = activeQuiz?.status === 'completed' || !!submissionResult;

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <FileQuestion className="w-4 h-4 text-emerald-400" />
            Academic Quizzes & Mock Examinations
          </h3>
          <p className="text-xs text-zinc-400">
            Generate custom exams with instant grading, error tracking, and pedagogical explanations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeQuizId && (
            <button
              onClick={() => {
                setActiveQuizId(null);
                setSubmissionResult(null);
              }}
              className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
            >
              Back to Quizzes
            </button>
          )}
          <button
            onClick={() => setIsGenerating(!isGenerating)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors"
          >
            <Plus className="w-3.5 h-3.5 text-emerald-400" />
            Generate Quiz
          </button>
        </div>
      </div>

      {/* Quiz Generator Form */}
      {isGenerating && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            generateMutation.mutate({
              title: quizTitle.trim(),
              difficulty: quizDifficulty,
              question_count: quizCount,
              time_limit_minutes: timeLimit,
            });
          }}
          className="p-5 rounded-xl bg-zinc-900/60 border border-emerald-500/30 space-y-4"
        >
          <div className="text-xs font-semibold text-emerald-400">Configure Examination Parameters</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Exam Title</label>
              <input
                type="text"
                value={quizTitle}
                onChange={(e) => setQuizTitle(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Difficulty Level</label>
              <select
                value={quizDifficulty}
                onChange={(e) => setQuizDifficulty(e.target.value)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="easy">Easy (Foundational Recall)</option>
                <option value="medium">Medium (Analytical & Synthesis)</option>
                <option value="hard">Hard (Advanced Problem Solving)</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Number of Questions</label>
              <input
                type="number"
                min={1}
                max={20}
                value={quizCount}
                onChange={(e) => setQuizCount(parseInt(e.target.value) || 5)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Time Limit (Minutes)</label>
              <input
                type="number"
                min={1}
                max={120}
                value={timeLimit}
                onChange={(e) => setTimeLimit(parseInt(e.target.value) || 15)}
                className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200 focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsGenerating(false)}
              className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={generateMutation.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
            >
              {generateMutation.isPending ? 'Generating Exam...' : 'Build Exam'}
            </button>
          </div>
        </form>
      )}

      {/* Main Quizzes List or Active Exam Area */}
      {!activeQuizId ? (
        <div className="space-y-3">
          <div className="text-xs font-semibold text-zinc-400">Available Examination Sessions</div>
          {loadingQuizzes ? (
            <div className="text-center py-8 text-xs text-zinc-500">Loading exams...</div>
          ) : quizzes.length === 0 ? (
            <div className="text-center py-12 rounded-xl border border-dashed border-zinc-800 text-zinc-500 text-xs">
              No examination sessions found. Click "Generate Quiz" to create your first academic assessment.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {quizzes.map((quiz) => (
                <div
                  key={quiz.id}
                  className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800 hover:border-zinc-700 flex flex-col justify-between gap-3 transition-colors"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <h4 className="text-xs font-semibold text-zinc-200 truncate">{quiz.title}</h4>
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                          quiz.status === 'completed'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {quiz.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-[11px] text-zinc-400">
                      <span>{quiz.total_questions} Questions</span>
                      <span className="capitalize">{quiz.difficulty}</span>
                      {quiz.status === 'completed' && (
                        <span className="font-medium text-emerald-400">
                          Score: {quiz.score_percentage.toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="pt-2 border-t border-zinc-800/80 flex items-center justify-between">
                    <span className="text-[10px] text-zinc-500">
                      {new Date(quiz.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={() => {
                        setActiveQuizId(quiz.id);
                        setCurrentQIndex(0);
                        setUserAnswers({});
                        setSubmissionResult(null);
                      }}
                      className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                    >
                      {quiz.status === 'completed' ? 'View Review' : 'Start Exam'}
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : loadingActiveQuiz || !activeQuiz ? (
        <div className="text-center py-12 text-xs text-zinc-500">Loading examination data...</div>
      ) : isCompleted ? (
        /* Results & Mistakes Review */
        <div className="p-6 rounded-2xl bg-zinc-900/60 border border-zinc-800 space-y-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-2">
                <Award className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-semibold text-zinc-100">{activeQuiz.title} — Results</h3>
              </div>
              <p className="text-xs text-zinc-400 mt-1">
                Completed assessment review with comprehensive pedagogical breakdowns.
              </p>
            </div>
            <div className="flex items-center gap-3 bg-zinc-950 px-4 py-2.5 rounded-xl border border-zinc-800">
              <div className="text-center">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Score</div>
                <div className="text-lg font-bold text-emerald-400">
                  {submissionResult?.score_percentage?.toFixed(0) ?? activeQuiz.score_percentage?.toFixed(0) ?? 0}%
                </div>
              </div>
              <div className="h-6 w-px bg-zinc-800" />
              <div className="text-center">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wider">Correct</div>
                <div className="text-xs font-semibold text-zinc-300">
                  {submissionResult?.correct_count ?? activeQuiz.correct_count} / {activeQuiz.total_questions}
                </div>
              </div>
            </div>
          </div>

          {/* Mistakes and Question breakdown */}
          <div className="space-y-4">
            <h4 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Question Breakdown</h4>
            <div className="space-y-3">
              {activeQuiz.questions.map((q, idx) => {
                const isCorrect = q.is_correct ?? (submissionResult?.mistakes_review.every((m) => m.question_id !== q.id));
                return (
                  <div
                    key={q.id}
                    className={`p-4 rounded-xl border ${
                      isCorrect ? 'bg-emerald-950/20 border-emerald-900/40' : 'bg-rose-950/20 border-rose-900/40'
                    } space-y-2.5`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
                        {isCorrect ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                        )}
                        <span>Q{idx + 1}: {q.question_text}</span>
                      </div>
                      <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full ${
                        isCorrect ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                      }`}>
                        {isCorrect ? 'Correct' : 'Incorrect'}
                      </span>
                    </div>

                    <div className="text-xs space-y-1 text-zinc-300 pl-6">
                      <div>Your Answer: <span className="font-mono text-zinc-100">{q.user_answer || userAnswers[q.id] || '(None)'}</span></div>
                      {q.explanation && (
                        <div className="text-xs text-zinc-400 bg-zinc-950/60 p-3 rounded-lg border border-zinc-800/80 mt-2">
                          <span className="font-semibold text-zinc-300">Explanation: </span>
                          <MarkdownRenderer content={q.explanation} />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        /* Active Quiz Taking Session */
        <div className="max-w-3xl mx-auto p-6 rounded-2xl bg-zinc-900/70 border border-zinc-800 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">{activeQuiz.title}</h3>
              <div className="text-[11px] text-zinc-400 flex items-center gap-3 mt-0.5">
                <span>Question {currentQIndex + 1} of {activeQuiz.questions.length}</span>
                <span className="capitalize text-indigo-400 font-medium">Difficulty: {activeQuiz.difficulty}</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-amber-400">
              <Clock className="w-3.5 h-3.5" />
              <span>Exam in progress</span>
            </div>
          </div>

          {/* Current Question */}
          {activeQuiz.questions[currentQIndex] && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-zinc-950/80 border border-zinc-800 text-sm text-zinc-100 font-medium">
                <MarkdownRenderer content={activeQuiz.questions[currentQIndex].question_text} />
              </div>

              {/* Options */}
              {activeQuiz.questions[currentQIndex].options && (
                <div className="space-y-2">
                  {activeQuiz.questions[currentQIndex].options!.map((opt, oIdx) => {
                    const qId = activeQuiz.questions[currentQIndex].id;
                    const isSelected = userAnswers[qId] === opt;
                    return (
                      <button
                        key={oIdx}
                        type="button"
                        onClick={() => handleSelectOption(qId, opt)}
                        className={`w-full p-3.5 rounded-xl border text-left text-xs transition-all flex items-center justify-between ${
                          isSelected
                            ? 'bg-emerald-950/40 border-emerald-500 text-emerald-200'
                            : 'bg-zinc-950/40 border-zinc-800 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-900/40'
                        }`}
                      >
                        <span>{opt}</span>
                        <div
                          className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                            isSelected ? 'border-emerald-400 bg-emerald-500/20' : 'border-zinc-600'
                          }`}
                        >
                          {isSelected && <div className="w-2 h-2 rounded-full bg-emerald-400" />}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Navigation Controls */}
          <div className="flex items-center justify-between pt-4 border-t border-zinc-800">
            <button
              onClick={() => setCurrentQIndex((prev) => Math.max(0, prev - 1))}
              disabled={currentQIndex === 0}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            {currentQIndex + 1 < activeQuiz.questions.length ? (
              <button
                onClick={() => setCurrentQIndex((prev) => prev + 1)}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => {
                  if (confirm('Submit all exam answers now for evaluation?')) {
                    submitMutation.mutate();
                  }
                }}
                disabled={submitMutation.isPending}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg disabled:opacity-50"
              >
                {submitMutation.isPending ? 'Grading Answers...' : 'Submit Examination'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
