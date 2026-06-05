const areaOptions = [
  "图书馆周边",
  "食堂周边",
  "宿舍区",
  "教学楼",
  "体育馆",
  "湖畔步道",
  "校门附近",
  "其他",
];

let cats = [];
let currentUser = null;
let editingId = null;
let activeDetailId = null;
let lastDetailTrigger = null;
let detailCloseTimer = null;
let adminCloseTimer = null;
let heartbeatTimer = null;
let toastTimer = null;

const loginScreen = document.querySelector("#loginScreen");
const loginForm = document.querySelector("#loginForm");
const loginButton = document.querySelector("#loginButton");
const loginError = document.querySelector("#loginError");
const appShell = document.querySelector("#appShell");
const form = document.querySelector("#catForm");
const grid = document.querySelector("#catGrid");
const emptyState = document.querySelector("#emptyState");
const searchInput = document.querySelector("#searchInput");
const areaFilter = document.querySelector("#areaFilter");
const campusAreaSuggestions = document.querySelector("#campusAreaSuggestions");
const statusFilter = document.querySelector("#statusFilter");
const careFilter = document.querySelector("#careFilter");
const resultText = document.querySelector("#resultText");
const registryPreview = document.querySelector("#registryPreview");
const submitText = document.querySelector("#submitText");
const cancelEditBtn = document.querySelector("#cancelEditBtn");
const photoInput = document.querySelector("#photoInput");
const photoDataInput = document.querySelector("#photoData");
const photoPreview = document.querySelector("#photoPreview");
const removePhotoBtn = document.querySelector("#removePhotoBtn");
const readonlyNotice = document.querySelector("#readonlyNotice");
const detailShell = document.querySelector("#detailShell");
const detailPage = document.querySelector("#detailPage");
const detailContent = document.querySelector("#detailContent");
const adminShell = document.querySelector("#adminShell");
const adminMetrics = document.querySelector("#adminMetrics");
const visitorTableBody = document.querySelector("#visitorTableBody");
const logTableBody = document.querySelector("#logTableBody");
const visitorCountText = document.querySelector("#visitorCountText");
const toast = document.querySelector("#toast");

const icons = {
  download: '<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>',
  upload: '<svg viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/></svg>',
  refresh: '<svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 1-15.5 6.2"/><path d="M3 12A9 9 0 0 1 18.5 5.8"/><path d="M18 2v5h5"/><path d="M6 22v-5H1"/></svg>',
  eraser: '<svg viewBox="0 0 24 24"><path d="M7 21h9"/><path d="M15.5 3.5l5 5L9 20H4l-2-2z"/><path d="M13 6l5 5"/></svg>',
  save: '<svg viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><path d="M17 21v-8H7v8"/><path d="M7 3v5h8"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14"/><path d="M5 12h14"/></svg>',
  search: '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/></svg>',
  edit: '<svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',
  eye: '<svg viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  x: '<svg viewBox="0 0 24 24"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
  login: '<svg viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><path d="m10 17 5-5-5-5"/><path d="M15 12H3"/></svg>',
  logout: '<svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/></svg>',
  chart: '<svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 16v-4"/><path d="M12 16V8"/><path d="M17 16V5"/></svg>',
  lock: '<svg viewBox="0 0 24 24"><rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
};

document.querySelectorAll("[data-icon]").forEach((node) => {
  node.innerHTML = icons[node.dataset.icon] || "";
});

function isAdmin() {
  return currentUser?.role === "admin";
}

async function api(path, options = {}) {
  const request = {
    method: options.method || "GET",
    headers: {},
  };
  if (options.body !== undefined) {
    request.headers["Content-Type"] = "application/json";
    request.body = JSON.stringify(options.body);
  }

  const response = await fetch(path, request);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && currentUser) {
      showLogin("登录已失效，请重新进入系统。");
    }
    throw new Error(payload.error || "请求失败");
  }
  return payload;
}

function showToast(message, tone = "success") {
  window.clearTimeout(toastTimer);
  toast.textContent = message;
  toast.dataset.tone = tone;
  toast.hidden = false;
  requestAnimationFrame(() => toast.classList.add("show"));
  toastTimer = window.setTimeout(() => {
    toast.classList.remove("show");
    window.setTimeout(() => {
      toast.hidden = true;
    }, 220);
  }, 2600);
}

