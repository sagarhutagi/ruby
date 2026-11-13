import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Layers,
  Plus,
  Trash2,
  Play,
  HelpCircle,
  Sparkles,
} from 'lucide-react';
import {
  fetchFlashcardDecks,
  createFlashcardDeck,
  deleteFlashcardDeck,
  fetchFlashcards,
  createFlashcard,
  reviewFlashcard,
} from '../../services/api';
import { MarkdownRenderer } from '../MarkdownRenderer';

export const FlashcardSection: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedDeckId, setSelectedDeckId] = useState<string | null>(null);
  const [isCreatingDeck, setIsCreatingDeck] = useState(false);
  const [newDeckName, setNewDeckName] = useState('');
  const [newDeckDesc, setNewDeckDesc] = useState('');

  // Add Card state
  const [isAddingCard, setIsAddingCard] = useState(false);
  const [cardFront, setCardFront] = useState('');
  const [cardBack, setCardBack] = useState('');
  const [cardHints, setCardHints] = useState('');
  const [cardExplanation, setCardExplanation] = useState('');

  // Review mode state
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewIndex, setReviewIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);

  const { data: decks = [] } = useQuery({
    queryKey: ['flashcardDecks'],
    queryFn: fetchFlashcardDecks,
  });

  // Set default selected deck
  React.useEffect(() => {
    if (!selectedDeckId && decks.length > 0) {
      setSelectedDeckId(decks[0].id);
    }
  }, [decks, selectedDeckId]);

  const { data: cards = [], isLoading: loadingCards } = useQuery({
    queryKey: ['flashcards', selectedDeckId],
    queryFn: () => (selectedDeckId ? fetchFlashcards(selectedDeckId) : Promise.resolve([])),
    enabled: !!selectedDeckId,
  });

  const dueCards = cards.filter((c) => {
    if (!c.due_date) return true;
    const today = new Date().toISOString().split('T')[0];
    return c.due_date <= today;
  });

  const createDeckMutation = useMutation({
    mutationFn: createFlashcardDeck,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['flashcardDecks'] });
      setSelectedDeckId(data.id);
      setIsCreatingDeck(false);
      setNewDeckName('');
      setNewDeckDesc('');
    },
  });

  const deleteDeckMutation = useMutation({
    mutationFn: deleteFlashcardDeck,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flashcardDecks'] });
      setSelectedDeckId(null);
    },
  });

  const createCardMutation = useMutation({
    mutationFn: createFlashcard,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flashcards', selectedDeckId] });
      queryClient.invalidateQueries({ queryKey: ['flashcardDecks'] });
      setIsAddingCard(false);
      setCardFront('');
      setCardBack('');
      setCardHints('');
      setCardExplanation('');
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ cardId, rating }: { cardId: string; rating: number }) =>
      reviewFlashcard(cardId, rating),
    onSuccess: () => {
      if (reviewIndex + 1 < dueCards.length) {
        setReviewIndex((prev) => prev + 1);
        setShowAnswer(false);
      } else {
        // Finished review session
        queryClient.invalidateQueries({ queryKey: ['flashcards', selectedDeckId] });
        queryClient.invalidateQueries({ queryKey: ['flashcardDecks'] });
        setIsReviewing(false);
        setReviewIndex(0);
        setShowAnswer(false);
      }
    },
  });

  const handleStartReview = () => {
    if (dueCards.length === 0) return;
    setIsReviewing(true);
    setReviewIndex(0);
    setShowAnswer(false);
  };

  const handleReviewRating = (rating: number) => {
    const currentCard = dueCards[reviewIndex];
    if (!currentCard) return;
    reviewMutation.mutate({ cardId: currentCard.id, rating });
  };

  const selectedDeck = decks.find((d) => d.id === selectedDeckId);

  return (
    <div className="space-y-6">
      {/* Deck selection and header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-zinc-800">
        <div>
          <h3 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            FSRS Spaced Repetition Decks
          </h3>
          <p className="text-xs text-zinc-400">
            Optimize long-term recall with mathematically modeled retention decay curves.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsCreatingDeck(!isCreatingDeck)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg transition-colors border border-zinc-700"
          >
            <Plus className="w-3.5 h-3.5 text-indigo-400" />
            New Deck
          </button>
        </div>
      </div>

      {/* New Deck Form */}
      {isCreatingDeck && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!newDeckName.trim()) return;
            createDeckMutation.mutate({ name: newDeckName.trim(), description: newDeckDesc.trim() || undefined });
          }}
          className="p-4 rounded-xl bg-zinc-900/60 border border-indigo-500/30 space-y-3"
        >
          <div className="font-medium text-xs text-indigo-300">Create New Flashcard Deck</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Deck Title (e.g., Operating Systems Midterm)"
              value={newDeckName}
              onChange={(e) => setNewDeckName(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
              required
            />
            <input
              type="text"
              placeholder="Description (Optional)"
              value={newDeckDesc}
              onChange={(e) => setNewDeckDesc(e.target.value)}
              className="w-full px-3 py-2 bg-zinc-950 border border-zinc-700 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsCreatingDeck(false)}
              className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createDeckMutation.isPending || !newDeckName.trim()}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
            >
              {createDeckMutation.isPending ? 'Creating...' : 'Create Deck'}
            </button>
          </div>
        </form>
      )}

      {/* Decks horizontally scrollable list */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2 scrollbar-thin">
        {decks.map((deck) => {
          const isSelected = deck.id === selectedDeckId;
          return (
            <button
              key={deck.id}
              onClick={() => {
                setSelectedDeckId(deck.id);
                setIsReviewing(false);
              }}
              className={`flex-shrink-0 px-4 py-3 rounded-xl border text-left transition-all ${
                isSelected
                  ? 'bg-indigo-950/40 border-indigo-500/60 ring-1 ring-indigo-500/20'
                  : 'bg-zinc-900/30 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/60'
              }`}
            >
              <div className="flex items-center justify-between gap-3 mb-1">
                <span className="text-xs font-semibold text-zinc-200">{deck.name}</span>
                {deck.due_cards > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {deck.due_cards} due
                  </span>
                )}
              </div>
              <div className="text-[11px] text-zinc-500">
                {deck.total_cards} card{deck.total_cards === 1 ? '' : 's'}
              </div>
            </button>
          );
        })}
      </div>

      {/* Main Flashcard Work Area */}
      {selectedDeck && !isReviewing && (
        <div className="p-5 rounded-xl bg-zinc-900/40 border border-zinc-800 space-y-5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-zinc-800">
            <div>
              <h4 className="text-sm font-semibold text-zinc-200">{selectedDeck.name}</h4>
              <p className="text-xs text-zinc-400">
                {selectedDeck.description || 'No description provided.'}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIsAddingCard(!isAddingCard)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-lg border border-zinc-700 transition-colors"
              >
                <Plus className="w-3.5 h-3.5 text-emerald-400" />
                Add Card
              </button>
              <button
                onClick={handleStartReview}
                disabled={dueCards.length === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg disabled:opacity-50 transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                Study Due Cards ({dueCards.length})
              </button>
              <button
                onClick={() => {
                  if (confirm(`Delete deck "${selectedDeck.name}" and all its flashcards?`)) {
                    deleteDeckMutation.mutate(selectedDeck.id);
                  }
                }}
                className="p-1.5 text-zinc-500 hover:text-rose-400 rounded-lg hover:bg-zinc-800 transition-colors"
                title="Delete Deck"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Add Card Form */}
          {isAddingCard && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!cardFront.trim() || !cardBack.trim()) return;
                createCardMutation.mutate({
                  deck_id: selectedDeck.id,
                  front: cardFront.trim(),
                  back: cardBack.trim(),
                  hints: cardHints.trim() || undefined,
                  explanation: cardExplanation.trim() || undefined,
                });
              }}
              className="p-4 rounded-xl bg-zinc-950 border border-zinc-700/80 space-y-3"
            >
              <div className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                New Academic Flashcard (KaTeX Math $...$ Supported)
              </div>
              <div className="space-y-2">
                <textarea
                  rows={2}
                  placeholder="Front Prompt / Question (e.g., What is Amdahl's Law formula?)"
                  value={cardFront}
                  onChange={(e) => setCardFront(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  required
                />
                <textarea
                  rows={3}
                  placeholder="Back Answer (e.g., S_{latency} = \frac{1}{(1-p) + \frac{p}{s}})"
                  value={cardBack}
                  onChange={(e) => setCardBack(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  required
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input
                    type="text"
                    placeholder="Hint (Optional)"
                    value={cardHints}
                    onChange={(e) => setCardHints(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  />
                  <input
                    type="text"
                    placeholder="Explanation / Context (Optional)"
                    value={cardExplanation}
                    onChange={(e) => setCardExplanation(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsAddingCard(false)}
                  className="px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createCardMutation.isPending || !cardFront.trim() || !cardBack.trim()}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg disabled:opacity-50"
                >
                  {createCardMutation.isPending ? 'Saving...' : 'Save Card'}
                </button>
              </div>
            </form>
          )}

          {/* Cards List Table */}
          {loadingCards ? (
            <div className="text-center py-8 text-xs text-zinc-500">Loading cards...</div>
          ) : cards.length === 0 ? (
            <div className="text-center py-12 rounded-lg border border-dashed border-zinc-800 text-zinc-500 text-xs">
              This deck has no flashcards yet. Click "Add Card" to create one.
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-xs font-medium text-zinc-400">All Cards ({cards.length})</div>
              <div className="divide-y divide-zinc-800/60 rounded-xl border border-zinc-800 overflow-hidden bg-zinc-950/40">
                {cards.map((card) => {
                  const isDue = !card.due_date || card.due_date <= new Date().toISOString().split('T')[0];
                  return (
                    <div key={card.id} className="p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 hover:bg-zinc-900/30 transition-colors">
                      <div className="space-y-1 max-w-xl">
                        <div className="text-xs font-medium text-zinc-200">
                          <MarkdownRenderer content={card.front} />
                        </div>
                        <div className="text-[11px] text-zinc-400 line-clamp-2">
                          <MarkdownRenderer content={card.back} />
                        </div>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-zinc-500 flex-shrink-0">
                        <span className={`px-2 py-0.5 rounded-full ${isDue ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' : 'bg-zinc-800 text-zinc-400'}`}>
                          {isDue ? 'Due' : `Due in ${card.scheduled_days}d`}
                        </span>
                        <span>Reps: {card.reps}</span>
                        <span>Diff: {card.difficulty.toFixed(1)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Active FSRS Review Session */}
      {selectedDeck && isReviewing && dueCards.length > 0 && (
        <div className="max-w-2xl mx-auto p-6 rounded-2xl bg-zinc-900/70 border border-zinc-800 shadow-xl space-y-6">
          <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-indigo-400">
                Card {reviewIndex + 1} of {dueCards.length}
              </span>
              <span className="text-[11px] text-zinc-500">({selectedDeck.name})</span>
            </div>
            <button
              onClick={() => setIsReviewing(false)}
              className="text-xs text-zinc-400 hover:text-zinc-200"
            >
              Exit Review
            </button>
          </div>

          {/* Current Card Front */}
          <div className="min-h-[140px] flex flex-col justify-center p-6 rounded-xl bg-zinc-950/80 border border-zinc-800/90 text-center space-y-3">
            <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">Prompt</span>
            <div className="text-sm font-medium text-zinc-100">
              <MarkdownRenderer content={dueCards[reviewIndex].front} />
            </div>
            {dueCards[reviewIndex].hints && (
              <div className="text-xs text-zinc-500 italic flex items-center justify-center gap-1">
                <HelpCircle className="w-3.5 h-3.5" />
                Hint: {dueCards[reviewIndex].hints}
              </div>
            )}
          </div>

          {/* Flip / Show Answer */}
          {!showAnswer ? (
            <div className="flex justify-center">
              <button
                onClick={() => setShowAnswer(true)}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg transition-all"
              >
                Show Answer (Space)
              </button>
            </div>
          ) : (
            <div className="space-y-6 animate-in fade-in duration-200">
              {/* Back Answer */}
              <div className="min-h-[120px] flex flex-col justify-center p-6 rounded-xl bg-zinc-950/80 border border-indigo-500/30 text-center space-y-3">
                <span className="text-[10px] uppercase font-bold tracking-wider text-emerald-400">Answer</span>
                <div className="text-sm font-medium text-zinc-200">
                  <MarkdownRenderer content={dueCards[reviewIndex].back} />
                </div>
                {dueCards[reviewIndex].explanation && (
                  <div className="text-xs text-zinc-400 pt-2 border-t border-zinc-800">
                    <MarkdownRenderer content={dueCards[reviewIndex].explanation} />
                  </div>
                )}
              </div>

              {/* FSRS Rating Buttons */}
              <div className="space-y-2">
                <div className="text-center text-[11px] text-zinc-400 font-medium">
                  Grade your recall to update FSRS memory parameters:
                </div>
                <div className="grid grid-cols-4 gap-2">
                  <button
                    onClick={() => handleReviewRating(1)}
                    disabled={reviewMutation.isPending}
                    className="py-2.5 px-2 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-xs font-medium transition-colors"
                  >
                    <div className="font-semibold">Again</div>
                    <div className="text-[10px] text-rose-400/80">&lt; 10m</div>
                  </button>
                  <button
                    onClick={() => handleReviewRating(2)}
                    disabled={reviewMutation.isPending}
                    className="py-2.5 px-2 bg-amber-950/40 hover:bg-amber-900/60 border border-amber-800/60 text-amber-300 rounded-xl text-xs font-medium transition-colors"
                  >
                    <div className="font-semibold">Hard</div>
                    <div className="text-[10px] text-amber-400/80">1.2x</div>
                  </button>
                  <button
                    onClick={() => handleReviewRating(3)}
                    disabled={reviewMutation.isPending}
                    className="py-2.5 px-2 bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-800/60 text-emerald-300 rounded-xl text-xs font-medium transition-colors"
                  >
                    <div className="font-semibold">Good</div>
                    <div className="text-[10px] text-emerald-400/80">Optimal</div>
                  </button>
                  <button
                    onClick={() => handleReviewRating(4)}
                    disabled={reviewMutation.isPending}
                    className="py-2.5 px-2 bg-blue-950/40 hover:bg-blue-900/60 border border-blue-800/60 text-blue-300 rounded-xl text-xs font-medium transition-colors"
                  >
                    <div className="font-semibold">Easy</div>
                    <div className="text-[10px] text-blue-400/80">Extended</div>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
