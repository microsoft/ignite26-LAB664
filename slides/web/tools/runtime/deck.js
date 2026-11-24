(() => {
  'use strict';
  const D = JSON.parse(document.getElementById('deck-data').textContent);
  const W = D.w, H = D.h;
  const root = document.documentElement, body = document.body;
  const deckEl = document.getElementById('deck');
  const viewport = document.querySelector('.viewport');
  const stage = document.querySelector('.stage');
  const slides = Array.from(document.querySelectorAll('.slide'));
  const N = slides.length;
  const qs = new URLSearchParams(location.search);
  const THUMB = qs.has('thumb');
  const RM = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const $ = (s) => document.querySelector(s);
  let cur = -1, gi = 0, busy = null, timers = [], live = [], ovOpen = false, helpOpen = false, notesOpen = false;
  const idCache = [];

  /* ---------- layout ---------- */
  function fit() {
    const r = viewport.getBoundingClientRect();
    const s = Math.min(r.width / W, r.height / H) || 1;
    const x = (r.width - W * s) / 2, y = (r.height - H * s) / 2;
    stage.style.transform = `translate(${x}px,${y}px) scale(${s})`;
  }

  /* ---------- lazy media ---------- */
  function hydrate(i) {
    const s = slides[i];
    if (!s || s._h) return;
    s._h = 1;
    s.querySelectorAll('img[data-src]').forEach((im) => { im.src = im.dataset.src; im.removeAttribute('data-src'); });
    s.querySelectorAll('video[data-src]').forEach((v) => {
      if (v.dataset.poster) v.poster = v.dataset.poster;
      v.preload = v.classList.contains('gifv') ? 'auto' : 'metadata';
      v.src = v.dataset.src;
      v.removeAttribute('data-src');
    });
  }

  /* ---------- shrink-on-overflow text (PowerPoint autofit) ---------- */
  function fitText(i) {
    const s = slides[i];
    if (!s || s._fit) return;
    s._fit = 1;
    s.querySelectorAll('.tx.fit').forEach((tx) => {
      const inner = tx.firstElementChild;
      if (!inner) return;
      const cs = getComputedStyle(tx);
      const avail = tx.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      if (avail <= 0 || inner.offsetHeight <= avail + 1) return;
      let lo = 0.2, hi = 1;
      for (let k = 0; k < 8; k++) {
        const mid = (lo + hi) / 2;
        inner.style.setProperty('--fs', mid);
        if (inner.offsetHeight <= avail + 1) lo = mid; else hi = mid;
      }
      inner.style.setProperty('--fs', lo);
    });
  }

  /* ---------- targets ---------- */
  function byId(i, id) {
    let c = idCache[i];
    if (!c) {
      c = idCache[i] = {};
      slides[i].querySelectorAll('[data-id]').forEach((e) => { if (!c[e.dataset.id]) c[e.dataset.id] = e; });
    }
    return c[id];
  }
  function targets(i, tg) {
    const e = byId(i, tg.id);
    if (!e) return [];
    if (!tg.p) return [e];
    return Array.from(e.querySelectorAll('p[data-pi]')).filter((p) => { const k = +p.dataset.pi; return k >= tg.p[0] && k <= tg.p[1]; });
  }

  /* ---------- timers ---------- */
  function schedule(fn, ms) { const t = setTimeout(() => { timers = timers.filter((x) => x !== t); fn(); }, Math.max(0, ms)); timers.push(t); }
  function clearTimers() { timers.forEach(clearTimeout); timers = []; }
  function finishLive() { live.forEach((a) => { try { a.finish(); } catch (e) { /* ignore */ } }); live = []; }

  /* ---------- media ---------- */
  function mediaInfo(v) {
    const s = v.closest('.slide'), e = v.closest('[data-id]');
    if (!s || !e) return {};
    return ((D.slides[+s.dataset.n - 1] || {}).media || {})[e.dataset.id] || {};
  }
  function playVideo(v) {
    const info = mediaInfo(v);
    if (v.dataset.src) hydrate(slides.indexOf(v.closest('.slide')));
    v.loop = !!info.loop;
    if (typeof info.vol === 'number') v.volume = Math.max(0, Math.min(1, info.vol));
    if (info.mute) v.muted = true;
    const p = v.play();
    if (p && p.catch) {
      p.catch(() => {
        v.muted = true;
        const box = v.closest('.media');
        if (box) box.classList.add('muted');
        v.play().catch(() => {});
      });
    }
  }
  function mediaCmd(v, m) {
    if (m.a === 'play') { if (typeof m.f === 'number' && m.f > 0) { try { v.currentTime = m.f; } catch (e) { /* ignore */ } } playVideo(v); }
    else if (m.a === 'toggle') { if (v.paused) playVideo(v); else v.pause(); }
    else if (m.a === 'pause') v.pause();
    else if (m.a === 'stop') { v.pause(); try { v.currentTime = 0; } catch (e) { /* ignore */ } }
  }
  function stopMedia(i) {
    const s = slides[i];
    if (!s) return;
    s.querySelectorAll('video').forEach((v) => { try { v.pause(); } catch (e) { /* ignore */ } });
  }
  function startLoops(i) {
    slides[i].querySelectorAll('video.gifv').forEach((v) => {
      try { v.currentTime = 0; } catch (e) { /* ignore */ }
      v.muted = true;
      const p = v.play();
      if (p && p.catch) p.catch(() => {});
    });
  }
  function wireVideos() {
    document.querySelectorAll('.media').forEach((box) => {
      const v = box.querySelector('video.vid');
      if (!v) return;
      const el = box.closest('.el');
      const bar = box.querySelector('.vbar i');
      const toggle = (ev) => { ev.stopPropagation(); ev.preventDefault(); if (v.paused) playVideo(v); else v.pause(); };
      box.addEventListener('click', toggle);
      const mute = document.createElement('button');
      mute.type = 'button'; mute.className = 'vmute'; mute.textContent = 'Sound off \u2013 click to unmute';
      mute.addEventListener('click', (ev) => { ev.stopPropagation(); v.muted = false; box.classList.remove('muted'); });
      box.appendChild(mute);
      const vb = box.querySelector('.vbar');
      if (vb) vb.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const r = vb.getBoundingClientRect();
        if (v.duration) v.currentTime = Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * v.duration;
      });
      v.addEventListener('play', () => { box.classList.add('playing'); if (mediaInfo(v).full && el) el.classList.add('vfs'); });
      const stop = () => { box.classList.remove('playing'); if (el) el.classList.remove('vfs'); };
      v.addEventListener('pause', stop);
      v.addEventListener('ended', stop);
      v.addEventListener('timeupdate', () => { if (bar && v.duration) bar.style.width = (100 * v.currentTime / v.duration) + '%'; });
    });
  }

  /* ---------- animation ---------- */
  function resetSlide(i) {
    const s = slides[i], sd = D.slides[i];
    s.getAnimations({ subtree: true }).forEach((a) => { if (a.effect && a.effect.target !== s) a.cancel(); });
    s.querySelectorAll('[style*="visibility"]').forEach((e) => { e.style.visibility = ''; });
    for (const tg of sd.init) for (const e of targets(i, tg)) e.style.visibility = 'hidden';
    s.querySelectorAll('video.vid').forEach((v) => {
      try { v.pause(); if (v.readyState) v.currentTime = 0; } catch (e) { /* ignore */ }
      const box = v.closest('.media'); if (box) box.classList.remove('playing');
    });
    s.querySelectorAll('.vfs').forEach((e) => e.classList.remove('vfs'));
  }
  function playGroup(i, grp, instant, base) {
    if (!grp) return 0;
    base = base || 0;
    let end = 0;
    for (const fx of grp.fx) {
      const els = targets(i, fx.tg);
      for (const e of els) {
        for (const tr of fx.tr) {
          const kf = tr.k.map(([o, v]) => ({ offset: o, [tr.p]: v }));
          let a;
          try {
            a = e.animate(kf, { delay: base + fx.t + tr.t, duration: Math.max(1, tr.d), fill: 'both', easing: 'linear' });
          } catch (err) { continue; }
          if (instant || RM) a.finish(); else live.push(a);
        }
      }
      if (!instant && fx.m && fx.m.length) {
        const host = byId(i, fx.tg.id);
        const v = host && host.querySelector('video');
        if (v) fx.m.forEach((m) => schedule(() => { if (cur === i) mediaCmd(v, m); }, base + fx.t + m.t));
      }
      end = Math.max(end, fx.t + (fx.d || 0));
    }
    return end;
  }
  function autoCount(i) { const g = D.slides[i].g; let n = 0; while (n < g.length && g[n].a) n++; return n; }
  function runAuto(i) {
    const g = D.slides[i].g;
    let base = 0;
    while (gi < g.length && g[gi].a) { base += playGroup(i, g[gi], false, base); gi++; }
  }
  function setState(i, k) {
    clearTimers(); live = [];
    resetSlide(i);
    const g = D.slides[i].g;
    for (let n = 0; n < k && n < g.length; n++) playGroup(i, g[n], true);
    gi = Math.min(k, g.length);
  }

  /* ---------- transitions ---------- */
  function vec(dir) { return ({ l: [1, 0], r: [-1, 0], u: [0, 1], d: [0, -1] })[dir] || [1, 0]; }
  function runTransition(from, to, tr) {
    return new Promise((res) => {
      if (!tr || RM || !from) { res(); return; }
      const d = Math.max(50, tr.d || 500);
      const ease = 'cubic-bezier(.4,0,.2,1)';
      const A = [];
      const pct = (x, y) => `translate(${x * 100}%,${y * 100}%)`;
      const [dx, dy] = vec(tr.dir);
      switch (tr.type) {
        case 'push':
          A.push(from.animate([{ transform: pct(0, 0) }, { transform: pct(-dx, -dy) }], { duration: d, easing: ease }));
          A.push(to.animate([{ transform: pct(dx, dy) }, { transform: pct(0, 0) }], { duration: d, easing: ease }));
          break;
        case 'cover':
          A.push(to.animate([{ transform: pct(dx, dy) }, { transform: pct(0, 0) }], { duration: d, easing: ease }));
          break;
        case 'pull':
          to.style.zIndex = 1; from.style.zIndex = 2;
          A.push(from.animate([{ transform: pct(0, 0) }, { transform: pct(-dx, -dy) }], { duration: d, easing: ease }));
          break;
        case 'wipe': {
          const st = { l: 'inset(0 0 0 100%)', r: 'inset(0 100% 0 0)', u: 'inset(100% 0 0 0)', d: 'inset(0 0 100% 0)' }[tr.dir || 'l'] || 'inset(0 0 0 100%)';
          A.push(to.animate([{ clipPath: st }, { clipPath: 'inset(0 0 0 0)' }], { duration: d, easing: ease }));
          break;
        }
        case 'split':
          A.push(to.animate([{ clipPath: 'inset(0 50% 0 50%)' }, { clipPath: 'inset(0 0 0 0)' }], { duration: d, easing: ease }));
          break;
        case 'zoom':
          A.push(to.animate([{ opacity: 0, transform: 'scale(.6)' }, { opacity: 1, transform: 'scale(1)' }], { duration: d, easing: ease }));
          break;
        default:
          if (tr.black) {
            A.push(from.animate([{ opacity: 1 }, { opacity: 0 }], { duration: d / 2, fill: 'forwards' }));
            A.push(to.animate([{ opacity: 0 }, { opacity: 0, offset: 0.5 }, { opacity: 1 }], { duration: d }));
          } else {
            A.push(to.animate([{ opacity: 0 }, { opacity: 1 }], { duration: d, easing: 'linear' }));
          }
      }
      busy = A;
      Promise.all(A.map((a) => a.finished.catch(() => {}))).then(() => {
        A.forEach((a) => { try { a.cancel(); } catch (e) { /* ignore */ } });
        to.style.zIndex = ''; from.style.zIndex = '';
        if (busy === A) busy = null;
        res();
      });
    });
  }

  function flushTransition() {
    const b = busy;
    busy = null;
    if (b) b.forEach((a) => { try { a.finish(); } catch (e) { /* ignore */ } });
  }

  /* ---------- navigation ---------- */
  function go(i, mode, opts) {
    opts = opts || {};
    i = Math.max(0, Math.min(N - 1, i | 0));
    if (busy) flushTransition();
    clearTimers(); finishLive();
    const prevIdx = cur;
    const from = prevIdx >= 0 ? slides[prevIdx] : null;
    const to = slides[i];
    [i, i + 1, i + 2, i - 1].forEach(hydrate);
    if (from && from !== to) stopMedia(prevIdx);
    resetSlide(i);
    const sd = D.slides[i];
    if (mode === 'end') setState(i, sd.g.length); else gi = 0;
    cur = i;
    slides.forEach((s) => { if (s !== to && s !== from) { s.classList.remove('active', 'leaving'); s.setAttribute('aria-hidden', 'true'); } });
    to.classList.add('active'); to.classList.remove('leaving'); to.removeAttribute('aria-hidden');
    fitText(i);
    if (from && from !== to) { from.classList.remove('active'); from.classList.add('leaving'); from.setAttribute('aria-hidden', 'true'); }
    updateUI();
    let tr = sd.tr;
    if (from && prevIdx > i && tr) tr = { type: 'fade', d: Math.min(350, tr.d || 350) };
    const doTr = !opts.instant && from && from !== to && tr;
    const start = () => {
      if (from && from !== to) from.classList.remove('leaving');
      if (cur !== i) return;
      if (mode !== 'end') runAuto(i);
      startLoops(i);
    };
    if (doTr) runTransition(from, to, tr).then(start); else start();
  }
  function next() {
    if (ovOpen || helpOpen) return;
    if (busy) { flushTransition(); return; }
    const sd = D.slides[cur];
    if (gi < sd.g.length) {
      finishLive();
      playGroup(cur, sd.g[gi], false);
      gi++;
      updateUI();
      return;
    }
    if (cur < N - 1) go(cur + 1, 'start');
  }
  function prev() {
    if (ovOpen || helpOpen) return;
    if (busy) flushTransition();
    if (gi > autoCount(cur)) { setState(cur, gi - 1); updateUI(); return; }
    if (cur > 0) go(cur - 1, 'end');
  }

  /* ---------- UI ---------- */
  const curEl = $('.count .cur'), prog = $('.progress i');
  const notes = $('.notes'), notesBody = $('.notes-body'), nSlide = $('.nslide');
  function updateUI() {
    if (curEl) curEl.textContent = cur + 1;
    if (prog) prog.style.width = (100 * (cur + 1) / N) + '%';
    if (notesOpen) renderNotes();
    if (!THUMB) {
      const h = '#/' + (cur + 1);
      if (location.hash !== h) history.replaceState(null, '', h);
    }
    document.querySelectorAll('.ov-card').forEach((c, k) => c.classList.toggle('cur', k === cur));
  }
  function renderNotes() {
    const n = D.slides[cur].notes;
    notesBody.innerHTML = n || '<p class="none">No speaker notes for this slide.</p>';
    nSlide.textContent = 'Slide ' + (cur + 1) + ' of ' + N;
    notesBody.scrollTop = 0;
  }
  function toggleNotes(force) {
    notesOpen = typeof force === 'boolean' ? force : !notesOpen;
    notes.hidden = !notesOpen;
    body.classList.toggle('notes-open', notesOpen);
    $('.hbtn.nt').classList.toggle('on', notesOpen);
    if (notesOpen) renderNotes();
    fit();
  }
  let ovBuilt = false;
  function buildOverview() {
    if (ovBuilt) return;
    ovBuilt = true;
    const grid = $('.ov-grid');
    D.slides.forEach((s, k) => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'ov-card';
      const num = String(k + 1).padStart(2, '0');
      b.innerHTML = `<img loading="lazy" alt="" src="assets/thumbs/${num}.jpg"><span><b>${k + 1}</b></span>`;
      b.querySelector('span').append(document.createTextNode(s.title || ''));
      b.setAttribute('aria-label', `Slide ${k + 1}: ${s.title || ''}`);
      b.addEventListener('click', () => { toggleOverview(false); go(k, 'start'); });
      grid.appendChild(b);
    });
  }
  function toggleOverview(force) {
    ovOpen = typeof force === 'boolean' ? force : !ovOpen;
    if (ovOpen) buildOverview();
    $('.overview').hidden = !ovOpen;
    if (ovOpen) {
      updateUI();
      const c = document.querySelectorAll('.ov-card')[cur];
      if (c) { c.focus(); c.scrollIntoView({ block: 'center' }); }
    } else deckEl.focus({ preventScroll: true });
  }
  function ovMove(dk) {
    const cards = Array.from(document.querySelectorAll('.ov-card'));
    let k = cards.indexOf(document.activeElement);
    if (k < 0) k = cur;
    const cols = Math.max(1, Math.round($('.ov-grid').clientWidth / (cards[0].offsetWidth + 18)));
    const map = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols };
    k = Math.max(0, Math.min(cards.length - 1, k + map[dk]));
    cards[k].focus();
  }
  function toggleHelp(force) {
    helpOpen = typeof force === 'boolean' ? force : !helpOpen;
    $('.help').hidden = !helpOpen;
    if (helpOpen) $('.hclose').focus(); else deckEl.focus({ preventScroll: true });
  }
  function toggleFS() {
    const d = document;
    if (d.fullscreenElement || d.webkitFullscreenElement) (d.exitFullscreen || d.webkitExitFullscreen).call(d);
    else { const r = root.requestFullscreen || root.webkitRequestFullscreen; if (r) r.call(root); }
  }
  const blank = $('.blank');
  function setBlank(color) {
    if (!blank.hidden) { blank.hidden = true; return; }
    blank.style.background = color; blank.hidden = false;
  }
  let uiT = 0;
  function pokeUI() { body.classList.add('ui'); clearTimeout(uiT); uiT = setTimeout(() => body.classList.remove('ui'), 2600); }

  /* ---------- input ---------- */
  let numBuf = '', numT = 0;
  document.addEventListener('keydown', (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const k = e.key;
    if (!blank.hidden) { blank.hidden = true; e.preventDefault(); return; }
    if (helpOpen) { if (k === 'Escape' || k === '?') { toggleHelp(false); e.preventDefault(); } return; }
    if (ovOpen) {
      if (k === 'Escape' || k === 'o' || k === 'O' || k === 'g' || k === 'G') { toggleOverview(false); e.preventDefault(); }
      else if (k.startsWith('Arrow')) { ovMove(k); e.preventDefault(); }
      return;
    }
    const tag = (e.target && e.target.tagName) || '';
    if (/^\d$/.test(k)) { numBuf += k; clearTimeout(numT); numT = setTimeout(() => { numBuf = ''; }, 1600); return; }
    switch (k) {
      case 'ArrowRight': case 'ArrowDown': case 'PageDown': case ' ': case 'Spacebar':
        if ((k === ' ' || k === 'Spacebar') && tag === 'BUTTON' && !e.target.closest('.slide')) return;
        next(); break;
      case 'Enter':
        if (numBuf) { const n = parseInt(numBuf, 10); numBuf = ''; go(n - 1, 'start'); }
        else if (tag === 'BUTTON' || tag === 'A') return;
        else next();
        break;
      case 'ArrowLeft': case 'ArrowUp': case 'PageUp': case 'Backspace': prev(); break;
      case 'Home': go(0, 'start'); break;
      case 'End': go(N - 1, 'start'); break;
      case 'f': case 'F': toggleFS(); break;
      case 'o': case 'O': case 'g': case 'G': toggleOverview(); break;
      case 'n': case 'N': toggleNotes(); break;
      case 'b': case 'B': case '.': setBlank('#000'); break;
      case 'w': case 'W': case ',': setBlank('#fff'); break;
      case '?': case 'h': case 'H': toggleHelp(); break;
      case 'Escape': if (notesOpen) toggleNotes(false); else return; break;
      default: return;
    }
    e.preventDefault();
  });
  deckEl.addEventListener('click', (e) => {
    if (e.button !== 0) return;
    if (e.target.closest('a,button,video,.media,input,textarea')) return;
    const sel = window.getSelection && String(window.getSelection());
    if (sel) return;
    next();
  });
  let wheelT = 0;
  deckEl.addEventListener('wheel', (e) => {
    if (ovOpen || helpOpen || Math.abs(e.deltaY) < 30) return;
    const now = Date.now();
    if (now - wheelT < 650) return;
    wheelT = now;
    if (e.deltaY > 0) next(); else prev();
  }, { passive: true });
  let tx0 = null, ty0 = 0;
  deckEl.addEventListener('touchstart', (e) => { if (e.touches.length === 1) { tx0 = e.touches[0].clientX; ty0 = e.touches[0].clientY; } pokeUI(); }, { passive: true });
  deckEl.addEventListener('touchend', (e) => {
    if (tx0 === null) return;
    const t = e.changedTouches[0], dx = t.clientX - tx0, dy = t.clientY - ty0;
    tx0 = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) { e.preventDefault(); if (dx < 0) next(); else prev(); }
  });
  document.addEventListener('mousemove', pokeUI, { passive: true });
  $('.hbtn.prev').addEventListener('click', (e) => { e.stopPropagation(); prev(); });
  $('.hbtn.next').addEventListener('click', (e) => { e.stopPropagation(); next(); });
  $('.hbtn.ov').addEventListener('click', () => toggleOverview());
  $('.hbtn.nt').addEventListener('click', () => toggleNotes());
  $('.hbtn.fs').addEventListener('click', () => toggleFS());
  $('.hbtn.hp').addEventListener('click', () => toggleHelp());
  $('.nclose').addEventListener('click', () => toggleNotes(false));
  $('.ovclose').addEventListener('click', () => toggleOverview(false));
  $('.hclose').addEventListener('click', () => toggleHelp(false));
  $('.help').addEventListener('click', (e) => { if (e.target.classList.contains('help')) toggleHelp(false); });
  blank.addEventListener('click', () => { blank.hidden = true; });

  // interactive (trigger) sequences
  D.slides.forEach((sd, i) => (sd.inter || []).forEach((seq) => {
    const t = seq.trigger && byId(i, seq.trigger);
    if (!t) return;
    let k = 0;
    t.style.cursor = 'pointer';
    t.addEventListener('click', (e) => {
      e.stopPropagation();
      if (cur !== i || !seq.groups.length) return;
      playGroup(i, seq.groups[k % seq.groups.length], false);
      k++;
    });
  }));

  // in-slide links
  document.querySelectorAll('.slide a[href^="#"]').forEach((a) => a.addEventListener('click', (e) => {
    const h = a.getAttribute('href');
    e.preventDefault(); e.stopPropagation();
    if (h === '#next') next(); else if (h === '#prev') prev();
    else if (h === '#first') go(0, 'start'); else if (h === '#last') go(N - 1, 'start');
    else { const m = h.match(/(\d+)/); if (m) go(+m[1] - 1, 'start'); }
  }));

  function fromHash() {
    const m = (location.hash || '').match(/(\d+)/);
    return m ? Math.max(0, Math.min(N - 1, parseInt(m[1], 10) - 1)) : null;
  }
  window.addEventListener('hashchange', () => { const h = fromHash(); if (h !== null && h !== cur) go(h, 'start'); });
  window.addEventListener('resize', fit);
  if (window.ResizeObserver) new ResizeObserver(fit).observe(viewport);
  window.addEventListener('beforeprint', () => {
    slides.forEach((s, i) => {
      hydrate(i);
      if (!s._fit) { const d = s.style.display; s.style.display = 'block'; fitText(i); s.style.display = d; }
      resetSlide(i);
      D.slides[i].g.forEach((g) => playGroup(i, g, true));
    });
  });
  window.addEventListener('afterprint', () => { slides.forEach((s, i) => { if (i !== cur) resetSlide(i); }); setState(cur, gi); });

  // warm the image cache for every slide in the background (keeps navigation and printing smooth)
  function preloadAll() {
    let k = 0;
    const step = () => {
      for (let n = 0; n < 3 && k < N; n++, k++) {
        const s = slides[k];
        if (s._h) continue;
        s.querySelectorAll('img[data-src]').forEach((im) => { im.src = im.dataset.src; im.removeAttribute('data-src'); });
        s.querySelectorAll('video[data-poster]').forEach((v) => { if (!v.poster) v.poster = v.dataset.poster; });
      }
      if (k < N) setTimeout(step, 250);
    };
    setTimeout(step, 1200);
  }

  /* ---------- start ---------- */
  wireVideos();
  fit();
  if (THUMB) {
    root.classList.add('thumb');
    const n = Math.max(1, Math.min(N, parseInt(qs.get('thumb'), 10) || 1));
    hydrate(n - 1);
    go(n - 1, 'end', { instant: true });
    if (qs.has('step')) setState(n - 1, parseInt(qs.get('step'), 10) || 0);
    slides[n - 1].querySelectorAll('video').forEach((v) => { v.preload = 'auto'; });
  } else if (qs.has('selftest')) {
    const errs = [], rows = [];
    window.addEventListener('error', (e) => errs.push(String(e.message)));
    try {
      let steps = 0;
      go(0, 'start', { instant: true });
      for (let s = 0; s < N; s++) {
        if (cur !== s) errs.push('expected slide ' + (s + 1) + ' got ' + (cur + 1));
        const groups = D.slides[s].g.length;
        let guard = 0;
        while (gi < groups && guard++ < 500) { next(); steps++; }
        finishLive();
        let hidden = 0;
        for (const tg of D.slides[s].init) for (const e of targets(s, tg)) if (getComputedStyle(e).visibility === 'hidden') hidden++;
        rows.push((s + 1) + ':' + groups + ':' + D.slides[s].init.length + ':' + hidden);
        if (s < N - 1) { next(); flushTransition(); }
      }
      let back = 0;
      while ((cur > 0 || gi > autoCount(0)) && back < 5000) { prev(); flushTransition(); back++; }
      const pre = document.createElement('pre');
      pre.id = 'selftest';
      pre.textContent = JSON.stringify({ ok: errs.length === 0, steps, back, end: cur + 1, rows, errs });
      document.body.appendChild(pre);
    } catch (err) {
      const pre = document.createElement('pre'); pre.id = 'selftest'; pre.textContent = 'EXCEPTION ' + err.stack; document.body.appendChild(pre);
    }
  } else {
    go(fromHash() ?? 0, 'start', { instant: true });
    deckEl.focus({ preventScroll: true });
    pokeUI();
    preloadAll();
  }
  window.deck = { next, prev, go: (n) => go(n - 1, 'start'), get slide() { return cur + 1; }, get step() { return gi; }, count: N };
})();
