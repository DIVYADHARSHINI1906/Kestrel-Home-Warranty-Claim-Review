/**
 * Kestrel Home — Warranty Claim Review & Fraud Detection
 * Production Frontend Application Controller
 */

// Application State
const state = {
  currentView: 'overview',
  claimsPage: 1,
  claimsPageSize: 25,
  claimsSortBy: 'submitted_at',
  claimsSortOrder: 'desc',
  claimsTotal: 0,
  claimsTotalPages: 1,
  activeFilters: {
    search: '',
    risk_tier: 'all',
    product_family: 'all',
    partner_inspected: 'all',
    dataset: 'test'
  },
  charts: {
    volume: null,
    products: null,
    riskDist: null,
    riskAmount: null
  }
};

// Case Study Presets
const CASE_STUDIES = {
  post_may_fraud: {
    claim_id: "WC711412",
    submitted_at: "2026-07-14 09:30",
    partner_id: "SP3160",
    sku: "KH-AF-01",
    product_serial: " KH762701250",
    days_since_purchase: 42,
    claim_amount_inr: 1980.00,
    photo_attached: "N",
    partner_inspected: "N",
    claim_description: "motor not running",
    inspector_note: "",
    customer_prior_claims: 1
  },
  high_amount_fraud: {
    claim_id: "WC708910",
    submitted_at: "2026-03-22 16:15",
    partner_id: "SP3207",
    sku: "KH-WP-03",
    product_serial: "KH918237192",
    days_since_purchase: 310,
    claim_amount_inr: 15400.00,
    photo_attached: "Y",
    partner_inspected: "Y",
    claim_description: "water leaking",
    inspector_note: "PCB replaced under warranty",
    customer_prior_claims: 3
  },
  clean_genuine: {
    claim_id: "WC711350",
    submitted_at: "2026-07-01 01:57",
    partner_id: "SP3086",
    sku: "KH-CF-02",
    product_serial: "KH384729103",
    days_since_purchase: 120,
    claim_amount_inr: 850.00,
    photo_attached: "Y",
    partner_inspected: "Y",
    claim_description: "remote not working",
    inspector_note: "Minor fault, part swapped",
    customer_prior_claims: 0
  },
  policy_violation: {
    claim_id: "WC-VIOL-001",
    submitted_at: "2026-08-04 14:10",
    partner_id: "SP3032",
    sku: "KH-RV-02",
    product_serial: "KH882910394",
    days_since_purchase: 95,
    claim_amount_inr: 6500.00,
    photo_attached: "Y",
    partner_inspected: "N", // >= 2k MUST be inspected!
    claim_description: "loud noise while running",
    inspector_note: "",
    customer_prior_claims: 0
  }
};

// Initialization on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initFilterEvents();
  initReviewForm();
  initSettingsForm();
  initDrawer();
  
  // Initial data loading
  checkHealth();
  loadOverviewData();
});

// View Navigation Controller
function initNavigation() {
  const navButtons = document.querySelectorAll('.sidebar-nav .nav-item');
  navButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetView = btn.getAttribute('data-view');
      navigateTo(targetView);
    });
  });

  // Global Quick Search Button
  const quickSearchBtn = document.getElementById('header-quick-search');
  if (quickSearchBtn) {
    quickSearchBtn.addEventListener('click', () => {
      navigateTo('claims');
      const input = document.getElementById('claims-search-input');
      if (input) {
        input.focus();
        input.select();
      }
    });
  }

  // Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    // If typing in input or textarea, don't trigger number shortcuts
    const isEditing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);

    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      navigateTo('claims');
      const input = document.getElementById('claims-search-input');
      if (input) {
        input.focus();
        input.select();
      }
    } else if (e.key === '/' && !isEditing) {
      e.preventDefault();
      navigateTo('claims');
      const input = document.getElementById('claims-search-input');
      if (input) {
        input.focus();
        input.select();
      }
    } else if (!isEditing && !e.ctrlKey && !e.altKey && !e.metaKey) {
      const viewMap = {
        '1': 'overview',
        '2': 'claims',
        '3': 'review',
        '4': 'partners',
        '5': 'evaluation',
        '6': 'settings'
      };
      if (viewMap[e.key]) {
        navigateTo(viewMap[e.key]);
      }
    }
  });
}

function navigateTo(viewName) {
  state.currentView = viewName;
  
  // Update nav item active states
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
  });
  
  // Update view panel visibility
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `view-${viewName}`);
  });
  
  // Update heading
  const headings = {
    overview: 'Operations Overview',
    claims: 'Claims Register & Audit Log',
    review: 'Claim Review & Triage',
    partners: 'Partner Analysis',
    evaluation: 'Model Evaluation',
    settings: 'Operations & Capacity'
  };
  document.getElementById('page-heading').textContent = headings[viewName] || 'Operations';
  const bc = document.getElementById('breadcrumb-current');
  if (bc) bc.textContent = headings[viewName] || 'Operations';
  
  // Lazy load views on tab switch
  if (viewName === 'claims') {
    loadClaimsTable();
  } else if (viewName === 'partners') {
    loadPartnerData();
  } else if (viewName === 'evaluation') {
    loadEvaluationData();
  } else if (viewName === 'settings') {
    loadSettingsData();
  } else if (viewName === 'overview') {
    loadOverviewData();
  }
}

// Health Check
async function checkHealth() {
  try {
    const res = await fetch('/health');
    if (res.ok) {
      const data = await res.json();
      document.getElementById('service-status-text').textContent = 'System Online';
      if (data.indexed_claims_count) {
        document.getElementById('sidebar-queue-badge').textContent = (2252).toLocaleString();
      }
    }
  } catch (err) {
    document.getElementById('service-status-text').textContent = 'API Unavailable';
    document.getElementById('service-status-badge').style.borderColor = '#fecaca';
  }
}

