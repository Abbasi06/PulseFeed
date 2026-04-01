/**
 * AtmosphericBackground — Vintage Editorial Edition
 *
 * Scene elements adapted for a "Printed Technical Manifesto" aesthetic:
 * All emissive glows, blurs, and AdditiveBlending have been purged.
 * Elements render as faint, sharp charcoal/ink lines on a cream paper background,
 * simulating an architectural wireframe or an ink-drawn constellation.
 */

import { useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { useInView } from "framer-motion";

const BLACK_HOLE_POS = new THREE.Vector3(-11, -7, -6);
const GRAVITY = 0.00018; 
const MOON_BASE = new THREE.Vector3(9, 5.5, -4);
const SINGULARITY_BASE = new THREE.Vector3(-11, -7, -6);

const INK_COLOR = "#231F20";
const PAPER_COLOR = "#FFFFFF";

// ─────────────────────────────────────────────────────────────────────────────
// Particle factory
// ─────────────────────────────────────────────────────────────────────────────

function buildParticles(count, depthRange = [-12, 8]) {
  return Array.from({ length: count }, () => {
    const depth = Math.random();
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
// FloatingShards (Flat Ink Wireframes)
// ─────────────────────────────────────────────────────────────────────────────

function FloatingShards({ count = 200 }) {
  const meshRef = useRef(null);
  const dummy = useRef(new THREE.Object3D());
  const wind = useRef(new THREE.Vector2(0.002, 0));
  const particlesRef = useRef(buildParticles(count));

  useFrame((state) => {
    if (!meshRef.current) return;

    wind.current.x += (state.mouse.x * 0.009 - wind.current.x) * 0.04;
    wind.current.y += (state.mouse.y * 0.004 - wind.current.y) * 0.04;

    for (let i = 0; i < count; i++) {
      const p = particlesRef.current[i];

      const dx = BLACK_HOLE_POS.x - p.pos.x;
      const dy = BLACK_HOLE_POS.y - p.pos.y;
      const dist2 = dx * dx + dy * dy + 8;
      const pull = GRAVITY / dist2;
      p.vel.x = Math.max(-0.015, Math.min(0.015, p.vel.x + dx * pull));
      p.vel.y = Math.max(-0.015, Math.min(0.015, p.vel.y + dy * pull));

      p.pos.x += p.vel.x + wind.current.x * (0.2 + p.depth * 0.8);
      p.pos.y += p.vel.y + wind.current.y * 0.15 * p.depth;
      p.rot.x += p.rSpd.x;
      p.rot.y += p.rSpd.y;
      p.rot.z += p.rSpd.z;

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
      <meshBasicMaterial
        color={INK_COLOR}
        wireframe={true}
        transparent
        opacity={0.15}
      />
    </instancedMesh>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DataNodes (Flat Ink Dots)
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
        color={INK_COLOR}
        transparent
        opacity={0.3}
        wireframe={true}
      />
    </instancedMesh>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// KnowledgeMoon (Technical Outline Sketch)
// ─────────────────────────────────────────────────────────────────────────────

function KnowledgeMoon() {
  const groupRef = useRef(null);
  const glow1Ref = useRef(null);

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;

    groupRef.current.scale.setScalar(1 + Math.sin(t * 0.6) * 0.04);

    if (glow1Ref.current)
      glow1Ref.current.material.opacity = 0.05 + Math.sin(t * 0.6) * 0.02;

    const tx = MOON_BASE.x + state.mouse.x * 0.5;
    const ty = MOON_BASE.y + state.mouse.y * 0.35;
    groupRef.current.position.x += (tx - groupRef.current.position.x) * 0.025;
    groupRef.current.position.y += (ty - groupRef.current.position.y) * 0.025;
  });

  return (
    <group ref={groupRef} position={MOON_BASE.toArray()}>
      {/* Core Outline */}
      <mesh>
        <sphereGeometry args={[1.2, 16, 16]} />
        <meshBasicMaterial
          color={INK_COLOR}
          wireframe={true}
          transparent
          opacity={0.2}
        />
      </mesh>

      {/* Orbit Outline */}
      <mesh ref={glow1Ref}>
        <sphereGeometry args={[1.65, 8, 8]} />
        <meshBasicMaterial
          color={INK_COLOR}
          wireframe={true}
          transparent
          opacity={0.08}
        />
      </mesh>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DataSingularity (Ink Orbit Rings)
// ─────────────────────────────────────────────────────────────────────────────

function DataSingularity() {
  const groupRef = useRef(null);
  const ring1Ref = useRef(null);
  const ring2Ref = useRef(null);

  useFrame((state) => {
    if (ring1Ref.current) ring1Ref.current.rotation.z += 0.004;
    if (ring2Ref.current) ring2Ref.current.rotation.z -= 0.0025;

    if (!groupRef.current) return;

    const tx = SINGULARITY_BASE.x + state.mouse.x * 0.3;
    const ty = SINGULARITY_BASE.y + state.mouse.y * 0.2;
    groupRef.current.position.x += (tx - groupRef.current.position.x) * 0.018;
    groupRef.current.position.y += (ty - groupRef.current.position.y) * 0.018;
  });

  return (
    <group ref={groupRef} position={SINGULARITY_BASE.toArray()}>
      {/* Core Dotted */}
      <mesh>
        <icosahedronGeometry args={[1.4, 0]} />
        <meshBasicMaterial 
          color={INK_COLOR} 
          wireframe={true} 
          transparent 
          opacity={0.25} 
        />
      </mesh>

      {/* Ink Ring 1 */}
      <mesh ref={ring1Ref} rotation={[Math.PI / 4, 0, 0]}>
        <torusGeometry args={[2.2, 0.02, 16, 100]} />
        <meshBasicMaterial
          color={INK_COLOR}
          transparent
          opacity={0.4}
        />
      </mesh>

      {/* Ink Ring 2 */}
      <mesh ref={ring2Ref} rotation={[Math.PI / 3.5, 0.4, 0]}>
        <torusGeometry args={[3.0, 0.01, 16, 100]} />
        <meshBasicMaterial
          color={INK_COLOR}
          transparent
          opacity={0.2}
        />
      </mesh>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Navigator (Ink Draft)
// ─────────────────────────────────────────────────────────────────────────────

function Navigator() {
  const groupRef = useRef(null);
  const mouseOffset = useRef(new THREE.Vector2(0, 0));

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;
    const progress = (t % 60) / 60;

    mouseOffset.current.x +=
      (state.mouse.x * 1.2 - mouseOffset.current.x) * 0.04;
    mouseOffset.current.y +=
      (state.mouse.y * 0.8 - mouseOffset.current.y) * 0.04;

    groupRef.current.position.x = -16 + progress * 34 + mouseOffset.current.x;
    groupRef.current.position.y = 9 - progress * 19 + mouseOffset.current.y;
    groupRef.current.position.z = -1 + Math.sin(progress * Math.PI * 4) * 1.2;

    groupRef.current.rotation.x = t * 0.07;
    groupRef.current.rotation.y = t * 0.11;
    groupRef.current.rotation.z = t * 0.04;
  });

  const inkMaterial = new THREE.MeshBasicMaterial({
    color: INK_COLOR,
    wireframe: true,
    transparent: true,
    opacity: 0.1,
  });

  return (
    <group ref={groupRef} scale={0.85}>
      <mesh position={[0, 0.78, 0]} material={inkMaterial}>
        <sphereGeometry args={[0.42, 10, 10]} />
      </mesh>
      <mesh position={[0, 0.78, 0.3]} material={inkMaterial}>
        <sphereGeometry args={[0.28, 8, 8]} />
      </mesh>
      <mesh position={[0, 0.05, 0]} material={inkMaterial}>
        <capsuleGeometry args={[0.3, 0.65, 4, 8]} />
      </mesh>
      <mesh position={[0, 0.12, -0.4]} material={inkMaterial}>
        <boxGeometry args={[0.38, 0.52, 0.2]} />
      </mesh>
      <mesh position={[-0.48, 0.18, 0]} rotation={[0, 0, 0.6]} material={inkMaterial}>
        <capsuleGeometry args={[0.1, 0.42, 4, 6]} />
      </mesh>
      <mesh position={[0.48, 0.18, 0]} rotation={[0, 0, -0.6]} material={inkMaterial}>
        <capsuleGeometry args={[0.1, 0.42, 4, 6]} />
      </mesh>
      <mesh position={[-0.2, -0.88, 0]} rotation={[0, 0, 0.12]} material={inkMaterial}>
        <capsuleGeometry args={[0.12, 0.38, 4, 6]} />
      </mesh>
      <mesh position={[0.2, -0.88, 0]} rotation={[0, 0, -0.12]} material={inkMaterial}>
        <capsuleGeometry args={[0.12, 0.38, 4, 6]} />
      </mesh>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Scene
// ─────────────────────────────────────────────────────────────────────────────

function Scene() {
  return (
    <>
      {/* Light fog to match paper depth */}
      <fog attach="fog" color={PAPER_COLOR} near={16} far={42} />

      {/* No lights needed for MeshBasicMaterial wireframes */}

      <KnowledgeMoon />
      <DataSingularity />
      <Navigator />
      <FloatingShards count={150} />
      <DataNodes count={40} />
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────────────────────────────────────

export default function AtmosphericBackground() {
  const containerRef = useRef(null);
  const isInView = useInView(containerRef);

  return (
    <div ref={containerRef} className="fixed inset-0 z-0 bg-paper" aria-hidden="true">
      <Canvas
        frameloop={isInView ? "always" : "never"}
        camera={{ position: [0, 0, 15], fov: 65 }}
        dpr={[1, 1.5]}
        gl={{
          antialias: true, // Turn on antialias for thin wireframes
          powerPreference: "high-performance",
          alpha: false,
        }}
        style={{ background: PAPER_COLOR }}
      >
        <Scene />
      </Canvas>

      {/* Flat Vignette to darken edges slightly like old paper */}
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none mix-blend-multiply"
        style={{
          background:
            "radial-gradient(ellipse 80% 70% at 50% 50%, transparent 20%, rgba(35,31,32,0.03) 65%, rgba(35,31,32,0.08) 100%)",
        }}
      />
    </div>
  );
}
