import { useRef, useMemo, useEffect } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

const PARTICLE_COUNT = 1500;

// All animation runs on the GPU — zero JS loop per frame
const vertexShader = `
  attribute float aIndex;
  attribute vec3  aColor;
  attribute vec3  basePosition;

  uniform float uTime;
  uniform vec3  uMouse;

  varying vec3  vColor;
  varying float vAlpha;

  void main() {
    vColor = aColor;

    // Ambient drift — pure GPU sin/cos, no CPU math
    vec3 pos = basePosition;
    pos.x += sin(uTime * 0.45 + aIndex * 0.09) * 1.6;
    pos.y += cos(uTime * 0.45 + aIndex * 0.09) * 1.6;

    // Mouse repulsion
    vec3  diff = pos - uMouse;
    float dist = length(diff);
    if (dist < 8.0) {
      float force = dist < 4.0 ? 5.0 : -1.8;
      pos.xy += normalize(diff.xy) * force * (1.0 - dist / 8.0);
    }

    // Subtle pulse
    vAlpha = 0.45 + sin(uTime * 1.2 + aIndex * 0.6) * 0.3;

    // Screen-space point size with mild depth attenuation
    vec4 mvPos  = modelViewMatrix * vec4(pos, 1.0);
    gl_PointSize = max(1.0, 220.0 / -mvPos.z);
    gl_Position  = projectionMatrix * mvPos;
  }
`;

const fragmentShader = `
  varying vec3  vColor;
  varying float vAlpha;

  void main() {
    // Soft circular sprite
    vec2  coord = gl_PointCoord - vec2(0.5);
    float r     = length(coord);
    if (r > 0.5) discard;
    float alpha = vAlpha * smoothstep(0.5, 0.1, r);
    gl_FragColor = vec4(vColor, alpha);
  }
`;

export default function AntigravityField({
  inView = true,
}: {
  inView?: boolean;
}) {
  const pointsRef = useRef<THREE.Points>(null);
  const { viewport } = useThree();

  const { geometry, material } = useMemo(() => {
    const posArr = new Float32Array(PARTICLE_COUNT * 3);
    const colArr = new Float32Array(PARTICLE_COUNT * 3);
    const idxArr = new Float32Array(PARTICLE_COUNT);
    const colorMint = new THREE.Color("#D1E8E2");
    const colorPink = new THREE.Color("#B7397A");

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      posArr[i * 3] = (Math.random() - 0.5) * 40;
      posArr[i * 3 + 1] = (Math.random() - 0.5) * 40;
      posArr[i * 3 + 2] = (Math.random() - 0.5) * 20 - 10;

      const c = Math.random() > 0.5 ? colorMint : colorPink;
      colArr[i * 3] = c.r;
      colArr[i * 3 + 1] = c.g;
      colArr[i * 3 + 2] = c.b;

      idxArr[i] = i;
    }

    const geo = new THREE.BufferGeometry();
    // basePosition = rest position (static), position = required by Three.js
    geo.setAttribute("position", new THREE.BufferAttribute(posArr.slice(), 3));
    geo.setAttribute("basePosition", new THREE.BufferAttribute(posArr, 3));
    geo.setAttribute("aColor", new THREE.BufferAttribute(colArr, 3));
    geo.setAttribute("aIndex", new THREE.BufferAttribute(idxArr, 1));

    const mat = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uMouse: { value: new THREE.Vector3(999, 999, 0) },
      },
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    return { geometry: geo, material: mat };
  }, []);

  useEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  // Per frame: only 2 uniform writes — no JS particle loop at all
  useFrame((state) => {
    if (!inView) return;
    if (!pointsRef.current) return;
    const u = (pointsRef.current.material as THREE.ShaderMaterial).uniforms;
    u.uTime.value = state.clock.elapsedTime;
    u.uMouse.value.set(
      (state.pointer.x * viewport.width) / 2,
      (state.pointer.y * viewport.height) / 2,
      0,
    );
  });

  return <points ref={pointsRef} geometry={geometry} material={material} />;
}
