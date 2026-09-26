import { useEffect, useRef, useState } from "react";
import { useGLTF, useCursor } from "@react-three/drei";
import * as THREE from "three";

const HIGHLIGHT_COLOR = new THREE.Color("#38bdf8");
const HIGHLIGHT_INTENSITY = 0.65;
const CLICK_DRAG_THRESHOLD_PX = 6;

export default function Model({ url, onSelect, onHoverChange }) {
  const { scene } = useGLTF(url);
  const originalEmissive = useRef(new Map());
  const pointerDownAt = useRef(null);
  const [hoveredName, setHoveredName] = useState(null);

  useCursor(Boolean(hoveredName));

  // Cada malla necesita su propio material (no compartido) para poder
  // resaltar solo la que está bajo el cursor sin afectar a las demás.
  useEffect(() => {
    scene.traverse((child) => {
      if (!child.isMesh) return;
      child.material = child.material.clone();
      originalEmissive.current.set(child.uuid, {
        color: child.material.emissive ? child.material.emissive.clone() : null,
        intensity: child.material.emissiveIntensity ?? 0,
      });
    });
  }, [scene]);

  useEffect(() => {
    scene.traverse((child) => {
      if (!child.isMesh || !child.material?.emissive) return;
      const original = originalEmissive.current.get(child.uuid);
      if (!original) return;
      if (child.name === hoveredName) {
        child.material.emissive.set(HIGHLIGHT_COLOR);
        child.material.emissiveIntensity = HIGHLIGHT_INTENSITY;
      } else {
        child.material.emissive.copy(original.color ?? new THREE.Color(0, 0, 0));
        child.material.emissiveIntensity = original.intensity;
      }
    });
  }, [hoveredName, scene]);

  const handlePointerDown = (event) => {
    pointerDownAt.current = { x: event.clientX, y: event.clientY };
  };

  // OrbitControls y el raycasting de R3F comparten el mismo canvas: sin este
  // chequeo, arrastrar la cámara para rotar el modelo también dispararía una
  // selección de estructura en cuanto el puntero pasara sobre una malla.
  const handlePointerUp = (event) => {
    const start = pointerDownAt.current;
    pointerDownAt.current = null;
    if (!start || !event.object?.isMesh) return;

    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    const movedDistance = Math.hypot(dx, dy);
    if (movedDistance > CLICK_DRAG_THRESHOLD_PX) return;

    event.stopPropagation();
    onSelect(event.object.name);
  };

  const handlePointerOver = (event) => {
    event.stopPropagation();
    setHoveredName(event.object.name);
    onHoverChange?.(event.object.name);
  };

  const handlePointerOut = (event) => {
    event.stopPropagation();
    setHoveredName(null);
    onHoverChange?.(null);
  };

  return (
    <primitive
      object={scene}
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
    />
  );
}
