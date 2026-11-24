/**
 * PixelAgents // Antigravity Live Visualizer
 * Motor 2D Pixel Art en HTML5 Canvas con:
 *  - 8 Zonas interactivas (Biblioteca, Pizarra, Orchestrator, Cabina Web, Computadores, Terminal Lab, Estudio UI, Cafetería)
 *  - Pathfinding por pasillos y puertas (los agentes caminan físicamente de una sala a otra)
 *  - Cola de actividades por agente (para que cada herramienta se vea con su caminata y animación)
 *  - Enlaces holográficos entre Orchestrator y sus Subagentes
 *  - Soporte multi-chat (cada chat de Antigravity es un personaje con su modelo y paleta)
 */

(() => {
  const canvas = document.getElementById("pixelCanvas");
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;

  const W = canvas.width;   // 1024
  const H = canvas.height;  // 600
  const HALLWAY_Y = 284;    // Pasillo central horizontal

  // =========================================================================
  // DEFINICIÓN DE LAS 8 SALAS / ESTACIONES DE LA OFICINA PIXEL ART
  // =========================================================================
  const STATIONS = {
    library: {
      id: "library",
      title: "📚 BIBLIOTECA & LIBRERÍAS",
      subtitle: "Docs / Read / Search",
      rect: { x: 18, y: 42, w: 245, h: 214 },
      door: { x: 140, y: 256 },
      color: "#8d5524",
      floorA: "#3b281e",
      floorB: "#332219",
      border: "#d49a6a",
      slots: [
        { x: 68,  y: 122, face: "up" },
        { x: 142, y: 122, face: "up" },
        { x: 212, y: 122, face: "up" },
        { x: 105, y: 192, face: "down" },
        { x: 175, y: 192, face: "down" },
      ],
    },
    strategy_board: {
      id: "strategy_board",
      title: "💭 PIZARRA DE ESTRATEGIA",
      subtitle: "Thinking / Planning",
      rect: { x: 277, y: 42, w: 225, h: 214 },
      door: { x: 390, y: 256 },
      color: "#1e88e5",
      floorA: "#1a283b",
      floorB: "#162233",
      border: "#4fc3f7",
      slots: [
        { x: 335, y: 130, face: "up" },
        { x: 395, y: 130, face: "up" },
        { x: 452, y: 130, face: "up" },
        { x: 365, y: 195, face: "up" },
        { x: 425, y: 195, face: "up" },
      ],
    },
    orchestrator_hub: {
      id: "orchestrator_hub",
      title: "🎛️ NÚCLEO ORCHESTRATOR",
      subtitle: "Multi-Agent Command",
      rect: { x: 516, y: 42, w: 235, h: 214 },
      door: { x: 634, y: 256 },
      color: "#ffb300",
      floorA: "#261e14",
      floorB: "#1f1810",
      border: "#ffd54f",
      slots: [
        { x: 595, y: 145, face: "down" },
        { x: 672, y: 145, face: "down" },
        { x: 560, y: 195, face: "right" },
        { x: 705, y: 195, face: "left" },
      ],
    },
    web_station: {
      id: "web_station",
      title: "🌐 CABINA WEB & RADAR",
      subtitle: "Browser / APIs / Net",
      rect: { x: 765, y: 42, w: 241, h: 214 },
      door: { x: 885, y: 256 },
      color: "#00e5ff",
      floorA: "#112833",
      floorB: "#0e222b",
      border: "#00e5ff",
      slots: [
        { x: 820, y: 132, face: "up" },
        { x: 888, y: 132, face: "up" },
        { x: 955, y: 132, face: "up" },
        { x: 855, y: 198, face: "up" },
        { x: 925, y: 198, face: "up" },
      ],
    },
    coding_desk: {
      id: "coding_desk",
      title: "💻 SALA DE COMPUTADORES",
      subtitle: "Coding / Write & Edit",
      rect: { x: 18, y: 312, w: 356, h: 268 },
      door: { x: 196, y: 312 },
      color: "#00e676",
      floorA: "#162621",
      floorB: "#12201c",
      border: "#00e676",
      slots: [
        { x: 78,  y: 402, face: "up", deskIndex: 0 },
        { x: 196, y: 402, face: "up", deskIndex: 1 },
        { x: 314, y: 402, face: "up", deskIndex: 2 },
        { x: 78,  y: 506, face: "up", deskIndex: 3 },
        { x: 196, y: 506, face: "up", deskIndex: 4 },
        { x: 314, y: 506, face: "up", deskIndex: 5 },
      ],
    },
    server_lab: {
      id: "server_lab",
      title: "⚡ LABORATORIO TERMINAL",
      subtitle: "Bash / Tests / Build",
      rect: { x: 388, y: 312, w: 224, h: 268 },
      door: { x: 500, y: 312 },
      color: "#ff9100",
      floorA: "#21242b",
      floorB: "#1b1e24",
      border: "#ffab40",
      slots: [
        { x: 445, y: 432, face: "up" },
        { x: 505, y: 432, face: "up" },
        { x: 562, y: 432, face: "up" },
        { x: 472, y: 515, face: "up" },
        { x: 535, y: 515, face: "up" },
      ],
    },
    art_studio: {
      id: "art_studio",
      title: "🎨 ESTUDIO CREATIVO",
      subtitle: "UI / Design / Assets",
      rect: { x: 626, y: 312, w: 168, h: 268 },
      door: { x: 710, y: 312 },
      color: "#d500f9",
      floorA: "#291836",
      floorB: "#22142d",
      border: "#ea80fc",
      slots: [
        { x: 675, y: 428, face: "up" },
        { x: 745, y: 428, face: "up" },
        { x: 710, y: 512, face: "up" },
      ],
    },
    lounge: {
      id: "lounge",
      title: "☕ CAFETERÍA & DESCANSO",
      subtitle: "Idle / Waiting Prompt",
      rect: { x: 808, y: 312, w: 198, h: 268 },
      door: { x: 907, y: 312 },
      color: "#ff5252",
      floorA: "#2b1d24",
      floorB: "#24181e",
      border: "#ff8a80",
      slots: [
        { x: 855, y: 405, face: "up" },
        { x: 952, y: 405, face: "up" },
        { x: 862, y: 495, face: "right" },
        { x: 912, y: 495, face: "up" },
        { x: 958, y: 495, face: "left" },
      ],
    },
  };

  // =========================================================================
  // ESTADO EN MEMORIA DEL CLIENTE
  // =========================================================================
  let lastEventId = 0;
  let filterMode = "all"; // "all" | "live"
  let selectedAgentId = null;
  let hoveredStationId = null;

  // Mapa de entidades visuales animadas: agentId -> SpriteEntity
  const entities = new Map();
  // Partículas flotantes (pasos, símbolos de código </>, libros, café, chispas)
  const particles = [];
  // Registro de eventos recientes para el panel lateral
  let recentLogs = [];

  // =========================================================================
  // CLASE ENTIDAD DE AGENTE (CON PATHFINDING Y COLA DE ACCIONES)
  // =========================================================================
  class AgentEntity {
    constructor(data) {
      this.id = data.id;
      this.syncMetadata(data);

      // Posición inicial en su estación actual
      const initialStation = STATIONS[data.station] ? data.station : "lounge";
      this.currentStation = initialStation;
      this.slotIndex = this.computeSlotIndex(initialStation);
      const slot = this.getSlotCoords(initialStation, this.slotIndex);

      // Si es un subagente recién invocado, aparece en el Portal de Orchestrator
      if (data.is_subagent) {
        this.x = 675;
        this.y = 115;
        this.spawnTimer = 1.4; // Efecto de teletransporte
      } else {
        this.x = slot.x;
        this.y = slot.y;
        this.spawnTimer = 0.6;
      }

      this.face = slot.face || "down";
      this.isWalking = false;
      this.walkFrame = 0;
      this.walkAnimTimer = 0;
      this.waypoints = [];

      // Cola de visitas a estaciones para que se vea cada caminata aunque ocurran rápido
      this.actionQueue = [];
      this.currentActionHoldTimer = 0;

      // Si nació en el portal y su estación destino es otra, caminar hacia allá
      if (data.is_subagent && initialStation !== "orchestrator_hub") {
        this.navigateToStation(initialStation);
      }
    }

    syncMetadata(data) {
      this.shortId = data.short_id || this.id.slice(0, 8);
      this.name = data.name || this.shortId;
      this.chatTitle = data.chat_title || "Sesión Antigravity";
      this.model = data.model || "Gemini";
      this.isSubagent = Boolean(data.is_subagent);
      this.subagentType = data.subagent_type || "main";
      this.parentId = data.parent_id || null;
      this.childrenIds = data.children_ids || [];
      this.palette = data.palette || {
        suit: "#00e5ff",
        hair: "#1a237e",
        accent: "#80d8ff",
        hat: "headphones",
      };
      this.stepCount = data.step_count || 0;
      this.isLive = Boolean(data.is_live);
      this.isSimulated = Boolean(data.is_simulated);
      this.idleSeconds = data.idle_seconds || 0;
      this.toolHistory = data.tool_History || [];

      // Si no tiene acción en cola ni está caminando, sincronizar badge/actividad
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
      // Evitar colisiones con otros agentes en la misma estación
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
      // Si el último elemento en la cola ya es la misma estación y badge, actualizarlo
      const last = this.actionQueue[this.actionQueue.length - 1];
      if (last && last.station === ev.station && last.badge === ev.badge) {
        return;
      }
      this.actionQueue.push({
        station: ev.station,
        activity: ev.activity || "coding",
        badge: ev.badge || ev.detail || "Trabajando...",
        detail: ev.detail || "",
        icon: ev.icon || "✨",
      });
      if (this.actionQueue.length > 6) {
        this.actionQueue.shift();
      }
    }

    navigateToStation(targetStationId) {
      if (!STATIONS[targetStationId]) return;
      const fromStation = STATIONS[this.currentStation] || STATIONS.lounge;
      const toStation = STATIONS[targetStationId];

      this.currentStation = targetStationId;
      this.slotIndex = this.computeSlotIndex(targetStationId);
      const targetSlot = this.getSlotCoords(targetStationId, this.slotIndex);

      const pts = [];
      // Si cambia de habitación, salir por la puerta al pasillo central y entrar por la puerta destino
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
      if (this.spawnTimer > 0) {
        this.spawnTimer = Math.max(0, this.spawnTimer - dt);
      }

      // 1. Si está caminando por waypoints
      if (this.waypoints.length > 0) {
        this.isWalking = true;
        const wp = this.waypoints[0];
        const dx = wp.x - this.x;
        const dy = wp.y - this.y;
        const dist = Math.hypot(dx, dy);
        // Velocidad de caminata (más rápida si hay varias acciones en cola)
        const speed = this.actionQueue.length > 1 ? 185 : 135;

        if (dist <= speed * dt) {
          this.x = wp.x;
          this.y = wp.y;
          if (wp.face) this.face = wp.face;
          this.waypoints.shift();
          if (this.waypoints.length === 0) {
            this.isWalking = false;
            this.walkFrame = 0;
            // Mantener al personaje trabajando en la estación al menos 2.6 segundos antes del siguiente movimiento
            this.currentActionHoldTimer = this.actionQueue.length > 1 ? 1.8 : 2.8;
          }
        } else {
          this.x += (dx / dist) * speed * dt;
          this.y += (dy / dist) * speed * dt;
          if (Math.abs(dx) > Math.abs(dy)) {
            this.face = dx > 0 ? "right" : "left";
          } else {
            this.face = dy > 0 ? "down" : "up";
          }

          // Animación de pasos
          this.walkAnimTimer += dt;
          if (this.walkAnimTimer >= 0.12) {
            this.walkAnimTimer = 0;
            this.walkFrame = (this.walkFrame + 1) % 4;
            // Polvo de pisadas pixel art
            particles.push({
              x: this.x + (Math.random() * 6 - 3),
              y: this.y + 12,
              vx: 0,
              vy: -8,
              life: 0.35,
              maxLife: 0.35,
              type: "dust",
              color: "rgba(200, 220, 255, 0.35)",
            });
          }
        }
        return;
      }

      this.isWalking = false;

      // 2. Si está en una estación ejecutando su actividad, emitir partículas temáticas
      if (this.currentActionHoldTimer > 0) {
        this.currentActionHoldTimer = Math.max(0, this.currentActionHoldTimer - dt);
      }

      // Emitir partículas visuales según la estación donde está trabajando
      if (Math.random() < dt * 2.2) {
        this.emitActivityParticle();
      }

      // 3. Si terminó el tiempo mínimo en la estación y hay más acciones en cola, avanzar a la siguiente
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
      const st = this.currentStation;
      let text = null;
      let color = "#00e5ff";

      if (st === "coding_desk") {
        const syms = ["</>", "{ }", "01", "fn()", "git", "py"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#00e676";
      } else if (st === "library") {
        const syms = ["📖", "📚", "pkg", "doc", "🔍"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#ffd54f";
      } else if (st === "server_lab") {
        const syms = ["⚡", "$>", "OK", "⚙️"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#ffab40";
      } else if (st === "strategy_board") {
        const syms = ["💭", "💡", "?", "✓"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#4fc3f7";
      } else if (st === "orchestrator_hub") {
        const syms = ["🎛️", "📡", "⚡"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#ffd54f";
      } else if (st === "web_station") {
        const syms = ["🌐", "HTTP", "200", "📡"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#00e5ff";
      } else if (st === "art_studio") {
        const syms = ["🎨", "✨", "CSS", "UI"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#ea80fc";
      } else if (st === "lounge") {
        const syms = ["☕", "~", "zZ"];
        text = syms[Math.floor(Math.random() * syms.length)];
        color = "#ff8a80";
      }

      if (text) {
        particles.push({
          x: this.x + (Math.random() * 18 - 9),
          y: this.y - 22,
          vx: (Math.random() - 0.5) * 10,
          vy: -18 - Math.random() * 10,
          life: 1.1,
          maxLife: 1.1,
          type: "text",
          text,
          color,
        });
      }
    }
  }

  // =========================================================================
  // DIBUJO DEL ESCENARIO PIXEL ART (SALAS, MUEBLES, PASILLO Y DETALLES)
  // =========================================================================
  function drawPixelRect(x, y, w, h, fill, stroke = null, strokeWidth = 2) {
    ctx.fillStyle = fill;
    ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = strokeWidth;
      ctx.strokeRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
    }
  }

  function drawWorld(nowSec) {
    // Fondo general del complejo
    ctx.fillStyle = "#0b0e17";
    ctx.fillRect(0, 0, W, H);

    // Pasillo Central Horizontal
    drawPixelRect(18, 258, W - 36, 52, "#151c2c", "#26324d", 2);
    // Líneas guía luminosas en el pasillo
    ctx.strokeStyle = "rgba(0, 229, 255, 0.18)";
    ctx.setLineDash([8, 8]);
    ctx.beginPath();
    ctx.moveTo(35, HALLWAY_Y);
    ctx.lineTo(W - 35, HALLWAY_Y);
    ctx.stroke();
    ctx.setLineDash([]);

    // Etiqueta del pasillo
    ctx.fillStyle = "rgba(139, 155, 180, 0.35)";
    ctx.font = "bold 10px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillText("◄═══ CORREDOR CENTRAL ANTIGRAVITY HQ ═══►", W / 2, HALLWAY_Y + 4);

    // Dibujar cada una de las 8 estaciones
    for (const st of Object.values(STATIONS)) {
      drawStationBase(st, nowSec);
    }

    // Dibujar el mobiliario Pixel Art detallado de cada sala
    drawLibraryFurniture(STATIONS.library, nowSec);
    drawStrategyFurniture(STATIONS.strategy_board, nowSec);
    drawOrchestratorFurniture(STATIONS.orchestrator_hub, nowSec);
    drawWebStationFurniture(STATIONS.web_station, nowSec);
    drawCodingDesksFurniture(STATIONS.coding_desk, nowSec);
    drawServerLabFurniture(STATIONS.server_lab, nowSec);
    drawArtStudioFurniture(STATIONS.art_studio, nowSec);
    drawLoungeFurniture(STATIONS.lounge, nowSec);
  }

  function drawStationBase(st, nowSec) {
    const { x, y, w, h } = st.rect;
    const isHovered = hoveredStationId === st.id;

    // Piso con patrón de baldosas pixeladas 16x16
    const tile = 16;
    for (let ty = y; ty < y + h; ty += tile) {
      for (let tx = x; tx < x + w; tx += tile) {
        const even = ((Math.floor((tx - x) / tile) + Math.floor((ty - y) / tile)) % 2) === 0;
        ctx.fillStyle = even ? st.floorA : st.floorB;
        ctx.fillRect(tx, ty, Math.min(tile, x + w - tx), Math.min(tile, y + h - ty));
      }
    }

    // Borde de la sala
    ctx.strokeStyle = isHovered ? "#ffffff" : st.border;
    ctx.lineWidth = isHovered ? 3 : 2;
    ctx.strokeRect(x, y, w, h);

    // Abertura de la puerta hacia el pasillo
    ctx.fillStyle = "#151c2c";
    if (st.door.y <= 260) {
      ctx.fillRect(st.door.x - 18, y + h - 3, 36, 6);
    } else {
      ctx.fillRect(st.door.x - 18, y - 3, 36, 6);
    }

    // Cartel superior de la sala
    drawPixelRect(x + 6, y + 6, w - 12, 24, "rgba(11, 14, 23, 0.85)", st.border, 1);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText(st.title, x + 12, y + 22);
  }

  // 1. MOBILIARIO BIBLIOTECA (Estanterías con libros de colores, mesas de lectura)
  function drawLibraryFurniture(st, nowSec) {
    const { x, y } = st.rect;
    const bookColors = ["#ff5252", "#448aff", "#00e676", "#ffd740", "#e040fb", "#ff6e40"];

    // 3 Grandes estanterías de madera en la pared norte
    for (let s = 0; s < 3; s++) {
      const sx = x + 18 + s * 74;
      const sy = y + 40;
      drawPixelRect(sx, sy, 62, 52, "#4e342e", "#8d6e63", 2);

      // 3 niveles de libros por estantería
      for (let row = 0; row < 3; row++) {
        const ry = sy + 6 + row * 15;
        drawPixelRect(sx + 4, ry + 10, 54, 3, "#3e2723");
        for (let b = 0; b < 8; b++) {
          ctx.fillStyle = bookColors[(s * 7 + row * 3 + b) % bookColors.length];
          ctx.fillRect(sx + 6 + b * 6, ry, 5, 10);
        }
      }
    }

    // Mesas de lectura inferiores con libros abiertos
    for (let t = 0; t < 2; t++) {
      const tx = x + 38 + t * 96;
      const ty = y + 155;
      drawPixelRect(tx, ty, 70, 32, "#6d4c41", "#a1887f", 2);
      // Libro abierto sobre la mesa
      drawPixelRect(tx + 16, ty + 8, 16, 12, "#fff8e1", "#bcaaa4", 1);
      drawPixelRect(tx + 32, ty + 8, 16, 12, "#fff8e1", "#bcaaa4", 1);
      // Lupa brillante
      ctx.fillStyle = "#00e5ff";
      ctx.fillRect(tx + 54, ty + 10, 8, 8);
    }
  }

  // 2. MOBILIARIO PIZARRA DE ESTRATEGIA (Pizarra con diagramas, post-its, mesa táctica)
  function drawStrategyFurniture(st, nowSec) {
    const { x, y } = st.rect;
    // Gran pizarra blanca/cristal
    const bx = x + 22;
    const by = y + 40;
    drawPixelRect(bx, by, 180, 54, "#0d1b2a", "#4fc3f7", 2);

    // Diagrama de flujo pixelado en la pizarra
    drawPixelRect(bx + 14, by + 12, 28, 14, "#00e5ff");
    drawPixelRect(bx + 62, by + 12, 28, 14, "#ffb300");
    drawPixelRect(bx + 110, by + 12, 28, 14, "#00e676");
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(bx + 42, by + 19);
    ctx.lineTo(bx + 62, by + 19);
    ctx.moveTo(bx + 90, by + 19);
    ctx.lineTo(bx + 110, by + 19);
    ctx.stroke();

    // Notas adhesivas (Post-its)
    drawPixelRect(bx + 150, by + 10, 10, 10, "#ffeb3b");
    drawPixelRect(bx + 163, by + 10, 10, 10, "#ff4081");
    drawPixelRect(bx + 150, by + 24, 10, 10, "#00e676");

    // Mesa de planificación inferior
    drawPixelRect(x + 48, y + 155, 130, 28, "#1e2f48", "#4fc3f7", 1);
  }

  // 3. MOBILIARIO NÚCLEO ORCHESTRATOR (Mesa holográfica + Portal de Subagentes)
  function drawOrchestratorFurniture(st, nowSec) {
    const { x, y } = st.rect;
    const cx = x + 82;
    const cy = y + 105;

    // Consola Holográfica Central
    drawPixelRect(cx - 42, cy - 26, 84, 52, "#1c160c", "#ffb300", 2);
    const pulse = 18 + Math.sin(nowSec * 4) * 4;
    ctx.strokeStyle = "rgba(255, 213, 79, 0.85)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, pulse, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "#ffd54f";
    ctx.font = "bold 9px Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillText("ORCH-CORE", cx, cy + 3);

    // PORTAL DE TELETRANSPORTE DE SUBAGENTES (Derecha de la sala)
    const px = x + 178;
    const py = y + 85;
    drawPixelRect(px - 26, py - 26, 52, 52, "#140f24", "#d500f9", 2);
    const portalRadius = 14 + Math.cos(nowSec * 5) * 3;
    ctx.strokeStyle = "#00e5ff";
    ctx.beginPath();
    ctx.arc(px, py, portalRadius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "#ea80fc";
    ctx.font = "bold 8px Consolas, monospace";
    ctx.fillText("SPAWN PAD", px, py + 36);
  }

  // 4. MOBILIARIO CABINA WEB & RADAR
  function drawWebStationFurniture(st, nowSec) {
    const { x, y } = st.rect;
    // Escritorio curvo con 3 monitores
    for (let m = 0; m < 3; m++) {
      const mx = x + 24 + m * 68;
      const my = y + 48;
      drawPixelRect(mx, my, 54, 34, "#0a1929", "#00e5ff", 2);
      // Líneas de radar/web en pantalla
      ctx.fillStyle = "rgba(0, 229, 255, 0.35)";
      const barW = 14 + ((Math.floor(nowSec * 6) + m * 5) % 30);
      ctx.fillRect(mx + 6, my + 8, barW, 4);
      ctx.fillRect(mx + 6, my + 16, 36, 4);
      ctx.fillRect(mx + 6, my + 24, 24, 4);
    }

    // Globo terráqueo holográfico inferior
    const gx = x + 120;
    const gy = y + 165;
    drawPixelRect(gx - 35, gy - 20, 70, 40, "#0b1d28", "#00b0ff", 1);
    ctx.strokeStyle = "#00e5ff";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(gx, gy, 14, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(gx - 14, gy);
    ctx.lineTo(gx + 14, gy);
    ctx.moveTo(gx, gy - 14);
    ctx.lineTo(gx, gy + 14);
    ctx.stroke();
  }

  // 5. MOBILIARIO SALA DE COMPUTADORES (6 Estaciones de programación con doble monitor)
  function drawCodingDesksFurniture(st, nowSec) {
    // Determinar qué escritorios tienen un agente sentado programando ahora mismo
    const activeDesks = new Set();
    for (const ent of entities.values()) {
      if (!ent.isWalking && ent.currentStation === "coding_desk") {
        activeDesks.add(ent.slotIndex);
      }
    }

    st.slots.forEach((slot, idx) => {
      const dx = slot.x - 42;
      const dy = slot.y - 46;
      const isOccupied = activeDesks.has(idx);

      // Silla ergonómica donde se sienta el agente
      drawPixelRect(slot.x - 10, slot.y + 4, 20, 14, "#263238", "#455a64", 1);

      // Mesa del computador
      drawPixelRect(dx, dy, 84, 34, "#2c384e", isOccupied ? "#00e676" : "#4a5d80", 2);

      // Monitor Izquierdo y Monitor Derecho
      for (let m = 0; m < 2; m++) {
        const mx = dx + 8 + m * 36;
        const my = dy + 4;
        drawPixelRect(mx, my, 28, 18, isOccupied ? "#061f14" : "#0f141d", isOccupied ? "#00e676" : "#37474f", 1);

        if (isOccupied) {
          // Código verde/cyan desplazándose en vivo cuando el agente programa
          const scroll = Math.floor(nowSec * 8 + idx + m) % 3;
          ctx.fillStyle = m === 0 ? "#00e676" : "#00e5ff";
          ctx.fillRect(mx + 3, my + 4 + scroll, 16, 2);
          ctx.fillRect(mx + 3, my + 9, 20, 2);
          ctx.fillRect(mx + 3, my + 14 - scroll, 12, 2);
        }
      }

      // Teclado mecánico y gabinete RGB
      drawPixelRect(dx + 24, dy + 25, 28, 6, "#111722", "#546e7a", 1);
      drawPixelRect(dx + 70, dy + 6, 10, 22, "#111722", isOccupied ? "#00e5ff" : "#37474f", 1);
    });
  }

  // 6. MOBILIARIO LABORATORIO DE SERVIDORES & TERMINAL
  function drawServerLabFurniture(st, nowSec) {
    const { x, y } = st.rect;
    // 4 Racks de servidores con LEDs parpadeantes
    for (let r = 0; r < 4; r++) {
      const rx = x + 16 + r * 50;
      const ry = y + 42;
      drawPixelRect(rx, ry, 42, 62, "#12151c", "#546e7a", 2);

      for (let u = 0; u < 4; u++) {
        const uy = ry + 6 + u * 14;
        drawPixelRect(rx + 4, uy, 34, 10, "#1e2430");
        // LEDs parpadeantes
        const blink = ((Math.floor(nowSec * 6) + r * 3 + u) % 3) === 0;
        ctx.fillStyle = blink ? "#00e676" : "#ff9100";
        ctx.fillRect(rx + 7, uy + 3, 4, 4);
        ctx.fillStyle = "#00e5ff";
        ctx.fillRect(rx + 14, uy + 3, 4, 4);
      }
    }

    // Consola Terminal Central
    drawPixelRect(x + 35, y + 168, 154, 34, "#161b22", "#ff9100", 2);
    ctx.fillStyle = "#00e676";
    ctx.font = "bold 10px Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText("$ antigravity --exec", x + 46, y + 189);
  }

  // 7. MOBILIARIO ESTUDIO CREATIVO (Caballete de arte y tableta digital)
  function drawArtStudioFurniture(st, nowSec) {
    const { x, y } = st.rect;
    // Caballete con lienzo pixel art
    drawPixelRect(x + 24, y + 48, 52, 42, "#fff8e1", "#ffb300", 2);
    ctx.fillStyle = "#ff4081";
    ctx.fillRect(x + 32, y + 56, 16, 14);
    ctx.fillStyle = "#00e5ff";
    ctx.fillRect(x + 48, y + 62, 18, 18);

    // Mesa de diseño UI
    drawPixelRect(x + 92, y + 52, 58, 38, "#311b92", "#ea80fc", 2);
    drawPixelRect(x + 102, y + 60, 38, 22, "#1a0933", "#00e5ff", 1);
  }

  // 8. MOBILIARIO CAFETERÍA & ZONA DE DESCANSO
  function drawLoungeFurniture(st, nowSec) {
    const { x, y } = st.rect;
    // Barra de Café y Máquina Espresso
    drawPixelRect(x + 18, y + 44, 162, 34, "#4e342e", "#a1887f", 2);
    // Máquina de café
    drawPixelRect(x + 32, y + 48, 28, 24, "#b71c1c", "#ffcdd2", 1);
    // Dispensador de agua
    drawPixelRect(x + 140, y + 46, 22, 26, "#e1f5fe", "#29b6f6", 1);

    // Sofá rojo Pixel Art en la parte inferior
    drawPixelRect(x + 42, y + 150, 114, 42, "#880e4f", "#f48fb1", 2);
    drawPixelRect(x + 50, y + 158, 98, 26, "#ad1457");
  }

  // =========================================================================
  // ENLACES HOLOGRÁFICOS ENTRE ORCHESTRATOR Y SUBAGENTES
  // =========================================================================
  function drawOrchestratorLinks(nowSec) {
    for (const ent of entities.values()) {
      if (filterMode === "live" && !ent.isLive && !ent.isSimulated) continue;
      if (ent.parentId && entities.has(ent.parentId)) {
        const parent = entities.get(ent.parentId);
        ctx.save();
        ctx.strokeStyle = "rgba(255, 213, 79, 0.55)";
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 6]);
        ctx.lineDashOffset = -nowSec * 28;
        ctx.beginPath();
        ctx.moveTo(parent.x, parent.y - 8);
        ctx.lineTo(ent.x, ent.y - 8);
        ctx.stroke();

        // Pulso de datos viajando del Orchestrator al Subagente
        const t = (nowSec * 0.9) % 1;
        const px = parent.x + (ent.x - parent.x) * t;
        const py = (parent.y - 8) + ((ent.y - 8) - (parent.y - 8)) * t;
        ctx.fillStyle = "#00e5ff";
        ctx.fillRect(px - 3, py - 3, 6, 6);
        ctx.restore();
      }
    }
  }

  // =========================================================================
  // RENDERIZADO DE PERSONAJES PIXEL ART (SPRITE 16-BIT PROCEDURAL)
  // =========================================================================
  function drawAgentSprite(ent, nowSec) {
    const x = Math.round(ent.x);
    const y = Math.round(ent.y);
    const isSelected = ent.id === selectedAgentId;

    // Rebote vertical al caminar o respirar
    const walkBob = ent.isWalking
      ? (ent.walkFrame % 2 === 1 ? -3 : 0)
      : Math.round(Math.sin(nowSec * 4 + x) * 1);

    ctx.save();

    // Efecto de teletransporte si acaba de aparecer (Spawn Pad)
    if (ent.spawnTimer > 0) {
      ctx.strokeStyle = "#00e5ff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y - 6, 22 * ent.spawnTimer, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Anillo de selección debajo del personaje
    if (isSelected) {
      ctx.strokeStyle = "#00e5ff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(x, y + 12, 16, 7, 0, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Sombra en el suelo
    ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
    ctx.fillRect(x - 10, y + 10, 20, 5);

    const py = y + walkBob;

    // Piernas animadas (4 frames de caminata)
    const legOffsetL = ent.isWalking ? (ent.walkFrame === 1 ? -3 : ent.walkFrame === 3 ? 2 : 0) : 0;
    const legOffsetR = ent.isWalking ? (ent.walkFrame === 3 ? -3 : ent.walkFrame === 1 ? 2 : 0) : 0;
    ctx.fillStyle = "#1e272e";
    ctx.fillRect(x - 7, py + 3 + legOffsetL, 5, 8);
    ctx.fillRect(x + 2, py + 3 + legOffsetR, 5, 8);

    // Torso / Traje del Agente
    drawPixelRect(x - 9, py - 9, 18, 13, ent.palette.suit, "#0b0e17", 1);
    // Detalle de pecho / insignia
    ctx.fillStyle = ent.palette.accent || "#ffffff";
    ctx.fillRect(x - 3, py - 6, 6, 4);

    // Brazos (se mueven al caminar o al teclear en el computador)
    const isTyping = !ent.isWalking && (ent.currentStation === "coding_desk" || ent.currentStation === "server_lab");
    const armJitter = isTyping ? Math.round(Math.sin(nowSec * 26) * 2) : 0;
    ctx.fillStyle = ent.palette.suit;
    ctx.fillRect(x - 13, py - 8 + armJitter, 4, 10);
    ctx.fillRect(x + 9,  py - 8 - armJitter, 4, 10);

    // Cabeza Pixel Art
    drawPixelRect(x - 8, py - 23, 16, 14, "#ffccaa", "#0b0e17", 1);

    // Cabello
    ctx.fillStyle = ent.palette.hair || "#263238";
    ctx.fillRect(x - 9, py - 25, 18, 5);
    if (ent.face === "left") ctx.fillRect(x + 5, py - 23, 4, 9);
    if (ent.face === "right") ctx.fillRect(x - 9, py - 23, 4, 9);

    // Ojos según dirección en la que mira
    ctx.fillStyle = "#111111";
    if (ent.face === "left") {
      ctx.fillRect(x - 6, py - 17, 3, 3);
      ctx.fillRect(x - 1, py - 17, 3, 3);
    } else if (ent.face === "right") {
      ctx.fillRect(x - 2, py - 17, 3, 3);
      ctx.fillRect(x + 3, py - 17, 3, 3);
    } else if (ent.face === "down") {
      ctx.fillRect(x - 5, py - 17, 3, 3);
      ctx.fillRect(x + 2, py - 17, 3, 3);
    }

    // Accesorio / Casco / Visor según rol o modelo
    if (ent.isSubagent) {
      // Antena luminosa de Subagente
      ctx.fillStyle = "#ffd54f";
      ctx.fillRect(x - 1, py - 30, 2, 5);
      ctx.fillStyle = "#00e5ff";
      ctx.fillRect(x - 2, py - 32, 4, 3);
    } else {
      // Visor Cyber o Audífonos de Agente Principal
      ctx.fillStyle = ent.palette.accent || "#00e5ff";
      ctx.fillRect(x - 10, py - 19, 2, 6);
      ctx.fillRect(x + 8,  py - 19, 2, 6);
    }

    // Objeto en las manos según la estación actual
    if (!ent.isWalking) {
      if (ent.currentStation === "library") {
        // Sosteniendo un libro abierto en la biblioteca
        drawPixelRect(x - 7, py - 5, 14, 9, "#fff8e1", "#d49a6a", 1);
        ctx.fillStyle = "#e65100";
        ctx.fillRect(x - 5, py - 4, 5, 7);
      } else if (ent.currentStation === "lounge") {
        // Sosteniendo una taza de café caliente
        drawPixelRect(x + 6, py - 6, 7, 8, "#ffffff", "#ff5252", 1);
      }
    }

    // Etiqueta con el nombre del agente y modelo debajo de los pies
    const nameTag = ent.isSubagent ? `⚡ ${ent.name}` : ent.name;
    ctx.font = "bold 10px Consolas, monospace";
    const nameW = ctx.measureText(nameTag).width + 10;
    drawPixelRect(x - nameW / 2, y + 15, nameW, 15, "rgba(11, 14, 23, 0.88)", ent.palette.suit, 1);
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.fillText(nameTag, x, y + 26);

    // Globo de diálogo / estado sobre la cabeza
    const bubbleText = ent.isWalking
      ? `🚶 → ${STATIONS[ent.currentStation]?.title.split(" ")[1] || ent.currentStation}`
      : ent.badge;
    if (bubbleText) {
      ctx.font = "bold 10px 'Segoe UI', Consolas, sans-serif";
      const bw = Math.min(185, ctx.measureText(bubbleText).width + 14);
      const bx = Math.max(12, Math.min(W - bw - 12, x - bw / 2));
      const by = py - 46;

      drawPixelRect(bx, by, bw, 17, "rgba(19, 24, 38, 0.94)", isSelected ? "#00e5ff" : "#4a5d80", 1);
      ctx.fillStyle = "#edf2ff";
      ctx.textAlign = "center";
      ctx.fillText(bubbleText.slice(0, 26), bx + bw / 2, by + 12);
    }

    ctx.restore();
  }

  // =========================================================================
  // SISTEMA DE PARTÍCULAS
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
        ctx.fillRect(Math.round(p.x), Math.round(p.y), 4, 4);
      } else {
        ctx.fillStyle = p.color;
        ctx.font = "bold 11px Consolas, monospace";
        ctx.textAlign = "center";
        ctx.fillText(p.text, Math.round(p.x), Math.round(p.y));
      }
      ctx.restore();
    }
  }

  // =========================================================================
  // BUCLE PRINCIPAL DE ANIMACIÓN (60 FPS)
  // =========================================================================
  let lastFrameTime = performance.now();

  function frameLoop(nowMs) {
    const dt = Math.min(0.1, (nowMs - lastFrameTime) / 1000);
    lastFrameTime = nowMs;
    const nowSec = nowMs / 1000;

    drawWorld(nowSec);
    drawOrchestratorLinks(nowSec);

    // Ordenar entidades por coordenada Y (depth sorting)
    const visibleEntities = Array.from(entities.values()).filter(
      (e) => filterMode === "all" || e.isLive || e.isSimulated
    );
    visibleEntities.sort((a, b) => a.y - b.y);

    for (const ent of visibleEntities) {
      ent.update(dt);
      drawAgentSprite(ent, nowSec);
    }

    updateAndDrawParticles(dt);
    requestAnimationFrame(frameLoop);
  }

  // =========================================================================
  // SINCRONIZACIÓN CON EL BACKEND (ANTIGRAVITY BRAIN WATCHER)
  // =========================================================================
  async function pollBackendState() {
    try {
      const res = await fetch(`/api/state?since=${lastEventId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const snap = await res.json();
      applySnapshot(snap);
    } catch (err) {
      const pill = document.getElementById("connPill");
      const txt = document.getElementById("connText");
      if (pill && txt) {
        txt.textContent = "RECONECTANDO...";
        pill.style.borderColor = "#ff1744";
      }
    }
  }

  function applySnapshot(snap) {
    const txt = document.getElementById("connText");
    if (txt) txt.textContent = "CONECTADO A ANTIGRAVITY BRAIN";

    const currentIds = new Set();
    for (const agData of snap.agents || []) {
      currentIds.add(agData.id);
      if (!entities.has(agData.id)) {
        entities.set(agData.id, new AgentEntity(agData));
      } else {
        entities.get(agData.id).syncMetadata(agData);
      }
    }

    // Eliminar agentes simulados si fueron limpiados
    for (const existingId of Array.from(entities.keys())) {
      if (!currentIds.has(existingId)) {
        entities.delete(existingId);
        if (selectedAgentId === existingId) selectedAgentId = null;
      }
    }

    // Procesar eventos nuevos en la cola de movimiento de cada agente
    if (Array.isArray(snap.events) && snap.events.length > 0) {
      for (const ev of snap.events) {
        if (ev.id > lastEventId) lastEventId = ev.id;
        const ent = entities.get(ev.agent_id);
        if (ent) {
          ent.enqueueAction(ev);
        }
      }
    } else if (snap.latest_event_id > lastEventId) {
      lastEventId = snap.latest_event_id;
    }

    if (!selectedAgentId && entities.size > 0) {
      selectedAgentId = entities.keys().next().value;
    }

    recentLogs = snap.recent_log || [];
    renderSidebarUI();
  }

  // =========================================================================
  // ACTUALIZACIÓN DE LA INTERFAZ LATERAL (INSPECTOR, LISTA Y TELEMETRÍA)
  // =========================================================================
  function renderSidebarUI() {
    const allList = Array.from(entities.values());
    const visibleList = allList.filter((e) => filterMode === "all" || e.isLive || e.isSimulated);

    const mainChats = visibleList.filter((e) => !e.isSubagent).length;
    const subAgents = visibleList.filter((e) => e.isSubagent).length;

    document.getElementById("statChats").textContent = String(mainChats);
    document.getElementById("statSubs").textContent = String(subAgents);
    document.getElementById("agentCountBadge").textContent = String(visibleList.length);

    // 1. Renderizar lista de agentes (agrupando subagentes debajo de su Orchestrator padre)
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

      const rolePrefix = ent.isSubagent ? "↳ [SUB] " : "💬 ";
      const statusBadge = ent.isWalking
        ? `🚶 Caminando a ${STATIONS[ent.currentStation]?.title || ent.currentStation}`
        : ent.badge;

      card.innerHTML = `
        <div class="agent-row-top">
          <div class="agent-name">${rolePrefix}${escapeHtml(ent.name)}</div>
          <span class="agent-model-pill">${escapeHtml(ent.model)}</span>
        </div>
        <div class="agent-badge-row">${escapeHtml(statusBadge)}</div>
        <div class="agent-prompt-row">${escapeHtml(ent.chatTitle)}</div>
      `;
      agentsContainer.appendChild(card);
    }

    // 2. Renderizar Inspector del Agente Seleccionado
    const inspBody = document.getElementById("inspectorBody");
    const inspBadge = document.getElementById("inspTypeBadge");
    const sel = entities.get(selectedAgentId);

    if (!sel) {
      inspBadge.textContent = "NINGUNO";
      inspBody.innerHTML = `<p class="empty-hint">Haz clic sobre un personaje en el mapa para ver sus detalles.</p>`;
    } else {
      inspBadge.textContent = sel.isSubagent ? `SUBAGENTE (${sel.subagentType.toUpperCase()})` : "AGENTE PRINCIPAL";
      const stTitle = STATIONS[sel.currentStation]?.title || sel.currentStation;
      const parentInfo = sel.parentId && entities.has(sel.parentId)
        ? `<div><strong>Padre Orchestrator:</strong> ${escapeHtml(entities.get(sel.parentId).name)}</div>`
        : "";
      const childrenInfo = sel.childrenIds && sel.childrenIds.length > 0
        ? `<div><strong>Subagentes a cargo:</strong> ${sel.childrenIds.length} activos</div>`
        : "";

      inspBody.innerHTML = `
        <div class="insp-title">
          <span style="color:${sel.palette.suit}">●</span>
          ${escapeHtml(sel.name)}
        </div>
        <div class="insp-model">Modelo: ${escapeHtml(sel.model)}</div>
        <div class="insp-detail">
          <div><strong>Ubicación:</strong> ${escapeHtml(stTitle)}</div>
          <div><strong>Estado:</strong> ${escapeHtml(sel.badge)}</div>
          <div style="margin-top:3px;color:#8b9bb4">${escapeHtml(sel.detail || sel.chatTitle)}</div>
        </div>
        <div class="insp-meta">
          <span>Pasos: <strong>${sel.stepCount}</strong></span>
          <span>ID: <strong>${escapeHtml(sel.shortId)}</strong></span>
          ${parentInfo}
          ${childrenInfo}
        </div>
      `;
    }

    // 3. Renderizar Feed de Telemetría en Tiempo Real
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
  // EVENTOS DE INTERACCIÓN (CLIC EN EL MAPA, BOTONES DE ZONA Y SIMULACIÓN)
  // =========================================================================
  function getCanvasMouseCoords(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = W / rect.width;
    const scaleY = H / rect.height;
    return {
      x: (evt.clientX - rect.left) * scaleX,
      y: (evt.clientY - rect.top) * scaleY,
    };
  }

  canvas.addEventListener("mousemove", (evt) => {
    const pt = getCanvasMouseCoords(evt);
    hoveredStationId = null;
    for (const st of Object.values(STATIONS)) {
      const r = st.rect;
      if (pt.x >= r.x && pt.x <= r.x + r.w && pt.y >= r.y && pt.y <= r.y + r.h) {
        hoveredStationId = st.id;
        break;
      }
    }
  });

  canvas.addEventListener("click", async (evt) => {
    const pt = getCanvasMouseCoords(evt);

    // 1. Verificar si hizo clic sobre un personaje
    for (const ent of entities.values()) {
      if (Math.hypot(pt.x - ent.x, pt.y - (ent.y - 6)) <= 22) {
        selectedAgentId = ent.id;
        renderSidebarUI();
        return;
      }
    }

    // 2. Si hizo clic sobre una sala/estación y hay un agente seleccionado, enviar al agente caminando a esa sala
    for (const st of Object.values(STATIONS)) {
      const r = st.rect;
      if (pt.x >= r.x && pt.x <= r.x + r.w && pt.y >= r.y && pt.y <= r.y + r.h) {
        if (selectedAgentId) {
          await commandAgentToStation(selectedAgentId, st.id);
        }
        return;
      }
    }
  });

  async function commandAgentToStation(agentId, stationId) {
    try {
      await fetch("/api/command_agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_id: agentId, station: stationId }),
      });
      await pollBackendState();
    } catch (e) {
      console.error(e);
    }
  }

  async function triggerSimAction(action) {
    try {
      const res = await fetch("/api/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (data.agent_id) selectedAgentId = data.agent_id;
      if (data.orchestrator_id) selectedAgentId = data.orchestrator_id;
      await pollBackendState();
    } catch (e) {
      console.error(e);
    }
  }

  // Conectar botones de la interfaz
  document.getElementById("btnSpawnChat").onclick = () => triggerSimAction("spawn_chat");
  document.getElementById("btnSpawnOrch").onclick = () => triggerSimAction("spawn_orchestrator");
  document.getElementById("btnClearSim").onclick = () => triggerSimAction("clear_sim");

  document.querySelectorAll("[data-sim]").forEach((btn) => {
    btn.onclick = () => triggerSimAction(btn.getAttribute("data-sim"));
  });

  document.querySelectorAll("[data-station]").forEach((btn) => {
    btn.onclick = () => {
      const st = btn.getAttribute("data-station");
      if (selectedAgentId) {
        commandAgentToStation(selectedAgentId, st);
      }
    };
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

  // Iniciar polling y bucle de renderizado 60 FPS
  pollBackendState();
  setInterval(pollBackendState, 900);
  requestAnimationFrame(frameLoop);
})();
