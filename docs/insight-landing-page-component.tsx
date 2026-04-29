import React, { useEffect, useMemo, useState } from 'react';

// Example source data for autocomplete and grid rendering
const insightsData = [
  {
    id: 1,
    title: '2026 Housing Cost Pressure Report',
    category: 'Housing',
    state: 'California',
    city: 'San Diego',
    summary: 'Median housing costs remain elevated, with coastal metros showing the strongest pressure.',
  },
  {
    id: 2,
    title: 'Commuter Utility Spend Benchmark',
    category: 'Utilities',
    state: 'Texas',
    city: 'Austin',
    summary: 'Utility spend trends flatten as energy-efficiency upgrades accelerate adoption.',
  },
  {
    id: 3,
    title: 'Property Tax Burden Snapshot',
    category: 'Taxes',
    state: 'Texas',
    city: 'Dallas',
    summary: 'Property tax burden varies significantly by county with widening suburban gaps.',
  },
  {
    id: 4,
    title: 'Urban Cost-of-Living Pulse',
    category: 'Cost of Living',
    state: 'New York',
    city: 'Buffalo',
    summary: 'Secondary cities show stable inflation compared to major urban cores.',
  },
  {
    id: 5,
    title: 'Home Insurance Premium Outlook',
    category: 'Insurance',
    state: 'Florida',
    city: 'Miami',
    summary: 'Premium volatility remains high in climate-exposed coastal ZIP clusters.',
  },
] as const;

type InsightCard = (typeof insightsData)[number];

export default function InsightLandingPage() {
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [selectedState, setSelectedState] = useState('');
  const [selectedCity, setSelectedCity] = useState('');

  // 300ms debounce for search performance
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
    }, 300);

    return () => clearTimeout(timer);
  }, [searchInput]);

  const states = useMemo(() => {
    return Array.from(new Set(insightsData.map((item) => item.state))).sort();
  }, []);

  // Cascading dropdown logic: city options depend on selected state
  const cities = useMemo(() => {
    if (!selectedState) return [];

    return Array.from(
      new Set(insightsData.filter((item) => item.state === selectedState).map((item) => item.city))
    ).sort();
  }, [selectedState]);

  const autocompleteOptions = useMemo(() => {
    const query = searchInput.trim().toLowerCase();
    if (!query) return [];

    const options = insightsData.flatMap((item) => [item.title, item.category]);
    return Array.from(new Set(options))
      .filter((option) => option.toLowerCase().includes(query))
      .slice(0, 8);
  }, [searchInput]);

  const filteredCards = useMemo(() => {
    const q = debouncedSearch.toLowerCase();

    return insightsData.filter((item) => {
      const matchesSearch =
        !q ||
        item.title.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q);

      const matchesState = !selectedState || item.state === selectedState;
      const matchesCity = !selectedCity || item.city === selectedCity;

      return matchesSearch && matchesState && matchesCity;
    });
  }, [debouncedSearch, selectedState, selectedCity]);

  const handleStateChange = (nextState: string) => {
    setSelectedState(nextState);
    // Reset city whenever state changes (cascading consistency)
    setSelectedCity('');
  };

  const handleReset = () => {
    setSearchInput('');
    setDebouncedSearch('');
    setSelectedState('');
    setSelectedCity('');
  };

  const handleSearchClick = () => {
    // Force immediate search when user clicks Search
    setDebouncedSearch(searchInput.trim());
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <header className="mb-8 space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Insight Hub</p>
          <h1 className="text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">
            Find insights by topic and geography
          </h1>
          <p className="max-w-3xl text-base text-slate-700">
            Explore curated insights with a fast smart search and cascading location filters.
          </p>
        </header>

        {/* Hero Search (F-pattern emphasis, primary action on right) */}
        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <div className="flex flex-col gap-3 md:flex-row">
            <div className="relative flex-1">
              <label htmlFor="insight-search" className="mb-2 block text-sm font-medium text-slate-800">
                Search insights
              </label>
              <input
                id="insight-search"
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by title, category, or summary"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
                list="insight-autocomplete"
              />
              <datalist id="insight-autocomplete">
                {autocompleteOptions.map((option) => (
                  <option key={option} value={option} />
                ))}
              </datalist>
            </div>

            <button
              type="button"
              onClick={handleSearchClick}
              className="mt-7 inline-flex h-12 items-center justify-center rounded-xl bg-[#007BFF] px-6 font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300 md:mt-auto"
            >
              Search
            </button>
          </div>
        </div>

        {/* Sticky Geographic Filter Bar */}
        <div className="sticky top-0 z-20 mb-8 rounded-2xl border border-slate-200 bg-white/95 p-4 shadow-sm backdrop-blur">
          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="w-full md:w-64">
              <label className="mb-2 block text-sm font-medium text-slate-800">State</label>
              <select
                value={selectedState}
                onChange={(e) => handleStateChange(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              >
                <option value="">All States</option>
                {states.map((state) => (
                  <option key={state} value={state}>
                    {state}
                  </option>
                ))}
              </select>
            </div>

            <div className="w-full md:w-64">
              <label className="mb-2 block text-sm font-medium text-slate-800">City</label>
              <select
                value={selectedCity}
                disabled={!selectedState}
                onChange={(e) => setSelectedCity(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-900 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
              >
                <option value="">{selectedState ? 'All Cities' : 'Select state first'}</option>
                {cities.map((city) => (
                  <option key={city} value={city}>
                    {city}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              onClick={handleReset}
              className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-300 px-5 font-medium text-slate-700 hover:bg-slate-100"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Data Grid */}
        <section aria-label="Filtered insights" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {filteredCards.map((card) => (
            <article key={card.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold text-slate-950">{card.title}</h2>
                <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-800">
                  {card.city}, {card.state}
                </span>
              </div>
              <p className="mb-2 text-sm font-medium text-slate-600">{card.category}</p>
              <p className="text-sm leading-6 text-slate-700">{card.summary}</p>
            </article>
          ))}
        </section>

        {filteredCards.length === 0 && (
          <p className="mt-6 rounded-xl border border-dashed border-slate-300 bg-white p-4 text-slate-700">
            No insights match your current search and location filters.
          </p>
        )}
      </section>
    </main>
  );
}
