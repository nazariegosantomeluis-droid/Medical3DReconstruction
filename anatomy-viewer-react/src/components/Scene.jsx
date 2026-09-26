import { Suspense, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import Model from "./Model";

export default function Scene({
  modelUrl,
  onSelect,
  onHoverChange,
  onMeshNames,
  forcedHighlightName,
  activeGroupNodeName,
}) {
  // Model necesita esta referencia para mover la cámara y actualizar el
  // "target" de OrbitControls cada vez que cambia el grupo visible — el
  // encuadre automático no funciona solo con la posición de la cámara.
  const controlsRef = useRef();

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
        <Model
          url={modelUrl}
          onSelect={onSelect}
          onHoverChange={onHoverChange}
          onMeshNames={onMeshNames}
          forcedHighlightName={forcedHighlightName}
          activeGroupNodeName={activeGroupNodeName}
          controlsRef={controlsRef}
        />
      </Suspense>

      <OrbitControls ref={controlsRef} enablePan enableZoom enableRotate makeDefault />
    </Canvas>
  );
}