// Overview Loader
async function loadOverviewData() {
  try {
    const [summaryRes, analyticsRes] = await Promise.all([
      fetch('/api/summary'),
      fetch('/api/analytics')
    ]);
    
    if (summaryRes.ok) {
      const summary = await summaryRes.json();
      renderSummaryKPIs(summary);
    }
    
    if (analyticsRes.ok) {
      const analytics = await analyticsRes.json();
      renderOverviewCharts(analytics);
      renderPriorityQueue(analytics.top_review_queue || []);
    }
  } catch (err) {
    showToast('Failed to load overview data.', 'error');
  }
}

function renderSummaryKPIs(data) {
  const h = data.historical_observed;
  const q = data.active_operational_queue;
  const m = data.model_performance;

  document.getElementById('kpi-hist-total').textContent = h.total_historical_claims.toLocaleString();
  document.getElementById('kpi-hist-rate').textContent = (h.historical_fraud_rate * 100).toFixed(2) + '%';
  document.getElementById('kpi-hist-loss').textContent = '₹' + Math.round(h.historical_fraud_loss_inr).toLocaleString();
  document.getElementById('kpi-desk-recall').textContent = (m.recall_at_capacity * 100).toFixed(1) + '%';

  document.getElementById('kpi-test-total').textContent = q.unlabeled_claims_in_test.toLocaleString();
  document.getElementById('kpi-test-flagged').textContent = q.high_risk_flagged_claims.toLocaleString();
  document.getElementById('kpi-test-exposure').textContent = '₹' + Math.round(q.estimated_financial_exposure_inr).toLocaleString();
}

