/**
 * AtmosphericBackground — Bio-Cosmic Edition
 *
 * Scene elements:
 *  1. FloatingShards    — 200 instanced tetrahedrons; respond to mouse wind
 *                         + subtle gravitational pull toward the singularity
 *  2. DataNodes         — 80 instanced octahedrons; additive neon bloom
 *  3. KnowledgeMoon     — glowing teal sphere (top-right); two bloom-shell
 *                         layers pulse in sync; slow mouse parallax
 *  4. DataSingularity   — void core + three spinning accretion rings (bottom-left);
 *                         gravitational well that gently warps particles
 *  5. Navigator         — translucent 3D astronaut drifts diagonally across
 *                         the full scene in 60 s; slow tumble; medium parallax
 *  6. SearchLight       — point-light that lags behind the cursor
 *
 * Performance: 2 instanced draw calls for particles, ~12 small meshes total.
 * Bloom is faked with AdditiveBlending shells — no postprocessing library.
 * DPR capped at 1.5, antialias off.
 */

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

// ─────────────────────────────────────────────────────────────────────────────
// Scene constants
// ─────────────────────────────────────────────────────────────────────────────

const BLACK_HOLE_POS = new THREE.Vector3(-11, -7, -6);
const GRAVITY = 0.00018; // very subtle pull toward singularity

const MOON_BASE = new THREE.Vector3(9, 5.5, -4);
const SINGULARITY_BASE = new THREE.Vector3(-11, -7, -6);

// ─────────────────────────────────────────────────────────────────────────────
// Particle factory
// ─────────────────────────────────────────────────────────────────────────────

