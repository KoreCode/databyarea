(function () {
  function buildExplorerMarkup() {
    return `
      <h2 class="sectionTitle compactTop">Regional data explorer preview</h2>
      <section class="explorer" aria-label="Interactive regional data explorer" data-sitewide-explorer="true">
        <div class="explorer-topbar">
          <p class="explorer-current" data-explorer-current>Selected region: California</p>
          <button class="btn filter-btn" type="button" aria-controls="filter-drawer-global" aria-expanded="false" data-filter-toggle>Filters</button>
        </div>
        <div class="filter-ribbon" id="filter-drawer-global">
          <label>Date Range
            <select aria-label="Date range">
              <option>Last 12 months</option>
              <option>Last 24 months</option>
              <option>Last 5 years</option>
            </select>
          </label>
          <label>Region Level
            <select aria-label="Region level">
              <option>State</option>
              <option>County</option>
              <option>City</option>
            </select>
          </label>
          <label>Metric Type
            <select aria-label="Metric type">
              <option>Cost Index</option>
              <option>Utility Spend</option>
              <option>Insurance Costs</option>
            </select>
          </label>
        </div>
        <div class="summary-cards" aria-label="Key metrics">
          <article class="summary-card">
            <p class="summary-label">Regional Cost Index</p>
            <p class="summary-value" data-kpi-index>112</p>
            <p class="summary-note">+4.5% year over year</p>
          </article>
          <article class="summary-card">
            <p class="summary-label">Avg Household Utilities</p>
            <p class="summary-value" data-kpi-utilities>$319</p>
            <p class="summary-note">Monthly estimate</p>
          </article>
          <article class="summary-card">
            <p class="summary-label">Compared to U.S. Avg</p>
            <p class="summary-value" data-kpi-benchmark>+8%</p>
            <p class="summary-note">Benchmark delta</p>
          </article>
        </div>
        <div class="explorer-main">
          <article class="map-panel card" aria-label="Region selector">
            <h3>Select a region</h3>
            <p class="mutedSmall">Color is paired with labels and patterns to remain accessible.</p>
            <div class="region-map" role="list" aria-label="Available regions">
              <button type="button" class="region-node active" data-region="california" aria-pressed="true">California</button>
              <button type="button" class="region-node" data-region="texas" aria-pressed="false">Texas</button>
              <button type="button" class="region-node" data-region="florida" aria-pressed="false">Florida</button>
            </div>
          </article>
          <article class="chart-panel card" aria-label="Metric comparison chart">
            <h3>Metric snapshot</h3>
            <p class="mutedSmall">Patterned bars indicate category values.</p>
            <div class="bars" role="img" aria-label="Bar chart comparing housing, utilities, and insurance values by region">
              <div class="bar-row"><span>Housing</span><div class="bar pattern-a" data-bar-housing style="width:78%">78</div></div>
              <div class="bar-row"><span>Utilities</span><div class="bar pattern-b" data-bar-utilities style="width:64%">64</div></div>
              <div class="bar-row"><span>Insurance</span><div class="bar pattern-c" data-bar-insurance style="width:58%">58</div></div>
            </div>
          </article>
        </div>
        <article class="table-panel card" aria-label="Tabular metric fallback">
          <h3>Accessible data table</h3>
          <table>
            <caption class="mutedSmall">Current metrics for selected region</caption>
            <thead>
              <tr><th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Delta vs U.S.</th></tr>
            </thead>
            <tbody data-explorer-table-body>
              <tr><th scope="row">Cost Index</th><td>112</td><td>+8%</td></tr>
              <tr><th scope="row">Monthly Utilities</th><td>$319</td><td>+6%</td></tr>
              <tr><th scope="row">Insurance Cost Index</th><td>108</td><td>+5%</td></tr>
            </tbody>
          </table>
        </article>
      </section>
    `;
  }

  function regionDataByPage() {
    var path = window.location.pathname;
    if (path.indexOf('/utility-costs/') === 0) {
      return {
        california: { label: 'California', kpiIndex: '104', kpiUtilities: '$312', kpiBenchmark: '+9%', bars: { housing: '59', utilities: '79', insurance: '54' }, rows: [['Cost Index', '104', '+9%'], ['Monthly Utilities', '$312', '+11%'], ['Insurance Cost Index', '102', '+2%']] },
        texas: { label: 'Texas', kpiIndex: '96', kpiUtilities: '$274', kpiBenchmark: '-2%', bars: { housing: '55', utilities: '63', insurance: '47' }, rows: [['Cost Index', '96', '-2%'], ['Monthly Utilities', '$274', '-3%'], ['Insurance Cost Index', '93', '-5%']] },
        florida: { label: 'Florida', kpiIndex: '101', kpiUtilities: '$295', kpiBenchmark: '+4%', bars: { housing: '57', utilities: '71', insurance: '64' }, rows: [['Cost Index', '101', '+4%'], ['Monthly Utilities', '$295', '+5%'], ['Insurance Cost Index', '110', '+8%']] }
      };
    }
    if (path.indexOf('/insurance-costs/') === 0) {
      return {
        california: { label: 'California', kpiIndex: '109', kpiUtilities: '$319', kpiBenchmark: '+7%', bars: { housing: '74', utilities: '58', insurance: '73' }, rows: [['Cost Index', '109', '+7%'], ['Monthly Utilities', '$319', '+6%'], ['Insurance Cost Index', '116', '+12%']] },
        texas: { label: 'Texas', kpiIndex: '98', kpiUtilities: '$276', kpiBenchmark: '-1%', bars: { housing: '62', utilities: '55', insurance: '60' }, rows: [['Cost Index', '98', '-1%'], ['Monthly Utilities', '$276', '-2%'], ['Insurance Cost Index', '101', '+1%']] },
        florida: { label: 'Florida', kpiIndex: '106', kpiUtilities: '$301', kpiBenchmark: '+3%', bars: { housing: '69', utilities: '61', insurance: '78' }, rows: [['Cost Index', '106', '+3%'], ['Monthly Utilities', '$301', '+3%'], ['Insurance Cost Index', '121', '+15%']] }
      };
    }
    return {
      california: { label: 'California', kpiIndex: '112', kpiUtilities: '$319', kpiBenchmark: '+8%', bars: { housing: '78', utilities: '64', insurance: '58' }, rows: [['Cost Index', '112', '+8%'], ['Monthly Utilities', '$319', '+6%'], ['Insurance Cost Index', '108', '+5%']] },
      texas: { label: 'Texas', kpiIndex: '97', kpiUtilities: '$276', kpiBenchmark: '-3%', bars: { housing: '62', utilities: '55', insurance: '49' }, rows: [['Cost Index', '97', '-3%'], ['Monthly Utilities', '$276', '-2%'], ['Insurance Cost Index', '95', '-4%']] },
      florida: { label: 'Florida', kpiIndex: '104', kpiUtilities: '$301', kpiBenchmark: '+2%', bars: { housing: '71', utilities: '61', insurance: '66' }, rows: [['Cost Index', '104', '+2%'], ['Monthly Utilities', '$301', '+3%'], ['Insurance Cost Index', '113', '+9%']] }
    };
  }

  function initExplorer() {
    if (!document.body || document.querySelector('.explorer')) return;
    var container = document.querySelector('.container');
    var footer = document.querySelector('.footer');
    if (!container || !footer) return;
    footer.insertAdjacentHTML('beforebegin', buildExplorerMarkup());

    var explorer = container.querySelector('[data-sitewide-explorer="true"]');
    if (!explorer) return;
    var data = regionDataByPage();
    var nodes = explorer.querySelectorAll('.region-node');
    var tableBody = explorer.querySelector('[data-explorer-table-body]');
    var current = explorer.querySelector('[data-explorer-current]');
    var barHousing = explorer.querySelector('[data-bar-housing]');
    var barUtilities = explorer.querySelector('[data-bar-utilities]');
    var barInsurance = explorer.querySelector('[data-bar-insurance]');
    var kpiIndex = explorer.querySelector('[data-kpi-index]');
    var kpiUtilities = explorer.querySelector('[data-kpi-utilities]');
    var kpiBenchmark = explorer.querySelector('[data-kpi-benchmark]');
    var filterToggle = explorer.querySelector('[data-filter-toggle]');
    var filterDrawer = explorer.querySelector('#filter-drawer-global');

    function updateRegion(key) {
      var selected = data[key];
      if (!selected) return;
      kpiIndex.textContent = selected.kpiIndex;
      kpiUtilities.textContent = selected.kpiUtilities;
      kpiBenchmark.textContent = selected.kpiBenchmark;
      current.textContent = 'Selected region: ' + selected.label;
      barHousing.style.width = selected.bars.housing + '%';
      barHousing.textContent = selected.bars.housing;
      barUtilities.style.width = selected.bars.utilities + '%';
      barUtilities.textContent = selected.bars.utilities;
      barInsurance.style.width = selected.bars.insurance + '%';
      barInsurance.textContent = selected.bars.insurance;
      tableBody.innerHTML = selected.rows.map(function (row) {
        return '<tr><th scope="row">' + row[0] + '</th><td>' + row[1] + '</td><td>' + row[2] + '</td></tr>';
      }).join('');
      nodes.forEach(function (node) {
        var active = node.dataset.region === key;
        node.classList.toggle('active', active);
        node.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
    }

    nodes.forEach(function (node) {
      node.addEventListener('click', function () {
        updateRegion(node.dataset.region);
      });
    });
    filterToggle.addEventListener('click', function () {
      var expanded = filterToggle.getAttribute('aria-expanded') === 'true';
      filterToggle.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      filterDrawer.classList.toggle('open', !expanded);
    });
  }

  initExplorer();

  const root = document.createElement('div');
  root.id = 'site-version-footer';
  root.style.cssText = 'position:fixed;bottom:8px;right:8px;background:#111;color:#fff;font:12px/1.2 Arial,sans-serif;padding:6px 8px;border-radius:8px;opacity:.82;z-index:99999';

  fetch('/assets/site-version.json', { cache: 'no-store' })
    .then((r) => (r.ok ? r.json() : null))
    .then((v) => {
      if (!v) return;
      root.textContent = `v ${v.commit_short || 'unknown'} · ${v.updated_utc || ''}`;
      document.body.appendChild(root);
    })
    .catch(() => {});
})();
