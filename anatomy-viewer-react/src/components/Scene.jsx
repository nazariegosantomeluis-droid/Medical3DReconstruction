import { Suspense, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { ContactShadows, OrbitControls } from "@react-three/drei";
import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";
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
    // alpha:true deja pasar el fondo degradado de App.jsx por detrás del
    // canvas en vez de un negro sólido — así el visor se siente flotando
    // dentro de la atmósfera de la página en vez de ser una caja aparte.
    <Canvas camera={{ position: [0, 1.2, 3.4], fov: 45 }} shadows gl={{ alpha: true, antialias: true }}>
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
      {/* Luz de contorno fría desde atrás: separa la silueta del tejido del
          fondo oscuro y le da un borde sutil, casi de "escáner médico". */}
      <directionalLight position={[-1, 1.5, -4]} intensity={0.6} color="#8fb4ff" />

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
        <ContactShadows position={[0, -1.05, 0]} opacity={0.45} scale={10} blur={2.4} far={2} color="#000000" />
      </Suspense>

      <OrbitControls
        ref={controlsRef}
        enablePan
        enableZoom
        enableRotate
        makeDefault
        autoRotate={!selectedMeshName}
        autoRotateSpeed={0.5}
        enableDamping
        dampingFactor={0.08}
      />

      {/* Bloom sutil: solo las zonas realmente brillantes (el resalte
          ámbar del hover) florecen; el tejido normal no se ve "lavado".
          Vignette oscurece los bordes para que el ojo se quede en el
          centro, como en un visor de instrumental real. multisampling=0
          porque el canvas ya pide antialias en el WebGLRenderer de base
          (arriba) — sumarle MSAA también en el composer es el gasto más
          caro de toda esta cadena de postprocesado para una ganancia casi
          imperceptible, y aquí interesa que corra fluido en laptops
          normales, no solo en una GPU dedicada. */}
      <EffectComposer multisampling={0}>
        <Bloom luminanceThreshold={0.92} luminanceSmoothing={0.3} intensity={0.55} mipmapBlur />
        <Vignette eskil={false} offset={0.18} darkness={0.55} />
      </EffectComposer>
    </Canvas>
  );
}
