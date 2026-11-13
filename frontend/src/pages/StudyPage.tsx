import React, { useState } from 'react';
import { GraduationCap, Layers, FileQuestion, Cpu } from 'lucide-react';
import { FlashcardSection } from '../components/academic/FlashcardSection';
import { QuizSection } from '../components/academic/QuizSection';
import { SimulatorsSection } from '../components/academic/SimulatorsSection';

export const StudyPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'flashcards' | 'quizzes' | 'simulators'>('flashcards');

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
          <GraduationCap className="w-5 h-5 text-amber-400" />
          Academic Intelligence & Study Hub
        </h2>
        <p className="text-xs text-zinc-400 mt-0.5">
          FSRS v4 spaced repetition flashcards, automated exam simulations, and sandboxed subject tutors.
        </p>
      </div>

      {/* Main Tabs */}
      <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
        <button
          onClick={() => setActiveTab('flashcards')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'flashcards'
              ? 'bg-indigo-600 text-white shadow-md'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
          }`}
        >
          <Layers className="w-4 h-4" />
          FSRS Flashcards
        </button>
        <button
          onClick={() => setActiveTab('quizzes')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'quizzes'
              ? 'bg-emerald-600 text-white shadow-md'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
          }`}
        >
          <FileQuestion className="w-4 h-4" />
          Quizzes & Mock Exams
        </button>
        <button
          onClick={() => setActiveTab('simulators')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
            activeTab === 'simulators'
              ? 'bg-amber-600 text-white shadow-md'
              : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
          }`}
        >
          <Cpu className="w-4 h-4" />
          Academic Simulators & Sandbox
        </button>
      </div>

      {/* Active Tab Content */}
      <div className="pt-2">
        {activeTab === 'flashcards' && <FlashcardSection />}
        {activeTab === 'quizzes' && <QuizSection />}
        {activeTab === 'simulators' && <SimulatorsSection />}
      </div>
    </div>
  );
};

export default StudyPage;