function buildParticles(count, depthRange = [-12, 8]) {
  return Array.from({ length: count }, () => {
    const depth = Math.random(); // 0 = far, 1 = close
    const [zMin, zSpan] = depthRange;
    return {
      pos: new THREE.Vector3(
        (Math.random() - 0.5) * 38,
        (Math.random() - 0.5) * 26,
        zMin + depth * zSpan,
      ),
      vel: new THREE.Vector3(
        (Math.random() - 0.5) * 0.004,
        -(0.003 + Math.random() * 0.01) * (0.3 + depth * 0.7),
        0,
      ),
      rot: new THREE.Euler(
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2,
      ),
      rSpd: new THREE.Vector3(
        (Math.random() - 0.5) * 0.016,
        (Math.random() - 0.5) * 0.016,
        (Math.random() - 0.5) * 0.016,
      ),
      scale: 0.04 + depth * 0.22,
      depth,
    };
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// FloatingShards  (tetrahedrons — warp toward singularity)
// ─────────────────────────────────────────────────────────────────────────────

function FloatingShards({ count = 200 }) {
  const meshRef = useRef(null);
  const dummy = useRef(new THREE.Object3D());
  const wind = useRef(new THREE.Vector2(0.002, 0));
  const particlesRef = useRef(buildParticles(count));

  useFrame((state) => {
    if (!meshRef.current) return;

    // Mouse wind
    wind.current.x += (state.mouse.x * 0.009 - wind.current.x) * 0.04;
    wind.current.y += (state.mouse.y * 0.004 - wind.current.y) * 0.04;

    for (let i = 0; i < count; i++) {
      const p = particlesRef.current[i];

      // Gravitational warp toward black hole
      const dx = BLACK_HOLE_POS.x - p.pos.x;
      const dy = BLACK_HOLE_POS.y - p.pos.y;
      const dist2 = dx * dx + dy * dy + 8; // +8 prevents runaway near core
      const pull = GRAVITY / dist2;
      p.vel.x = Math.max(-0.015, Math.min(0.015, p.vel.x + dx * pull));
      p.vel.y = Math.max(-0.015, Math.min(0.015, p.vel.y + dy * pull));

      // Parallax wind (close particles react more)
      p.pos.x += p.vel.x + wind.current.x * (0.2 + p.depth * 0.8);
      p.pos.y += p.vel.y + wind.current.y * 0.15 * p.depth;
      p.rot.x += p.rSpd.x;
      p.rot.y += p.rSpd.y;
      p.rot.z += p.rSpd.z;

      // Screen wrap
      if (p.pos.y < -14) p.pos.y = 14;
      if (p.pos.x > 20) p.pos.x = -20;
      if (p.pos.x < -20) p.pos.x = 20;

      dummy.current.position.copy(p.pos);
      dummy.current.rotation.copy(p.rot);
      dummy.current.scale.setScalar(p.scale);
      dummy.current.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.current.matrix);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[null, null, count]}
      frustumCulled={false}
    >
      <tetrahedronGeometry args={[1, 0]} />
      <meshStandardMaterial
        color="#7C3AED"
        emissive="#5b21b6"
        emissiveIntensity={0.6}
        metalness={0.9}
        roughness={0.15}
        transparent
        opacity={0.5}
      />
    </instancedMesh>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DataNodes  (octahedrons — additive neon bloom)
// ─────────────────────────────────────────────────────────────────────────────

function DataNodes({ count = 80 }) {
  const meshRef = useRef(null);
  const dummy = useRef(new THREE.Object3D());
  const particlesRef = useRef(buildParticles(count, [-10, 6]));

  useFrame(() => {
    if (!meshRef.current) return;

    for (let i = 0; i < count; i++) {
      const p = particlesRef.current[i];

      p.pos.x += p.vel.x;
      p.pos.y += p.vel.y;
      p.rot.x += p.rSpd.x;
      p.rot.y += p.rSpd.y;

      if (p.pos.y < -14) p.pos.y = 14;
      if (p.pos.x > 20) p.pos.x = -20;
      if (p.pos.x < -20) p.pos.x = 20;

      dummy.current.position.copy(p.pos);
      dummy.current.rotation.copy(p.rot);
      dummy.current.scale.setScalar(p.scale * 0.55);
      dummy.current.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.current.matrix);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[null, null, count]}
      frustumCulled={false}
    >
      <octahedronGeometry args={[1, 0]} />
      <meshBasicMaterial
        color="#B7397A"
        transparent
        opacity={0.55}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
      />
    </instancedMesh>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// KnowledgeMoon  (top-right, slow parallax, pulsing bloom shells)
// ─────────────────────────────────────────────────────────────────────────────

function KnowledgeMoon() {
  const groupRef = useRef(null);
  const glow1Ref = useRef(null);
  const glow2Ref = useRef(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;

    // Pulsing scale
    groupRef.current.scale.setScalar(1 + Math.sin(t * 0.6) * 0.04);

    // Glow shell opacity pulse
    if (glow1Ref.current)
      glow1Ref.current.material.opacity = 0.18 + Math.sin(t * 0.6) * 0.06;
    if (glow2Ref.current)
      glow2Ref.current.material.opacity = 0.09 + Math.sin(t * 0.6 + 0.8) * 0.03;

    // Slow mouse parallax (factor 0.5 — feels far away)
    const tx = MOON_BASE.x + state.mouse.x * 0.5;
    const ty = MOON_BASE.y + state.mouse.y * 0.35;
    groupRef.current.position.x += (tx - groupRef.current.position.x) * 0.025;
    groupRef.current.position.y += (ty - groupRef.current.position.y) * 0.025;
  });

  return (
    <group ref={groupRef} position={MOON_BASE.toArray()}>
      {/* Core */}
      <mesh>
        <sphereGeometry args={[1.2, 32, 32]} />
        <meshStandardMaterial
          color="#7C3AED"
          emissive="#A855F7"
          emissiveIntensity={0.9}
          roughness={0.25}
          metalness={0.7}
        />
      </mesh>

      {/* Inner bloom shell */}
      <mesh ref={glow1Ref}>
        <sphereGeometry args={[1.65, 20, 20]} />
        <meshBasicMaterial
          color="#B7397A"
          transparent
          opacity={0.18}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Outer bloom shell */}
      <mesh ref={glow2Ref}>
        <sphereGeometry args={[2.3, 16, 16]} />
        <meshBasicMaterial
          color="#F472B6"
          transparent
          opacity={0.09}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Violet scene light so nearby shards catch the glow */}
      <pointLight color="#A855F7" intensity={1.5} distance={18} decay={2} />
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DataSingularity  (bottom-left, three spinning accretion rings)
// ─────────────────────────────────────────────────────────────────────────────

function DataSingularity() {
  const groupRef = useRef(null);
  const ring1Ref = useRef(null);
  const ring2Ref = useRef(null);
  const ring3Ref = useRef(null);

  useFrame((state) => {
    // Rings spin independently
    if (ring1Ref.current) ring1Ref.current.rotation.z += 0.004;
    if (ring2Ref.current) ring2Ref.current.rotation.z -= 0.0025;
    if (ring3Ref.current) ring3Ref.current.rotation.z += 0.0015;

    if (!groupRef.current) return;

    // Very slow parallax (factor 0.3 — feels even further away than moon)
    const tx = SINGULARITY_BASE.x + state.mouse.x * 0.3;
    const ty = SINGULARITY_BASE.y + state.mouse.y * 0.2;
    groupRef.current.position.x += (tx - groupRef.current.position.x) * 0.018;
    groupRef.current.position.y += (ty - groupRef.current.position.y) * 0.018;
  });

  return (
    <group ref={groupRef} position={SINGULARITY_BASE.toArray()}>
      {/* Event horizon — absolute void */}
      <mesh>
        <sphereGeometry args={[1.4, 32, 32]} />
        <meshBasicMaterial color="#000000" />
      </mesh>

      {/* Hot inner accretion ring */}
      <mesh ref={ring1Ref} rotation={[Math.PI / 4, 0, 0]}>
        <torusGeometry args={[2.2, 0.22, 8, 80]} />
        <meshBasicMaterial
          color="#B7397A"
          transparent
          opacity={0.45}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Cooler outer ring */}
      <mesh ref={ring2Ref} rotation={[Math.PI / 3.5, 0.4, 0]}>
        <torusGeometry args={[3.0, 0.14, 8, 80]} />
        <meshBasicMaterial
          color="#7C3AED"
          transparent
          opacity={0.3}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Faint outer halo */}
      <mesh ref={ring3Ref} rotation={[Math.PI / 2.8, -0.3, 0.2]}>
        <torusGeometry args={[3.9, 0.08, 8, 80]} />
        <meshBasicMaterial
          color="#4C6E94"
          transparent
          opacity={0.18}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </mesh>

      {/* Gravitational lensing glow */}
      <mesh>
        <sphereGeometry args={[2.6, 20, 20]} />
        <meshBasicMaterial
          color="#7c3aed"
          transparent
          opacity={0.06}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.BackSide}
        />
      </mesh>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Navigator  (translucent astronaut, 60-second diagonal drift + slow tumble)
// ─────────────────────────────────────────────────────────────────────────────

function Navigator() {
  const groupRef = useRef(null);
  const mouseOffset = useRef(new THREE.Vector2(0, 0));

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;
    const progress = (t % 60) / 60; // 0 → 1 every 60 s

    // Medium mouse parallax
    mouseOffset.current.x +=
      (state.mouse.x * 1.2 - mouseOffset.current.x) * 0.04;
    mouseOffset.current.y +=
      (state.mouse.y * 0.8 - mouseOffset.current.y) * 0.04;

    // Diagonal drift: top-left → bottom-right + gentle Z wobble
    groupRef.current.position.x = -16 + progress * 34 + mouseOffset.current.x;
    groupRef.current.position.y = 9 - progress * 19 + mouseOffset.current.y;
    groupRef.current.position.z = -1 + Math.sin(progress * Math.PI * 4) * 1.2;

    // Slow tumble on all axes
    groupRef.current.rotation.x = t * 0.07;
    groupRef.current.rotation.y = t * 0.11;
    groupRef.current.rotation.z = t * 0.04;
  });

  return (
    <group ref={groupRef} scale={0.85}>
      {/* ── Helmet ── */}
      <mesh position={[0, 0.78, 0]}>
        <sphereGeometry args={[0.42, 20, 20]} />
        <meshStandardMaterial
          color="#c7d2fe"
          transparent
          opacity={0.7}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>

      {/* Visor — dark reflective face-plate with violet emissive */}
      <mesh position={[0, 0.78, 0.3]}>
        <sphereGeometry args={[0.28, 14, 14]} />
        <meshStandardMaterial
          color="#0f172a"
          transparent
          opacity={0.9}
          metalness={0.95}
          roughness={0.05}
          emissive="#7C3AED"
          emissiveIntensity={0.4}
        />
      </mesh>

      {/* ── Torso ── */}
      <mesh position={[0, 0.05, 0]}>
        <capsuleGeometry args={[0.3, 0.65, 4, 14]} />
        <meshStandardMaterial
          color="#c7d2fe"
          transparent
          opacity={0.65}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>

      {/* Life-support backpack */}
      <mesh position={[0, 0.12, -0.4]}>
        <boxGeometry args={[0.38, 0.52, 0.2]} />
        <meshStandardMaterial
          color="#94a3b8"
          transparent
          opacity={0.55}
          metalness={0.5}
          roughness={0.4}
        />
      </mesh>

      {/* ── Arms ── */}
      <mesh position={[-0.48, 0.18, 0]} rotation={[0, 0, 0.6]}>
        <capsuleGeometry args={[0.1, 0.42, 4, 10]} />
        <meshStandardMaterial
          color="#c7d2fe"
          transparent
          opacity={0.65}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>
      <mesh position={[0.48, 0.18, 0]} rotation={[0, 0, -0.6]}>
        <capsuleGeometry args={[0.1, 0.42, 4, 10]} />
        <meshStandardMaterial
          color="#c7d2fe"
          transparent
          opacity={0.65}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>

      {/* ── Legs ── */}
      <mesh position={[-0.2, -0.88, 0]} rotation={[0, 0, 0.12]}>
        <capsuleGeometry args={[0.12, 0.38, 4, 10]} />
        <meshStandardMaterial
          color="#c7d2fe"
          transparent
          opacity={0.65}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>
      <mesh position={[0.2, -0.88, 0]} rotation={[0, 0, -0.12]}>
        <capsuleGeometry args={[0.12, 0.38, 4, 10]} />
        <meshStandardMaterial
          color="#c7d2fe"
          transparent
          opacity={0.65}
          metalness={0.3}
          roughness={0.5}
        />
      </mesh>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SearchLight  (follows cursor with lag)
// ─────────────────────────────────────────────────────────────────────────────

function SearchLight() {
  const lightRef = useRef(null);

  useFrame((state) => {
    if (!lightRef.current) return;
    lightRef.current.position.x +=
      (state.mouse.x * 13 - lightRef.current.position.x) * 0.07;
    lightRef.current.position.y +=
      (state.mouse.y * 9 - lightRef.current.position.y) * 0.07;
  });

  return (
    <pointLight
      ref={lightRef}
      position={[0, 0, 7]}
      color="#DDD6FE"
      intensity={5}
      distance={20}
      decay={2}
    />
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Scene
// ─────────────────────────────────────────────────────────────────────────────

function Scene() {
  return (
    <>
      {/* Deep dark fog */}
      <fog attach="fog" color="#04040f" near={16} far={42} />

      {/* Dim violet fill so unlit shards aren't pure black */}
      <ambientLight color="#1e1b4b" intensity={0.5} />

      {/* Static back-light for depth */}
      <pointLight
        position={[-6, 10, -8]}
        color="#4C1D95"
        intensity={3}
        distance={35}
        decay={1.5}
      />

      {/* Cursor searchlight */}
      <SearchLight />

      {/* Celestial bodies (parallax: slower = further) */}
      <KnowledgeMoon />
      <DataSingularity />

      {/* Navigator drifts at medium depth */}
      <Navigator />

      {/* Particle fields (fastest, in front) */}
      <FloatingShards count={200} />
      <DataNodes count={80} />
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────────────────────────────────────

export default function AtmosphericBackground() {
  return (
    <div className="fixed inset-0 z-0" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 15], fov: 65 }}
        dpr={[1, 1.5]}
        gl={{
          antialias: false,
          powerPreference: "high-performance",
          alpha: false,
        }}
        style={{ background: "#04040f" }}
      >
        <Scene />
      </Canvas>

      {/* Vignette: pulls focus to the centre card */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 80% 70% at 50% 50%, transparent 20%, rgba(4,4,15,0.55) 65%, rgba(4,4,15,0.92) 100%)",
        }}
      />
    </div>
  );
}
