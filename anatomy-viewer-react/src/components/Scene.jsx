import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Center } from "@react-three/drei";
import Model from "./Model";

export default function Scene({ modelUrl, onSelect, onHoverChange }) {
  return (
    <Canvas camera={{ position: [0, 1.2, 3.4], fov: 45 }} shadows>
      <ambientLight intensity={0.6} />
      <directionalLight
        position={[3, 5, 2]}
        intensity={1.2}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-4, -2, -3]} intensity={0.35} />

      <Suspense fallback={null}>
        <Center>
          <Model url={modelUrl} onSelect={onSelect} onHoverChange={onHoverChange} />
        </Center>
      </Suspense>

      <OrbitControls enablePan enableZoom enableRotate makeDefault />
    </Canvas>
  );
}