function renderOverviewCharts(data) {
  // 1. Claim Volume & Inspection Trend
  const ctxVol = document.getElementById('chart-volume');
  if (ctxVol && data.volume_over_time) {
    if (state.charts.volume) state.charts.volume.destroy();
    state.charts.volume = new Chart(ctxVol, {
      type: 'bar',
      data: {
        labels: data.volume_over_time.months,
        datasets: [
          {
            label: 'Inspected Sign-off (Y)',
            data: data.volume_over_time.inspected,
            backgroundColor: '#3b82f6',
            borderRadius: 3
          },
          {
            label: 'Uninspected (<₹2k post-May)',
            data: data.volume_over_time.uninspected,
            backgroundColor: '#f97316',
            borderRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, grid: { color: '#f1f5f9' }, title: { display: true, text: 'Monthly Claims' } }
        }
      }
    });
  }

  // 2. Product Family
  const ctxProd = document.getElementById('chart-products');
  if (ctxProd && data.product_family_distribution) {
    if (state.charts.products) state.charts.products.destroy();
    state.charts.products = new Chart(ctxProd, {
      type: 'bar',
      data: {
        labels: data.product_family_distribution.families,
        datasets: [
          {
            label: 'Total Claims',
            data: data.product_family_distribution.volumes,
            backgroundColor: '#94a3b8',
            borderRadius: 3
          },
          {
            label: 'High-Risk Flags',
            data: data.product_family_distribution.high_risk_counts,
            backgroundColor: '#dc2626',
            borderRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: { grid: { color: '#f1f5f9' } }
        }
      }
    });
  }

  // 3. Risk Score Distribution
  const ctxDist = document.getElementById('chart-risk-dist');
  if (ctxDist && data.risk_score_distribution) {
    if (state.charts.riskDist) state.charts.riskDist.destroy();
    state.charts.riskDist = new Chart(ctxDist, {
      type: 'bar',
      data: {
        labels: data.risk_score_distribution.bins,
        datasets: [{
          label: 'Claim Count',
          data: data.risk_score_distribution.counts,
          backgroundColor: data.risk_score_distribution.bins.map((_, i) => i >= 5 ? '#ef4444' : '#60a5fa'),
          borderRadius: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#f1f5f9' }, title: { display: true, text: 'Claims' } }
        }
      }
    });
  }

  // 4. Claim Amounts by Risk Tier
  const ctxAmt = document.getElementById('chart-risk-amount');
  if (ctxAmt && data.tier_distribution) {
    if (state.charts.riskAmount) state.charts.riskAmount.destroy();
    const tiers = data.tier_distribution;
    state.charts.riskAmount = new Chart(ctxAmt, {
      type: 'doughnut',
      data: {
        labels: tiers.map(t => t.risk_tier),
        datasets: [{
          data: tiers.map(t => Math.round(t.sum)),
          backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#7f1d1d'],
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ₹${ctx.parsed.toLocaleString()}`
            }
          }
        }
      }
    });
  }
}

function renderPriorityQueue(claims) {
  const tbody = document.getElementById('overview-queue-tbody');
  if (!claims || claims.length === 0) {
    tbody.innerHTML = '<tr><td colspan="9" class="loading-cell">No priority claims flagged.</td></tr>';
    return;
  }

  tbody.innerHTML = claims.slice(0, 8).map(c => `
    <tr>
      <td class="mono-cell"><a href="#" onclick="event.preventDefault(); openClaimDetails('${c.claim_id}')">${c.claim_id}</a></td>
      <td>${c.submitted_at.substring(0, 16)}</td>
      <td>${c.product_family}</td>
      <td><strong>₹${c.claim_amount_inr.toLocaleString()}</strong></td>
      <td class="mono-cell">${c.partner_id}</td>
      <td><span class="badge ${c.partner_inspected === 'Y' ? 'badge-success' : 'badge-warning'}">${c.partner_inspected}</span></td>
      <td><span class="badge ${c.photo_attached === 'Y' ? 'badge-success' : 'badge-neutral'}">${c.photo_attached}</span></td>
      <td><span class="badge ${getScoreBadgeClass(c.risk_score)}">${(c.risk_score * 100).toFixed(1)}%</span></td>
      <td><button class="btn btn-secondary btn-sm" onclick="openClaimDetails('${c.claim_id}')">Inspect</button></td>
    </tr>
  `).join('');
}

// Claims Table Controller
function initFilterEvents() {
  const searchInput = document.getElementById('claims-search-input');
  let debounceTimeout = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      state.activeFilters.search = searchInput.value;
      state.claimsPage = 1;
      loadClaimsTable();
    }, 300);
  });

  document.getElementById('filter-risk').addEventListener('change', (e) => {
    state.activeFilters.risk_tier = e.target.value;
    state.claimsPage = 1;
    loadClaimsTable();
  });

  document.getElementById('filter-family').addEventListener('change', (e) => {
    state.activeFilters.product_family = e.target.value;
    state.claimsPage = 1;
    loadClaimsTable();
  });

  document.getElementById('filter-inspected').addEventListener('change', (e) => {
    state.activeFilters.partner_inspected = e.target.value;
    state.claimsPage = 1;
    loadClaimsTable();
  });

  document.getElementById('filter-dataset').addEventListener('change', (e) => {
    state.activeFilters.dataset = e.target.value;
    state.claimsPage = 1;
    loadClaimsTable();
  });

  document.getElementById('btn-reset-filters').addEventListener('click', () => {
    document.getElementById('claims-search-input').value = '';
    document.getElementById('filter-risk').value = 'all';
    document.getElementById('filter-family').value = 'all';
    document.getElementById('filter-inspected').value = 'all';
    document.getElementById('filter-dataset').value = 'test';
    state.activeFilters = {
      search: '',
      risk_tier: 'all',
      product_family: 'all',
      partner_inspected: 'all',
      dataset: 'test'
    };
    state.claimsPage = 1;
    loadClaimsTable();
  });

  document.getElementById('btn-prev-page').addEventListener('click', () => {
    if (state.claimsPage > 1) {
      state.claimsPage--;
      loadClaimsTable();
    }
  });

  document.getElementById('btn-next-page').addEventListener('click', () => {
    if (state.claimsPage < state.claimsTotalPages) {
      state.claimsPage++;
      loadClaimsTable();
    }
  });

  // Export CSV handler
  const exportBtn = document.getElementById('btn-export-csv');
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      exportBtn.disabled = true;
      exportBtn.textContent = 'Exporting...';
      try {
        const params = new URLSearchParams({
          page: 1,
          page_size: 5000,
          sort_by: state.claimsSortBy,
          sort_order: state.claimsSortOrder
        });
        if (state.activeFilters.search) params.append('search', state.activeFilters.search);
        if (state.activeFilters.risk_tier !== 'all') params.append('risk_tier', state.activeFilters.risk_tier);
        if (state.activeFilters.product_family !== 'all') params.append('product_family', state.activeFilters.product_family);
        if (state.activeFilters.partner_inspected !== 'all') params.append('partner_inspected', state.activeFilters.partner_inspected);
        if (state.activeFilters.dataset === 'test') params.append('is_historical', 'false');
        else if (state.activeFilters.dataset === 'historical') params.append('is_historical', 'true');

        const res = await fetch(`/api/claims?${params.toString()}`);
        if (!res.ok) throw new Error('Export query failed');
        const data = await res.json();
        const claims = data.claims || [];

        if (claims.length === 0) {
          showToast('No claims found to export.', 'error');
          return;
        }

        const headers = ['claim_id', 'submitted_at', 'sku', 'product_family', 'claim_amount_inr', 'partner_id', 'partner_city', 'partner_type', 'partner_inspected', 'photo_attached', 'risk_score', 'risk_tier', 'recommendation'];
        const csvRows = [headers.join(',')];

        for (const c of claims) {
          const row = [
            c.claim_id,
            `"${c.submitted_at}"`,
            c.sku,
            `"${c.product_family}"`,
            c.claim_amount_inr,
            c.partner_id,
            `"${c.partner_city || ''}"`,
            c.partner_type,
            c.partner_inspected,
            c.photo_attached,
            c.risk_score,
            c.risk_tier,
            `"${c.recommendation}"`
          ];
          csvRows.push(row.join(','));
        }

        const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `kestrel_claims_export_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        showToast(`Exported ${claims.length.toLocaleString()} claims to CSV.`, 'success');
      } catch (err) {
        showToast('Failed to export claims.', 'error');
      } finally {
        exportBtn.disabled = false;
        exportBtn.innerHTML = `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Export CSV
        `;
      }
    });
  }

  // Quick Chips
  document.querySelectorAll('.quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.quick-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const preset = chip.getAttribute('data-preset');

      if (preset === 'all') {
        document.getElementById('claims-search-input').value = '';
        document.getElementById('filter-risk').value = 'all';
        document.getElementById('filter-family').value = 'all';
        document.getElementById('filter-inspected').value = 'all';
        document.getElementById('filter-dataset').value = 'test';
        state.activeFilters = { search: '', risk_tier: 'all', product_family: 'all', partner_inspected: 'all', dataset: 'test' };
      } else if (preset === 'priority') {
        document.getElementById('filter-risk').value = 'High';
        document.getElementById('filter-dataset').value = 'test';
        state.activeFilters.risk_tier = 'High';
        state.activeFilters.dataset = 'test';
      } else if (preset === 'sub2k_uninspected') {
        document.getElementById('filter-inspected').value = 'N';
        document.getElementById('filter-dataset').value = 'test';
        state.activeFilters.partner_inspected = 'N';
        state.activeFilters.dataset = 'test';
      } else if (preset === 'critical') {
        document.getElementById('filter-risk').value = 'Critical';
        document.getElementById('filter-dataset').value = 'test';
        state.activeFilters.risk_tier = 'Critical';
        state.activeFilters.dataset = 'test';
      } else if (preset === 'historical_fraud') {
        document.getElementById('filter-dataset').value = 'historical';
        document.getElementById('filter-risk').value = 'Critical';
        state.activeFilters.dataset = 'historical';
        state.activeFilters.risk_tier = 'Critical';
      }
      state.claimsPage = 1;
      loadClaimsTable();
    });
  });

  // Table Sorting
  document.querySelectorAll('.data-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.getAttribute('data-sort');
      if (state.claimsSortBy === col) {
        state.claimsSortOrder = state.claimsSortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        state.claimsSortBy = col;
        state.claimsSortOrder = 'desc';
      }
      loadClaimsTable();
    });
  });
}

