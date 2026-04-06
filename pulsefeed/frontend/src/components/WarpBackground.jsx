import { useEffect, useRef } from "react";

// ─── Config ───────────────────────────────────────────────────────────────────
const NODE_COUNT = 45;
const CONNECT_RADIUS = 0.26; // fraction of min(W,H)
const PULSE_SPEED = 2.8; // px per frame
const PULSE_EVERY = 220; // frames between new pulses
const REPEL_RADIUS = 130; // px — mouse pushes nodes away gently
const FLASH_DURATION = 110; // frames for activation bloom to decay

// Ink & Clay Aesthetic Colors
const INK_COLOR = "#231F20";
const CLAY_COLOR = "#D97757";
const PAPER_COLOR = "#FDFCF8";

// ─── Helpers ──────────────────────────────────────────────────────────────────
function hexToRgba(hex, a) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function buildNodes(W, H) {
  return Array.from({ length: NODE_COUNT }, (_, i) => ({
    x: Math.random() * W,
    y: Math.random() * H,
    vx: (Math.random() - 0.5) * 0.18,
    vy: (Math.random() - 0.5) * 0.18,
    r: Math.random() * 2.2 + 1.4,
    phase: (i / NODE_COUNT) * Math.PI * 2,
    beatRate: Math.random() * 0.018 + 0.012,
    activatedAt: -9999,
  }));
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function WarpBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    let W, H, nodes, rafId;
    let pulses = [];
    let time = 0;
    const mouse = { x: 0.5, y: 0.5 };
    const smoothMouse = { x: 0.5, y: 0.5 };
    let scrollProgress = 0; // 0..1 based on page scroll
    let smoothScroll = 0;

    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
      nodes = buildNodes(W, H);
      pulses = [];
    }

    function onMouseMove(e) {
      mouse.x = e.clientX / W;
      mouse.y = e.clientY / H;
    }
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
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < maxD) edges.push({ i, j, d, alpha: 1 - d / maxD });
        }
      }
      return edges;
    }

    function spawnPulse(edges) {
      if (!edges.length) return;
      const e = edges[Math.floor(Math.random() * edges.length)];
      pulses.push({
        i: e.i,
        j: e.j,
        d: e.d,
        progress: 0,
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

      // Smooth scroll tracking
      smoothScroll += (scrollProgress - smoothScroll) * 0.06;
      const scrollDrift = smoothScroll * 1.2; // scroll-linked drift multiplier

      // Move nodes + mouse repulsion + scroll-linked drift + wrap
      for (const n of nodes) {
        n.x += n.vx + scrollDrift * 0.3 * Math.sin(n.phase);
        n.y += n.vy - scrollDrift * 0.15;

        const dx = n.x - mx;
        const dy = n.y - my;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < REPEL_RADIUS && d > 0) {
          const force = ((REPEL_RADIUS - d) / REPEL_RADIUS) * 0.4;
          n.x += (dx / d) * force;
          n.y += (dy / d) * force;
        }

        if (n.x < -60) n.x = W + 60;
        if (n.x > W + 60) n.x = -60;
        if (n.y < -60) n.y = H + 60;
        if (n.y > H + 60) n.y = -60;
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

      // ── Background (Print Paper) ─────────────────────────────────────────
      ctx.fillStyle = PAPER_COLOR;
      ctx.fillRect(0, 0, W, H);

      // ── Edges (Ink Lines) ────────────────────────────────────────────────
      for (const e of edges) {
        ctx.beginPath();
        ctx.moveTo(nodes[e.i].x, nodes[e.i].y);
        ctx.lineTo(nodes[e.j].x, nodes[e.j].y);
        ctx.strokeStyle = hexToRgba(INK_COLOR, e.alpha * 0.6); // Ink color with variable opacity
        ctx.lineWidth = 1; // Strict 1px geometric lines
        ctx.stroke();
      }

      // ── Pulse particles (Ink pencil marks) ────────────────────────────
      for (const p of pulses) {
        const from = p.reverse ? nodes[p.j] : nodes[p.i];
        const to = p.reverse ? nodes[p.i] : nodes[p.j];
        const px = from.x + (to.x - from.x) * p.progress;
        const py = from.y + (to.y - from.y) * p.progress;

        ctx.fillStyle = INK_COLOR;
        ctx.fillRect(px - 3, py - 3, 6, 6);
        ctx.strokeStyle = INK_COLOR;
        ctx.lineWidth = 1;
        ctx.strokeRect(px - 3, py - 3, 6, 6);
      }

      // ── Nodes (Ink Geometry) ─────────────────────────────────────────────
      for (const n of nodes) {
        const beat = 0.5 + 0.5 * Math.sin(time * n.beatRate + n.phase);
        const age = time - n.activatedAt;
        const flash = age < FLASH_DURATION ? 1 - age / FLASH_DURATION : 0;

        // Base geometry
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = INK_COLOR;
        ctx.fill();

        // Pulsing / Activation Rings
        if (flash > 0) {
          const ringR = n.r + (1 - flash) * 15;
          ctx.beginPath();
          ctx.arc(n.x, n.y, ringR, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(217,119,87, ${flash})`; // Clay terracotta rings on activation
          ctx.lineWidth = 1.5;
          ctx.stroke();
        } else if (beat > 0.8) {
          // Subtle idle beat ring
          const beatR = n.r + 4;
          ctx.beginPath();
          ctx.arc(n.x, n.y, beatR, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(35,31,32, ${0.4 * (beat - 0.8) * 5})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      rafId = requestAnimationFrame(frame);
    }

    resize();
    rafId = requestAnimationFrame(frame);

    window.addEventListener("resize", resize);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("touchmove", onTouchMove, { passive: true });

    // Scroll tracking for canvas sync
    const onScroll = () => {
      const maxScroll =
        document.documentElement.scrollHeight - window.innerHeight;
      scrollProgress = maxScroll > 0 ? window.scrollY / maxScroll : 0;
    };
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      cancelAnimationFrame(rafId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <>
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        className="fixed inset-0 z-0 block"
      />
      {/* Subtle Grain Overlay (Replaced dark vignette) */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-0 pointer-events-none opacity-20 mix-blend-multiply"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
        }}
      />
    </>
  );
}