function setLoginError(message = "") {
  loginError.textContent = message;
  loginError.hidden = !message;
}

function showLogin(message = "") {
  currentUser = null;
  cats = [];
  window.clearInterval(heartbeatTimer);
  heartbeatTimer = null;
  closeDetail({ restoreFocus: false });
  closeAdmin();
  appShell.hidden = true;
  loginScreen.hidden = false;
  setLoginError(message);
  document.querySelector("#loginStudentId").focus({ preventScroll: true });
}

async function enterApp(user) {
  currentUser = user;
  loginScreen.hidden = true;
  appShell.hidden = false;
  appShell.classList.toggle("viewer-mode", !isAdmin());
  document.querySelector("#userName").textContent = `${user.name} · ${user.studentId}`;
  document.querySelector("#userRole").textContent = isAdmin() ? "管理员" : "只读访客";
  readonlyNotice.hidden = isAdmin();
  document.querySelectorAll("[data-admin-only]").forEach((node) => {
    node.hidden = !isAdmin();
  });
  resetForm();
  await loadCats();
  window.clearInterval(heartbeatTimer);
  heartbeatTimer = window.setInterval(() => {
    api("/api/heartbeat", { method: "POST" }).catch(() => {});
  }, 60000);
}

async function bootstrap() {
  try {
    const payload = await api("/api/session");
    await enterApp(payload.user);
  } catch {
    showLogin();
  }
}

async function handleLogin(event) {
  event.preventDefault();
  setLoginError();
  const data = Object.fromEntries(new FormData(loginForm));
  const studentId = data.studentId.trim();
  const name = data.name.trim();
  if (!/^\d{9}$/.test(studentId)) {
    setLoginError("学号必须为 9 位数字。");
    document.querySelector("#loginStudentId").focus();
    return;
  }
  if (!name) {
    setLoginError("请输入姓名。");
    document.querySelector("#loginName").focus();
    return;
  }

  loginButton.disabled = true;
  loginButton.querySelector("span:last-child").textContent = "正在进入";
  try {
    const payload = await api("/api/login", {
      method: "POST",
      body: {
        studentId,
        name,
      },
    });
    loginForm.reset();
    await enterApp(payload.user);
  } catch (error) {
    setLoginError(error.message);
  } finally {
    loginButton.disabled = false;
    loginButton.querySelector("span:last-child").textContent = "进入系统";
  }
}

document.querySelector("#loginStudentId").addEventListener("input", (event) => {
  event.target.value = event.target.value.replace(/\D/g, "").slice(0, 9);
});

async function handleLogout() {
  try {
    await api("/api/logout", { method: "POST" });
  } catch {
    // Local state still needs to be cleared when the server session is already gone.
  }
  showLogin();
}

async function loadCats() {
  const payload = await api("/api/cats");
  cats = payload.cats || [];
  render();
}

function fillAreaFilter() {
  const selected = areaFilter.value || "all";
  const knownAreas = Array.from(new Set([...areaOptions, ...cats.map((cat) => cat.campusArea).filter(Boolean)]));
  areaFilter.innerHTML = '<option value="all">全部区域</option>';
  campusAreaSuggestions.innerHTML = "";
  knownAreas.forEach((area) => {
    const option = document.createElement("option");
    option.value = area;
    option.textContent = area;
    areaFilter.append(option);

    const suggestion = document.createElement("option");
    suggestion.value = area;
    campusAreaSuggestions.append(suggestion);
  });
  areaFilter.value = knownAreas.includes(selected) ? selected : "all";
}

function safePhotoSrc(value) {
  const text = String(value || "");
  return /^data:image\/(jpeg|jpg|png|webp);base64,/i.test(text) ? text : "";
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(reader.result));
    reader.addEventListener("error", reject);
    reader.readAsDataURL(file);
  });
}

function loadImage(dataUrl) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.addEventListener("load", () => resolve(image));
    image.addEventListener("error", reject);
    image.src = dataUrl;
  });
}