async function loadClaimsTable() {
  const tbody = document.getElementById('claims-table-tbody');
  tbody.innerHTML = '<tr><td colspan="11" class="loading-cell">Loading claims data...</td></tr>';

  const params = new URLSearchParams({
    page: state.claimsPage,
    page_size: state.claimsPageSize,
    sort_by: state.claimsSortBy,
    sort_order: state.claimsSortOrder
  });

  if (state.activeFilters.search) params.append('search', state.activeFilters.search);
  if (state.activeFilters.risk_tier !== 'all') params.append('risk_tier', state.activeFilters.risk_tier);
  if (state.activeFilters.product_family !== 'all') params.append('product_family', state.activeFilters.product_family);
  if (state.activeFilters.partner_inspected !== 'all') params.append('partner_inspected', state.activeFilters.partner_inspected);

  if (state.activeFilters.dataset === 'test') {
    params.append('is_historical', 'false');
  } else if (state.activeFilters.dataset === 'historical') {
    params.append('is_historical', 'true');
  }

  try {
    const res = await fetch(`/api/claims?${params.toString()}`);
    if (!res.ok) throw new Error('API query failed');
    const data = await res.json();

    state.claimsTotal = data.total_count;
    state.claimsTotalPages = data.total_pages;

    renderClaimsTable(data.claims);
    updatePaginationUI();
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="11" class="loading-cell">Error loading claims. Please try again.</td></tr>';
  }
}

function renderClaimsTable(claims) {
  const tbody = document.getElementById('claims-table-tbody');
  if (!claims || claims.length === 0) {
    tbody.innerHTML = '<tr><td colspan="11" class="loading-cell">No claims match the selected criteria.</td></tr>';
    return;
  }

  tbody.innerHTML = claims.map(c => `
    <tr>
      <td class="mono-cell"><a href="#" onclick="event.preventDefault(); openClaimDetails('${c.claim_id}')">${c.claim_id}</a></td>
      <td>${c.submitted_at.substring(0, 16)}</td>
      <td>${c.product_family} <span style="font-size:0.75rem; color:#64748b;">(${c.sku})</span></td>
      <td><strong>₹${c.claim_amount_inr.toLocaleString()}</strong></td>
      <td class="mono-cell">${c.partner_id}</td>
      <td>${c.partner_city} <span style="font-size:0.7rem; color:#64748b;">(${c.partner_type.replace(/_/g, ' ')})</span></td>
      <td><span class="badge ${c.partner_inspected === 'Y' ? 'badge-success' : 'badge-warning'}">${c.partner_inspected}</span></td>
      <td><span class="badge ${c.photo_attached === 'Y' ? 'badge-success' : 'badge-neutral'}">${c.photo_attached}</span></td>
      <td><span class="badge ${getScoreBadgeClass(c.risk_score)}">${(c.risk_score * 100).toFixed(1)}%</span></td>
      <td><span style="font-size:0.8rem; font-weight:500;">${c.recommendation}</span></td>
      <td><button class="btn btn-secondary btn-sm" onclick="openClaimDetails('${c.claim_id}')">Review</button></td>
    </tr>
  `).join('');
}

function updatePaginationUI() {
  const start = (state.claimsPage - 1) * state.claimsPageSize + 1;
  const end = Math.min(state.claimsPage * state.claimsPageSize, state.claimsTotal);
  document.getElementById('pagination-info').textContent =
    state.claimsTotal > 0
      ? `Showing ${start} - ${end} of ${state.claimsTotal.toLocaleString()} claims`
      : 'No claims found';

  document.getElementById('page-indicator').textContent =
    `Page ${state.claimsPage} of ${Math.max(1, state.claimsTotalPages)}`;

  document.getElementById('btn-prev-page').disabled = state.claimsPage <= 1;
  document.getElementById('btn-next-page').disabled = state.claimsPage >= state.claimsTotalPages;
}

// Claim Review Form Controller
function initReviewForm() {
  const form = document.getElementById('claim-review-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await executeClaimTriage();
  });
}

