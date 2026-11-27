/**
 * PixelAgents // Antigravity Live Visualizer — Pure Spectator Engine
 * Motor 2D Pixel Art en HTML5 Canvas:
 *  - Modo Espectador puro: sin controles de simulación ni movimiento manual
 *  - Iluminación dinámica de salas (las salas activas se iluminan sutilmente)
 *  - Etiquetas inteligentes anti-solapamiento (burbujas completas en agentes activos o al hacer hover/clic)
 *  - Pathfinding por corredor central y puertas con animación fluida a 60 FPS
 */

(() => {
  const canvas = document.getElementById("pixelCanvas");
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;

  const W = canvas.width;   // 1040
  const H = canvas.height;  // 620
  const HALLWAY_Y = 294;

  // =========================================================================
  // DEFINICIÓN DE LAS 8 SALAS (DISTRIBUCIÓN LIMPIA Y ESPACIADA)
  // =========================================================================
  const STATIONS = {
    library: {
      id: "library",
      title: "BIBLIOTECA",
      icon: "📚",
      rect: { x: 20, y: 20, w: 244, h: 240 },
      door: { x: 142, y: 260 },
      floorA: "#271d18",
      floorB: "#221915",
      accent: "#d49a6a",
      slots: [
        { x: 68,  y: 130, face: "up" },
        { x: 142, y: 130, face: "up" },
        { x: 216, y: 130, face: "up" },
        { x: 100, y: 212, face: "down" },
        { x: 184, y: 212, face: "down" },
      ],
    },
    strategy_board: {
      id: "strategy_board",
      title: "ESTRATEGIA",
      icon: "💭",
      rect: { x: 278, y: 20, w: 232, h: 240 },
      door: { x: 394, y: 260 },
      floorA: "#141f2e",
      floorB: "#111b28",
      accent: "#38bdf8",
      slots: [
        { x: 332, y: 132, face: "up" },
        { x: 394, y: 132, face: "up" },
        { x: 456, y: 132, face: "up" },
        { x: 360, y: 212, face: "up" },
        { x: 428, y: 212, face: "up" },
      ],
    },
    orchestrator_hub: {
      id: "orchestrator_hub",
      title: "ORCHESTRATOR",
      icon: "🎛️",
      rect: { x: 524, y: 20, w: 240, h: 240 },
      door: { x: 644, y: 260 },
      floorA: "#211a12",
      floorB: "#1c160f",
      accent: "#fbbf24",
      slots: [
        { x: 604, y: 162, face: "down" },
        { x: 682, y: 162, face: "down" },
        { x: 568, y: 216, face: "right" },
        { x: 718, y: 216, face: "left" },
      ],
    },
    web_station: {
      id: "web_station",
      title: "CABINA WEB",
      icon: "🌐",
      rect: { x: 778, y: 20, w: 242, h: 240 },
      door: { x: 899, y: 260 },
      floorA: "#10212b",
      floorB: "#0d1c25",
      accent: "#22d3ee",
      slots: [
        { x: 828, y: 132, face: "up" },
        { x: 899, y: 132, face: "up" },
        { x: 968, y: 132, face: "up" },
        { x: 862, y: 214, face: "up" },
        { x: 936, y: 214, face: "up" },
      ],
    },
    coding_desk: {
      id: "coding_desk",
      title: "COMPUTADORES",
      icon: "💻",
      rect: { x: 20, y: 328, w: 344, h: 272 },
      door: { x: 192, y: 328 },
      floorA: "#12211c",
      floorB: "#0f1c18",
      accent: "#34d399",
      slots: [
        { x: 78,  y: 422, face: "up" },
        { x: 192, y: 422, face: "up" },
        { x: 306, y: 422, face: "up" },
        { x: 78,  y: 530, face: "up" },
        { x: 192, y: 530, face: "up" },
        { x: 306, y: 530, face: "up" },
      ],
    },
    server_lab: {
      id: "server_lab",
      title: "TERMINAL LAB",
      icon: "⚡",
      rect: { x: 378, y: 328, w: 218, h: 272 },
      door: { x: 487, y: 328 },
      floorA: "#1a1e26",
      floorB: "#161920",
      accent: "#fb923c",
      slots: [
        { x: 428, y: 446, face: "up" },
        { x: 487, y: 446, face: "up" },
        { x: 546, y: 446, face: "up" },
        { x: 454, y: 536, face: "up" },
        { x: 522, y: 536, face: "up" },
      ],
    },
    art_studio: {
      id: "art_studio",
      title: "ESTUDIO UI",
      icon: "🎨",
      rect: { x: 610, y: 328, w: 154, h: 272 },
      door: { x: 687, y: 328 },
      floorA: "#21152c",
      floorB: "#1c1225",
      accent: "#e879f9",
      slots: [
        { x: 656, y: 446, face: "up" },
        { x: 722, y: 446, face: "up" },
        { x: 687, y: 536, face: "up" },
      ],
    },
    lounge: {
      id: "lounge",
      title: "CAFETERÍA & LOUNGE",
      icon: "☕",
      rect: { x: 778, y: 328, w: 242, h: 272 },
      door: { x: 899, y: 328 },
      floorA: "#21171d",
      floorB: "#1c1318",
      accent: "#f87171",
      // 6 slots bien espaciados en 2 filas para evitar superposición de etiquetas
      slots: [
        { x: 822, y: 426, face: "up" },
        { x: 899, y: 426, face: "up" },
        { x: 976, y: 426, face: "up" },
        { x: 822, y: 536, face: "up" },
        { x: 899, y: 536, face: "up" },
        { x: 976, y: 536, face: "up" },
      ],
    },
  };

  // =========================================================================
  // ESTADO EN MEMORIA DEL CLIENTE
  // =========================================================================
  let lastEventId = 0;
  let isFirstSync = true;
  let filterMode = "all"; // "all" | "live"
  let selectedAgentId = null;
  let hoveredAgentId = null;

  const entities = new Map();
  const particles = [];
  let recentLogs = [];

  // =========================================================================
  // ENTIDAD DE AGENTE (PATHFINDING + ANIMACIÓN)
  // =========================================================================
  class AgentEntity {
    constructor(data) {
      this.id = data.id;
      this.isWalking = false;
      this.walkFrame = 0;
      this.walkAnimTimer = 0;
      this.waypoints = [];
      this.actionQueue = [];
      this.currentActionHoldTimer = 0;

      const initialStation = STATIONS[data.station] ? data.station : "lounge";
      this.currentStation = initialStation;
      this.slotIndex = 0;

      this.syncMetadata(data);

      this.slotIndex = this.computeSlotIndex(initialStation);
      const slot = this.getSlotCoords(initialStation, this.slotIndex);

      if (data.is_subagent) {
        this.x = 708;
        this.y = 114;
        this.spawnTimer = 1.4;
      } else {
        this.x = slot.x;
        this.y = slot.y;
        this.spawnTimer = 0.6;
      }

      this.face = slot.face || "down";

      if (data.is_subagent && initialStation !== "orchestrator_hub") {
        this.navigateToStation(initialStation);
      }
    }

    syncMetadata(data) {
      this.shortId = data.short_id || this.id.slice(0, 8);
      this.name = data.name || this.shortId;
      this.compactName = this.name.replace(/\s*\[[^\]]+\]/, "").trim() || this.name;
      this.chatTitle = data.chat_title || "Sesión Antigravity";
      this.model = data.model || "Gemini";
      this.isSubagent = Boolean(data.is_subagent);
      this.subagentType = data.subagent_type || "main";
      this.parentId = data.parent_id || null;
      this.childrenIds = data.children_ids || [];
      this.palette = data.palette || {
        suit: "#38bdf8",
        hair: "#1e293b",
        accent: "#7dd3fc",
      };
      this.stepCount = data.step_count || 0;
      this.isLive = Boolean(data.is_live);
      this.isSimulated = Boolean(data.is_simulated);
      this.idleSeconds = data.idle_seconds || 0;

      if (!this.isWalking && this.actionQueue.length === 0) {
        this.badge = data.badge || "☕ En espera";
        this.detail = data.detail || "";
        this.activity = data.activity || "idle";
        this.icon = data.icon || "🤖";
        if (data.station && STATIONS[data.station] && data.station !== this.currentStation) {
          this.enqueueAction({
            station: data.station,
            activity: data.activity,
            badge: data.badge,
            detail: data.detail,
            icon: data.icon,
          });
        }
      }
    }

    computeSlotIndex(stationId) {
      const st = STATIONS[stationId] || STATIONS.lounge;
      let hash = 0;
      for (let i = 0; i < this.id.length; i++) {
        hash = (hash * 31 + this.id.charCodeAt(i)) >>> 0;
      }
      const taken = new Set();
      for (const [otherId, other] of entities.entries()) {
        if (otherId !== this.id && other.currentStation === stationId) {
          taken.add(other.slotIndex);
        }
      }
      for (let offset = 0; offset < st.slots.length; offset++) {
        const candidate = (hash + offset) % st.slots.length;
        if (!taken.has(candidate)) return candidate;
      }
      return hash % st.slots.length;
    }

    getSlotCoords(stationId, slotIdx) {
      const st = STATIONS[stationId] || STATIONS.lounge;
      return st.slots[slotIdx % st.slots.length];
    }

    enqueueAction(ev) {
      if (!ev || !STATIONS[ev.station]) return;
      const last = this.actionQueue[this.actionQueue.length - 1];
      if (last && last.station === ev.station && last.badge === ev.badge) return;
      this.actionQueue.push({
        station: ev.station,
        activity: ev.activity || "coding",
        badge: ev.badge || ev.detail || "Trabajando...",
        detail: ev.detail || "",
        icon: ev.icon || "✨",
      });
      if (this.actionQueue.length > 6) this.actionQueue.shift();
    }

    navigateToStation(targetStationId) {
      if (!STATIONS[targetStationId]) return;
      const fromStation = STATIONS[this.currentStation] || STATIONS.lounge;
      const toStation = STATIONS[targetStationId];

      this.currentStation = targetStationId;
      this.slotIndex = this.computeSlotIndex(targetStationId);
      const targetSlot = this.getSlotCoords(targetStationId, this.slotIndex);

      const pts = [];
      if (fromStation.id !== toStation.id) {
        pts.push({ x: fromStation.door.x, y: fromStation.door.y });
        pts.push({ x: fromStation.door.x, y: HALLWAY_Y });
        pts.push({ x: toStation.door.x,   y: HALLWAY_Y });
        pts.push({ x: toStation.door.x,   y: toStation.door.y });
      }
      pts.push({ x: targetSlot.x, y: targetSlot.y, face: targetSlot.face });
      this.waypoints = pts;
      this.isWalking = true;
    }

    update(dt) {
      if (this.spawnTimer > 0) this.spawnTimer = Math.max(0, this.spawnTimer - dt);

      if (this.waypoints.length > 0) {
        this.isWalking = true;
        const wp = this.waypoints[0];
        const dx = wp.x - this.x;
        const dy = wp.y - this.y;
        const dist = Math.hypot(dx, dy);
        const speed = this.actionQueue.length > 1 ? 185 : 135;

        if (dist <= speed * dt) {
          this.x = wp.x;
          this.y = wp.y;
          if (wp.face) this.face = wp.face;
          this.waypoints.shift();
          if (this.waypoints.length === 0) {
            this.isWalking = false;
            this.walkFrame = 0;
            this.currentActionHoldTimer = this.actionQueue.length > 1 ? 1.8 : 2.6;
          }
        } else {
          this.x += (dx / dist) * speed * dt;
          this.y += (dy / dist) * speed * dt;
          this.face = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up");

          this.walkAnimTimer += dt;
          if (this.walkAnimTimer >= 0.12) {
            this.walkAnimTimer = 0;
            this.walkFrame = (this.walkFrame + 1) % 4;
            particles.push({
              x: this.x + (Math.random() * 6 - 3),
              y: this.y + 12,
              vx: 0,
              vy: -7,
              life: 0.32,
              maxLife: 0.32,
              type: "dust",
              color: "rgba(180, 210, 255, 0.28)",
            });
          }
        }
        return;
      }

      this.isWalking = false;
      if (this.currentActionHoldTimer > 0) {
        this.currentActionHoldTimer = Math.max(0, this.currentActionHoldTimer - dt);
      }

      // Emitir partículas solo cuando el agente está trabajando (o muy sutil en lounge)
      const rate = this.currentStation === "lounge" ? 0.35 : 1.7;
      if (Math.random() < dt * rate) {
        this.emitActivityParticle();
      }

      if (this.currentActionHoldTimer <= 0 && this.actionQueue.length > 0) {
        const nextAct = this.actionQueue.shift();
        this.badge = nextAct.badge;
        this.detail = nextAct.detail;
        this.activity = nextAct.activity;
        this.icon = nextAct.icon;
        if (nextAct.station !== this.currentStation) {
          this.navigateToStation(nextAct.station);
        } else {
          this.currentActionHoldTimer = 2.0;
        }
      }
    }

    emitActivityParticle() {
      const table = {
        coding_desk: [["</>", "{ }", "01"], "#34d399"],
        library: [["📖", "doc", "🔍"], "#fbbf24"],
        server_lab: [["⚡", "$>", "OK"], "#fb923c"],
        strategy_board: [["💭", "💡"], "#38bdf8"],
        orchestrator_hub: [["📡", "⚡"], "#fbbf24"],
        web_station: [["🌐", "200"], "#22d3ee"],
        art_studio: [["✨", "UI"], "#e879f9"],
        lounge: [["~"], "#94a3b8"],
      };
      const entry = table[this.currentStation];
      if (!entry) return;
      const [syms, color] = entry;
      particles.push({
        x: this.x + (Math.random() * 14 - 7),
        y: this.y - 24,
        vx: (Math.random() - 0.5) * 8,
        vy: -16 - Math.random() * 8,
        life: 1.0,
        maxLife: 1.0,
        type: "text",
        text: syms[Math.floor(Math.random() * syms.length)],
        color,
      });
    }
  }

  // =========================================================================
  // UTILIDADES DE DIBUJO PIXEL ART LIMPIO
  // =========================================================================
  function drawRect(x, y, w, h, fill, stroke = null, sw = 1) {
    ctx.fillStyle = fill;
    ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = sw;
      ctx.strokeRect(Math.round(x) + 0.5, Math.round(y) + 0.5, Math.round(w) - 1, Math.round(h) - 1);
    }
  }

  function drawRoundPill(x, y, w, h, r, fill, stroke = null) {
    ctx.beginPath();
    ctx.roundRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h), r);
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }

  function getOccupiedStations(visibleEntities) {
    const counts = {};
    for (const ent of visibleEntities) {
      counts[ent.currentStation] = (counts[ent.currentStation] || 0) + 1;
    }
    return counts;
  }

  function drawWorld(nowSec, visibleEntities) {
    const occupied = getOccupiedStations(visibleEntities);

    // Fondo profundo estilo Pixel Agents
    ctx.fillStyle = "#1c1e2a";
    ctx.fillRect(0, 0, W, H);

    // Corredor central
    drawRect(20, 264, W - 40, 60, "#ddd0b6", "#131820", 2);
    ctx.strokeStyle = "rgba(168, 144, 112, 0.45)";
    ctx.lineWidth = 1;
    ctx.setLineDash([6, 8]);
    ctx.beginPath();
    ctx.moveTo(40, HALLWAY_Y);
    ctx.lineTo(W - 40, HALLWAY_Y);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "rgba(69, 42, 24, 0.55)";
    ctx.font = "600 9px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillText("PIXELAVITY HQ  ·  CORREDOR CENTRAL", W / 2, HALLWAY_Y + 3);

    // Dibujar las 8 salas con iluminación dinámica según actividad
    for (const st of Object.values(STATIONS)) {
      const count = occupied[st.id] || 0;
      const isWorkingRoom = count > 0 && st.id !== "lounge";
      drawStationBase(st, count, isWorkingRoom);
    }

    // Mobiliario detallado
    drawLibraryFurniture(STATIONS.library);
    drawStrategyFurniture(STATIONS.strategy_board);
    drawOrchestratorFurniture(STATIONS.orchestrator_hub, nowSec, (occupied.orchestrator_hub || 0) > 0);
    drawWebStationFurniture(STATIONS.web_station, nowSec, (occupied.web_station || 0) > 0);
    drawCodingDesksFurniture(STATIONS.coding_desk, nowSec, visibleEntities);
    drawServerLabFurniture(STATIONS.server_lab, nowSec, (occupied.server_lab || 0) > 0);
    drawArtStudioFurniture(STATIONS.art_studio);
    drawLoungeFurniture(STATIONS.lounge, nowSec);
  }

  function drawStationBase(st, count, isWorkingRoom) {
    const { x, y, w, h } = st.rect;

    // Piso en cuadrícula cálida Pixel Agents
    const tile = 16;
    for (let ty = y; ty < y + h; ty += tile) {
      for (let tx = x; tx < x + w; tx += tile) {
        const tw = Math.min(tile, x + w - tx);
        const th = Math.min(tile, y + h - ty);
        ctx.fillStyle = "#ddd0b6";
        ctx.fillRect(tx, ty, tw, th);
        ctx.fillStyle = "#c9b899";
        ctx.fillRect(tx + tw - 1, ty, 1, th);
        ctx.fillRect(tx, ty + th - 1, tw, 1);
      }
    }

    // Muro arquitectónico teal estilo Pixel Agents
    ctx.strokeStyle = isWorkingRoom ? st.accent : "#1e4255";
    ctx.lineWidth = 3;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);

    // Puerta abierta al corredor
    ctx.fillStyle = "#ddd0b6";
    if (st.door.y <= 270) {
      ctx.fillRect(st.door.x - 18, y + h - 4, 36, 8);
    } else {
      ctx.fillRect(st.door.x - 18, y - 4, 36, 8);
    }

    // Cabecera de sala estilo muro teal
    drawRect(x + 1, y + 1, w - 2, 24, "#1e4255");
    ctx.fillStyle = isWorkingRoom ? "#fde047" : "#f8fafc";
    ctx.font = "bold 10px Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText(`${st.icon} ${st.title}`, x + 10, y + 17);

    // Indicador numérico discreto si hay agentes dentro
    if (count > 0) {
      const badgeW = 20;
      drawRoundPill(x + w - badgeW - 8, y + 6, badgeW, 15, 7, "rgba(56, 189, 248, 0.16)");
      ctx.fillStyle = isWorkingRoom ? st.accent : "#cbd5e1";
      ctx.font = "bold 9px Consolas, monospace";
      ctx.textAlign = "center";
      ctx.fillText(String(count), x + w - badgeW / 2 - 8, y + 17);
    }
  }

  function drawLibraryFurniture(st) {
    const { x, y } = st.rect;
    const books = ["#ef4444", "#3b82f6", "#10b981", "#f59e0b", "#a855f7", "#ec4899"];
    for (let s = 0; s < 3; s++) {
      const sx = x + 18 + s * 72;
      const sy = y + 38;
      drawRect(sx, sy, 62, 52, "#3e2723", "#6d4c41", 1);
      for (let row = 0; row < 3; row++) {
        const ry = sy + 6 + row * 15;
        ctx.fillStyle = "#2b1b17";
        ctx.fillRect(sx + 4, ry + 10, 54, 3);
        for (let b = 0; b < 8; b++) {
          ctx.fillStyle = books[(s * 7 + row * 3 + b) % books.length];
          ctx.fillRect(sx + 6 + b * 6, ry, 5, 10);
        }
      }
    }
    for (let t = 0; t < 2; t++) {
      const tx = x + 36 + t * 98;
      const ty = y + 162;
      drawRect(tx, ty, 70, 30, "#4e342e", "#795548", 1);
      drawRect(tx + 14, ty + 7, 16, 12, "#fef3c7", "#a1887f", 1);
      drawRect(tx + 30, ty + 7, 16, 12, "#fef3c7", "#a1887f", 1);
    }
  }

  function drawStrategyFurniture(st) {
    const { x, y } = st.rect;
    const bx = x + 22;
    const by = y + 40;
    drawRect(bx, by, 188, 54, "#0d1726", "#2a4365", 1);
    drawRect(bx + 14, by + 13, 28, 14, "#38bdf8");
    drawRect(bx + 62, by + 13, 28, 14, "#fbbf24");
    drawRect(bx + 110, by + 13, 28, 14, "#34d399");
    ctx.strokeStyle = "#94a3b8";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(bx + 42, by + 20);
    ctx.lineTo(bx + 62, by + 20);
    ctx.moveTo(bx + 90, by + 20);
    ctx.lineTo(bx + 110, by + 20);
    ctx.stroke();
    drawRect(bx + 152, by + 11, 10, 10, "#fde047");
    drawRect(bx + 166, by + 11, 10, 10, "#f472b6");
    drawRect(bx + 152, by + 25, 10, 10, "#34d399");
    drawRect(x + 48, y + 162, 136, 26, "#162235", "#2a4365", 1);
  }

  function drawOrchestratorFurniture(st, nowSec, active) {
    const { x, y } = st.rect;
    const cx = x + 80;
    const cy = y + 98;
    drawRect(cx - 42, cy - 26, 84, 52, "#19130b", active ? "#fbbf24" : "#5c4620", 1);
    const pulse = 17 + Math.sin(nowSec * 3.5) * 3;
    ctx.strokeStyle = active ? "rgba(251, 191, 36, 0.85)" : "rgba(251, 191, 36, 0.35)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(cx, cy, pulse, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "#fcd34d";
    ctx.font = "bold 8px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillText("ORCH-CORE", cx, cy + 3);

    // Spawn Pad
    const px = x + 184;
    const py = y + 92;
    drawRect(px - 26, py - 26, 52, 52, "#140f24", "#7e22ce", 1);
    const pr = 13 + Math.cos(nowSec * 4) * 2.5;
    ctx.strokeStyle = "rgba(56, 189, 248, 0.65)";
    ctx.beginPath();
    ctx.arc(px, py, pr, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "#c084fc";
    ctx.font = "bold 7.5px Consolas, monospace";
    ctx.fillText("SPAWN PAD", px, py + 37);
  }

  function drawWebStationFurniture(st, nowSec, active) {
    const { x, y } = st.rect;
    for (let m = 0; m < 3; m++) {
      const mx = x + 22 + m * 68;
      const my = y + 46;
      drawRect(mx, my, 56, 34, "#0a1724", active ? "#22d3ee" : "#1e3a52", 1);
      ctx.fillStyle = active ? "rgba(34, 211, 238, 0.45)" : "rgba(34, 211, 238, 0.16)";
      const bw = active ? 14 + ((Math.floor(nowSec * 6) + m * 5) % 30) : 26;
      ctx.fillRect(mx + 6, my + 8, bw, 4);
      ctx.fillRect(mx + 6, my + 16, 36, 4);
      ctx.fillRect(mx + 6, my + 24, 22, 4);
    }
    const gx = x + 121;
    const gy = y + 164;
    drawRect(gx - 34, gy - 20, 68, 40, "#0b1a24", "#1e3a52", 1);
    ctx.strokeStyle = active ? "#22d3ee" : "rgba(34, 211, 238, 0.4)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(gx, gy, 13, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(gx - 13, gy);
    ctx.lineTo(gx + 13, gy);
    ctx.moveTo(gx, gy - 13);
    ctx.lineTo(gx, gy + 13);
    ctx.stroke();
  }

  function drawCodingDesksFurniture(st, nowSec, visibleEntities) {
    const activeDesks = new Set();
    for (const ent of visibleEntities) {
      if (!ent.isWalking && ent.currentStation === "coding_desk") {
        activeDesks.add(ent.slotIndex);
      }
    }
    st.slots.forEach((slot, idx) => {
      const dx = slot.x - 42;
      const dy = slot.y - 46;
      const occ = activeDesks.has(idx);
      drawRect(slot.x - 10, slot.y + 4, 20, 14, "#a67443", "#452a18", 1);
      drawRect(dx, dy, 84, 34, "#c4925c", "#54351c", 1);
      for (let m = 0; m < 2; m++) {
        const mx = dx + 8 + m * 36;
        const my = dy + 4;
        drawRect(mx, my, 28, 18, "#ece9df", "#18161e", 1);
        drawRect(mx + 3, my + 3, 22, 12, occ ? "#112a22" : "#242b38");
        if (occ) {
          const sc = Math.floor(nowSec * 8 + idx + m) % 3;
          ctx.fillStyle = m === 0 ? "#34d399" : "#38bdf8";
          ctx.fillRect(mx + 5, my + 5 + sc, 12, 2);
          ctx.fillRect(mx + 5, my + 9, 16, 2);
        }
      }
      drawRect(dx + 24, dy + 25, 28, 5, "#ece9df", "#18161e", 1);
    });
  }

  function drawServerLabFurniture(st, nowSec, active) {
    const { x, y } = st.rect;
    for (let r = 0; r < 4; r++) {
      const rx = x + 15 + r * 49;
      const ry = y + 40;
      drawRect(rx, ry, 40, 62, "#0f131a", "#2d3748", 1);
      for (let u = 0; u < 4; u++) {
        const uy = ry + 6 + u * 14;
        ctx.fillStyle = "#1a202c";
        ctx.fillRect(rx + 4, uy, 32, 10);
        const speed = active ? 8 : 2;
        const blink = ((Math.floor(nowSec * speed) + r * 3 + u) % 3) === 0;
        ctx.fillStyle = blink ? "#34d399" : "#fb923c";
        ctx.fillRect(rx + 7, uy + 3, 4, 4);
        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(rx + 14, uy + 3, 4, 4);
      }
    }
    drawRect(x + 32, y + 174, 154, 32, "#111620", active ? "#fb923c" : "#334155", 1);
    ctx.fillStyle = active ? "#34d399" : "#64748b";
    ctx.font = "bold 9.5px Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText("$ antigravity --exec", x + 43, y + 194);
  }

  function drawArtStudioFurniture(st) {
    const { x, y } = st.rect;
    drawRect(x + 18, y + 46, 48, 40, "#fef3c7", "#d97706", 1);
    ctx.fillStyle = "#f43f5e";
    ctx.fillRect(x + 25, y + 53, 15, 13);
    ctx.fillStyle = "#38bdf8";
    ctx.fillRect(x + 40, y + 59, 17, 17);
    drawRect(x + 80, y + 50, 56, 36, "#2e1065", "#a855f7", 1);
    drawRect(x + 90, y + 58, 36, 20, "#13072e", "#38bdf8", 1);
  }

  function drawLoungeFurniture(st, nowSec) {
    const { x, y } = st.rect;
    // Barra de café limpia
    drawRect(x + 20, y + 42, 202, 30, "#3b231e", "#6d4c41", 1);
    // Máquina espresso con vapor sutil
    drawRect(x + 34, y + 46, 26, 22, "#991b1b", "#f87171", 1);
    ctx.fillStyle = "rgba(255,255,255,0.22)";
    const steamY = y + 40 - ((nowSec * 12) % 8);
    ctx.fillRect(x + 44, steamY, 3, 4);
    // Dispensador de agua
    drawRect(x + 186, y + 44, 22, 24, "#bae6fd", "#38bdf8", 1);
    // Sofá amplio y limpio
    drawRect(x + 46, y + 148, 150, 34, "#6b153b", "#be185d", 1);
    drawRect(x + 54, y + 155, 134, 20, "#831843");
  }

  // =========================================================================
  // ENLACES HOLOGRÁFICOS ENTRE ORCHESTRATOR Y SUBAGENTES
  // =========================================================================
  function drawOrchestratorLinks(nowSec, visibleEntities) {
    const visibleSet = new Set(visibleEntities.map((e) => e.id));
    for (const ent of visibleEntities) {
      if (ent.parentId && visibleSet.has(ent.parentId)) {
        const parent = entities.get(ent.parentId);
        ctx.save();
        ctx.strokeStyle = "rgba(251, 191, 36, 0.5)";
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 6]);
        ctx.lineDashOffset = -nowSec * 24;
        ctx.beginPath();
        ctx.moveTo(parent.x, parent.y - 8);
        ctx.lineTo(ent.x, ent.y - 8);
        ctx.stroke();

        const t = (nowSec * 0.85) % 1;
        const px = parent.x + (ent.x - parent.x) * t;
        const py = (parent.y - 8) + ((ent.y - 8) - (parent.y - 8)) * t;
        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(px - 2.5, py - 2.5, 5, 5);
        ctx.restore();
      }
    }
  }

  // =========================================================================
  // RENDERIZADO DE PERSONAJES PIXEL ART (CAPA 1: SPRITE, CAPA 2: ETIQUETAS)
  // =========================================================================
  function drawAgentBody(ent, nowSec) {
    const x = Math.round(ent.x);
    const y = Math.round(ent.y);
    const isSelected = ent.id === selectedAgentId;
    const isHovered = ent.id === hoveredAgentId;

    const walkBob = ent.isWalking
      ? (ent.walkFrame % 2 === 1 ? -3 : 0)
      : Math.round(Math.sin(nowSec * 3.5 + x) * 1);

    ctx.save();

    if (ent.spawnTimer > 0) {
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(x, y - 6, 20 * ent.spawnTimer, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Anillo de selección o hover
    if (isSelected || isHovered) {
      ctx.strokeStyle = isSelected ? "#38bdf8" : "rgba(255, 255, 255, 0.55)";
      ctx.lineWidth = isSelected ? 2 : 1.2;
      ctx.beginPath();
      ctx.ellipse(x, y + 12, 15, 6, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Sombra suave
    ctx.fillStyle = "rgba(0, 0, 0, 0.42)";
    ctx.fillRect(x - 9, y + 10, 18, 4);

    const py = y + walkBob;

    // Piernas y zapatos (estilo Pixel Agents 16x32)
    const legL = ent.isWalking ? (ent.walkFrame === 1 ? -2 : ent.walkFrame === 3 ? 2 : 0) : 0;
    const legR = ent.isWalking ? (ent.walkFrame === 3 ? -2 : ent.walkFrame === 1 ? 2 : 0) : 0;
    drawRect(x - 6, py + 3 + legL, 5, 7, "#1d4e78", "#18161e", 1);
    drawRect(x + 1, py + 3 + legR, 5, 7, "#1d4e78", "#18161e", 1);
    ctx.fillStyle = "#1a1e26";
    ctx.fillRect(x - 6, py + 8 + legL, 5, 3);
    ctx.fillRect(x + 1, py + 8 + legR, 5, 3);

    // Torso con camisa y corbata
    drawRect(x - 8, py - 9, 16, 13, ent.palette.suit || "#1f6199", "#18161e", 1);
    ctx.fillStyle = "#f8fafc";
    ctx.fillRect(x - 2, py - 8, 4, 10);
    ctx.fillStyle = "#18161e";
    ctx.fillRect(x - 1, py - 7, 2, 7);

    // Brazos
    const isTyping = !ent.isWalking && (ent.currentStation === "coding_desk" || ent.currentStation === "server_lab");
    const jitter = isTyping ? Math.round(Math.sin(nowSec * 24) * 2) : 0;
    drawRect(x - 12, py - 8 + jitter, 4, 9, ent.palette.suit || "#1f6199", "#18161e", 1);
    drawRect(x + 8, py - 8 - jitter, 4, 9, ent.palette.suit || "#1f6199", "#18161e", 1);
    ctx.fillStyle = "#f5c59c";
    ctx.fillRect(x - 11, py - 1 + jitter, 2, 2);
    ctx.fillRect(x + 9, py - 1 - jitter, 2, 2);

    // Cabeza
    drawRect(x - 7, py - 21, 14, 12, "#f5c59c", "#18161e", 1);

    // Cabello con mechón estilo Pixel Agents
    const hairC = ent.palette.hair || "#946b3e";
    drawRect(x - 9, py - 28, 18, 10, hairC, "#18161e", 1);
    ctx.fillRect(x - 5, py - 31, 4, 4);
    ctx.fillRect(x + 1, py - 30, 3, 3);
    if (ent.face === "left") ctx.fillRect(x + 3, py - 22, 5, 8);
    if (ent.face === "right") ctx.fillRect(x - 8, py - 22, 5, 8);

    // Ojos 2x2 blanco + pupila oscura
    if (ent.face === "down") {
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(x - 5, py - 16, 2, 3);
      ctx.fillRect(x + 3, py - 16, 2, 3);
      ctx.fillStyle = "#18161e";
      ctx.fillRect(x - 3, py - 16, 2, 3);
      ctx.fillRect(x + 1, py - 16, 2, 3);
    } else if (ent.face === "left") {
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(x - 6, py - 16, 2, 3);
      ctx.fillStyle = "#18161e";
      ctx.fillRect(x - 4, py - 16, 2, 3);
    } else if (ent.face === "right") {
      ctx.fillStyle = "#18161e";
      ctx.fillRect(x + 2, py - 16, 2, 3);
      ctx.fillStyle = "#f8fafc";
      ctx.fillRect(x + 4, py - 16, 2, 3);
    }

    // Libro en biblioteca (con lentes) o taza en lounge
    if (!ent.isWalking) {
      if (ent.currentStation === "library") {
        ctx.fillStyle = "#18161e";
        ctx.fillRect(x - 6, py - 16, 12, 1);
        drawRect(x - 5, py - 6, 10, 8, "#f8fafc", "#18161e", 1);
      } else if (ent.currentStation === "lounge") {
        drawRect(x + 6, py - 6, 6, 6, "#f8fafc", "#18161e", 1);
      }
    }

    ctx.restore();
  }

  function drawAgentOverlay(ent, nowSec, forceFullBubble) {
    const x = Math.round(ent.x);
    const y = Math.round(ent.y);
    const isSelected = ent.id === selectedAgentId;
    const isHovered = ent.id === hoveredAgentId;
    const isIdleInLounge = !ent.isWalking && ent.currentStation === "lounge";

    const walkBob = ent.isWalking
      ? (ent.walkFrame % 2 === 1 ? -3 : 0)
      : Math.round(Math.sin(nowSec * 3.5 + x) * 1);
    const py = y + walkBob;

    ctx.save();

    // 1. Etiqueta compacta debajo de los pies (limpia, sin desbordar)
    const label = ent.isSubagent ? `⚡ ${ent.compactName}` : ent.compactName;
    const shortLabel = label.length > 13 ? label.slice(0, 12) + "…" : label;
    ctx.font = "600 9px Consolas, monospace";
    const nw = ctx.measureText(shortLabel).width + 10;
    drawRoundPill(
      x - nw / 2,
      y + 15,
      nw,
      14,
      4,
      isSelected ? "rgba(15, 23, 42, 0.96)" : "rgba(10, 14, 24, 0.82)",
      isSelected ? "#38bdf8" : "rgba(148, 163, 184, 0.25)"
    );
    ctx.fillStyle = isSelected ? "#ffffff" : "#cbd5e1";
    ctx.textAlign = "center";
    ctx.fillText(shortLabel, x, y + 25);

    // 2. Globo de estado sobre la cabeza:
    //    - Si está descansando en Cafetería y NO está seleccionado/hover: solo un pequeño badge "☕" para no ensuciar
    //    - Si está trabajando, caminando, o seleccionado/hover: burbuja completa nítida
    if (isIdleInLounge && !forceFullBubble) {
      drawRoundPill(x - 10, py - 42, 20, 15, 7, "rgba(15, 23, 42, 0.82)", "rgba(248, 113, 113, 0.35)");
      ctx.fillStyle = "#fca5a5";
      ctx.font = "10px 'Segoe UI', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("☕", x, py - 31);
    } else {
      const bubbleText = ent.isWalking
        ? `→ ${STATIONS[ent.currentStation]?.title || ent.currentStation}`
        : ent.badge;
      if (bubbleText) {
        const clipped = bubbleText.length > 26 ? bubbleText.slice(0, 25) + "…" : bubbleText;
        ctx.font = "600 9.5px 'Segoe UI', Consolas, sans-serif";
        const bw = ctx.measureText(clipped).width + 14;
        const bx = Math.max(10, Math.min(W - bw - 10, x - bw / 2));
        const by = py - 46;
        drawRoundPill(
          bx,
          by,
          bw,
          18,
          6,
          "rgba(15, 23, 42, 0.95)",
          isSelected || isHovered ? "#38bdf8" : "rgba(148, 163, 184, 0.35)"
        );
        ctx.fillStyle = "#f1f5f9";
        ctx.textAlign = "center";
        ctx.fillText(clipped, bx + bw / 2, by + 12.5);
      }
    }

    ctx.restore();
  }

  // =========================================================================
  // PARTÍCULAS
  // =========================================================================
  function updateAndDrawParticles(dt) {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.life -= dt;
      if (p.life <= 0) {
        particles.splice(i, 1);
        continue;
      }
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      const alpha = Math.max(0, p.life / p.maxLife);

      ctx.save();
      ctx.globalAlpha = alpha;
      if (p.type === "dust") {
        ctx.fillStyle = p.color;
        ctx.fillRect(Math.round(p.x), Math.round(p.y), 3, 3);
      } else {
        ctx.fillStyle = p.color;
        ctx.font = "bold 10px Consolas, monospace";
        ctx.textAlign = "center";
        ctx.fillText(p.text, Math.round(p.x), Math.round(p.y));
      }
      ctx.restore();
    }
  }

  // =========================================================================
  // BUCLE PRINCIPAL (60 FPS)
  // =========================================================================
  let lastFrameTime = performance.now();

  function frameLoop(nowMs) {
    const dt = Math.min(0.1, (nowMs - lastFrameTime) / 1000);
    lastFrameTime = nowMs;
    const nowSec = nowMs / 1000;

    const visibleEntities = Array.from(entities.values()).filter(
      (e) => !e.isSimulated && (filterMode === "all" || e.isLive)
    );
    visibleEntities.sort((a, b) => a.y - b.y);

    drawWorld(nowSec, visibleEntities);
    drawOrchestratorLinks(nowSec, visibleEntities);

    // 1. Actualizar y dibujar cuerpos de todos los agentes
    for (const ent of visibleEntities) {
      ent.update(dt);
      drawAgentBody(ent, nowSec);
    }

    // 2. Dibujar etiquetas de fondo (no seleccionados)
    let priorityAgent = null;
    for (const ent of visibleEntities) {
      if (ent.id === hoveredAgentId || ent.id === selectedAgentId) {
        priorityAgent = ent;
        continue;
      }
      drawAgentOverlay(ent, nowSec, false);
    }

    // 3. Dibujar al agente seleccionado o bajo el cursor siempre encima de todo
    if (priorityAgent) {
      drawAgentOverlay(priorityAgent, nowSec, true);
    }

    updateAndDrawParticles(dt);
    requestAnimationFrame(frameLoop);
  }

  // =========================================================================
  // SINCRONIZACIÓN CON ANTIGRAVITY BRAIN WATCHER
  // =========================================================================
  async function pollBackendState() {
    let snap = null;
    try {
      const res = await fetch(`/api/state?since=${lastEventId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      snap = await res.json();
    } catch (err) {
      const pill = document.getElementById("connPill");
      const txt = document.getElementById("connText");
      if (pill && txt) {
        txt.textContent = "RECONECTANDO...";
        pill.style.borderColor = "#f87171";
        pill.style.color = "#f87171";
      }
      return;
    }

    try {
      applySnapshot(snap);
    } catch (err) {
      console.error("[PixelAgents] Error aplicando snapshot:", err);
    }
  }

  function applySnapshot(snap) {
    const pill = document.getElementById("connPill");
    const txt = document.getElementById("connText");
    if (txt) txt.textContent = "EN VIVO";
    if (pill) {
      pill.style.borderColor = "rgba(52, 211, 153, 0.3)";
      pill.style.color = "#34d399";
    }

    const currentIds = new Set();
    for (const agData of snap.agents || []) {
      if (agData.is_simulated) continue; // Modo espectador puro: solo agentes reales
      currentIds.add(agData.id);
      if (!entities.has(agData.id)) {
        entities.set(agData.id, new AgentEntity(agData));
      } else {
        entities.get(agData.id).syncMetadata(agData);
      }
    }

    for (const existingId of Array.from(entities.keys())) {
      if (!currentIds.has(existingId)) {
        entities.delete(existingId);
        if (selectedAgentId === existingId) selectedAgentId = null;
      }
    }

    if (isFirstSync) {
      isFirstSync = false;
      lastEventId = snap.latest_event_id || 0;
    } else if (Array.isArray(snap.events) && snap.events.length > 0) {
      for (const ev of snap.events) {
        if (ev.id > lastEventId) lastEventId = ev.id;
        const ent = entities.get(ev.agent_id);
        if (ent) ent.enqueueAction(ev);
      }
    } else if (snap.latest_event_id > lastEventId) {
      lastEventId = snap.latest_event_id;
    }

    if (!selectedAgentId && entities.size > 0) {
      selectedAgentId = entities.keys().next().value;
    }

    recentLogs = (snap.recent_log || []).filter((l) => !String(l.agent_id || "").startsWith("sim-") && !String(l.agent_id || "").startsWith("sub-"));
    renderSidebarUI();
  }

  // =========================================================================
  // PANEL LATERAL
  // =========================================================================
  function renderSidebarUI() {
    const visibleList = Array.from(entities.values()).filter(
      (e) => !e.isSimulated && (filterMode === "all" || e.isLive)
    );

    const mainChats = visibleList.filter((e) => !e.isSubagent).length;
    const subAgents = visibleList.filter((e) => e.isSubagent).length;

    document.getElementById("statChats").textContent = String(mainChats);
    document.getElementById("statSubs").textContent = String(subAgents);
    document.getElementById("agentCountBadge").textContent = String(visibleList.length);

    // Lista de agentes
    const agentsContainer = document.getElementById("agentsList");
    agentsContainer.innerHTML = "";
    for (const ent of visibleList) {
      const card = document.createElement("div");
      card.className = `agent-item${ent.id === selectedAgentId ? " selected" : ""}${ent.isSubagent ? " is-subagent" : ""}`;
      card.style.borderLeftColor = ent.palette.suit;
      card.onclick = () => {
        selectedAgentId = ent.id;
        renderSidebarUI();
      };

      const prefix = ent.isSubagent ? "↳ " : "";
      const statusText = ent.isWalking
        ? `Caminando a ${STATIONS[ent.currentStation]?.title || ent.currentStation}`
        : ent.badge;

      card.innerHTML = `
        <div class="agent-row-top">
          <div class="agent-name">${prefix}${escapeHtml(ent.name)}</div>
          <span class="agent-model-pill">${escapeHtml(ent.model)}</span>
        </div>
        <div class="agent-badge-row">${escapeHtml(statusText)}</div>
        <div class="agent-prompt-row">${escapeHtml(ent.chatTitle)}</div>
      `;
      agentsContainer.appendChild(card);
    }

    // Inspector
    const inspBody = document.getElementById("inspectorBody");
    const inspBadge = document.getElementById("inspTypeBadge");
    const sel = entities.get(selectedAgentId);

    if (!sel) {
      inspBadge.textContent = "ESPECTADOR";
      inspBody.innerHTML = `<p class="empty-hint">Haz clic sobre un personaje para ver sus detalles en vivo.</p>`;
    } else {
      inspBadge.textContent = sel.isSubagent ? `SUB · ${sel.subagentType.toUpperCase()}` : "PRINCIPAL";
      const st = STATIONS[sel.currentStation];
      const stLabel = st ? `${st.icon} ${st.title}` : sel.currentStation;
      inspBody.innerHTML = `
        <div class="insp-title">
          <span class="insp-dot" style="background:${sel.palette.suit}"></span>
          ${escapeHtml(sel.name)}
        </div>
        <div class="insp-model">${escapeHtml(sel.model)}</div>
        <div class="insp-detail">
          <div><strong>Sala:</strong> ${escapeHtml(stLabel)}</div>
          <div><strong>Estado:</strong> ${escapeHtml(sel.badge)}</div>
          <div class="insp-detail-muted">${escapeHtml(sel.chatTitle)}</div>
        </div>
        <div class="insp-meta">
          <span>Pasos: <strong>${sel.stepCount}</strong></span>
          <span>ID: <strong>${escapeHtml(sel.shortId)}</strong></span>
        </div>
      `;
    }

    // Telemetría reciente
    const feedContainer = document.getElementById("feedList");
    feedContainer.innerHTML = "";
    for (const item of recentLogs.slice(0, 12)) {
      const div = document.createElement("div");
      div.className = "feed-item";
      div.innerHTML = `
        <div class="feed-top">
          <span class="feed-agent">${escapeHtml(item.agent_name || "")}</span>
          <span>${escapeHtml(item.time_str || "")}</span>
        </div>
        <div class="feed-badge">${escapeHtml(item.badge || "")}</div>
        <div class="feed-detail">${escapeHtml(item.detail || "")}</div>
      `;
      feedContainer.appendChild(div);
    }
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // =========================================================================
  // INTERACCIÓN SOLO ESPECTADOR (HOVER Y CLIC PARA INSPECCIONAR PERSONAJES)
  // =========================================================================
  function getCanvasCoords(evt) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: (evt.clientX - rect.left) * (W / rect.width),
      y: (evt.clientY - rect.top) * (H / rect.height),
    };
  }

  canvas.addEventListener("mousemove", (evt) => {
    const pt = getCanvasCoords(evt);
    let found = null;
    for (const ent of entities.values()) {
      if (ent.isSimulated || (filterMode === "live" && !ent.isLive)) continue;
      if (Math.hypot(pt.x - ent.x, pt.y - (ent.y - 6)) <= 24) {
        found = ent.id;
        break;
      }
    }
    hoveredAgentId = found;
    canvas.style.cursor = found ? "pointer" : "default";
  });

  canvas.addEventListener("click", (evt) => {
    const pt = getCanvasCoords(evt);
    for (const ent of entities.values()) {
      if (ent.isSimulated || (filterMode === "live" && !ent.isLive)) continue;
      if (Math.hypot(pt.x - ent.x, pt.y - (ent.y - 6)) <= 24) {
        selectedAgentId = ent.id;
        renderSidebarUI();
        return;
      }
    }
  });

  document.getElementById("btnFilterAll").onclick = () => {
    filterMode = "all";
    document.getElementById("btnFilterAll").classList.add("active");
    document.getElementById("btnFilterLive").classList.remove("active");
    renderSidebarUI();
  };

  document.getElementById("btnFilterLive").onclick = () => {
    filterMode = "live";
    document.getElementById("btnFilterLive").classList.add("active");
    document.getElementById("btnFilterAll").classList.remove("active");
    renderSidebarUI();
  };

  pollBackendState();
  setInterval(pollBackendState, 850);
  requestAnimationFrame(frameLoop);
})();
