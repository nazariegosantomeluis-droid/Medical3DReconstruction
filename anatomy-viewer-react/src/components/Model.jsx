import { useEffect, useRef, useState } from "react";
import { useThree } from "@react-three/fiber";
import { useGLTF, useCursor } from "@react-three/drei";
import * as THREE from "three";
import { GROUP_NODE_NAMES } from "../constants/modelGroups";

// Un resaltado sutil, solo para el hover en vivo — la pieza seleccionada ya
// se distingue de sobra por ser la única opaca (ver más abajo).
const HIGHLIGHT_COLOR = new THREE.Color("#fbbf24");
const HIGHLIGHT_INTENSITY = 0.28;
const CLICK_DRAG_THRESHOLD_PX = 6;
const KNOWN_GROUP_NAMES = new Set(Object.values(GROUP_NODE_NAMES));

// Qué tan tenues quedan las estructuras relacionadas con la seleccionada:
// deben leerse como contexto anatómico, no como piezas propias — bastante
// transparentes, casi un fantasma, no una versión "aguada" del color real.
const RELATED_OPACITY = 0.12;

function findGroupName(object) {
  let node = object;
  while (node) {
    if (KNOWN_GROUP_NAMES.has(node.name)) return node.name;
    node = node.parent;
  }
  return null;
}

// Encuadra la cámara a lo que esté visible ahora mismo, no al modelo
// completo — necesario porque solo un grupo (el corazón real o las piezas
// del atlas) está visible a la vez, y cada uno vive en su propia escala/
// posición dentro del archivo.
function fitCameraToVisible(camera, controls, root) {
  const box = new THREE.Box3();
  let any = false;
  root.traverse((child) => {
    if (child.isMesh && child.visible) {
      box.expandByObject(child);
      any = true;
    }
  });
  if (!any) return;

  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  box.getCenter(center);
  box.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z, 0.001);
  const fov = (camera.fov * Math.PI) / 180;
  const distance = ((maxDim / 2) / Math.tan(fov / 2)) * 1.7;
  const direction = new THREE.Vector3(0.55, 0.4, 1).normalize();

  camera.position.copy(center.clone().addScaledVector(direction, distance));
  camera.near = Math.max(distance / 100, 0.01);
  camera.far = distance * 100;
  camera.updateProjectionMatrix();

  if (controls) {
    controls.target.copy(center);
    controls.update();
  }
}

export default function Model({
  url,
  onSelect,
  onHoverChange,
  onMeshNames,
  selectedMeshName,
  relatedMeshNames,
  activeGroupNodeName,
  controlsRef,
}) {
  const { scene } = useGLTF(url);
  const { camera } = useThree();
  const originalEmissive = useRef(new Map());
  const meshGroups = useRef(new Map());
  const pointerDownAt = useRef(null);
  const [hoveredName, setHoveredName] = useState(null);

  useCursor(Boolean(hoveredName));

  // Cada malla necesita su propio material (no compartido) para poder
  // resaltar solo la que está bajo el cursor sin afectar a las demás.
  // De paso, este es el único recorrido garantizado del árbol completo del
  // modelo, así que aquí mismo se arma el inventario de nombres crudos que
  // usa el Modo Debug, y a qué grupo (especimen real / atlas) pertenece
  // cada malla, caminando hacia arriba hasta encontrar un nodo-grupo
  // conocido — sin esto habría que pasar mesh por mesh a mano.
  useEffect(() => {
    const counts = new Map();
    scene.traverse((child) => {
      if (!child.isMesh) return;
      child.material = child.material.clone();
      originalEmissive.current.set(child.uuid, {
        color: child.material.emissive ? child.material.emissive.clone() : null,
        intensity: child.material.emissiveIntensity ?? 0,
      });
      meshGroups.current.set(child.uuid, findGroupName(child));
      counts.set(child.name, (counts.get(child.name) ?? 0) + 1);
    });
    onMeshNames?.(Array.from(counts, ([name, count]) => ({ name, count })));
  }, [scene, onMeshNames]);

  // Qué se ve ahora mismo, en un solo lugar: (1) el .glb trae dos
  // especímenes reales que no comparten coordenadas — solo el grupo activo
  // se muestra, nunca los dos a la vez (ver notaEspecimen en
  // estructuras.json); y (2) al seleccionar una estructura (panel abierto
  // para ella), esta queda opaca, sus relacionadas (mapa de conexiones
  // clínicas) quedan muy tenues como contexto anatómico, y el resto del
  // grupo activo se OCULTA por completo para que no quede ruido visual — la
  // cámara se acerca a lo que queda visible. Sin selección, vuelve a verse
  // todo el grupo activo, opaco.
  useEffect(() => {
    const relatedSet = new Set(relatedMeshNames ?? []);
    scene.traverse((child) => {
      if (!child.isMesh) return;
      const group = meshGroups.current.get(child.uuid);
      const inActiveGroup = !group || group === activeGroupNodeName;

      if (!inActiveGroup) {
        child.visible = false;
        return;
      }

      const isSelected = child.name === selectedMeshName;
      const isRelated = relatedSet.has(child.name);

      if (!selectedMeshName || isSelected) {
        child.visible = true;
        child.material.transparent = false;
        child.material.opacity = 1;
        child.material.depthWrite = true;
      } else if (isRelated) {
        child.visible = true;
        child.material.transparent = true;
        child.material.opacity = RELATED_OPACITY;
        child.material.depthWrite = false;
      } else {
        child.visible = false;
      }
    });
    fitCameraToVisible(camera, controlsRef?.current, scene);
  }, [activeGroupNodeName, selectedMeshName, relatedMeshNames, scene, camera, controlsRef]);

  // Solo el hover en vivo tiñe con emissive — es una señal momentánea
  // mientras el cursor está encima. La pieza "seleccionada" (panel abierto)
  // ya se distingue de sobra por quedar opaca mientras el resto se
  // transparenta arriba; sumarle también un tinte de color persistente
  // solo tapaba su color anatómico real.
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