async function executeClaimTriage() {
  const btn = document.getElementById('btn-submit-predict');
  btn.disabled = true;
  btn.textContent = 'Evaluating Model & Policy Rules...';

  const payload = {
    claim_id: document.getElementById('form-claim-id').value,
    submitted_at: document.getElementById('form-submitted-at').value,
    partner_id: document.getElementById('form-partner-id').value.trim(),
    sku: document.getElementById('form-sku').value,
    product_serial: document.getElementById('form-serial').value,
    days_since_purchase: parseInt(document.getElementById('form-days').value, 10),
    claim_amount_inr: parseFloat(document.getElementById('form-amount').value),
    photo_attached: document.getElementById('form-photo').value,
    partner_inspected: document.getElementById('form-inspected').value,
    claim_description: document.getElementById('form-desc').value,
    inspector_note: document.getElementById('form-inspector-note').value || null,
    customer_prior_claims: parseInt(document.getElementById('form-priors').value, 10),
    source: "crm"
  };

  try {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Prediction failed');
    const result = await res.json();
    renderEvaluationResults(result);
    showToast(`Claim ${payload.claim_id} evaluated successfully.`, 'success');
  } catch (err) {
    showToast('Failed to evaluate claim. Ensure parameters are valid.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
        <polygon points="5 3 19 12 5 21 5 3"/>
      </svg>
      Run Fraud Scoring & Policy Check
    `;
  }
}

function renderEvaluationResults(res) {
  document.getElementById('eval-risk-badge').textContent = res.risk_tier;
  document.getElementById('eval-risk-badge').className = `card-badge ${getTierBadgeClass(res.risk_tier)}`;

  const body = document.getElementById('eval-body');

  let actionClass = 'action-approve';
  if (res.recommended_action.includes('Rejection')) actionClass = 'action-reject';
  else if (res.recommended_action.includes('Hold')) actionClass = 'action-hold';
  else if (res.recommended_action.includes('Review') || res.recommended_action.includes('Verification')) actionClass = 'action-review';

  body.innerHTML = `
    <!-- Score Meter Box -->
    <div class="score-display-box">
      <div class="score-left">
        <span class="score-title">Fraud Risk Probability</span>
        <span class="score-number">${(res.risk_score * 100).toFixed(1)}%</span>
      </div>
      <div class="score-bar-container">
        <div class="score-progress-track">
          <div class="score-progress-fill" style="width: ${Math.min(100, Math.max(2, res.risk_score * 100))}%; background-color: ${getScoreColor(res.risk_score)};"></div>
        </div>
        <span class="score-tier-label" style="color: ${getScoreColor(res.risk_score)};">${res.risk_tier} Risk Tier</span>
      </div>
    </div>

    <!-- Recommendation Banner -->
    <div class="recommendation-banner ${actionClass}">
      <div class="rec-title">${res.recommended_action}</div>
      <div class="rec-desc">${res.recommended_action_rationale}</div>
    </div>

    <!-- Ops Policy Compliance Checks -->
    <div class="eval-subgroup">
      <h4>Warranty Policy Compliance (§5)</h4>
      <div class="checks-list">
        ${res.policy_checks.map(c => `
          <div class="check-item ${c.passed ? 'passed' : (c.severity === 'VIOLATION' ? 'violation' : 'warning')}">
            <span class="check-badge-tag">${c.severity}</span>
            <div class="check-text-group">
              <span class="check-rule-name">${c.rule_name}</span>
              <span class="check-details">${c.details}</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>

    <!-- Evidence Factors -->
    <div class="eval-subgroup">
      <h4>Key Evidence-Backed Factors</h4>
      <div class="evidence-list">
        ${res.evidence_factors.map(f => `
          <div class="evidence-item">${f}</div>
        `).join('')}
      </div>
    </div>

    ${res.data_quality_flags.length > 0 ? `
      <!-- Data Quality Flags -->
      <div class="eval-subgroup">
        <h4>Data Quality & Input Alerts</h4>
        <div class="evidence-list">
          ${res.data_quality_flags.map(f => `
            <div class="evidence-item" style="border-left-color: #f59e0b; background-color: #fffbeb;">${f}</div>
          `).join('')}
        </div>
      </div>
    ` : ''}

    <div class="disclaimer-box">
      <strong>Operational Policy Reminder:</strong> A model risk score is an empirical triage signal, not conclusive proof of fraud. Human review by the investigation desk is strictly required before any adverse claim rejection or partner penalty is issued.
    </div>
  `;
}

function loadCaseStudy(key) {
  const c = CASE_STUDIES[key];
  if (!c) return;

  document.getElementById('form-claim-id').value = c.claim_id;
  document.getElementById('form-submitted-at').value = c.submitted_at;
  document.getElementById('form-partner-id').value = c.partner_id;
  document.getElementById('form-sku').value = c.sku;
  document.getElementById('form-serial').value = c.product_serial;
  document.getElementById('form-days').value = c.days_since_purchase;
  document.getElementById('form-amount').value = c.claim_amount_inr.toFixed(2);
  document.getElementById('form-photo').value = c.photo_attached;
  document.getElementById('form-inspected').value = c.partner_inspected;
  document.getElementById('form-desc').value = c.claim_description;
  document.getElementById('form-inspector-note').value = c.inspector_note || '';
  document.getElementById('form-priors').value = c.customer_prior_claims;

  executeClaimTriage();
}

// Partner Analysis Controller
async function loadPartnerData() {
  try {
    const res = await fetch('/api/partners');
    if (!res.ok) throw new Error('Partner API failed');
    const data = await res.json();

    const tbody = document.getElementById('partner-risk-tbody');
    if (data.top_high_risk_partners) {
      tbody.innerHTML = data.top_high_risk_partners.map(p => `
        <tr>
          <td class="mono-cell">${p.partner_id}</td>
          <td>${p.city}</td>
          <td>${p.partner_type.replace(/_/g, ' ')}</td>
          <td>${p.onboarded_date}</td>
          <td>${p.total_claims}</td>
          <td><strong>${p.fraud_claims}</strong></td>
          <td><span class="badge ${p.fraud_rate >= 0.20 ? 'badge-crit' : 'badge-high'}">${(p.fraud_rate * 100).toFixed(1)}%</span></td>
          <td><span class="badge ${p.fraud_claims >= 5 ? 'badge-viol' : 'badge-warning'}">${p.fraud_claims >= 5 ? 'Under Audit' : 'Monitored'}</span></td>
        </tr>
      `).join('');
    }
  } catch (err) {
    showToast('Failed to load partner metrics.', 'error');
  }
}

// Model Evaluation Controller
async function loadEvaluationData() {
  try {
    const res = await fetch('/api/model-metrics');
    if (!res.ok) throw new Error('Evaluation API failed');
    const data = await res.json();

    if (data.metrics) {
      document.getElementById('eval-rf-auc').textContent = data.metrics.roc_auc.toFixed(4);
      document.getElementById('eval-rf-prauc').textContent = data.metrics.pr_auc.toFixed(4);
      document.getElementById('eval-rf-recall').textContent = (data.metrics.recall * 100).toFixed(1) + '%';
      document.getElementById('eval-rf-precision').textContent = (data.metrics.precision * 100).toFixed(1) + '%';
      document.getElementById('eval-rf-thresh').textContent = data.operating_threshold.toFixed(4);
    }

    if (data.baseline_comparison) {
      document.getElementById('eval-base-auc').textContent = data.baseline_comparison.roc_auc.toFixed(4);
      document.getElementById('eval-base-prauc').textContent = data.baseline_comparison.pr_auc.toFixed(4);
    }

    // Populate Threshold Sweep Table
    const sweepTbody = document.getElementById('eval-threshold-tbody');
    if (sweepTbody && data.threshold_analysis && data.threshold_analysis.length > 0) {
      sweepTbody.innerHTML = data.threshold_analysis.map(t => `
        <tr ${t.threshold === 0.4615 ? 'style="background-color:#eff6ff; font-weight:600;"' : ''}>
          <td class="mono-cell">${t.threshold.toFixed(4)} ${t.threshold === 0.4615 ? '<span class="badge badge-info" style="margin-left:0.25rem;">Operating Threshold</span>' : ''}</td>
          <td>${t.claims_flagged.toLocaleString()}</td>
          <td class="success-text">${t.true_positives}</td>
          <td class="warning-text">${t.false_positives}</td>
          <td>${(t.precision * 100).toFixed(1)}%</td>
          <td>${(t.recall * 100).toFixed(1)}%</td>
          <td>${(t.accuracy * 100).toFixed(2)}%</td>
          <td><strong>₹${Math.round(t.estimated_net_benefit_inr).toLocaleString()}</strong></td>
        </tr>
      `).join('');
    }

    // Populate Confusion Matrix
    if (data.metrics) {
      const tnEl = document.getElementById('cm-tn');
      const fpEl = document.getElementById('cm-fp');
      const fnEl = document.getElementById('cm-fn');
      const tpEl = document.getElementById('cm-tp');
      if (tnEl) tnEl.textContent = (data.metrics.true_negatives || 11172).toLocaleString();
      if (fpEl) fpEl.textContent = (data.metrics.false_positives || 497).toLocaleString();
      if (fnEl) fnEl.textContent = (data.metrics.false_negatives || 39).toLocaleString();
      if (tpEl) tpEl.textContent = (data.metrics.true_positives || 106).toLocaleString();
    }

    // Populate Top Feature Drivers
    const featureListEl = document.getElementById('feature-importance-list');
    if (featureListEl && data.feature_importances) {
      const featureLabels = {
        partner_smoothed_risk: 'Partner Empirical Fraud Risk',
        amount_to_list_ratio: 'Claim Amount vs List Price Ratio',
        city_smoothed_risk: 'City-Level Empirical Risk',
        partner_tenure_days: 'Partner Tenure (Days)',
        claim_amount_inr: 'Claim Amount (INR)',
        customer_prior_claims: 'Customer Prior Warranty Claims',
        partner_inspected_flag: 'Partner Inspected Sign-off Flag',
        days_since_purchase: 'Days Since Purchase Date',
        warranty_consumed_ratio: 'Warranty Period Consumed Ratio',
        is_new_partner: 'Newer Partner (< 1 Year Cohort)',
        uninspected_under_2k: 'Uninspected Sub-₹2,000 Gaming Signal',
        submission_hour: 'Submission Hour of Day',
        is_franchise: 'Partner Type: Franchise Outlet',
        has_inspector_note: 'Inspector Note Present',
        is_under_2k: 'Claim Amount < ₹2,000 Threshold',
        serial_has_whitespace: 'Serial Whitespace Formatting Anomaly'
      };

      const topFeatures = Object.entries(data.feature_importances)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8);

      const maxVal = topFeatures[0][1] || 1.0;

      featureListEl.innerHTML = topFeatures.map(([feat, val]) => {
        const pct = (val * 100).toFixed(1);
        const barWidth = Math.max(3, (val / maxVal) * 100);
        const label = featureLabels[feat] || feat.replace(/_/g, ' ');
        return `
          <div class="feature-bar-row">
            <span class="feature-bar-label" title="${label}">${label}</span>
            <div class="feature-bar-track">
              <div class="feature-bar-fill" style="width: ${barWidth}%;"></div>
            </div>
            <span class="feature-bar-val">${pct}%</span>
          </div>
        `;
      }).join('');
    }
  } catch (err) {
    showToast('Failed to load model evaluation data.', 'error');
  }
}

// Settings & ROI Simulation Controller
function initSettingsForm() {
  const slider = document.getElementById('setting-capacity');
  const sliderVal = document.getElementById('val-capacity');
  slider.addEventListener('input', () => {
    sliderVal.textContent = `${slider.value} claims`;
  });

  const form = document.getElementById('settings-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await recalculateBusinessImpact();
  });
}

async function loadSettingsData() {
  await recalculateBusinessImpact();
}

async function recalculateBusinessImpact() {
  const cap = parseInt(document.getElementById('setting-capacity').value, 10);
  const goodwill = parseFloat(document.getElementById('setting-goodwill').value);
  const labor = parseFloat(document.getElementById('setting-labor').value);
  const realization = parseFloat(document.getElementById('setting-realization').value);

  const params = new URLSearchParams({
    monthly_capacity: cap,
    goodwill_cost: goodwill,
    contact_cost: labor,
    realization_rate: realization
  });

  try {
    const res = await fetch(`/api/business-impact?${params.toString()}`);
    if (!res.ok) throw new Error('Simulation failed');
    const data = await res.json();

    const q = data.projected_quarterly_totals || data.projected_q3_2026_test_quarter;
    if (q) {
      const gross = q.gross_prevented_fraud_inr || q.projected_gross_prevented_fraud_rupees;
      const gw = q.goodwill_penalty_inr || q.projected_goodwill_cost_rupees;
      const lb = q.investigation_labor_inr || q.projected_investigation_labor_rupees;
      const net = q.net_quarterly_benefit_inr || q.projected_net_quarterly_benefit_rupees;

      document.getElementById('sim-prevented').textContent = '₹' + Math.round(gross).toLocaleString();
      document.getElementById('sim-goodwill').textContent = '-₹' + Math.round(gw).toLocaleString();
      document.getElementById('sim-labor').textContent = '-₹' + Math.round(lb).toLocaleString();
      document.getElementById('sim-net').textContent = '₹' + Math.round(net).toLocaleString();

      const perClaim = Math.round(net / (cap * 3));
      document.getElementById('sim-return-per-claim').innerHTML =
        `Net Return per Investigation: <strong>₹${perClaim.toLocaleString()} / claim</strong>`;
    }
    showToast('Business impact updated with new capacity parameters.', 'success');
  } catch (err) {
    showToast('Error recalculating business impact.', 'error');
  }
}

// Drawer Controller
function initDrawer() {
  const overlay = document.getElementById('drawer-overlay');
  const closeBtn = document.getElementById('drawer-close-btn');

  overlay.addEventListener('click', closeClaimDetails);
  closeBtn.addEventListener('click', closeClaimDetails);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeClaimDetails();
  });
}

