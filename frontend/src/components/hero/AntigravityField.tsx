import { useRef, useMemo } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const PARTICLE_COUNT = 3000;

function buildParticleData() {
    // We use Float32Array for performance
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const colors = new Float32Array(PARTICLE_COUNT * 3);
    
    // Celestial Aurora Palette
    const colorMint = new THREE.Color('#D1E8E2');
    const colorPink = new THREE.Color('#B7397A');

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        positions[i*3] = (Math.random() - 0.5) * 40;
        positions[i*3+1] = (Math.random() - 0.5) * 40;
        positions[i*3+2] = (Math.random() - 0.5) * 20 - 10; // Keep slightly behind

        const rand = Math.random();
        // 50/50 mix of Mint and Pink
        const baseColor = rand > 0.5 ? colorMint : colorPink;
        colors[i*3] = baseColor.r;
        colors[i*3+1] = baseColor.g;
        colors[i*3+2] = baseColor.b;
    }
    return { positions, colors };
}

const PARTICLE_DATA = buildParticleData();

export default function AntigravityField() {
    const meshRef = useRef<THREE.InstancedMesh>(null);
    const { viewport } = useThree();
    
    // Create a dummy object for matrix calculations (avoids GC overhead)
    const dummy = useMemo(() => new THREE.Object3D(), []);
    const { positions, colors } = PARTICLE_DATA;
    
    // Store localized particle state for physics (velocity, current position)
    const particleState = useRef(Array.from({ length: PARTICLE_COUNT }, (_, i) => ({
        pos: new THREE.Vector3(positions[i*3], positions[i*3+1], positions[i*3+2]),
        vel: new THREE.Vector3(0, 0, 0),
        baseScale: Math.random() * 0.4 + 0.1
    })));

    useFrame((state) => {
        if (!meshRef.current) return;
        
        // Map pointer to world coordinates
        const mouse = new THREE.Vector3(
            (state.pointer.x * viewport.width) / 2,
            (state.pointer.y * viewport.height) / 2,
            0
        );

        const time = state.clock.elapsedTime;

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const p = particleState.current[i];
            const baseIndex = i * 3;
            
            // Base anchor point (with slight ambient floating)
            const targetX = positions[baseIndex] + Math.sin(time * 0.5 + i) * 1.5;
            const targetY = positions[baseIndex+1] + Math.cos(time * 0.5 + i) * 1.5;
            const targetZ = positions[baseIndex+2];
            
            let targetPos = new THREE.Vector3(targetX, targetY, targetZ);

            // Antigravity Mouse Interaction: TUG & SCATTER
            const distToMouse = p.pos.distanceTo(mouse);
            
            if (distToMouse < 8) {
                const dir = p.pos.clone().sub(mouse).normalize();
                if (distToMouse < 4) {
                    // Scatter (Push away very strongly when extremely close)
                    targetPos.add(dir.multiplyScalar(6));
                } else {
                    // Tug (Pull slightly towards mouse when somewhat close)
                    targetPos.sub(dir.multiplyScalar(2));
                }
            }

            // Spring physics logic
            const springForce = targetPos.clone().sub(p.pos).multiplyScalar(0.02);
            p.vel.add(springForce);
            p.vel.multiplyScalar(0.9); // Damping value (lower = more friction)
            
            p.pos.add(p.vel);
            
            // Apply transformations
            dummy.position.copy(p.pos);
            
            // Pulsating scale effect
            const scale = p.baseScale + Math.sin(time * 2 + i) * 0.05;
            dummy.scale.set(scale, scale, scale);
            
            // Slow continuous rotation of individual nodes
            dummy.rotation.x = time * 0.5 + i;
            dummy.rotation.y = time * 0.3 + i;

            dummy.updateMatrix();
            meshRef.current.setMatrixAt(i, dummy.matrix);
        }
        
        // Slightly rotate the entire field for an epic cosmic feel
        meshRef.current.rotation.y = Math.sin(time * 0.05) * 0.1;
        meshRef.current.rotation.x = Math.cos(time * 0.05) * 0.1;

        meshRef.current.instanceMatrix.needsUpdate = true;
    });

    return (
        <instancedMesh ref={meshRef} args={[null as any, null as any, PARTICLE_COUNT]}>
            {/* Geometric Nodes */}
            <octahedronGeometry args={[0.1, 0]} />
            
            <meshStandardMaterial 
                roughness={0.2}
                metalness={0.8}
                transparent={true}
                opacity={0.8}
            />
            
            <instancedBufferAttribute 
                attach="instanceColor"
                args={[colors, 3]}
            />
        </instancedMesh>
    );
}
