import { Suspense, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import Model from "./Model";

export default function Scene({
  modelUrl,
  onSelect,
  onHoverChange,
  onMeshNames,
  selectedMeshName,
  relatedMeshNames,
  activeGroupNodeName,
}) {
  // Model necesita esta referencia para mover la cámara y actualizar el
  // "target" de OrbitControls cada vez que cambia el grupo visible — el
  // encuadre automático no funciona solo con la posición de la cámara.
  const controlsRef = useRef();

  return (
    <Canvas camera={{ position: [0, 1.2, 3.4], fov: 45 }} shadows>
      {/* La luz hemisférica (cielo/suelo) rellena las sombras con un rebote
          de color en vez de negro puro — sin ella, un tejido con roughness
          moderado bajo solo 2 luces direccionales se ve plano y apagado. */}
      <hemisphereLight args={["#dfe6f5", "#3a2a26", 0.55]} />
      <ambientLight intensity={0.35} />
      <directionalLight
        position={[3, 5, 2]}
        intensity={1.3}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-4, -2, -3]} intensity={0.5} />

      <Suspense fallback={null}>
        <Model
          url={modelUrl}
          onSelect={onSelect}
          onHoverChange={onHoverChange}
          onMeshNames={onMeshNames}
          selectedMeshName={selectedMeshName}
          relatedMeshNames={relatedMeshNames}
          activeGroupNodeName={activeGroupNodeName}
          controlsRef={controlsRef}
        />
      </Suspense>

      <OrbitControls ref={controlsRef} enablePan enableZoom enableRotate makeDefault />
    </Canvas>
  );
}