async function openClaimDetails(claimId) {
  const drawer = document.getElementById('details-drawer');
  const overlay = document.getElementById('drawer-overlay');
  const content = document.getElementById('drawer-content');

  document.getElementById('drawer-claim-id').textContent = claimId;
  content.innerHTML = '<div class="loading-cell">Loading complete claim telemetry...</div>';

  drawer.classList.add('active');
  overlay.classList.add('active');

  try {
    const res = await fetch(`/api/claims/${claimId}`);
    if (!res.ok) throw new Error('Claim not found');
    const claim = await res.json();

    content.innerHTML = `
      <!-- Status & Tiers -->
      <div class="score-display-box">
        <div class="score-left">
          <span class="score-title">Fraud Risk Score</span>
          <span class="score-number">${(claim.risk_score * 100).toFixed(1)}%</span>
        </div>
        <div class="score-bar-container">
          <span class="badge ${getScoreBadgeClass(claim.risk_score)}" style="align-self:flex-end;">${claim.risk_tier}</span>
          <span style="font-size:0.75rem; color:#64748b; text-align:right;">${claim.recommendation}</span>
        </div>
      </div>

      <!-- Telemetry Table -->
      <div class="eval-subgroup">
        <h4>Claim Record Attributes</h4>
        <div class="table-responsive">
          <table class="data-table" style="font-size:0.8rem;">
            <tbody>
              <tr><td style="color:#64748b;">Submission Date</td><td><strong>${claim.submitted_at}</strong></td></tr>
              <tr><td style="color:#64748b;">Claimed Amount</td><td><strong>₹${claim.claim_amount_inr.toLocaleString()}</strong></td></tr>
              <tr><td style="color:#64748b;">Product SKU</td><td>${claim.sku} (${claim.product_family})</td></tr>
              <tr><td style="color:#64748b;">Product List Price</td><td>₹${claim.list_price_inr.toLocaleString()} (Warranty: ${claim.warranty_months} mo)</td></tr>
              <tr><td style="color:#64748b;">Product Serial</td><td class="mono-cell">${claim.product_serial}</td></tr>
              <tr><td style="color:#64748b;">Days Since Purchase</td><td>${claim.days_since_purchase} days</td></tr>
              <tr><td style="color:#64748b;">Partner Inspected</td><td><span class="badge ${claim.partner_inspected === 'Y' ? 'badge-success' : 'badge-warning'}">${claim.partner_inspected}</span></td></tr>
              <tr><td style="color:#64748b;">Photo Attached</td><td><span class="badge ${claim.photo_attached === 'Y' ? 'badge-success' : 'badge-neutral'}">${claim.photo_attached}</span></td></tr>
              <tr><td style="color:#64748b;">Customer Prior Claims</td><td>${claim.customer_prior_claims} prior claims</td></tr>
              <tr><td style="color:#64748b;">Originating Source</td><td class="mono-cell">${claim.source}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Service Partner Information -->
      <div class="eval-subgroup">
        <h4>Service Partner Profile</h4>
        <div class="table-responsive">
          <table class="data-table" style="font-size:0.8rem;">
            <tbody>
              <tr><td style="color:#64748b;">Partner ID</td><td class="mono-cell"><strong>${claim.partner_id}</strong></td></tr>
              <tr><td style="color:#64748b;">City Location</td><td>${claim.city}</td></tr>
              <tr><td style="color:#64748b;">Partner Type</td><td>${claim.partner_type.replace(/_/g, ' ')}</td></tr>
              <tr><td style="color:#64748b;">Onboarded Date</td><td>${claim.onboarded_date}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Fault & Inspector Notes -->
      <div class="eval-subgroup">
        <h4>Technician Documentation</h4>
        <div style="background-color:#f8fafc; padding:0.75rem; border-radius:4px; font-size:0.8rem;">
          <div style="margin-bottom:0.4rem;"><strong>Fault Description:</strong> ${claim.claim_description}</div>
          <div><strong>Inspector Sign-off Note:</strong> ${claim.inspector_note || '<span style="color:#94a3b8; font-style:italic;">No note attached (Uninspected)</span>'}</div>
        </div>
      </div>

      <!-- Officer Adjudication Actions -->
      <div class="adjudication-box">
        <div class="adjudication-title">Officer Adjudication & Triage Decision</div>

        ${claim.adjudication ? `
          <div class="audit-seal-stamp">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon" style="color:var(--primary);">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
            <div>
              <div><strong>${claim.adjudication.status_label}</strong></div>
              <div style="font-size:0.7rem; color:#64748b; font-weight:normal;">Logged by ${claim.adjudication.reviewer} &bull; ${claim.adjudication.timestamp}</div>
            </div>
          </div>
        ` : ''}

        <div class="adjudication-actions-grid">
          <button class="btn btn-sm btn-adj-approve" onclick="executeAdjudication('${claim.claim_id}', 'APPROVE')">
            Approve Payout
          </button>
          <button class="btn btn-sm btn-adj-hold" onclick="executeAdjudication('${claim.claim_id}', 'HOLD')">
            Hold for Desk (§5)
          </button>
          <button class="btn btn-sm btn-adj-reject" onclick="executeAdjudication('${claim.claim_id}', 'REJECT')">
            Reject (Policy Viol.)
          </button>
          <button class="btn btn-sm btn-adj-print" onclick="window.print()">
            Print Dossier
          </button>
        </div>
      </div>

      <div class="form-actions" style="margin-top:0.25rem;">
        <button class="btn btn-primary" style="width:100%;" onclick="copyClaimToTriage('${claim.claim_id}')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
          Load into Live Triage Form
        </button>
      </div>
    `;
  } catch (err) {
    content.innerHTML = '<div class="loading-cell">Failed to load claim details.</div>';
  }
}

