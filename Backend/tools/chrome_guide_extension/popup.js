function setStatus(msg) {
  const el = document.getElementById('status');
  if (el) el.textContent = msg;
}

async function loadSettings() {
  const saved = await chrome.storage.local.get(['userId', 'backendUrl', 'guideType', 'lang']);
  if (saved.userId) document.getElementById('userId').value = saved.userId;
  if (saved.backendUrl) document.getElementById('backendUrl').value = saved.backendUrl;
  if (saved.guideType) document.getElementById('guideType').value = saved.guideType;
  if (saved.lang) document.getElementById('lang').value = saved.lang;
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0];
}

async function sendToContent(payload) {
  const tab = await getActiveTab();
  if (!tab || !tab.id) {
    setStatus('No active tab found');
    return false;
  }
  const tabId = tab.id;
  const ready = await ensureContentReady(tabId);
  if (!ready) {
    setStatus('Could not attach guide script to this page');
    return false;
  }
  try {
    await chrome.tabs.sendMessage(tabId, payload);
    return true;
  } catch (e) {
    setStatus('Guide message failed. Refresh page and retry.');
    return false;
  }
}

function detectGuideFromUrl(url) {
  const u = String(url || '').toLowerCase();
  if (u.includes('kfintech.com')) return 'cams';
  if (u.includes('tdscpc.gov.in')) return 'form16';
  return null;
}

async function pingContent(tabId) {
  try {
    const res = await chrome.tabs.sendMessage(tabId, { type: 'ASTRA_PING' });
    return !!(res && res.ok);
  } catch (e) {
    return false;
  }
}

async function ensureContentReady(tabId) {
  if (await pingContent(tabId)) return true;
  try {
    await chrome.scripting.insertCSS({ target: { tabId }, files: ['styles.css'] });
  } catch (e) {}
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] });
  } catch (e) {
    return false;
  }
  return await pingContent(tabId);
}

document.getElementById('startBtn').addEventListener('click', async () => {
  const guideTypeRaw = document.getElementById('guideType').value;
  const userId = document.getElementById('userId').value.trim();
  const backendUrl = document.getElementById('backendUrl').value.trim();
  const lang = document.getElementById('lang').value;
  const tab = await getActiveTab();
  let guideType = guideTypeRaw;
  if (guideTypeRaw === 'auto') {
    guideType = detectGuideFromUrl(tab?.url);
    if (!guideType) {
      setStatus('Auto detect failed. Open KFin or TRACES page.');
      return;
    }
  }
  await chrome.storage.local.set({ userId, backendUrl, guideType, lang });
  const ok = await sendToContent({ type: 'ASTRA_START_GUIDE', guideType, userId, backendUrl, lang });
  if (ok) setStatus(`Started ${guideType} guide`);
});

document.getElementById('nextBtn').addEventListener('click', async () => {
  await sendToContent({ type: 'ASTRA_NEXT_STEP' });
  setStatus('Moved to next step');
});

document.getElementById('stopBtn').addEventListener('click', async () => {
  await sendToContent({ type: 'ASTRA_STOP_GUIDE' });
  setStatus('Guide stopped');
});

loadSettings();
