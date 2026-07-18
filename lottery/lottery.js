(function () {
  "use strict";

  const STORAGE_KEY = "phbay-lottery-v1";
  const $ = (selector) => document.querySelector(selector);
  const elements = {
    participantInput: $("#participantInput"), fileInput: $("#fileInput"), applyParticipants: $("#applyParticipants"),
    participantCount: $("#participantCount"), participantMessage: $("#participantMessage"), prizeList: $("#prizeList"),
    addPrizeButton: $("#addPrizeButton"), prizeSelect: $("#prizeSelect"), drawQuantity: $("#drawQuantity"),
    lotteryStage: $("#lotteryStage"), stageKicker: $("#stageKicker"), rollingName: $("#rollingName"),
    stageDetail: $("#stageDetail"), eligibleCount: $("#eligibleCount"), winnerCount: $("#winnerCount"),
    prizeRemaining: $("#prizeRemaining"), drawButton: $("#drawButton"), drawAllButton: $("#drawAllButton"), drawMessage: $("#drawMessage"),
    winnerList: $("#winnerList"), resultsSummary: $("#resultsSummary"), exportButton: $("#exportButton"),
    resetButton: $("#resetButton"), fullscreenButton: $("#fullscreenButton"), saveState: $("#saveState"), confetti: $("#confetti"),
    ticketMachine: $("#ticketMachine"), poolTickets: $("#poolTickets"), poolCount: $("#poolCount"), winnerReveal: $("#winnerReveal"),
    manualSourceTab: $("#manualSourceTab"), metaSourceTab: $("#metaSourceTab"), manualSourcePanel: $("#manualSourcePanel"),
    metaSourcePanel: $("#metaSourcePanel"), metaConnectionDot: $("#metaConnectionDot"), metaConnectionText: $("#metaConnectionText"),
    adminLoginLink: $("#adminLoginLink"), metaPlatform: $("#metaPlatform"), loadMetaPosts: $("#loadMetaPosts"),
    metaPost: $("#metaPost"), metaKeyword: $("#metaKeyword"), metaCutoff: $("#metaCutoff"), fetchMetaComments: $("#fetchMetaComments"),
    metaPreview: $("#metaPreview"), metaPreviewSummary: $("#metaPreviewSummary"), metaNameList: $("#metaNameList"),
    applyMetaParticipants: $("#applyMetaParticipants")
  };

  let state = loadState();
  let rollingTimer = null;
  let ticketLoadTimer = null;
  let drawing = false;
  let batchDrawing = false;
  let stageMode = state.participants.length ? "pool" : "empty";
  let metaConfigured = { facebook: false, instagram: false };
  let pendingMetaParticipants = [];

  function defaultState() {
    return {
      participants: [],
      prizes: [
        { id: makeId("prize"), name: "頭獎", quantity: 1 },
        { id: makeId("prize"), name: "貳獎", quantity: 2 },
        { id: makeId("prize"), name: "參獎", quantity: 3 }
      ],
      winners: []
    };
  }

  function makeId(prefix) {
    if (window.crypto && crypto.randomUUID) return prefix + "-" + crypto.randomUUID();
    return prefix + "-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
  }

  function loadState() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved && Array.isArray(saved.participants) && Array.isArray(saved.prizes) && Array.isArray(saved.winners)) return migrateState(saved);
    } catch (error) {
      console.warn("無法讀取抽獎紀錄", error);
    }
    return defaultState();
  }

  function normalizeName(value) {
    return String(value || "").trim().replace(/\s+/g, " ").toLocaleLowerCase();
  }

  function migrateState(saved) {
    const keyMap = new Map();
    const seen = new Set();
    const participants = [];
    saved.participants.forEach((participant) => {
      const oldId = String(participant.id || "").trim();
      const source = String(participant.source || "").trim().toLowerCase();
      const sourceId = String(participant.sourceId || participant.source_id || "").trim();
      const wasGeneratedId = participant.explicitId === false || (participant.explicitId == null && /^P\d{3,}$/i.test(oldId));
      const explicitId = Boolean(oldId) && !wasGeneratedId;
      const id = explicitId ? oldId : "";
      const name = String(participant.name || "").trim();
      const key = source && sourceId ? `source:${source}:${sourceId.toLocaleLowerCase()}`
        : (explicitId ? `id:${id.toLocaleLowerCase()}` : `name:${normalizeName(name)}`);
      keyMap.set(participant.key, key);
      if (!name || seen.has(key)) return;
      seen.add(key);
      participants.push({ id, name, key, explicitId, source, sourceId });
    });
    const participantKeys = new Set(participants.map((participant) => participant.key));
    const winners = saved.winners.map((winner) => {
      const participantKey = keyMap.get(winner.participantKey) || winner.participantKey;
      const participant = participants.find((item) => item.key === participantKey);
      return { ...winner, participantKey, participantId: participant ? participant.id : String(winner.participantId || "").replace(/^P\d{3,}$/i, "") };
    }).filter((winner) => participantKeys.has(winner.participantKey));
    return { participants, prizes: saved.prizes, winners };
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    elements.saveState.textContent = "已儲存於本機";
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  }

  function csvRow(line) {
    const fields = [];
    let current = "";
    let quoted = false;
    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      if (char === '"' && quoted && line[i + 1] === '"') { current += '"'; i += 1; }
      else if (char === '"') quoted = !quoted;
      else if ((char === "," || char === "\t") && !quoted) { fields.push(current.trim()); current = ""; }
      else current += char;
    }
    fields.push(current.trim());
    return fields;
  }

  function parseParticipants(text) {
    const lines = String(text).replace(/^\uFEFF/, "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return [];
    const rows = lines.map(csvRow);
    const first = rows[0].map((value) => value.toLowerCase());
    const hasHeader = first.some((value) => ["id", "編號", "姓名", "name", "參加者", "participant"].includes(value));
    const body = hasHeader ? rows.slice(1) : rows;
    const seen = new Set();
    const participants = [];
    body.forEach((row) => {
      const values = row.filter((value) => value !== "");
      if (!values.length) return;
      const explicitId = values.length > 1;
      const id = explicitId ? values[0].trim() : "";
      const name = values.length > 1 ? values.slice(1).join(" ") : values[0];
      const key = explicitId ? `id:${id.toLocaleLowerCase()}` : `name:${normalizeName(name)}`;
      if (!name || seen.has(key)) return;
      seen.add(key);
      participants.push({ id, name: name.trim(), key, explicitId });
    });
    return participants;
  }

  function participantsToInput() {
    return state.participants.map((participant) => participant.explicitId && participant.id
      ? `${participant.id},${participant.name}` : participant.name).join("\n");
  }

  function renderPrizeRows() {
    elements.prizeList.innerHTML = state.prizes.map((prize) => `
      <div class="prize-row" data-prize-id="${escapeHtml(prize.id)}">
        <input type="text" class="prize-name" value="${escapeHtml(prize.name)}" aria-label="獎項名稱">
        <input type="number" class="prize-quantity" min="1" max="999" value="${prize.quantity}" aria-label="獎項名額">
        <button type="button" class="remove-prize" title="刪除獎項" aria-label="刪除 ${escapeHtml(prize.name)}">×</button>
      </div>`).join("");
  }

  function winnerCountForPrize(prizeId) {
    return state.winners.filter((winner) => winner.prizeId === prizeId).length;
  }

  function selectedPrize() {
    return state.prizes.find((prize) => prize.id === elements.prizeSelect.value) || state.prizes[0];
  }

  function eligibleParticipants() {
    const won = new Set(state.winners.map((winner) => winner.participantKey));
    return state.participants.filter((participant) => !won.has(participant.key));
  }

  function renderTicketPool(animate) {
    const eligible = eligibleParticipants();
    const visible = eligible.slice(0, 60);
    elements.poolTickets.innerHTML = visible.map((participant, index) => {
      const x = 13 + ((index * 37) % 75);
      const y = 55 + ((index * 29) % 35);
      const rotation = ((index * 17) % 31) - 15;
      const delay = Math.min(index, 35) * 0.045;
      const mixDelay = -((index % 9) * 0.04);
      return `<span class="pool-ticket" style="--ticket-x:${x}%;--ticket-y:${y}%;--ticket-r:${rotation}deg;--ticket-delay:${delay}s;--mix-delay:${mixDelay}s">${escapeHtml(participant.name)}</span>`;
    }).join("");
    elements.poolCount.textContent = `${eligible.length} 張抽獎券`;
    if (animate) {
      window.clearTimeout(ticketLoadTimer);
      elements.lotteryStage.classList.remove("pool-mode", "rolling", "winner");
      elements.lotteryStage.classList.add("loading");
      ticketLoadTimer = window.setTimeout(() => {
        elements.lotteryStage.classList.remove("loading");
        elements.lotteryStage.classList.add("pool-mode");
        const prize = selectedPrize();
        const remaining = prize ? Math.max(0, prize.quantity - winnerCountForPrize(prize.id)) : 0;
        elements.stageKicker.textContent = prize ? prize.name : "抽獎池";
        elements.stageDetail.textContent = prize ? `本獎尚有 ${remaining} 個名額` : "請先設定獎項";
      }, Math.min(visible.length, 35) * 45 + 900);
    }
  }

  function showPoolState(animate) {
    stageMode = "pool";
    const prize = selectedPrize();
    const remaining = prize ? Math.max(0, prize.quantity - winnerCountForPrize(prize.id)) : 0;
    elements.lotteryStage.classList.remove("rolling", "winner", "loading", "pool-mode");
    elements.lotteryStage.classList.add(animate ? "loading" : "pool-mode");
    elements.stageKicker.textContent = animate ? "抽獎券投入中" : (prize ? prize.name : "抽獎池");
    elements.stageDetail.textContent = prize ? `本獎尚有 ${remaining} 個名額` : "請先設定獎項";
    renderTicketPool(animate);
  }

  function showEmptyState() {
    stageMode = "empty";
    elements.lotteryStage.classList.remove("pool-mode", "loading", "rolling", "winner");
    elements.stageKicker.textContent = "準備開始";
    elements.rollingName.textContent = "等待名單";
    elements.stageDetail.textContent = "請先套用參加名單並設定獎項";
  }

  function renderPrizeSelect(previousId) {
    const selectedId = previousId || elements.prizeSelect.value;
    elements.prizeSelect.innerHTML = state.prizes.map((prize) => {
      const remaining = Math.max(0, prize.quantity - winnerCountForPrize(prize.id));
      return `<option value="${escapeHtml(prize.id)}">${escapeHtml(prize.name)}（剩 ${remaining}）</option>`;
    }).join("");
    if (state.prizes.some((prize) => prize.id === selectedId)) elements.prizeSelect.value = selectedId;
  }

  function renderWinners() {
    elements.winnerList.innerHTML = state.winners.map((winner, index) => {
      const date = new Date(winner.drawnAt);
      const time = Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit" });
      const meta = [winner.prizeName, winner.participantId, time].filter(Boolean).join(" · ");
      return `<li class="winner-item">
        <span class="winner-rank">${index + 1}</span>
        <div class="winner-info">
          <span class="winner-name">${escapeHtml(winner.name)}</span>
          <span class="winner-meta">${escapeHtml(meta)}</span>
        </div>
        <button type="button" class="undo-winner" data-winner-id="${escapeHtml(winner.id)}" title="撤銷這筆得獎" aria-label="撤銷 ${escapeHtml(winner.name)} 的得獎紀錄">↶</button>
      </li>`;
    }).join("");
    elements.resultsSummary.textContent = state.winners.length ? `共 ${state.winners.length} 位得獎者，皆已自候選名單排除` : "尚未抽出得獎者";
    elements.exportButton.disabled = !state.winners.length;
  }

  function renderStatus() {
    const prize = selectedPrize();
    const eligible = eligibleParticipants();
    const remaining = prize ? Math.max(0, prize.quantity - winnerCountForPrize(prize.id)) : 0;
    elements.participantCount.textContent = state.participants.length;
    elements.eligibleCount.textContent = eligible.length;
    elements.winnerCount.textContent = state.winners.length;
    elements.prizeRemaining.textContent = remaining;
    elements.drawQuantity.max = Math.max(1, Math.min(remaining, eligible.length));
    if (Number(elements.drawQuantity.value) > Number(elements.drawQuantity.max)) elements.drawQuantity.value = elements.drawQuantity.max;
    const canDraw = state.participants.length && prize && remaining > 0 && eligible.length > 0;
    const hasUnfilledPrize = state.prizes.some((item) => item.quantity - winnerCountForPrize(item.id) > 0);
    elements.drawButton.disabled = drawing || batchDrawing || !canDraw;
    elements.drawAllButton.disabled = drawing || batchDrawing || !eligible.length || !hasUnfilledPrize;
    elements.drawAllButton.textContent = batchDrawing ? "正在抽完全部獎項…" : "一次抽完全部獎項";
    if (drawing || batchDrawing || stageMode === "winner") return;
    if (!state.participants.length) {
      showEmptyState();
    } else if (!prize) {
      showPoolState(false);
    } else if (stageMode === "pool" || stageMode === "empty") {
      elements.stageKicker.textContent = remaining ? prize.name : `${prize.name}已抽完`;
      elements.stageDetail.textContent = remaining ? `本獎尚有 ${remaining} 個名額` : "請切換其他獎項，或使用一次抽完";
    }
  }

  function renderAll(selectedId) {
    renderPrizeRows();
    renderPrizeSelect(selectedId);
    renderWinners();
    renderStatus();
    if (state.participants.length && stageMode === "pool") renderTicketPool(false);
  }

  function commitParticipants(participants, message, updateInput) {
    if (!participants.length) {
      elements.participantMessage.textContent = "找不到有效名單，請確認每行至少有一個姓名。";
      elements.participantMessage.classList.add("error");
      return false;
    }
    const oldKeys = new Set(participants.map((participant) => participant.key));
    const removedWinners = state.winners.filter((winner) => !oldKeys.has(winner.participantKey)).length;
    state.participants = participants;
    if (removedWinners) state.winners = state.winners.filter((winner) => oldKeys.has(winner.participantKey));
    if (updateInput) elements.participantInput.value = participantsToInput();
    elements.participantMessage.textContent = `${message || `已套用 ${participants.length} 人`}${removedWinners ? `，並移除 ${removedWinners} 筆不在新名單中的紀錄` : ""}。`;
    elements.participantMessage.classList.remove("error");
    saveState();
    stageMode = "pool";
    renderAll();
    showPoolState(true);
    return true;
  }

  function applyParticipantText(text) {
    return commitParticipants(parseParticipants(text), "", false);
  }

  function switchSource(source) {
    const meta = source === "meta";
    elements.manualSourceTab.classList.toggle("active", !meta);
    elements.metaSourceTab.classList.toggle("active", meta);
    elements.manualSourceTab.setAttribute("aria-selected", String(!meta));
    elements.metaSourceTab.setAttribute("aria-selected", String(meta));
    elements.manualSourcePanel.hidden = meta;
    elements.metaSourcePanel.hidden = !meta;
    if (meta) loadMetaStatus();
  }

  async function metaRequest(path, options) {
    const response = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...options
    });
    let payload = {};
    try { payload = await response.json(); } catch (error) { payload = {}; }
    if (!response.ok || !payload.ok) {
      const failure = new Error(payload.error || "Meta 名單服務目前無法使用");
      failure.status = response.status;
      throw failure;
    }
    return payload;
  }

  function setMetaConnection(kind, text, showLogin) {
    elements.metaConnectionDot.className = `connection-dot ${kind || ""}`.trim();
    elements.metaConnectionText.textContent = text;
    elements.adminLoginLink.hidden = !showLogin;
  }

  function resetMetaPosts(message) {
    elements.metaPost.innerHTML = `<option value="">${escapeHtml(message || "尚未載入貼文")}</option>`;
    elements.metaPost.disabled = true;
    elements.fetchMetaComments.disabled = true;
    elements.metaPreview.hidden = true;
    pendingMetaParticipants = [];
  }

  async function loadMetaStatus() {
    setMetaConnection("", "正在確認連線…", false);
    try {
      const payload = await metaRequest("/api/lottery/meta/status");
      metaConfigured = payload.configured || metaConfigured;
      const platform = elements.metaPlatform.value;
      const configuredCount = [metaConfigured.facebook, metaConfigured.instagram].filter(Boolean).length;
      if (configuredCount === 2) setMetaConnection("ready", "Facebook 與 Instagram 已連線", false);
      else if (configuredCount === 1) setMetaConnection("partial", `${metaConfigured.facebook ? "Facebook" : "Instagram"} 已連線`, false);
      else setMetaConnection("error", "Meta 連線尚未設定", false);
      elements.loadMetaPosts.disabled = !metaConfigured[platform];
    } catch (error) {
      const needsLogin = error.status === 401;
      setMetaConnection("error", needsLogin ? "請先登入潮旅管理後台" : error.message, needsLogin);
      elements.loadMetaPosts.disabled = true;
    }
  }

  function postOptionLabel(post) {
    const date = post.timestamp ? new Date(post.timestamp) : null;
    const dateLabel = date && !Number.isNaN(date.getTime())
      ? date.toLocaleDateString("zh-TW", { month: "2-digit", day: "2-digit" }) : "";
    const text = String(post.text || "無文字貼文").replace(/\s+/g, " ").slice(0, 55);
    return [dateLabel, text].filter(Boolean).join(" · ");
  }

  async function loadMetaPosts() {
    const platform = elements.metaPlatform.value;
    elements.loadMetaPosts.disabled = true;
    elements.loadMetaPosts.textContent = "載入中…";
    resetMetaPosts("正在載入貼文…");
    try {
      const payload = await metaRequest(`/api/lottery/meta/posts?platform=${encodeURIComponent(platform)}`);
      elements.metaPost.innerHTML = "";
      if (!payload.posts.length) {
        resetMetaPosts("找不到可用貼文");
        return;
      }
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "請選擇活動貼文";
      elements.metaPost.appendChild(placeholder);
      payload.posts.forEach((post) => {
        const option = document.createElement("option");
        option.value = post.id;
        option.textContent = postOptionLabel(post);
        elements.metaPost.appendChild(option);
      });
      elements.metaPost.disabled = false;
      setMetaConnection("ready", `${platform === "facebook" ? "Facebook" : "Instagram"} 已載入 ${payload.posts.length} 篇貼文`, false);
    } catch (error) {
      resetMetaPosts("貼文載入失敗");
      setMetaConnection("error", error.message, error.status === 401);
    } finally {
      elements.loadMetaPosts.textContent = "載入最近貼文";
      elements.loadMetaPosts.disabled = !metaConfigured[platform];
    }
  }

  async function fetchMetaComments() {
    const platform = elements.metaPlatform.value;
    const postId = elements.metaPost.value;
    if (!postId) return;
    elements.fetchMetaComments.disabled = true;
    elements.fetchMetaComments.textContent = "整理留言中…";
    elements.metaPreview.hidden = true;
    try {
      const payload = await metaRequest("/api/lottery/meta/comments", {
        method: "POST",
        body: JSON.stringify({
          platform, post_id: postId, keyword: elements.metaKeyword.value.trim(),
          cutoff: elements.metaCutoff.value ? new Date(elements.metaCutoff.value).toISOString() : ""
        })
      });
      pendingMetaParticipants = payload.participants || [];
      const stats = payload.stats || {};
      const summaryParts = [
        `${stats.comments || 0} 則留言`,
        `${stats.eligible || 0} 位有效參加者`,
        `重複 ${stats.duplicates || 0}`
      ];
      if (stats.keyword_excluded) summaryParts.push(`未含關鍵字 ${stats.keyword_excluded}`);
      if (stats.after_cutoff) summaryParts.push(`超過截止時間 ${stats.after_cutoff}`);
      if (stats.missing_author) summaryParts.push(`無作者資料 ${stats.missing_author}`);
      if (stats.truncated) summaryParts.push("已達 1,000 則上限");
      elements.metaPreviewSummary.textContent = summaryParts.join(" · ");
      elements.metaNameList.innerHTML = pendingMetaParticipants.slice(0, 100)
        .map((participant) => `<li title="${escapeHtml(participant.name)}">${escapeHtml(participant.name)}</li>`).join("");
      elements.applyMetaParticipants.disabled = !pendingMetaParticipants.length;
      elements.metaPreview.hidden = false;
    } catch (error) {
      setMetaConnection("error", error.message, error.status === 401);
    } finally {
      elements.fetchMetaComments.textContent = "整理留言名單";
      elements.fetchMetaComments.disabled = !elements.metaPost.value;
    }
  }

  function applyMetaParticipants() {
    const participants = pendingMetaParticipants.map((participant) => {
      const source = String(participant.source || elements.metaPlatform.value).toLowerCase();
      const sourceId = String(participant.source_id || "");
      return {
        id: "", name: String(participant.name || "").trim(), explicitId: false,
        source, sourceId, key: `source:${source}:${sourceId.toLocaleLowerCase()}`
      };
    }).filter((participant) => participant.name && participant.sourceId);
    if (commitParticipants(participants, `已從 ${elements.metaPlatform.value === "facebook" ? "Facebook" : "Instagram"} 匯入 ${participants.length} 人`, true)) {
      elements.metaPreview.hidden = true;
    }
  }

  function secureRandomIndex(length) {
    if (length <= 0) return -1;
    if (!window.crypto || !crypto.getRandomValues) return Math.floor(Math.random() * length);
    const max = 0x100000000;
    const limit = max - (max % length);
    const value = new Uint32Array(1);
    do crypto.getRandomValues(value); while (value[0] >= limit);
    return value[0] % length;
  }

  function launchConfetti() {
    const colors = ["#f3b63f", "#45b8c8", "#e95f4f", "#ffffff", "#268b6b"];
    elements.confetti.innerHTML = Array.from({ length: 70 }, (_, index) => {
      const left = secureRandomIndex(101);
      const delay = secureRandomIndex(45) / 100;
      const drift = secureRandomIndex(161) - 80;
      const color = colors[index % colors.length];
      return `<i class="confetti-piece" style="left:${left}%;animation-delay:${delay}s;--drift:${drift}px;background:${color}"></i>`;
    }).join("");
    window.setTimeout(() => { elements.confetti.innerHTML = ""; }, 2400);
  }

  function finishDraw(pool, prize, count, resolve) {
    window.clearInterval(rollingTimer);
    rollingTimer = null;
    const selected = [];
    for (let i = 0; i < count; i += 1) {
      const index = secureRandomIndex(pool.length);
      selected.push(pool.splice(index, 1)[0]);
    }
    const drawnAt = new Date().toISOString();
    selected.forEach((participant) => state.winners.push({
      id: makeId("winner"), participantKey: participant.key, participantId: participant.id,
      name: participant.name, prizeId: prize.id, prizeName: prize.name, drawnAt
    }));
    drawing = false;
    stageMode = "winner";
    elements.lotteryStage.classList.remove("rolling", "pool-mode", "loading");
    elements.lotteryStage.classList.add("winner");
    elements.stageKicker.textContent = `${prize.name} 得獎者`;
    elements.rollingName.textContent = selected.map((participant) => participant.name).join("、");
    const ids = selected.map((participant) => participant.id).filter(Boolean);
    elements.stageDetail.textContent = ids.length ? ids.join(" · ") : `本次抽出 ${selected.length} 位`;
    elements.drawMessage.textContent = `恭喜 ${selected.map((participant) => participant.name).join("、")}！`;
    saveState();
    renderPrizeSelect(prize.id);
    renderWinners();
    renderTicketPool(false);
    renderStatus();
    launchConfetti();
    window.setTimeout(() => elements.lotteryStage.classList.remove("winner"), 900);
    if (resolve) resolve(selected);
  }

  function performDraw(prize, count, duration) {
    const pool = eligibleParticipants();
    if (!prize || !pool.length || count < 1) return Promise.resolve([]);
    drawing = true;
    renderTicketPool(false);
    renderStatus();
    elements.drawMessage.textContent = "正在隨機抽選…";
    elements.stageKicker.textContent = prize.name;
    elements.stageDetail.textContent = `本次將抽出 ${count} 位得獎者`;
    elements.lotteryStage.classList.remove("pool-mode", "loading", "winner");
    elements.lotteryStage.classList.add("rolling");
    rollingTimer = window.setInterval(() => {
      const preview = pool[secureRandomIndex(pool.length)];
      elements.rollingName.textContent = preview ? preview.name : "抽選中";
    }, 70);
    return new Promise((resolve) => {
      window.setTimeout(() => finishDraw(pool.slice(), prize, count, resolve), duration || 2200);
    });
  }

  async function startDraw() {
    if (drawing || batchDrawing) return;
    const prize = selectedPrize();
    const pool = eligibleParticipants();
    const remaining = prize ? Math.max(0, prize.quantity - winnerCountForPrize(prize.id)) : 0;
    const requested = Math.max(1, Number.parseInt(elements.drawQuantity.value, 10) || 1);
    const count = Math.min(requested, remaining, pool.length);
    await performDraw(prize, count, 2200);
  }

  function wait(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  async function drawAllPrizes() {
    if (drawing || batchDrawing) return;
    const initialCandidates = eligibleParticipants().length;
    const totalRemaining = state.prizes.reduce((total, prize) => total + Math.max(0, prize.quantity - winnerCountForPrize(prize.id)), 0);
    if (!initialCandidates || !totalRemaining) return;
    batchDrawing = true;
    let lastDraw = null;
    renderStatus();
    for (const prize of state.prizes) {
      const candidates = eligibleParticipants();
      const remaining = Math.max(0, prize.quantity - winnerCountForPrize(prize.id));
      if (!candidates.length) break;
      if (!remaining) continue;
      renderPrizeSelect(prize.id);
      elements.prizeSelect.value = prize.id;
      const count = Math.min(remaining, candidates.length);
      const selected = await performDraw(prize, count, 1500);
      lastDraw = { prize, selected };
      if (eligibleParticipants().length && prize !== state.prizes[state.prizes.length - 1]) await wait(700);
    }
    batchDrawing = false;
    renderPrizeSelect(lastDraw ? lastDraw.prize.id : elements.prizeSelect.value);
    if (lastDraw) {
      stageMode = "winner";
      elements.lotteryStage.classList.remove("rolling", "pool-mode", "loading");
      elements.lotteryStage.classList.add("winner");
      elements.stageKicker.textContent = `${lastDraw.prize.name} 得獎者`;
      elements.rollingName.textContent = lastDraw.selected.map((participant) => participant.name).join("、");
      const ids = lastDraw.selected.map((participant) => participant.id).filter(Boolean);
      elements.stageDetail.textContent = ids.length ? ids.join(" · ") : `本次抽出 ${lastDraw.selected.length} 位`;
    }
    renderStatus();
    if (initialCandidates < totalRemaining) {
      elements.drawMessage.textContent = `候選人只有 ${initialCandidates} 位，已全部抽出；仍有獎項名額未完成。`;
    } else {
      elements.drawMessage.textContent = "全部獎項已依設定順序抽選完成。";
    }
  }

  function csvEscape(value) {
    const text = String(value == null ? "" : value);
    return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function exportWinners() {
    if (!state.winners.length) return;
    const rows = [["抽出順序", "獎項", "參加者編號", "姓名", "抽獎時間"]];
    state.winners.forEach((winner, index) => rows.push([index + 1, winner.prizeName, winner.participantId, winner.name, winner.drawnAt]));
    const csv = "\uFEFF" + rows.map((row) => row.map(csvEscape).join(",")).join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `潮旅抽獎結果_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  elements.applyParticipants.addEventListener("click", () => applyParticipantText(elements.participantInput.value));
  elements.manualSourceTab.addEventListener("click", () => switchSource("manual"));
  elements.metaSourceTab.addEventListener("click", () => switchSource("meta"));
  elements.metaPlatform.addEventListener("change", () => {
    resetMetaPosts();
    elements.loadMetaPosts.disabled = !metaConfigured[elements.metaPlatform.value];
    const platformName = elements.metaPlatform.value === "facebook" ? "Facebook" : "Instagram";
    setMetaConnection(metaConfigured[elements.metaPlatform.value] ? "ready" : "error",
      metaConfigured[elements.metaPlatform.value] ? `${platformName} 已連線` : `${platformName} 尚未設定`, false);
  });
  elements.loadMetaPosts.addEventListener("click", loadMetaPosts);
  elements.metaPost.addEventListener("change", () => {
    elements.fetchMetaComments.disabled = !elements.metaPost.value;
    elements.metaPreview.hidden = true;
    pendingMetaParticipants = [];
  });
  elements.fetchMetaComments.addEventListener("click", fetchMetaComments);
  elements.applyMetaParticipants.addEventListener("click", applyMetaParticipants);
  elements.fileInput.addEventListener("change", async () => {
    const file = elements.fileInput.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      elements.participantInput.value = text;
      applyParticipantText(text);
    } catch (error) {
      elements.participantMessage.textContent = "檔案讀取失敗，請改用 CSV 或 TXT。";
      elements.participantMessage.classList.add("error");
    }
    elements.fileInput.value = "";
  });

  elements.addPrizeButton.addEventListener("click", () => {
    const prize = { id: makeId("prize"), name: `獎項 ${state.prizes.length + 1}`, quantity: 1 };
    state.prizes.push(prize);
    saveState();
    renderAll(prize.id);
  });

  elements.prizeList.addEventListener("input", (event) => {
    const row = event.target.closest(".prize-row");
    if (!row) return;
    const prize = state.prizes.find((item) => item.id === row.dataset.prizeId);
    if (!prize) return;
    if (event.target.classList.contains("prize-name")) prize.name = event.target.value.trimStart();
    if (event.target.classList.contains("prize-quantity")) prize.quantity = Math.max(1, Number.parseInt(event.target.value, 10) || 1);
    state.winners.filter((winner) => winner.prizeId === prize.id).forEach((winner) => { winner.prizeName = prize.name || "未命名獎項"; });
    saveState();
    renderPrizeSelect(prize.id);
    renderWinners();
    renderStatus();
  });

  elements.prizeList.addEventListener("click", (event) => {
    const button = event.target.closest(".remove-prize");
    if (!button) return;
    const row = button.closest(".prize-row");
    const prize = state.prizes.find((item) => item.id === row.dataset.prizeId);
    if (!prize) return;
    if (winnerCountForPrize(prize.id) && !window.confirm(`「${prize.name}」已有得獎紀錄，刪除獎項也會刪除這些紀錄。確定繼續？`)) return;
    state.prizes = state.prizes.filter((item) => item.id !== prize.id);
    state.winners = state.winners.filter((winner) => winner.prizeId !== prize.id);
    saveState();
    renderAll();
  });

  elements.prizeSelect.addEventListener("change", () => {
    if (drawing || batchDrawing) return;
    showPoolState(false);
    renderStatus();
  });
  elements.drawButton.addEventListener("click", startDraw);
  elements.drawAllButton.addEventListener("click", drawAllPrizes);
  elements.exportButton.addEventListener("click", exportWinners);
  elements.winnerList.addEventListener("click", (event) => {
    const button = event.target.closest(".undo-winner");
    if (!button || drawing) return;
    const winner = state.winners.find((item) => item.id === button.dataset.winnerId);
    if (!winner || !window.confirm(`確定撤銷 ${winner.name} 的「${winner.prizeName}」得獎紀錄？`)) return;
    state.winners = state.winners.filter((item) => item.id !== winner.id);
    saveState();
    renderPrizeSelect(winner.prizeId);
    renderWinners();
    renderStatus();
  });

  elements.resetButton.addEventListener("click", () => {
    if (!window.confirm("確定清除全部名單、獎項與得獎紀錄？這個動作無法復原。")) return;
    state = defaultState();
    localStorage.removeItem(STORAGE_KEY);
    elements.participantInput.value = "";
    elements.participantMessage.textContent = "名單只會保留在這台裝置。";
    elements.drawMessage.textContent = "";
    stageMode = "empty";
    renderAll();
    saveState();
  });

  elements.fullscreenButton.addEventListener("click", async () => {
    try {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
      else await document.exitFullscreen();
    } catch (error) {
      elements.drawMessage.textContent = "此瀏覽器目前不允許全螢幕模式。";
    }
  });

  elements.participantInput.value = participantsToInput();
  renderAll();
  if (state.participants.length) showPoolState(false);
})();