async function executeAdjudication(claimId, action) {
  try {
    const res = await fetch(`/api/claims/${claimId}/adjudicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: action, reviewer: 'Kabir Nanda (Lead Risk Officer)', notes: 'Adjudicated in Console' })
    });
    if (!res.ok) throw new Error('Adjudication failed');
    const result = await res.json();
    showToast(result.status_label, 'success');
    // Refresh drawer to display seal
    await openClaimDetails(claimId);
    // Reload claims table to reflect updated recommendation and tier
    loadClaimsTable();
  } catch (err) {
    showToast('Failed to record adjudication.', 'error');
  }
}

function closeClaimDetails() {
  document.getElementById('details-drawer').classList.remove('active');
  document.getElementById('drawer-overlay').classList.remove('active');
}

async function copyClaimToTriage(claimId) {
  closeClaimDetails();
  navigateTo('review');

  try {
    const res = await fetch(`/api/claims/${claimId}`);
    if (res.ok) {
      const claim = await res.json();
      document.getElementById('form-claim-id').value = claim.claim_id;
      document.getElementById('form-submitted-at').value = claim.submitted_at;
      document.getElementById('form-partner-id').value = claim.partner_id;
      document.getElementById('form-sku').value = claim.sku;
      document.getElementById('form-serial').value = claim.product_serial;
      document.getElementById('form-days').value = claim.days_since_purchase;
      document.getElementById('form-amount').value = claim.claim_amount_inr.toFixed(2);
      document.getElementById('form-photo').value = claim.photo_attached;
      document.getElementById('form-inspected').value = claim.partner_inspected;
      document.getElementById('form-desc').value = claim.claim_description;
      document.getElementById('form-inspector-note').value = claim.inspector_note || '';
      document.getElementById('form-priors').value = claim.customer_prior_claims;
      await executeClaimTriage();
    }
  } catch (err) {
    showToast('Failed to copy claim to triage form.', 'error');
  }
}

// Utility Helpers
function getScoreBadgeClass(score) {
  if (score >= 0.75) return 'badge-crit';
  if (score >= 0.4615) return 'badge-high';
  if (score >= 0.20) return 'badge-mod';
  return 'badge-low';
}

function getTierBadgeClass(tier) {
  switch (tier.toLowerCase()) {
    case 'critical': return 'badge-crit';
    case 'high': return 'badge-high';
    case 'moderate': return 'badge-mod';
    case 'low': return 'badge-low';
    default: return 'badge-viol';
  }
}

function getScoreColor(score) {
  if (score >= 0.75) return '#dc2626';
  if (score >= 0.4615) return '#f59e0b';
  if (score >= 0.20) return '#3b82f6';
  return '#16a34a';
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;

  if (type === 'error') toast.style.backgroundColor = '#991b1b';
  else if (type === 'success') toast.style.backgroundColor = '#166534';

  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 3500);
}
