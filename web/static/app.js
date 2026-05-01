// maps · cassette.help · MIT
// feeld-local frontend — vanilla JS, no framework

'use strict';

// -- State -------------------------------------------------------------------

const state = {
    activeTab: 'likes',
    data: { likes: null, passes: null, matches: null },
    loading: { likes: false, passes: false, matches: false },
};


// -- DOM helpers -------------------------------------------------------------

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function showError(msg) {
    const banner = $('#error-banner');
    banner.textContent = msg;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 8000);
}

function setLoading(tabId, isLoading) {
    const el = $(`#tab-${tabId} .loading`);
    if (el) el.style.display = isLoading ? 'block' : 'none';
}


// -- API calls ---------------------------------------------------------------

async function apiFetch(path) {
    const res = await fetch(path);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    return data;
}

async function loadMe() {
    try {
        const me = await apiFetch('/api/me');
        const status = $('#auth-status');
        status.textContent = me.displayName || 'authenticated';
        status.classList.add('ok');
    } catch (e) {
        const status = $('#auth-status');
        status.textContent = 'auth error';
        status.classList.add('error');
        showError(`Auth error: ${e.message}`);
    }
}

async function loadStats() {
    try {
        const stats = await apiFetch('/api/stats');
        const bar = $('#stats-bar');
        if (!stats || Object.keys(stats).length === 0) return;

        bar.innerHTML = Object.entries(stats).map(([k, v]) => `
            <div class="stat">
                <span class="stat-value">${v ?? '—'}</span>
                <span class="stat-label">${k.replace(/([A-Z])/g, ' $1').toLowerCase()}</span>
            </div>
        `).join('');
    } catch (e) {
        // Stats are optional — don't show error
    }
}

async function loadTab(tabId) {
    if (state.data[tabId] !== null) {
        renderTab(tabId, state.data[tabId]);
        return;
    }
    if (state.loading[tabId]) return;

    state.loading[tabId] = true;
    setLoading(tabId, true);

    try {
        const endpoint = `/api/${tabId === 'likes' ? 'likes' : tabId === 'passes' ? 'passes' : 'matches'}`;
        const data = await apiFetch(endpoint);
        state.data[tabId] = data;
        renderTab(tabId, data);
    } catch (e) {
        setLoading(tabId, false);
        if (tabId === 'passes') {
            $('#passes-unavailable').classList.remove('hidden');
        } else {
            showError(`Error loading ${tabId}: ${e.message}`);
        }
    } finally {
        state.loading[tabId] = false;
    }
}


// -- Rendering ---------------------------------------------------------------

function renderTab(tabId, items) {
    setLoading(tabId, false);

    const gridId = `${tabId}-grid`;
    const grid = $(`#${gridId}`);
    if (!grid) return;

    if (!items || items.length === 0) {
        grid.innerHTML = '<div class="notice">nothing here yet</div>';
        return;
    }

    if (tabId === 'matches') {
        grid.innerHTML = items.map(renderMatchCard).join('');
    } else {
        grid.innerHTML = items.map(renderSwipeCard).join('');
    }

    // Attach click handlers
    grid.querySelectorAll('.card').forEach((card) => {
        card.addEventListener('click', () => {
            const id = card.dataset.id;
            const item = items.find((i) => i.id === id || i.profile?.id === id);
            if (item) openModal(item, tabId);
        });
    });
}

function renderSwipeCard(event) {
    const p = event.profile;
    const photoHtml = p.primaryPhotoUrl
        ? `<img src="${escHtml(p.primaryPhotoUrl)}" alt="${escHtml(p.displayName)}" loading="lazy">`
        : `<div class="no-photo">♡</div>`;

    return `
        <div class="card" data-id="${escHtml(event.id)}">
            <div class="card-photo">${photoHtml}</div>
            <div class="card-info">
                <div class="card-name">${escHtml(p.displayName)}</div>
                <div class="card-meta">${p.age ? p.age : ''}${p.gender ? ' · ' + p.gender : ''}</div>
                <div class="card-time">${event.timeAgo || ''}</div>
            </div>
        </div>
    `;
}

function renderMatchCard(match) {
    const p = match.profile;
    const photoHtml = p.primaryPhotoUrl
        ? `<img src="${escHtml(p.primaryPhotoUrl)}" alt="${escHtml(p.displayName)}" loading="lazy">`
        : `<div class="no-photo">✦</div>`;

    const unread = match.unreadCount > 0
        ? `<span style="color: var(--amber)">${match.unreadCount} unread</span> · `
        : '';

    return `
        <div class="card" data-id="${escHtml(match.id)}">
            <div class="card-photo">${photoHtml}</div>
            <div class="card-info">
                <div class="card-name">${escHtml(p.displayName)}</div>
                <div class="card-meta">${p.age || ''}</div>
                <div class="card-time">${unread}${match.lastMessage ? escHtml(match.lastMessage.slice(0, 40)) : ''}</div>
            </div>
        </div>
    `;
}

function openModal(item, tabId) {
    const modal = $('#modal');
    const body = $('#modal-body');

    const isMatch = tabId === 'matches';
    const profile = isMatch ? item.profile : item.profile;
    if (!profile) return;

    const photosHtml = profile.photos && profile.photos.length > 0
        ? `<div class="modal-photos">${profile.photos.map(ph =>
            `<img src="${escHtml(ph.url)}" alt="" loading="lazy">`
          ).join('')}</div>`
        : '';

    const desiresHtml = profile.desires && profile.desires.length > 0
        ? `<div class="modal-section">
            <div class="modal-section-label">desires</div>
            <div class="modal-desires">${profile.desires.map(d =>
                `<span class="desire-tag">${escHtml(d)}</span>`
            ).join('')}</div>
           </div>`
        : '';

    const bioHtml = profile.bio
        ? `<div class="modal-section">
            <div class="modal-section-label">bio</div>
            <div class="modal-bio">${escHtml(profile.bio)}</div>
           </div>`
        : '';

    body.innerHTML = `
        ${photosHtml}
        <div class="modal-name">${escHtml(profile.displayName)}</div>
        <div class="modal-meta">${profile.age ? profile.age : ''}${profile.gender ? ' · ' + profile.gender : ''}</div>
        ${desiresHtml}
        ${bioHtml}
    `;

    modal.classList.remove('hidden');
}

function closeModal() {
    $('#modal').classList.add('hidden');
}

function escHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}


// -- Event listeners ---------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    $$('.tab').forEach((btn) => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            $$('.tab').forEach((t) => t.classList.remove('active'));
            $$('.tab-content').forEach((c) => c.classList.remove('active'));
            btn.classList.add('active');
            $(`#tab-${tabId}`).classList.add('active');
            state.activeTab = tabId;
            loadTab(tabId);
        });
    });

    // Modal close
    $('#modal-close').addEventListener('click', closeModal);
    $('#modal-backdrop').addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    // Initial load
    loadMe();
    loadStats();
    loadTab('likes'); // Load the default tab
});
