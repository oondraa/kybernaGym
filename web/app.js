(() => {
  "use strict";

  const TZ = "Europe/Prague";
  const WEEKDAY_TO_CODE = { Mon: "PO", Tue: "UT", Wed: "ST", Thu: "CT", Fri: "PA" };

  const els = {
    statusCard: document.getElementById("status-card"),
    statusBadge: document.getElementById("status-badge"),
    statusDetail: document.getElementById("status-detail"),
    statusSub: document.getElementById("status-sub"),
    dayTabs: document.getElementById("day-tabs"),
    timeline: document.getElementById("timeline"),
    timelineDayTitle: document.getElementById("timeline-day-title"),
    slotDetail: document.getElementById("slot-detail"),
    slotDetailContent: document.getElementById("slot-detail-content"),
    slotDetailClose: document.getElementById("slot-detail-close"),
    clock: document.getElementById("clock"),
    sourceNote: document.getElementById("source-note"),
    generatedAt: document.getElementById("generated-at"),
  };

  let schedule = null;
  let selectedDay = null;

  function pragueParts(date = new Date()) {
    const fmt = new Intl.DateTimeFormat("en-US", {
      timeZone: TZ,
      hour12: false,
      weekday: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
    const parts = Object.fromEntries(fmt.formatToParts(date).map((p) => [p.type, p.value]));
    return {
      weekday: parts.weekday,
      hm: `${parts.hour}:${parts.minute}`,
    };
  }

  function timeToMinutes(hm) {
    const [h, m] = hm.split(":").map(Number);
    return h * 60 + m;
  }

  function slotRange(slot) {
    const [from, to] = slot.time.split("-");
    return { from, to };
  }

  function findCurrentSlot(daySlots, nowHm) {
    const now = timeToMinutes(nowHm);
    return daySlots.find((slot) => {
      const { from, to } = slotRange(slot);
      return now >= timeToMinutes(from) && now < timeToMinutes(to);
    });
  }

  function describeEntries(entries) {
    if (!entries || entries.length === 0) return "";
    return entries
      .map((e) => {
        const bits = [e.group];
        if (e.subject) bits.push(e.subject);
        return bits.join(" · ");
      })
      .join(", ");
  }

  function updateClock() {
    const { hm } = pragueParts();
    els.clock.textContent = hm;
  }

  function renderStatus() {
    const { weekday, hm } = pragueParts();
    const todayCode = WEEKDAY_TO_CODE[weekday];

    els.statusCard.classList.remove("status-free", "status-busy", "status-loading");

    if (!todayCode) {
      els.statusCard.classList.add("status-free");
      els.statusBadge.textContent = "VOLNO";
      els.statusDetail.textContent = "Dnes je víkend, škola nemá výuku.";
      els.statusSub.textContent = "Rozvrh níže ukazuje typický školní den.";
      return;
    }

    const day = schedule.days[todayCode];
    if (!day) {
      els.statusCard.classList.add("status-free");
      els.statusBadge.textContent = "VOLNO";
      els.statusDetail.textContent = "Pro dnešek nemáme data.";
      els.statusSub.textContent = "";
      return;
    }

    const current = findCurrentSlot(day.slots, hm);

    if (!current) {
      els.statusCard.classList.add("status-free");
      els.statusBadge.textContent = "VOLNO";
      els.statusDetail.textContent = "Mimo rozvrh vyučovacích hodin.";
      els.statusSub.textContent = "Posilovnu neobsazuje žádná hodina tělesné výchovy.";
      return;
    }

    if (current.occupied) {
      const { to } = slotRange(current);
      els.statusCard.classList.add("status-busy");
      els.statusBadge.textContent = "OBSAZENO";
      els.statusDetail.textContent = `Do ${to} tam má tělocvik ${describeEntries(current.entries)}.`;
      const next = day.slots.find(
        (s) => s.period > current.period && !s.occupied
      );
      if (next) {
        els.statusSub.textContent = `Volno bude od ${slotRange(next).from}.`;
      } else {
        els.statusSub.textContent = "Do konce dne už se posilovna neuvolní.";
      }
    } else {
      els.statusCard.classList.add("status-free");
      els.statusBadge.textContent = "VOLNO";
      const nextBusy = day.slots.find((s) => s.period > current.period && s.occupied);
      if (nextBusy) {
        els.statusDetail.textContent = `Volno alespoň do ${slotRange(nextBusy).from}.`;
        els.statusSub.textContent = `Pak tam má tělocvik ${describeEntries(nextBusy.entries)}.`;
      } else {
        els.statusDetail.textContent = "Volno do konce dnešního rozvrhu.";
        els.statusSub.textContent = "";
      }
    }
  }

  function renderDayTabs() {
    const { weekday } = pragueParts();
    const todayCode = WEEKDAY_TO_CODE[weekday];

    els.dayTabs.innerHTML = "";
    schedule.day_order.forEach((code) => {
      const day = schedule.days[code];
      if (!day) return;
      const btn = document.createElement("button");
      btn.className = "day-tab";
      btn.textContent = day.name.slice(0, 2);
      btn.title = `${day.name} ${day.date_label}`;
      if (code === selectedDay) btn.classList.add("active");
      if (code === todayCode) btn.classList.add("is-today");
      btn.addEventListener("click", () => {
        selectedDay = code;
        renderDayTabs();
        renderTimeline();
        hideSlotDetail();
      });
      els.dayTabs.appendChild(btn);
    });
  }

  function renderTimeline() {
    const day = schedule.days[selectedDay];
    if (!day) return;

    els.timelineDayTitle.textContent = `${day.name} · ${day.date_label}`;
    els.timeline.innerHTML = "";

    const { weekday, hm } = pragueParts();
    const isToday = WEEKDAY_TO_CODE[weekday] === selectedDay;
    const currentSlot = isToday ? findCurrentSlot(day.slots, hm) : null;

    day.slots.forEach((slot) => {
      const row = document.createElement("div");
      row.className = "slot";
      if (currentSlot && currentSlot.period === slot.period) row.classList.add("is-now");

      const time = document.createElement("div");
      time.className = "slot-time";
      time.textContent = slot.time;

      const bar = document.createElement("div");
      bar.className = `slot-bar ${slot.occupied ? "busy" : "free"}`;
      bar.textContent = slot.occupied ? describeEntries(slot.entries) : "volno";

      row.appendChild(time);
      row.appendChild(bar);
      row.addEventListener("click", () => showSlotDetail(day, slot));

      els.timeline.appendChild(row);
    });
  }

  function showSlotDetail(day, slot) {
    els.slotDetail.hidden = false;
    if (slot.occupied) {
      els.slotDetailContent.innerHTML = `
        <strong>${slot.time}</strong> · ${day.name}<br>
        Posilovnu má obsazenou: <strong>${describeEntries(slot.entries)}</strong>
      `;
    } else {
      els.slotDetailContent.innerHTML = `
        <strong>${slot.time}</strong> · ${day.name}<br>
        Posilovna je podle rozvrhu volná.
      `;
    }
  }

  function hideSlotDetail() {
    els.slotDetail.hidden = true;
  }

  function renderFooter() {
    els.sourceNote.textContent = schedule.source_note;
    const gen = new Date(schedule.generated_at);
    const genLabel = gen.toLocaleString("cs-CZ", { timeZone: TZ, dateStyle: "medium", timeStyle: "short" });
    els.generatedAt.textContent = `Data vygenerována: ${genLabel}`;
  }

  async function init() {
    els.slotDetailClose.addEventListener("click", hideSlotDetail);

    try {
      const res = await fetch("data/schedule.json", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      schedule = await res.json();
    } catch (err) {
      els.statusCard.classList.remove("status-loading");
      els.statusBadge.textContent = "Chyba";
      els.statusDetail.textContent = "Data o rozvrhu se nepodařilo načíst.";
      els.statusSub.textContent = String(err.message || err);
      return;
    }

    const { weekday } = pragueParts();
    selectedDay = WEEKDAY_TO_CODE[weekday] || schedule.day_order[0];

    updateClock();
    renderStatus();
    renderDayTabs();
    renderTimeline();
    renderFooter();

    setInterval(() => {
      updateClock();
      renderStatus();
      renderTimeline();
    }, 30000);
  }

  init();
})();
