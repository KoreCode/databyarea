(function () {
  var INDEX_URL = '/assets/search-index.json';
  var indexPromise = null;
  var FALLBACK_STATES = [
    { slug: 'alabama', name: 'Alabama', abbr: 'AL' },
    { slug: 'alaska', name: 'Alaska', abbr: 'AK' },
    { slug: 'arizona', name: 'Arizona', abbr: 'AZ' },
    { slug: 'arkansas', name: 'Arkansas', abbr: 'AR' },
    { slug: 'california', name: 'California', abbr: 'CA' },
    { slug: 'colorado', name: 'Colorado', abbr: 'CO' },
    { slug: 'connecticut', name: 'Connecticut', abbr: 'CT' },
    { slug: 'delaware', name: 'Delaware', abbr: 'DE' },
    { slug: 'florida', name: 'Florida', abbr: 'FL' },
    { slug: 'georgia', name: 'Georgia', abbr: 'GA' },
    { slug: 'hawaii', name: 'Hawaii', abbr: 'HI' },
    { slug: 'idaho', name: 'Idaho', abbr: 'ID' },
    { slug: 'illinois', name: 'Illinois', abbr: 'IL' },
    { slug: 'indiana', name: 'Indiana', abbr: 'IN' },
    { slug: 'iowa', name: 'Iowa', abbr: 'IA' },
    { slug: 'kansas', name: 'Kansas', abbr: 'KS' },
    { slug: 'kentucky', name: 'Kentucky', abbr: 'KY' },
    { slug: 'louisiana', name: 'Louisiana', abbr: 'LA' },
    { slug: 'maine', name: 'Maine', abbr: 'ME' },
    { slug: 'maryland', name: 'Maryland', abbr: 'MD' },
    { slug: 'massachusetts', name: 'Massachusetts', abbr: 'MA' },
    { slug: 'michigan', name: 'Michigan', abbr: 'MI' },
    { slug: 'minnesota', name: 'Minnesota', abbr: 'MN' },
    { slug: 'mississippi', name: 'Mississippi', abbr: 'MS' },
    { slug: 'missouri', name: 'Missouri', abbr: 'MO' },
    { slug: 'montana', name: 'Montana', abbr: 'MT' },
    { slug: 'nebraska', name: 'Nebraska', abbr: 'NE' },
    { slug: 'nevada', name: 'Nevada', abbr: 'NV' },
    { slug: 'new-hampshire', name: 'New Hampshire', abbr: 'NH' },
    { slug: 'new-jersey', name: 'New Jersey', abbr: 'NJ' },
    { slug: 'new-mexico', name: 'New Mexico', abbr: 'NM' },
    { slug: 'new-york', name: 'New York', abbr: 'NY' },
    { slug: 'north-carolina', name: 'North Carolina', abbr: 'NC' },
    { slug: 'north-dakota', name: 'North Dakota', abbr: 'ND' },
    { slug: 'ohio', name: 'Ohio', abbr: 'OH' },
    { slug: 'oklahoma', name: 'Oklahoma', abbr: 'OK' },
    { slug: 'oregon', name: 'Oregon', abbr: 'OR' },
    { slug: 'pennsylvania', name: 'Pennsylvania', abbr: 'PA' },
    { slug: 'rhode-island', name: 'Rhode Island', abbr: 'RI' },
    { slug: 'south-carolina', name: 'South Carolina', abbr: 'SC' },
    { slug: 'south-dakota', name: 'South Dakota', abbr: 'SD' },
    { slug: 'tennessee', name: 'Tennessee', abbr: 'TN' },
    { slug: 'texas', name: 'Texas', abbr: 'TX' },
    { slug: 'utah', name: 'Utah', abbr: 'UT' },
    { slug: 'vermont', name: 'Vermont', abbr: 'VT' },
    { slug: 'virginia', name: 'Virginia', abbr: 'VA' },
    { slug: 'washington', name: 'Washington', abbr: 'WA' },
    { slug: 'west-virginia', name: 'West Virginia', abbr: 'WV' },
    { slug: 'wisconsin', name: 'Wisconsin', abbr: 'WI' },
    { slug: 'wyoming', name: 'Wyoming', abbr: 'WY' }
  ];

  function loadIndex() {
    if (!indexPromise) {
      indexPromise = fetch(INDEX_URL, { cache: 'force-cache' })
        .then(function (response) {
          if (!response.ok) throw new Error('Search index unavailable');
          return response.json();
        })
        .catch(function () {
          return { states: FALLBACK_STATES, items: [] };
        });
    }
    return indexPromise.then(function (data) {
      if (!data.states || !data.states.length) data.states = FALLBACK_STATES;
      if (!data.items) data.items = [];
      return data;
    });
  }

  function normalize(value) {
    return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function itemText(item) {
    return normalize([item.title, item.type, item.category, item.state_name, item.state_abbr, item.city].concat(item.aliases || []).join(' '));
  }

  function titleCaseSlug(slug) {
    return String(slug || '').split('-').filter(Boolean).map(function (part) {
      return part.charAt(0).toUpperCase() + part.slice(1);
    }).join(' ');
  }

  function knownInsightCategory(value) {
    return ['cost-of-living', 'utility-costs', 'property-taxes', 'insurance-costs'].indexOf(value) !== -1 ? value : '';
  }

  function inputCategory(input) {
    var explicit = knownInsightCategory(input.getAttribute('data-dba-category'));
    if (explicit) return explicit;
    var firstSegment = (window.location.pathname || '').split('/').filter(Boolean)[0] || '';
    return knownInsightCategory(firstSegment);
  }

  function buildItemLookup(items) {
    var lookup = {};
    items.forEach(function (item) {
      if (!item.category || !item.state) return;
      var key = item.category + '|' + item.state + '|' + (item.city || '');
      lookup[key] = item;
    });
    return lookup;
  }

  function stateUrl(state, category, lookup) {
    if (category) {
      var categoryItem = lookup[category + '|' + state.slug + '|'];
      return categoryItem && categoryItem.url ? categoryItem.url : '/' + category + '/' + state.slug + '/';
    }
    var profile = lookup['state|' + state.slug + '|'];
    return profile && profile.url ? profile.url : '/' + state.slug + '/';
  }

  function cityUrl(item, category, lookup) {
    if (category) {
      var categoryItem = lookup[category + '|' + item.state + '|' + item.city];
      if (categoryItem && categoryItem.url) return categoryItem.url;
    }
    return item.url;
  }

  function buildPlaceSuggestions(data, input) {
    var category = inputCategory(input);
    var stateFilter = input.getAttribute('data-dba-state') || '';
    var typeFilter = input.getAttribute('data-dba-type') || '';
    var lookup = buildItemLookup(data.items || []);
    var suggestions = [];
    var seen = {};

    (data.states || FALLBACK_STATES).forEach(function (state) {
      if (stateFilter && state.slug !== stateFilter) return;
      if (typeFilter && typeFilter !== 'State profile') return;
      var suggestion = {
        label: state.name,
        url: stateUrl(state, category, lookup),
        kind: 'State',
        state: state.slug,
        aliases: [state.name, state.abbr, state.slug]
      };
      seen['state|' + state.slug] = true;
      suggestions.push(suggestion);
    });

    (data.items || []).filter(function (item) {
      return item.category === 'city-dashboard' && item.city && item.url;
    }).forEach(function (item) {
      if (stateFilter && item.state !== stateFilter) return;
      if (typeFilter && typeFilter !== 'City profile') return;
      var key = 'city|' + item.state + '|' + item.city;
      if (seen[key]) return;
      seen[key] = true;
      suggestions.push({
        label: cityLabel(item),
        url: cityUrl(item, category, lookup),
        kind: 'City',
        state: item.state,
        city: item.city,
        aliases: [item.title, item.city, titleCaseSlug(item.city), titleCaseSlug(item.city) + ' ' + item.state_name, titleCaseSlug(item.city) + ' ' + item.state_abbr].concat(item.aliases || [])
      });
    });

    return suggestions;
  }

  function score(item, query) {
    var title = normalize(item.title);
    var text = itemText(item);
    if (!query) return 0;
    if (title === query) return 1000;
    if ((item.aliases || []).some(function (alias) { return normalize(alias) === query; })) return 950;
    if (title.indexOf(query) === 0) return 800;
    if (text.indexOf(query) === 0) return 650;
    if (text.indexOf(query) !== -1) return 450;
    return query.split(' ').filter(function (part) { return part && text.indexOf(part) !== -1; }).length * 100;
  }

  function findExact(items, value) {
    var query = normalize(value);
    if (!query) return null;
    return items.find(function (item) {
      return normalize(item.title) === query || (item.aliases || []).some(function (alias) {
        return normalize(alias) === query;
      });
    }) || null;
  }

  function suggestionText(suggestion) {
    return normalize([suggestion.label, suggestion.kind, suggestion.state, suggestion.city].concat(suggestion.aliases || []).join(' '));
  }

  function scoreSuggestion(suggestion, query) {
    var label = normalize(suggestion.label);
    var text = suggestionText(suggestion);
    if (!query) return 0;
    if (label === query) return 1200;
    if ((suggestion.aliases || []).some(function (alias) { return normalize(alias) === query; })) return 1150;
    if (label.indexOf(query) === 0) return 850;
    if (text.indexOf(query) === 0) return 700;
    if (text.indexOf(query) !== -1) return 500;
    return query.split(' ').filter(function (part) { return part && text.indexOf(part) !== -1; }).length * 100;
  }

  function findExactSuggestion(suggestions, value) {
    var query = normalize(value);
    if (!query) return null;
    return suggestions.find(function (suggestion) {
      return normalize(suggestion.label) === query || (suggestion.aliases || []).some(function (alias) {
        return normalize(alias) === query;
      });
    }) || null;
  }

  function matchesFilters(item, input) {
    var category = input.getAttribute('data-dba-category');
    var state = input.getAttribute('data-dba-state');
    var type = input.getAttribute('data-dba-type');
    if (category && item.category !== category) return false;
    if (state && item.state !== state) return false;
    if (type && item.type !== type) return false;
    return true;
  }

  function attachAutocomplete(input, data) {
    if (input.dataset.dbaAutocompleteReady === '1') return;
    input.dataset.dbaAutocompleteReady = '1';

    var listId = input.getAttribute('list') || ('dba-suggestions-' + Math.random().toString(36).slice(2));
    var datalist = document.getElementById(listId);
    if (!datalist) {
      datalist = document.createElement('datalist');
      datalist.id = listId;
      input.insertAdjacentElement('afterend', datalist);
      input.setAttribute('list', listId);
    }

    function render() {
      var query = normalize(input.value);
      var suggestions = buildPlaceSuggestions(data, input);
      datalist.innerHTML = '';
      if (!query) return;
      suggestions
        .map(function (suggestion) { return Object.assign({ _score: scoreSuggestion(suggestion, query) }, suggestion); })
        .filter(function (suggestion) { return suggestion._score > 0; })
        .sort(function (a, b) { return b._score - a._score || a.label.localeCompare(b.label); })
        .slice(0, Number(input.getAttribute('data-dba-max-suggestions')) || 10)
        .forEach(function (suggestion) {
          var option = document.createElement('option');
          option.value = suggestion.label;
          option.setAttribute('data-url', suggestion.url);
          option.setAttribute('data-kind', suggestion.kind);
          datalist.appendChild(option);
        });
    }

    input.addEventListener('input', render);
    input.addEventListener('focus', render);
  }

  function bindSearchForms(data) {
    document.querySelectorAll('form[data-dba-search-form]').forEach(function (form) {
      if (form.dataset.dbaSearchReady === '1') return;
      form.dataset.dbaSearchReady = '1';
      form.addEventListener('submit', function (event) {
        var input = form.querySelector('[data-dba-autocomplete]');
        if (!input) return;
        var exact = findExactSuggestion(buildPlaceSuggestions(data, input), input.value);
        if (exact && exact.url) {
          event.preventDefault();
          event.stopImmediatePropagation();
          window.location.href = exact.url;
        }
      }, true);
    });
  }

  function populateStateSelects(data) {
    document.querySelectorAll('select[data-dba-state-select]').forEach(function (select) {
      if (select.dataset.dbaSelectReady === '1') return;
      select.dataset.dbaSelectReady = '1';
      var category = select.getAttribute('data-dba-category') || 'cost-of-living';
      var current = select.getAttribute('data-current-state') || '';
      var first = select.querySelector('option[value=""]');
      select.innerHTML = '';
      select.appendChild(first || new Option('Choose a state...', ''));
      data.states.forEach(function (state) {
        var option = new Option(state.name, '/' + category + '/' + state.slug + '/');
        if (state.slug === current) option.selected = true;
        select.appendChild(option);
      });
    });
  }

  function cityLabel(item) {
    if (item.type === 'City profile') return item.title;
    return item.title
      .replace(/ cost of living$/i, '')
      .replace(/ utility costs$/i, '')
      .replace(/ property taxes$/i, '')
      .replace(/ insurance costs$/i, '');
  }

  function populateCitySelects(data) {
    document.querySelectorAll('select[data-dba-city-select]').forEach(function (select) {
      if (select.dataset.dbaSelectReady === '1') return;
      select.dataset.dbaSelectReady = '1';
      var state = select.getAttribute('data-dba-state') || 'minnesota';
      var category = select.getAttribute('data-dba-category') || 'city-dashboard';
      var includeFallback = select.getAttribute('data-dba-include-dashboard-fallback') !== 'false';
      var first = select.querySelector('option[value=""]');
      var cityMap = {};

      data.items
        .filter(function (item) { return item.state === state && item.city && item.category === category; })
        .forEach(function (item) { cityMap[item.city] = item; });

      if (includeFallback && category !== 'city-dashboard') {
        data.items
          .filter(function (item) { return item.state === state && item.city && item.category === 'city-dashboard'; })
          .forEach(function (item) {
            if (!cityMap[item.city]) cityMap[item.city] = item;
          });
      }

      var cities = Object.keys(cityMap).map(function (key) { return cityMap[key]; })
        .sort(function (a, b) { return cityLabel(a).localeCompare(cityLabel(b)); });

      select.innerHTML = '';
      select.appendChild(first || new Option('Choose a city page...', ''));
      cities.forEach(function (item) {
        select.appendChild(new Option(cityLabel(item), item.url));
      });
    });
  }

  function populateStateLinkGrids(data) {
    document.querySelectorAll('[data-state-link-grid]').forEach(function (grid) {
      if (grid.dataset.dbaStateGridReady === '1') return;
      grid.dataset.dbaStateGridReady = '1';
      var category = grid.getAttribute('data-state-link-grid') || 'cost-of-living';
      grid.innerHTML = '';
      data.states.forEach(function (state) {
        var link = document.createElement('a');
        link.href = '/' + category + '/' + state.slug + '/';
        link.textContent = state.name;
        grid.appendChild(link);
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadIndex().then(function (data) {
      document.querySelectorAll('[data-dba-autocomplete]').forEach(function (input) {
        attachAutocomplete(input, data);
      });
      bindSearchForms(data);
      populateStateSelects(data);
      populateCitySelects(data);
      populateStateLinkGrids(data);
    });
  });
})();
