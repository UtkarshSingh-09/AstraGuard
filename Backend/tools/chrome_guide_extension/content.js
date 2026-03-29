(function () {
  if (window.__astraGuideLoaded) {
    return;
  }
  window.__astraGuideLoaded = true;

  const state = {
    active: false,
    guideType: null,
    stepIndex: 0,
    steps: [],
    overlay: null,
    tooltip: null,
    ws: null,
    backendUrl: "",
    userId: "",
    lang: "en",
    urlWatcher: null,
    waitReminderTimer: null,
    waitingStepIndex: -1,
    waitingSinceTs: 0,
    waitingTarget: null,
    lastAdvanceTs: 0,
  };

  const CAMS_STEPS = [
    {
      instruction: "Select statement type and period options on KFin CAS page.",
      selectors: [
        "select[name*='statement' i]",
        "select[id*='statement' i]",
        "input[type='radio'][name*='statement' i]"
      ],
      textHint: "statement",
      trigger: "click",
    },
    {
      instruction: "Enter PAN in the PAN input field.",
      selectors: [
        "input[name*='pan' i]",
        "input[id*='pan' i]",
        "input[placeholder*='PAN' i]",
        "input[aria-label*='PAN' i]"
      ],
      textHint: "PAN",
      trigger: "input",
      inputMode: "pan",
      minChars: 10,
    },
    {
      instruction: "Enter registered email id.",
      selectors: [
        "input[name*='email' i]",
        "input[id*='email' i]",
        "input[type='email']",
        "input[placeholder*='email' i]"
      ],
      textHint: "email",
      trigger: "input",
      inputMode: "email",
      minChars: 6,
    },
    {
      instruction: "Set CAS PDF password and confirm password.",
      selectors: [
        "input[name*='password' i]",
        "input[id*='password' i]",
        "input[type='password']"
      ],
      textHint: "password",
      trigger: "input",
      inputMode: "password",
      minChars: 4,
    },
    {
      instruction: "Click submit/request and wait for confirmation screen.",
      selectors: [
        "button[type='submit']",
        "input[type='submit']",
        "button[id*='submit' i]",
        "button[class*='submit' i]"
      ],
      textHint: "submit",
      trigger: "click",
    },
  ];

  const FORM16_STEPS = [
    {
      instruction: "Click top menu 'Tax Payer'.",
      selectors: [
        "a",
        "li a",
        "ul li a",
        "nav a",
        "div a"
      ],
      textHint: "tax payer",
      textNeed: ["tax", "payer"],
      trigger: "click",
    },
    {
      instruction: "Click login/sign-in on TRACES.",
      selectors: [
        "#left_container a",
        ".left-panel a",
        "div.login a",
        "a[title='Login']",
        "a[href*='login' i]",
        "button[id*='login' i]",
        "input[type='submit'][value*='Login' i]",
        "a[title*='login' i]"
      ],
      textHint: "login sign in",
      textNeed: ["login"],
      trigger: "click",
    },
    {
      instruction: "Enter user ID or PAN.",
      selectors: ["input[name*='user' i]", "input[name*='pan' i]", "input[id*='user' i]"],
      textHint: "user",
      trigger: "input",
      inputMode: "generic",
      minChars: 3,
    },
    {
      instruction: "Enter password.",
      selectors: ["input[type='password']", "input[name*='pass' i]"],
      textHint: "password",
      trigger: "input",
      inputMode: "password",
      minChars: 4,
    },
    {
      instruction: "Complete captcha/OTP if asked, then continue.",
      selectors: [
        "input[name*='captcha' i]",
        "input[id*='captcha' i]",
        "input[name*='otp' i]",
        "input[id*='otp' i]"
      ],
      textHint: "captcha otp verification code",
      trigger: "input",
      inputMode: "otp_or_captcha",
      minChars: 4,
    },
    {
      instruction: "Open Downloads menu and choose Form16/Form16A option.",
      selectors: [
        "a[href*='download' i]",
        "a[id*='download' i]",
        "button[id*='download' i]",
        "li a"
      ],
      textHint: "downloads form 16 form16 form16a",
      textNeed: ["download"],
      trigger: "click",
    },
    {
      instruction: "Submit request/check status, then click Download when available.",
      selectors: [
        "a[href*='form16' i]",
        "a[href*='download' i]",
        "button[id*='download' i]",
        "input[type='submit'][value*='Download' i]",
        "input[type='submit'][value*='Request' i]"
      ],
      textHint: "download request status available",
      trigger: "click",
    },
  ];

  const I18N = {
    hi: {
      "Guide completed. Continue workflow in AstraGuard dashboard.": "गाइड पूरी हो गई। AstraGuard डैशबोर्ड में आगे बढ़ें।",
      "Wrong site for CAMS guide. Open KFin CAS page: mfs.kfintech.com": "CAMS गाइड के लिए गलत साइट है। KFin CAS पेज खोलें: mfs.kfintech.com",
      "Wrong site for Form16 guide. Open TRACES page: tdscpc.gov.in": "Form16 गाइड के लिए गलत साइट है। TRACES पेज खोलें: tdscpc.gov.in",
      "Click top menu 'Tax Payer'.": "ऊपर वाले मेन्यू में 'Tax Payer' पर क्लिक करें।",
      "Select statement type and period options on KFin CAS page.": "KFin CAS पेज पर statement type और period चुनें।",
      "Enter PAN in the PAN input field.": "PAN input field में PAN दर्ज करें।",
      "Enter registered email id.": "Registered email id दर्ज करें।",
      "Set CAS PDF password and confirm password.": "CAS PDF password और confirm password दर्ज करें।",
      "Click submit/request and wait for confirmation screen.": "Submit/request पर क्लिक करें और confirmation का इंतजार करें।",
      "Click login/sign-in on TRACES.": "TRACES पर login/sign-in पर क्लिक करें।",
      "Enter user ID or PAN.": "User ID या PAN दर्ज करें।",
      "Enter password.": "Password दर्ज करें।",
      "Complete captcha/OTP if asked, then continue.": "Captcha/OTP आए तो पूरा करें, फिर आगे बढ़ें।",
      "Open Downloads menu and choose Form16/Form16A option.": "Downloads मेन्यू खोलें और Form16/Form16A चुनें।",
      "Submit request/check status, then click Download when available.": "Request submit/status check करें, उपलब्ध होने पर Download करें।"
    },
    hinglish: {
      "Guide completed. Continue workflow in AstraGuard dashboard.": "Guide complete ho gayi. AstraGuard dashboard par continue karo.",
      "Wrong site for CAMS guide. Open KFin CAS page: mfs.kfintech.com": "CAMS guide ke liye wrong site hai. KFin CAS page kholo: mfs.kfintech.com",
      "Wrong site for Form16 guide. Open TRACES page: tdscpc.gov.in": "Form16 guide ke liye wrong site hai. TRACES page kholo: tdscpc.gov.in",
      "Click top menu 'Tax Payer'.": "Top menu me 'Tax Payer' par click karo.",
      "Select statement type and period options on KFin CAS page.": "KFin CAS page par statement type aur period select karo.",
      "Enter PAN in the PAN input field.": "PAN field me PAN daalo.",
      "Enter registered email id.": "Registered email id daalo.",
      "Set CAS PDF password and confirm password.": "CAS PDF password aur confirm password set karo.",
      "Click submit/request and wait for confirmation screen.": "Submit/request click karo aur confirmation ka wait karo.",
      "Click login/sign-in on TRACES.": "TRACES par login/sign-in click karo.",
      "Enter user ID or PAN.": "User ID ya PAN daalo.",
      "Enter password.": "Password daalo.",
      "Complete captcha/OTP if asked, then continue.": "Captcha/OTP aaye to complete karo, phir continue karo.",
      "Open Downloads menu and choose Form16/Form16A option.": "Downloads menu kholo aur Form16/Form16A option select karo.",
      "Submit request/check status, then click Download when available.": "Request submit/status check karo, available hone par Download click karo."
    }
  };

  function tr(text) {
    if (state.lang === "en") return text;
    return I18N[state.lang]?.[text] || text;
  }

  function translateStepInstruction(text) {
    if (state.lang === "en") return text;
    const map = I18N[state.lang] || {};
    return map[text] || text;
  }

  function getSteps(type) {
    return type === "form16" ? FORM16_STEPS : CAMS_STEPS;
  }

  function createOverlay() {
    const box = document.createElement("div");
    box.id = "astra-guide-overlay";
    box.innerHTML = `
      <div class="astra-guide-header">AstraGuard Guide</div>
      <div id="astra-guide-body"></div>
      <div id="astra-guide-meta"></div>
      <div class="astra-guide-actions">
        <button id="astra-guide-next">Next</button>
        <button id="astra-guide-stop">Stop</button>
      </div>
    `;
    document.body.appendChild(box);
    box.querySelector("#astra-guide-next").addEventListener("click", nextStep);
    box.querySelector("#astra-guide-stop").addEventListener("click", stopGuide);
    state.overlay = box;
  }

  function updateOverlay(text, meta) {
    if (!state.overlay) createOverlay();
    const body = state.overlay.querySelector("#astra-guide-body");
    const m = state.overlay.querySelector("#astra-guide-meta");
    body.textContent = tr(text);
    m.textContent = meta || "";
  }

  function clearHighlights() {
    document.querySelectorAll(".astra-guide-highlight").forEach((el) => {
      el.classList.remove("astra-guide-highlight");
    });
    if (state.tooltip) {
      state.tooltip.remove();
      state.tooltip = null;
    }
  }

  function clearWaitReminder() {
    if (state.waitReminderTimer) {
      clearInterval(state.waitReminderTimer);
      state.waitReminderTimer = null;
    }
    state.waitingStepIndex = -1;
    state.waitingSinceTs = 0;
    state.waitingTarget = null;
  }

  function isVisible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return r.width > 0 && r.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  }

  function normalizeText(s) {
    return String(s || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function matchTextNeed(text, step) {
    const need = step.textNeed || [];
    if (!need.length) return true;
    return need.every((tok) => text.includes(tok));
  }

  function findTarget(step) {
    const hintTokens = normalizeText(step.textHint || "").split(" ").filter(Boolean);
    for (const sel of step.selectors || []) {
      const nodes = Array.from(document.querySelectorAll(sel));
      const scored = nodes
        .filter(isVisible)
        .map((el) => {
          const text = normalizeText(el.textContent || el.getAttribute("value") || el.getAttribute("aria-label") || "");
          let score = 0;
          const id = normalizeText(el.id || "");
          const cls = normalizeText(el.className || "");
          if (matchTextNeed(text, step)) score += 5;
          for (const t of hintTokens) if (text.includes(t)) score += 1;
          if (id.includes("login") || cls.includes("login")) score += 1;
          return { el, score };
        })
        .sort((a, b) => b.score - a.score);
      if (scored.length && scored[0].score > 0) return scored[0].el;
      if (nodes.length && nodes[0].tagName === "INPUT") return nodes[0];
    }
    const hint = normalizeText(step.textHint || "");
    if (!hint) return null;
    const candidates = Array.from(document.querySelectorAll("button, a, input, label, div, span, li"));
    return (
      candidates.find((el) => {
        if (!isVisible(el)) return false;
        const text = normalizeText(el.textContent || el.getAttribute("value") || "");
        return hint.split(" ").some((tok) => tok && text.includes(tok)) && matchTextNeed(text, step);
      }) || null
    );
  }

  function placeTooltip(target, text) {
    const tip = document.createElement("div");
    tip.className = "astra-guide-tooltip";
    tip.textContent = text;
    const rect = target.getBoundingClientRect();
    tip.style.top = `${window.scrollY + rect.top - 36}px`;
    tip.style.left = `${window.scrollX + rect.left}px`;
    document.body.appendChild(tip);
    state.tooltip = tip;
  }

  function trackProgress(target, step) {
    if (!target) return;
    const stepIndexAtBind = state.stepIndex;
    const handler = () => {
      if (!state.active) return;
      if (state.stepIndex !== stepIndexAtBind) return;
      clearWaitReminder();
      nextStep();
    };
    if (step.trigger === "input") {
      let idleTimer = null;
      const minChars = typeof step.minChars === "number" ? step.minChars : 3;
      const inputMode = step.inputMode || "generic";
      const isValidInput = () => {
        const raw = String(target.value || "").trim();
        if (raw.length < minChars) return false;
        if (inputMode === "email") return raw.includes("@") && raw.includes(".");
        if (inputMode === "pan") return /^[A-Za-z]{5}[0-9]{4}[A-Za-z]$/.test(raw);
        return true;
      };
      const tryAdvance = () => {
        if (isValidInput()) handler();
      };
      target.addEventListener("blur", tryAdvance);
      target.addEventListener("change", tryAdvance);
      target.addEventListener("input", () => {
        if (idleTimer) clearTimeout(idleTimer);
        idleTimer = setTimeout(() => {
          tryAdvance();
        }, 1000);
      });
    } else {
      target.addEventListener("click", handler, { once: true });
    }

    clearWaitReminder();
    state.waitingStepIndex = stepIndexAtBind;
    state.waitingSinceTs = Date.now();
    state.waitingTarget = target;
    state.waitReminderTimer = setInterval(() => {
      if (!state.active || state.stepIndex !== stepIndexAtBind) {
        clearWaitReminder();
        return;
      }
      if (!state.waitingTarget || !document.contains(state.waitingTarget)) {
        clearWaitReminder();
        setTimeout(() => renderStep(), 200);
        return;
      }
      const waitedSec = Math.floor((Date.now() - state.waitingSinceTs) / 1000);
      const stepNow = state.steps[state.stepIndex];
      const msg = `${translateStepInstruction(stepNow.instruction)} Waiting for your action...`;
      updateOverlay(msg, `Step ${state.stepIndex + 1}/${state.steps.length} | waiting ${waitedSec}s`);
      state.waitingTarget.scrollIntoView({ behavior: "smooth", block: "center" });
      placeTooltip(state.waitingTarget, msg);
    }, 7000);
  }

  function renderStep() {
    if (!state.active) return;
    clearHighlights();
    if (state.stepIndex >= state.steps.length) {
      updateOverlay("Guide completed. Continue workflow in AstraGuard dashboard.", "All steps complete");
      persistGuide(false);
      return;
    }
    const step = state.steps[state.stepIndex];
    const target = findTarget(step);
    persistGuide(true);
    updateOverlay(translateStepInstruction(step.instruction), `Step ${state.stepIndex + 1}/${state.steps.length}`);
    if (!target) {
      updateOverlay(
        `${translateStepInstruction(step.instruction)} (Target not detected automatically. Use manual navigation and click Next.)`,
        `Step ${state.stepIndex + 1}/${state.steps.length} - manual assist`,
      );
      return;
    }
    target.classList.add("astra-guide-highlight");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    placeTooltip(target, translateStepInstruction(step.instruction));
    trackProgress(target, step);
  }

  function nextStep() {
    if (!state.active) return;
    const now = Date.now();
    if (now - state.lastAdvanceTs < 300) return;
    state.lastAdvanceTs = now;
    clearWaitReminder();
    state.stepIndex += 1;
    persistGuide(true);
    renderStep();
  }

  function stopGuide() {
    state.active = false;
    clearWaitReminder();
    clearHighlights();
    if (state.overlay) {
      state.overlay.remove();
      state.overlay = null;
    }
    if (state.ws) {
      state.ws.close();
      state.ws = null;
    }
    if (state.urlWatcher) {
      clearInterval(state.urlWatcher);
      state.urlWatcher = null;
    }
    persistGuide(false);
  }

  function openWS() {
    if (!state.backendUrl || !state.userId) return;
    try {
      const wsUrl = state.backendUrl.replace(/^http/, "ws") + `/ws/${encodeURIComponent(state.userId)}`;
      const ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type !== "job_update") return;
          const data = payload.data || {};
          const status = data.job_status || "running";
          const message = data.message || "";
          updateOverlay(
            `Guide running: ${state.steps[Math.min(state.stepIndex, state.steps.length - 1)]?.instruction || "In progress"}`,
            `Job: ${status} | ${message}`,
          );
        } catch (_) {}
      };
      state.ws = ws;
    } catch (_) {}
  }

  function persistGuide(active) {
    try {
      chrome.storage.local.set({
        astraGuideState: active
          ? {
              active: true,
              guideType: state.guideType,
              stepIndex: state.stepIndex,
              userId: state.userId,
              backendUrl: state.backendUrl,
              lang: state.lang,
              host: location.hostname,
              path: location.pathname,
              ts: Date.now(),
            }
          : { active: false, ts: Date.now() },
      });
    } catch (_) {}
  }

  function startUrlWatcher() {
    if (state.urlWatcher) clearInterval(state.urlWatcher);
    let last = location.href;
    state.urlWatcher = setInterval(() => {
      if (!state.active) return;
      if (location.href !== last) {
        last = location.href;
        clearWaitReminder();
        clearHighlights();
        setTimeout(() => renderStep(), 600);
      }
    }, 800);
  }

  function startGuide({ guideType, userId, backendUrl, lang }) {
    const host = location.hostname.toLowerCase();
    if (guideType === "auto") {
      if (host.includes("kfintech.com")) guideType = "cams";
      else if (host.includes("tdscpc.gov.in")) guideType = "form16";
      else {
        updateOverlay("Could not auto-detect guide for this site.", "Supported: KFin, TRACES");
        return;
      }
    }
    const isKfin = host.includes("kfintech.com");
    const isTraces = host.includes("tdscpc.gov.in");
    if (guideType === "cams" && !isKfin) {
      updateOverlay(
        "Wrong site for CAMS guide. Open KFin CAS page: mfs.kfintech.com",
        "Expected host: *.kfintech.com",
      );
      return;
    }
    if (guideType === "form16" && !isTraces) {
      updateOverlay(
        "Wrong site for Form16 guide. Open TRACES page: tdscpc.gov.in",
        "Expected host: *.tdscpc.gov.in",
      );
      return;
    }
    state.active = true;
    clearWaitReminder();
    state.guideType = guideType || "cams";
    state.userId = userId || "";
    state.backendUrl = backendUrl || "";
    state.lang = lang || "en";
    state.stepIndex = 0;
    state.steps = getSteps(state.guideType);
    openWS();
    startUrlWatcher();
    persistGuide(true);
    renderStep();
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message || !message.type) return;
    if (message.type === "ASTRA_PING") {
      sendResponse({ ok: true });
      return;
    }
    if (message.type === "ASTRA_START_GUIDE") {
      startGuide(message);
      sendResponse({ ok: true });
    } else if (message.type === "ASTRA_NEXT_STEP") {
      nextStep();
      sendResponse({ ok: true });
    } else if (message.type === "ASTRA_STOP_GUIDE") {
      stopGuide();
      sendResponse({ ok: true });
    }
  });

  async function resumeGuideIfPresent() {
    try {
      const { astraGuideState } = await chrome.storage.local.get(["astraGuideState"]);
      if (!astraGuideState || !astraGuideState.active) return;
      const host = location.hostname.toLowerCase();
      const targetHostOk =
        (astraGuideState.guideType === "cams" && host.includes("kfintech.com")) ||
        (astraGuideState.guideType === "form16" && host.includes("tdscpc.gov.in"));
      if (!targetHostOk) return;
      state.active = true;
      state.guideType = astraGuideState.guideType || "cams";
      state.userId = astraGuideState.userId || "";
      state.backendUrl = astraGuideState.backendUrl || "";
      state.lang = astraGuideState.lang || "en";
      state.steps = getSteps(state.guideType);
      state.stepIndex = Math.min(astraGuideState.stepIndex || 0, state.steps.length - 1);
      openWS();
      startUrlWatcher();
      setTimeout(() => renderStep(), 400);
    } catch (_) {}
  }

  resumeGuideIfPresent();
})();