async function compressPhoto(file) {
  if (!file || !file.type.startsWith("image/")) {
    throw new Error("请选择图片文件");
  }

  const dataUrl = await readFileAsDataUrl(file);
  const image = await loadImage(dataUrl);
  const maxSide = 900;
  const scale = Math.min(1, maxSide / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  context.drawImage(image, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", 0.82);
}

function renderPhotoPreview(photoData) {
  const src = safePhotoSrc(photoData);
  photoPreview.innerHTML = "";

  if (src) {
    const image = document.createElement("img");
    image.src = src;
    image.alt = "";
    photoPreview.append(image);
  } else {
    const placeholder = document.createElement("span");
    placeholder.className = "photo-placeholder";
    placeholder.textContent = "暂无照片";
    photoPreview.append(placeholder);
  }

  photoPreview.classList.toggle("empty", !src);
  removePhotoBtn.hidden = !src;
}

async function handlePhotoChange(event) {
  const file = event.target.files[0];
  if (!file) return;

  try {
    photoInput.disabled = true;
    const photoData = await compressPhoto(file);
    photoDataInput.value = photoData;
    renderPhotoPreview(photoData);
  } catch (error) {
    showToast(error.message || "照片读取失败，请换一张图片试试。", "error");
  } finally {
    photoInput.disabled = false;
    photoInput.value = "";
  }
}

function formDataToCat() {
  const data = Object.fromEntries(new FormData(form));
  return {
    photoData: data.photoData || "",
    name: data.name.trim(),
    gender: data.gender,
    coat: data.coat.trim(),
    age: data.age,
    campusArea: data.campusArea,
    location: data.location.trim(),
    status: data.status,
    sterilized: data.sterilized,
    vaccinated: data.vaccinated,
    caretaker: data.caretaker.trim(),
    notes: data.notes.trim(),
  };
}

async function saveCat(event) {
  event.preventDefault();
  if (!isAdmin()) {
    showToast("只有管理员可以保存档案。", "error");
    return;
  }
  if (!form.reportValidity()) return;

  const cat = formDataToCat();
  try {
    if (editingId) {
      await api(`/api/cats/${encodeURIComponent(editingId)}`, { method: "PUT", body: cat });
      showToast("档案已更新");
    } else {
      await api("/api/cats", { method: "POST", body: cat });
      showToast("档案已新增");
    }
    resetForm();
    await loadCats();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function resetForm() {
  editingId = null;
  form.reset();
  document.querySelector("#catId").value = "";
  photoDataInput.value = "";
  photoInput.value = "";
  renderPhotoPreview("");
  registryPreview.value = "自动生成";
  submitText.textContent = "保存档案";
  cancelEditBtn.hidden = true;
  document.querySelector("#formTitle").textContent = "新增小猫档案";
}

function editCat(id) {
  if (!isAdmin()) {
    showToast("当前账号只能查看档案。", "error");
    return;
  }
  const cat = cats.find((item) => item.id === id);
  if (!cat) return;

  editingId = id;
  Object.entries(cat).forEach(([key, value]) => {
    const field = form.elements[key];
    if (field) field.value = value || "";
  });
  registryPreview.value = cat.registryNo;
  photoDataInput.value = cat.photoData || "";
  renderPhotoPreview(cat.photoData || "");
  submitText.textContent = "更新档案";
  cancelEditBtn.hidden = false;
  document.querySelector("#formTitle").textContent = `编辑 ${cat.name}`;
  document.querySelector(".entry-panel").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function deleteCat(id) {
  if (!isAdmin()) {
    showToast("当前账号只能查看档案。", "error");
    return;
  }
  const cat = cats.find((item) => item.id === id);
  if (!cat) return;
  if (!confirm(`确定删除「${cat.name}」的档案吗？`)) return;

  try {
    if (activeDetailId === id) closeDetail({ restoreFocus: false });
    await api(`/api/cats/${encodeURIComponent(id)}`, { method: "DELETE" });
    if (editingId === id) resetForm();
    await loadCats();
    showToast("档案已删除");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function filteredCats() {
  const query = searchInput.value.trim().toLowerCase();
  const area = areaFilter.value;
  const status = statusFilter.value;
  const care = careFilter.value;

  return cats.filter((cat) => {
    const searchText = [
      cat.registryNo,
      cat.name,
      cat.gender,
      cat.coat,
      cat.age,
      cat.campusArea,
      cat.location,
      cat.status,
      cat.sterilized,
      cat.vaccinated,
      cat.caretaker,
      cat.notes,
    ]
      .join(" ")
      .toLowerCase();

    const careMatched = care === "all" || cat.sterilized === care || cat.vaccinated === care;

    return (
      (!query || searchText.includes(query)) &&
      (area === "all" || cat.campusArea === area) &&
      (status === "all" || cat.status === status) &&
      careMatched
    );
  });
}

function badgeClass(status) {
  if (status === "医疗观察") return "observe";
  if (status === "待领养" || status === "已领养") return "adopt";
  if (status === "失踪") return "missing";
  return "resident";
}

function avatarSeed(cat) {
  const palette = [
    "linear-gradient(135deg, #2f6f5e, #247c86)",
    "linear-gradient(135deg, #b8553e, #c08a2a)",
    "linear-gradient(135deg, #486f9f, #2f6f5e)",
    "linear-gradient(135deg, #334155, #b8553e)",
  ];
  const index = Math.abs([...cat.name].reduce((sum, char) => sum + char.charCodeAt(0), 0)) % palette.length;
  return palette[index];
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function displayValue(value) {
  return escapeHtml(value || "未记录");
}

function formatDate(value) {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "未记录";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function detailItem(label, value, full = false) {
  return `
    <section class="detail-item${full ? " full" : ""}">
      <span class="detail-label">${escapeHtml(label)}</span>
      <span class="detail-value">${displayValue(value)}</span>
    </section>
  `;
}

function detailHtml(cat) {
  const safeName = escapeHtml(cat.name);
  const photoSrc = safePhotoSrc(cat.photoData);
  const visual = photoSrc
    ? `<img src="${escapeHtml(photoSrc)}" alt="${safeName}的照片">`
    : `<div class="detail-visual-fallback">${escapeHtml(cat.name.slice(0, 1))}</div>`;
  const editAction = isAdmin()
    ? `<button class="primary-button" type="button" data-detail-edit="${escapeHtml(cat.id)}">${icons.edit}<span>编辑档案</span></button>`
    : "";

  return `
    <div class="detail-content">
      <div class="detail-visual">
        ${visual}
        <div class="detail-photo-caption">
          <h2>${safeName}</h2>
          <p>${escapeHtml(cat.registryNo)}</p>
        </div>
      </div>

      <div class="detail-info">
        <header class="detail-header">
          <div class="detail-header-row">
            <span class="badge ${badgeClass(cat.status)}">${escapeHtml(cat.status)}</span>
            <span class="detail-registry">${escapeHtml(cat.registryNo)}</span>
          </div>
          <h2 id="detailName">${safeName}</h2>
        </header>

        <div class="detail-grid">
          ${detailItem("性别", cat.gender)}
          ${detailItem("年龄阶段", cat.age)}
          ${detailItem("毛色特征", cat.coat, true)}
          ${detailItem("活动区域", cat.campusArea)}
          ${detailItem("固定点位", cat.location)}
          ${detailItem("绝育情况", cat.sterilized)}
          ${detailItem("疫苗情况", cat.vaccinated)}
          ${detailItem("联系人", cat.caretaker)}
          ${detailItem("当前状态", cat.status)}
          ${detailItem("创建时间", formatDate(cat.createdAt))}
          ${detailItem("更新时间", formatDate(cat.updatedAt))}
        </div>

        <section>
          <span class="detail-label">性格与备注</span>
          <p class="detail-notes">${displayValue(cat.notes)}</p>
        </section>

        <div class="detail-actions">
          ${editAction}
          <button class="secondary-button" type="button" data-detail-close>关闭详情</button>
        </div>
      </div>
    </div>
  `;
}

function setDetailOrigin(trigger) {
  const rect = trigger?.getBoundingClientRect?.();
  if (!rect) {
    detailPage.style.setProperty("--detail-origin-x", "50%");
    detailPage.style.setProperty("--detail-origin-y", "50%");
    return;
  }

  const x = ((rect.left + rect.width / 2) / window.innerWidth) * 100;
  const y = ((rect.top + rect.height / 2) / window.innerHeight) * 100;
  detailPage.style.setProperty("--detail-origin-x", `${Math.round(x)}%`);
  detailPage.style.setProperty("--detail-origin-y", `${Math.round(y)}%`);
}

function openDetail(id, trigger) {
  const cat = cats.find((item) => item.id === id);
  if (!cat) return;

  if (detailCloseTimer) {
    window.clearTimeout(detailCloseTimer);
    detailCloseTimer = null;
  }

  activeDetailId = id;
  lastDetailTrigger = trigger || document.activeElement;
  setDetailOrigin(trigger);
  detailContent.innerHTML = detailHtml(cat);
  detailShell.hidden = false;
  detailShell.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  detailShell.classList.remove("is-closing", "is-open");
  appShell.classList.remove("detail-open");
  detailPage.getBoundingClientRect();
  appShell.classList.add("detail-open");
  detailShell.classList.add("is-open");
  detailPage.querySelector(".detail-close")?.focus({ preventScroll: true });
  api("/api/track", { method: "POST", body: { action: "view_cat", path: id } }).catch(() => {});
}

function closeDetail({ restoreFocus = true } = {}) {
  if (detailShell.hidden) return;

  detailShell.classList.remove("is-open");
  detailShell.classList.add("is-closing");
  appShell.classList.remove("detail-open");
  detailShell.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  activeDetailId = null;

  if (detailCloseTimer) window.clearTimeout(detailCloseTimer);
  detailCloseTimer = window.setTimeout(() => {
    detailShell.hidden = true;
    detailShell.classList.remove("is-closing");
    detailContent.innerHTML = "";
    if (restoreFocus && lastDetailTrigger?.focus) {
      lastDetailTrigger.focus({ preventScroll: true });
    }
    lastDetailTrigger = null;
    detailCloseTimer = null;
  }, 310);
}

function cardHtml(cat) {
  const safeName = escapeHtml(cat.name);
  const location = cat.location || "未记录固定点位";
  const caretaker = cat.caretaker || "联系人待补充";
  const notes = cat.notes || "暂无备注。";
  const photoSrc = safePhotoSrc(cat.photoData);
  const photoMarkup = photoSrc ? `<img class="cat-photo" src="${escapeHtml(photoSrc)}" alt="${safeName}的照片">` : "";
  const adminActions = isAdmin()
    ? `
      <button class="mini-button" type="button" data-action="edit" data-id="${escapeHtml(cat.id)}" title="编辑 ${safeName}" aria-label="编辑 ${safeName}">
        ${icons.edit}
      </button>
      <button class="mini-button danger" type="button" data-action="delete" data-id="${escapeHtml(cat.id)}" title="删除 ${safeName}" aria-label="删除 ${safeName}">
        ${icons.trash}
      </button>
    `
    : "";

  return `
    <article class="cat-card${photoSrc ? "" : " no-photo"}" data-id="${escapeHtml(cat.id)}">
      ${photoMarkup}
      <div class="cat-card-head">
        <div class="cat-avatar" style="background:${avatarSeed(cat)}">${escapeHtml(cat.name.slice(0, 1))}</div>
        <div class="cat-title">
          <h3 title="${safeName}">${safeName}</h3>
          <span class="registry-no">${escapeHtml(cat.registryNo)}</span>
        </div>
        <span class="badge ${badgeClass(cat.status)}">${escapeHtml(cat.status)}</span>
      </div>

      <div class="cat-facts">
        <span class="fact">${escapeHtml(cat.gender)} · ${escapeHtml(cat.age)}</span>
        <span class="fact">${escapeHtml(cat.coat)}</span>
        <span class="fact">${escapeHtml(cat.campusArea)}</span>
        <span class="fact">${escapeHtml(location)}</span>
      </div>

      <p class="cat-notes">${escapeHtml(notes)}</p>

      <div class="cat-card-actions">
        <span class="care-line">${escapeHtml(cat.sterilized)} / ${escapeHtml(cat.vaccinated)} · ${escapeHtml(caretaker)}</span>
        <div class="mini-actions">
          <button class="mini-button primary" type="button" data-action="detail" data-id="${escapeHtml(cat.id)}" title="查看 ${safeName}" aria-label="查看 ${safeName}">
            ${icons.eye}
          </button>
          ${adminActions}
        </div>
      </div>
    </article>
  `;
}

function renderStats() {
  const watchStatuses = new Set(["医疗观察", "待领养", "失踪"]);
  document.querySelector("#totalCount").textContent = cats.length;
  document.querySelector("#sterilizedCount").textContent = cats.filter((cat) => cat.sterilized === "已绝育").length;
  document.querySelector("#watchCount").textContent = cats.filter((cat) => watchStatuses.has(cat.status)).length;
  document.querySelector("#areaCount").textContent = new Set(cats.map((cat) => cat.campusArea)).size;
}

function render() {
  fillAreaFilter();
  const visibleCats = filteredCats();
  grid.innerHTML = visibleCats.map(cardHtml).join("");
  emptyState.hidden = visibleCats.length > 0;
  resultText.textContent = `显示 ${visibleCats.length} 条档案`;
  renderStats();
}

function clearFilters() {
  searchInput.value = "";
  areaFilter.value = "all";
  statusFilter.value = "all";
  careFilter.value = "all";
  render();
}

function exportCats() {
  if (!isAdmin()) return;
  const payload = {
    school: "皖江工学院",
    system: "校园小猫户口收录系统",
    exportedAt: new Date().toISOString(),
    cats,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `皖江工学院小猫户口档案-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

function importCats(file) {
  if (!file || !isAdmin()) return;
  const reader = new FileReader();
  reader.addEventListener("load", async () => {
    try {
      const parsed = JSON.parse(reader.result);
      const incoming = Array.isArray(parsed) ? parsed : parsed.cats;
      if (!Array.isArray(incoming)) throw new Error("文件中没有档案列表");
      if (!confirm("导入会替换当前档案，确定继续吗？")) return;
      const payload = await api("/api/admin/import", { method: "POST", body: { cats: incoming } });
      cats = payload.cats || [];
      resetForm();
      clearFilters();
      showToast("档案导入完成");
    } catch (error) {
      showToast(error.message || "导入失败，请选择正确的 JSON 档案文件。", "error");
    }
  });
  reader.readAsText(file);
}

async function restoreSamples() {
  if (!isAdmin()) return;
  if (!confirm("确定恢复示例档案吗？当前档案会被替换。")) return;
  try {
    const payload = await api("/api/admin/restore-samples", { method: "POST" });
    cats = payload.cats || [];
    resetForm();
    clearFilters();
    showToast("示例档案已恢复");
  } catch (error) {
    showToast(error.message, "error");
  }
}

function actionLabel(action) {
  const labels = {
    landing: "打开登录页",
    login: "登录系统",
    logout: "退出登录",
    page_view: "访问首页",
    view_cat: "查看小猫档案",
    create_cat: "新增小猫档案",
    update_cat: "更新小猫档案",
    delete_cat: "删除小猫档案",
    import_cats: "导入档案",
    restore_samples: "恢复示例档案",
  };
  return labels[action] || action;
}

function targetLabel(log) {
  if (!log.path) return "—";
  const catId = log.path.split(":")[0];
  const cat = cats.find((item) => item.id === catId);
  if (cat) return `${cat.name} · ${cat.registryNo}`;
  return log.path;
}

function renderAdminStats(payload) {
  const metrics = payload.metrics || {};
  const metricItems = [
    ["累计访问", metrics.totalViews || 0],
    ["今日访问", metrics.todayViews || 0],
    ["访问人员", metrics.uniqueVisitors || 0],
    ["近 5 分钟活跃", metrics.activeVisitors || 0],
    ["累计登录", metrics.loginCount || 0],
    ["小猫档案", metrics.catCount || 0],
  ];
  adminMetrics.innerHTML = metricItems
    .map(
      ([label, value]) => `
        <section class="admin-metric">
          <span class="admin-metric-value">${escapeHtml(value)}</span>
          <span class="admin-metric-label">${escapeHtml(label)}</span>
        </section>
      `,
    )
    .join("");

  const visitors = payload.visitors || [];
  visitorCountText.textContent = `${visitors.length} 人`;
  visitorTableBody.innerHTML =
    visitors
      .map(
        (visitor) => `
          <tr>
            <td><span class="role-tag ${visitor.role === "admin" ? "admin" : ""}">${visitor.role === "admin" ? "管理员" : "访客"}</span></td>
            <td>${escapeHtml(visitor.studentId)}</td>
            <td>${escapeHtml(visitor.name)}</td>
            <td>${escapeHtml(visitor.loginCount)}</td>
            <td>${escapeHtml(visitor.pageViews)}</td>
            <td>${escapeHtml(formatDate(visitor.lastSeen))}</td>
            <td>${escapeHtml(visitor.lastIp || "—")}</td>
          </tr>
        `,
      )
      .join("") || '<tr><td colspan="7" class="table-empty">暂无访问人员</td></tr>';

  const logs = payload.logs || [];
  logTableBody.innerHTML =
    logs
      .map(
        (log) => `
          <tr>
            <td>${escapeHtml(formatDate(log.createdAt))}</td>
            <td>${escapeHtml(log.name ? `${log.name} · ${log.studentId}` : "未登录访问")}</td>
            <td>${escapeHtml(actionLabel(log.action))}</td>
            <td>${escapeHtml(targetLabel(log))}</td>
            <td>${escapeHtml(log.ip || "—")}</td>
          </tr>
        `,
      )
      .join("") || '<tr><td colspan="5" class="table-empty">暂无访问记录</td></tr>';
}

async function loadAdminStats() {
  if (!isAdmin()) return;
  try {
    document.querySelector("#refreshAdminBtn").disabled = true;
    const payload = await api("/api/admin/stats");
    renderAdminStats(payload);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    document.querySelector("#refreshAdminBtn").disabled = false;
  }
}

function openAdmin() {
  if (!isAdmin()) return;
  if (adminCloseTimer) {
    window.clearTimeout(adminCloseTimer);
    adminCloseTimer = null;
  }
  adminShell.hidden = false;
  adminShell.setAttribute("aria-hidden", "false");
  adminShell.classList.remove("is-closing");
  adminShell.getBoundingClientRect();
  adminShell.classList.add("is-open");
  document.body.style.overflow = "hidden";
  loadAdminStats();
}

function closeAdmin() {
  if (adminShell.hidden) return;
  adminShell.classList.remove("is-open");
  adminShell.classList.add("is-closing");
  adminShell.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
  if (adminCloseTimer) window.clearTimeout(adminCloseTimer);
  adminCloseTimer = window.setTimeout(() => {
    adminShell.hidden = true;
    adminShell.classList.remove("is-closing");
    adminCloseTimer = null;
  }, 260);
}

loginForm.addEventListener("submit", handleLogin);
document.querySelector("#logoutBtn").addEventListener("click", handleLogout);
form.addEventListener("submit", saveCat);
document.querySelector("#clearBtn").addEventListener("click", resetForm);
document.querySelector("#cancelEditBtn").addEventListener("click", resetForm);
photoInput.addEventListener("change", handlePhotoChange);
removePhotoBtn.addEventListener("click", () => {
  photoDataInput.value = "";
  photoInput.value = "";
  renderPhotoPreview("");
});
document.querySelector("#newRecordBtn").addEventListener("click", () => {
  resetForm();
  document.querySelector(".entry-panel").scrollIntoView({ behavior: "smooth", block: "start" });
});
document.querySelector("#emptyAddBtn").addEventListener("click", () => {
  clearFilters();
  document.querySelector(".entry-panel").scrollIntoView({ behavior: "smooth", block: "start" });
});
document.querySelector("#clearFiltersBtn").addEventListener("click", clearFilters);
document.querySelector("#exportBtn").addEventListener("click", exportCats);
document.querySelector("#sampleBtn").addEventListener("click", restoreSamples);
document.querySelector("#importInput").addEventListener("change", (event) => {
  importCats(event.target.files[0]);
  event.target.value = "";
});
document.querySelector("#adminBtn").addEventListener("click", openAdmin);
document.querySelector("#refreshAdminBtn").addEventListener("click", loadAdminStats);

[searchInput, areaFilter, statusFilter, careFilter].forEach((control) => {
  control.addEventListener("input", render);
  control.addEventListener("change", render);
});

grid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (button) {
    const id = button.dataset.id;
    if (button.dataset.action === "detail") openDetail(id, button.closest(".cat-card"));
    if (button.dataset.action === "edit") editCat(id);
    if (button.dataset.action === "delete") deleteCat(id);
    return;
  }

  const card = event.target.closest(".cat-card");
  if (card) openDetail(card.dataset.id, card);
});

detailShell.addEventListener("click", (event) => {
  if (event.target.closest("[data-detail-close]")) {
    closeDetail();
    return;
  }

  const editButton = event.target.closest("[data-detail-edit]");
  if (editButton) {
    const id = editButton.dataset.detailEdit;
    closeDetail({ restoreFocus: false });
    window.setTimeout(() => editCat(id), 120);
  }
});

adminShell.addEventListener("click", (event) => {
  if (event.target.closest("[data-admin-close]")) closeAdmin();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!adminShell.hidden) {
    closeAdmin();
  } else if (!detailShell.hidden) {
    closeDetail();
  }
});

bootstrap();
