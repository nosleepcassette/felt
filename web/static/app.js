// maps · cassette.help · MIT
// felt frontend — vanilla JS, no framework

'use strict';

// -- State -------------------------------------------------------------------

const state = {
 activeTab: 'likes',
 data: { likes: null, pings: null, matches: null, discovery: null },
 loading: { likes: false, pings: false, matches: false, discovery: false },
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

async function loadTab(tabId) {
 if (state.data[tabId] !== null) {
 renderTab(tabId, state.data[tabId]);
 return;
 }
 if (state.loading[tabId]) return;

 state.loading[tabId] = true;
 setLoading(tabId, true);

 try {
 const data = await apiFetch(`/api/${tabId}`);
 state.data[tabId] = data;
 renderTab(tabId, data);
 } catch (e) {
 setLoading(tabId, false);
 showError(`Error loading ${tabId}: ${e.message}`);
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
 grid.innerHTML = items.map(renderProfileCard).join('');
 }

 // Attach click handlers
 grid.querySelectorAll('.card').forEach((card) => {
 card.addEventListener('click', () => {
 const id = card.dataset.id;
 const item = items.find((i) => i.id === id);
 if (item) openModal(item, tabId);
 });
 });
}

function renderProfileCard(profile) {
 // Profile dicts come flat from the API: { id, displayName, age, gender, ... }
 const photoHtml = profile.primaryPhotoUrl
 ? `<img src="${escHtml(profile.primaryPhotoUrl)}" alt="${escHtml(profile.displayName)}" loading="lazy">`
 : `<div class="no-photo">♡</div>`;

 const meta = [profile.gender, profile.sexuality, profile.distanceKm ? profile.distanceKm + 'km' : '']
 .filter(Boolean).join(' · ');

 return `
 <div class="card" data-id="${escHtml(profile.id)}">
 <div class="card-photo">${photoHtml}</div>
 <div class="card-info">
 <div class="card-name">${escHtml(profile.displayName)}</div>
 <div class="card-meta">${profile.age || ''}${meta ? ' · ' + meta : ''}</div>
 </div>
 </div>
 `;
}

function renderMatchCard(match) {
 const photoHtml = '' // matches don't have photos in the summary
 const name = match.name || '—';
 const msg = match.latestMessage || '';

 return `
 <div class="card" data-id="${escHtml(match.id)}">
 <div class="card-photo"><div class="no-photo">✦</div></div>
 <div class="card-info">
 <div class="card-name">${escHtml(name)}</div>
 <div class="card-meta">${escHtml(msg.slice(0, 60)) || '—'}</div>
 </div>
 </div>
 `;
}

function openModal(item, tabId) {
 const modal = $('#modal');
 const body = $('#modal-body');

 if (tabId === 'matches') {
 // Match summaries are lightweight — just show name and latest message
 body.innerHTML = `
 <div class="modal-name">${escHtml(item.name || '—')}</div>
 <div class="modal-meta">${escHtml(item.latestMessage || 'No messages yet')}</div>
 <div class="modal-meta" style="margin-top:8px">Status: ${escHtml(item.status || '—')}</div>
 `;
 } else {
 // Profile items — show full detail
 const photosHtml = item.photos && item.photos.length > 0
 ? `<div class="modal-photos">${item.photos.map(ph =>
 `<img src="${escHtml(ph.url)}" alt="" loading="lazy">`
 ).join('')}</div>`
 : '';

 const desiresHtml = item.desires && item.desires.length > 0
 ? `<div class="modal-section">
 <div class="modal-section-label">desires</div>
 <div class="modal-desires">${item.desires.map(d =>
 `<span class="desire-tag">${escHtml(d)}</span>`
 ).join('')}</div>
 </div>`
 : '';

 const interestsHtml = item.interests && item.interests.length > 0
 ? `<div class="modal-section">
 <div class="modal-section-label">interests</div>
 <div class="modal-desires">${item.interests.map(d =>
 `<span class="desire-tag">${escHtml(d)}</span>`
 ).join('')}</div>
 </div>`
 : '';

 const bioHtml = item.bio
 ? `<div class="modal-section">
 <div class="modal-section-label">bio</div>
 <div class="modal-bio">${escHtml(item.bio)}</div>
 </div>`
 : '';

 const distHtml = item.distanceKm != null
 ? `<div class="modal-meta">${item.distanceKm}km away</div>`
 : '';

 body.innerHTML = `
 ${photosHtml}
 <div class="modal-name">${escHtml(item.displayName || '—')}</div>
 <div class="modal-meta">${item.age || ''}${item.gender ? ' · ' + item.gender : ''}${item.sexuality ? ' · ' + item.sexuality : ''}</div>
 ${distHtml}
 ${desiresHtml}
 ${interestsHtml}
 ${bioHtml}
 `;
 }

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
 loadTab('likes');
});
