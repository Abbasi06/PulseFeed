import { useEffect, useRef } from "react";

// ─── Config ───────────────────────────────────────────────────────────────────
const NODE_COUNT      = 52;
const CONNECT_RADIUS  = 0.26;  // fraction of min(W,H)
const PULSE_SPEED     = 2.8;   // px per frame
const PULSE_EVERY     = 220;   // frames between new pulses
const REPEL_RADIUS    = 130;   // px — mouse pushes nodes away gently
const FLASH_DURATION  = 110;   // frames for activation bloom to decay

const NODE_COLORS  = ["#9333EA", "#7C3AED", "#B7397A", "#D946EF", "#0EA5E9", "#6366F1"];
const PULSE_COLORS = ["#D946EF", "#9333EA", "#7C3AED", "#38BDF8", "#C084FC", "#E879F9"];

// ─── Helpers ──────────────────────────────────────────────────────────────────
function hexToRgba(hex, a) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function buildNodes(W, H) {
  return Array.from({ length: NODE_COUNT }, (_, i) => ({
    x:           Math.random() * W,
    y:           Math.random() * H,
    vx:          (Math.random() - 0.5) * 0.18,
    vy:          (Math.random() - 0.5) * 0.18,
    r:           Math.random() * 2.2 + 1.4,
    phase:       (i / NODE_COUNT) * Math.PI * 2,
    beatRate:    Math.random() * 0.018 + 0.012,
    color:       NODE_COLORS[i % NODE_COLORS.length],
    activatedAt: -9999,
  }));
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function WarpBackground({ bright = false }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let W, H, nodes, rafId;
    let pulses = [];
    let time   = 0;
    const mouse       = { x: 0.5, y: 0.5 };
    const smoothMouse = { x: 0.5, y: 0.5 };

    function resize() {
      W = canvas.width  = window.innerWidth;
      H = canvas.height = window.innerHeight;
      nodes  = buildNodes(W, H);
      pulses = [];
    }

    function onMouseMove(e) { mouse.x = e.clientX / W; mouse.y = e.clientY / H; }
    function onTouchMove(e) {
      if (!e.touches.length) return;
      mouse.x = e.touches[0].clientX / W;
      mouse.y = e.touches[0].clientY / H;
    }

    // ── Build edges within connection radius ─────────────────────────────────
    function buildEdges() {
      const maxD = CONNECT_RADIUS * Math.min(W, H);
      const edges = [];
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const d  = Math.sqrt(dx * dx + dy * dy);
          if (d < maxD) edges.push({ i, j, d, alpha: 1 - d / maxD });
        }
      }
      return edges;
    }

    function spawnPulse(edges) {
      if (!edges.length) return;
      const e = edges[Math.floor(Math.random() * edges.length)];
      pulses.push({
        i: e.i, j: e.j, d: e.d,
        progress: 0,
        color: PULSE_COLORS[Math.floor(Math.random() * PULSE_COLORS.length)],
        reverse: Math.random() > 0.5,
      });
    }

    // ── Draw one frame ────────────────────────────────────────────────────────
    function frame() {
      time++;

      // Smooth mouse
      smoothMouse.x += (mouse.x - smoothMouse.x) * 0.04;
      smoothMouse.y += (mouse.y - smoothMouse.y) * 0.04;
      const mx = smoothMouse.x * W;
      const my = smoothMouse.y * H;

      // Move nodes + mouse repulsion + wrap
      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;

        const dx = n.x - mx;
        const dy = n.y - my;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < REPEL_RADIUS && d > 0) {
          const force = (REPEL_RADIUS - d) / REPEL_RADIUS * 0.4;
          n.x += (dx / d) * force;
          n.y += (dy / d) * force;
        }

        if (n.x < -60)  n.x = W + 60;
        if (n.x > W+60) n.x = -60;
        if (n.y < -60)  n.y = H + 60;
        if (n.y > H+60) n.y = -60;
      }

      const edges = buildEdges();

      // Spawn + advance pulses; trigger activation on arrival
      if (time % PULSE_EVERY === 0) spawnPulse(edges);
      const nextPulses = [];
      for (const p of pulses) {
        const np = { ...p, progress: p.progress + PULSE_SPEED / p.d };
        if (np.progress >= 1) {
          const destIdx = np.reverse ? np.i : np.j;
          nodes[destIdx].activatedAt = time;
        } else {
          nextPulses.push(np);
        }
      }
      pulses = nextPulses;

      // ── Background ───────────────────────────────────────────────────────
      ctx.fillStyle = "#06080F";
      ctx.fillRect(0, 0, W, H);

      // ── Edges ────────────────────────────────────────────────────────────
      for (const e of edges) {
        ctx.beginPath();
        ctx.moveTo(nodes[e.i].x, nodes[e.i].y);
        ctx.lineTo(nodes[e.j].x, nodes[e.j].y);
        ctx.strokeStyle = `rgba(139,92,246,${e.alpha * 0.22})`;
        ctx.lineWidth   = e.alpha * 1.4;
        ctx.stroke();
      }

      // ── Pulse particles ───────────────────────────────────────────────────
      for (const p of pulses) {
        const from = p.reverse ? nodes[p.j] : nodes[p.i];
        const to   = p.reverse ? nodes[p.i] : nodes[p.j];
        const px   = from.x + (to.x - from.x) * p.progress;
        const py   = from.y + (to.y - from.y) * p.progress;

        const glow = ctx.createRadialGradient(px, py, 0, px, py, 10);
        glow.addColorStop(0,   hexToRgba(p.color, 0.85));
        glow.addColorStop(0.5, hexToRgba(p.color, 0.25));
        glow.addColorStop(1,   hexToRgba(p.color, 0));
        ctx.beginPath();
        ctx.arc(px, py, 10, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(px, py, 1.8, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,0.95)";
        ctx.fill();
      }

      // ── Nodes ─────────────────────────────────────────────────────────────
      for (const n of nodes) {
        const beat  = 0.5 + 0.5 * Math.sin(time * n.beatRate + n.phase);

        const age   = time - n.activatedAt;
        const flash = age < FLASH_DURATION ? 1 - age / FLASH_DURATION : 0;

        const r     = n.r + beat * 1.8 + flash * n.r * 2.5;
        const alpha = 0.78 + beat * 0.18 + flash * 0.4;

        // shockwave ring
        if (flash > 0) {
          const ringR = n.r * (1 + (1 - flash) * 12);
          ctx.beginPath();
          ctx.arc(n.x, n.y, ringR, 0, Math.PI * 2);
          ctx.strokeStyle = hexToRgba(n.color, flash * 0.6);
          ctx.lineWidth   = 2 * flash;
          ctx.stroke();
        }

        // outer glow
        const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 5);
        glow.addColorStop(0,   hexToRgba(n.color, alpha * 0.55));
        glow.addColorStop(0.5, hexToRgba(n.color, alpha * 0.12));
        glow.addColorStop(1,   hexToRgba(n.color, 0));
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 5, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        // solid core
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = hexToRgba(n.color, alpha);
        ctx.fill();

        // specular highlight
        ctx.beginPath();
        ctx.arc(n.x - r * 0.25, n.y - r * 0.25, r * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${alpha * 0.35})`;
        ctx.fill();
      }

      rafId = requestAnimationFrame(frame);
    }

    resize();
    rafId = requestAnimationFrame(frame);

    window.addEventListener("resize",    resize);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("touchmove", onTouchMove, { passive: true });

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize",    resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
    };
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="fixed inset-0 z-0 block"
      />
      {/* Vignette: lighter on landing (bright=true), heavier on onboarding */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-0 pointer-events-none"
        style={{
          transition: "background 0.9s ease",
          background: bright
            ? "radial-gradient(ellipse 70% 60% at 50% 50%, transparent 15%, rgba(6,8,15,0.18) 55%, rgba(6,8,15,0.60) 100%)"
            : "radial-gradient(ellipse 70% 60% at 50% 50%, transparent 10%, rgba(6,8,15,0.52) 58%, rgba(6,8,15,0.92) 100%)",
        }}
      />
    </>
  );
}
