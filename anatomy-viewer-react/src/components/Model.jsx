import { useEffect, useRef, useState } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { useGLTF, useCursor } from "@react-three/drei";
import * as THREE from "three";
import { GROUP_NODE_NAMES } from "../constants/modelGroups";

// Resaltado de hover: antes era un tinte emissive sobre TODA la malla, que
// a cualquier intensidad visible aplastaba el sombreado por curvatura (AO)
// que le costó tanto trabajo a esta sesión — el órgano se veía como un
// blob naranja plano en vez de un tejido con relieve. Ahora es un
// contorno/aura en el borde (silueta "inflada" renderizada por detrás,
// técnica clásica de "inverted hull"): el color propio de la malla queda
// intacto, y lo que "respira" es la opacidad del contorno, no un lavado
// de color sobre toda la superficie.
const HIGHLIGHT_COLOR = new THREE.Color("#fbbf24");
const HIGHLIGHT_OPACITY = 0.85;
const HIGHLIGHT_PULSE_SPEED = 3.2;
const HIGHLIGHT_PULSE_DEPTH = 0.35;
// Qué tan "inflado" queda el contorno, como fracción del radio de cada
// malla — una fracción (no un valor fijo en mm) para que el grosor del
// contorno se vea proporcional sin importar si la malla es una válvula
// diminuta o el pulmón entero.
const OUTLINE_THICKNESS_FRACTION = 0.01;
const CLICK_DRAG_THRESHOLD_PX = 6;
const KNOWN_GROUP_NAMES = new Set(Object.values(GROUP_NODE_NAMES));

// Qué tan tenues quedan las estructuras relacionadas con la seleccionada:
// deben leerse como contexto anatómico, no como piezas propias — bastante
// transparentes, casi un fantasma, no una versión "aguada" del color real.
const RELATED_OPACITY = 0.12;

// Qué tan rápido la cámara "planea" hacia el nuevo encuadre en vez de
// saltar de golpe — más alto = más rápido. Independiente del framerate
// porque se aplica como 1 - lerpSpeed^delta, no como una fracción fija.
const CAMERA_GLIDE_SPEED = 3.2;

function findGroupName(object) {
  let node = object;
  while (node) {
    if (KNOWN_GROUP_NAMES.has(node.name)) return node.name;
    node = node.parent;
  }
  return null;
}

// Calcula a dónde DEBERÍA apuntar la cámara para encuadrar lo visible ahora
// mismo, sin moverla todavía — el useFrame de más abajo la desliza hasta
// ahí con una animación suave en vez de saltar de golpe, que es lo que
// hace que cambiar de estructura se sienta como una transición de cámara
// de verdad y no un corte brusco.
function computeFrameForVisible(camera, root) {
  const box = new THREE.Box3();
  let any = false;
  root.traverse((child) => {
    if (child.isMesh && child.visible && !child.userData.isOutline) {
      box.expandByObject(child);
      any = true;
    }
  });
  if (!any) return null;

  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  box.getCenter(center);
  box.getSize(size);
  const maxDim = Math.max(size.x, size.y, size.z, 0.001);
  const fov = (camera.fov * Math.PI) / 180;
  const distance = ((maxDim / 2) / Math.tan(fov / 2)) * 1.7;
  const direction = new THREE.Vector3(0.55, 0.4, 1).normalize();

  return {
    position: center.clone().addScaledVector(direction, distance),
    target: center,
    near: Math.max(distance / 100, 0.01),
    far: distance * 100,
  };
}

// Crea la malla-contorno de "cáscara invertida" para una malla dada:
// misma geometría, desplazada hacia afuera a lo largo de cada normal, con
// material de solo-color renderizado por su cara TRASERA (BackSide) — así
// solo asoma el borde (silueta) por detrás de la malla real, nunca la
// superficie completa. Se agrega como hijo directo de la malla original
// para heredar su transform sin tener que llevar la cuenta aparte.
function buildOutlineMesh(mesh) {
  if (!mesh.geometry.boundingSphere) mesh.geometry.computeBoundingSphere();
  const radius = mesh.geometry.boundingSphere?.radius || 1;
  const offset = radius * OUTLINE_THICKNESS_FRACTION;

  const outlineGeometry = mesh.geometry.clone();
  const position = outlineGeometry.attributes.position;
  const normal = outlineGeometry.attributes.normal;
  for (let i = 0; i < position.count; i++) {
    position.setXYZ(
      i,
      position.getX(i) + normal.getX(i) * offset,
      position.getY(i) + normal.getY(i) * offset,
      position.getZ(i) + normal.getZ(i) * offset
    );
  }
  position.needsUpdate = true;

  const outlineMaterial = new THREE.MeshBasicMaterial({
    color: HIGHLIGHT_COLOR,
    side: THREE.BackSide,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    toneMapped: false,
  });

  const outlineMesh = new THREE.Mesh(outlineGeometry, outlineMaterial);
  outlineMesh.raycast = () => {}; // nunca debe interceptar el puntero
  outlineMesh.renderOrder = 10;
  // Marcado para que el resto del componente lo excluya de cualquier
  // scene.traverse() que busque mallas "reales" (visibilidad, encuadre de
  // cámara, inventario de nombres) — si no, hereda esa lógica como si
  // fuera una estructura más y termina forzado a visible/opaco.
  outlineMesh.userData.isOutline = true;
  return outlineMesh;
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
  const meshGroups = useRef(new Map());
  const outlineMeshes = useRef(new Map());
  const pointerDownAt = useRef(null);
  const hoveredMeshRef = useRef(null);
  const cameraGoalRef = useRef(null);
  const [hoveredName, setHoveredName] = useState(null);

  useCursor(Boolean(hoveredName));

  // Desliza la cámara hacia el encuadre objetivo (calculado más abajo cada
  // vez que cambia la selección/grupo) en vez de saltar de golpe, y hace
  // "respirar" el resalte ámbar de la malla bajo el cursor. No se llama a
  // controls.update() aquí: drei's <OrbitControls> ya lo hace en todos los
  // frames (prioridad -1, antes de este hook) — llamarlo otra vez
  // duplicaría el incremento de autoRotate y el amortiguamiento.
  //
  // Importante: una vez que la cámara LLEGA al objetivo, se suelta
  // (cameraGoalRef pasa a null) en vez de seguir tirando de ella hacia ese
  // punto fijo para siempre. Si no se soltara, pelearía cada frame contra
  // el autoRotate de OrbitControls (que sí mueve camera.position en órbita
  // continuamente) y el resultado es un enganche errático, no una órbita
  // suave — se descubrió exactamente así, visualmente, al probar la
  // rotación automática en reposo.
  useFrame((state, delta) => {
    const goal = cameraGoalRef.current;
    if (goal) {
      const alpha = 1 - Math.exp(-CAMERA_GLIDE_SPEED * delta);
      camera.position.lerp(goal.position, alpha);
      const controls = controlsRef?.current;
      if (controls) {
        controls.target.lerp(goal.target, alpha);
      }
      camera.near = goal.near;
      camera.far = goal.far;
      camera.updateProjectionMatrix();

      const framingDistance = goal.position.distanceTo(goal.target) || 1;
      const epsilon = framingDistance * 0.004;
      const posDone = camera.position.distanceTo(goal.position) < epsilon;
      const targetDone = !controls || controls.target.distanceTo(goal.target) < epsilon;
      if (posDone && targetDone) {
        cameraGoalRef.current = null;
      }
    }

    // Solo el contorno de la malla bajo el cursor queda visible (opacidad
    // "respirando"); todos los demás contornos quedan en 0 — recorrer los
    // ~20 contornos cada frame es trivial, así que no hace falta llevar
    // la cuenta de cuál era el anterior para apagarlo a mano.
    if (outlineMeshes.current.size > 0) {
      const hoveredUuid = hoveredMeshRef.current?.uuid;
      const wave = 1 - HIGHLIGHT_PULSE_DEPTH * (0.5 + 0.5 * Math.sin(state.clock.elapsedTime * HIGHLIGHT_PULSE_SPEED));
      outlineMeshes.current.forEach((outlineMesh, uuid) => {
        outlineMesh.material.opacity = uuid === hoveredUuid ? HIGHLIGHT_OPACITY * wave : 0;
      });
    }
  });

  // Cada malla necesita su propio material (no compartido) para poder
  // resaltar solo la que está bajo el cursor sin afectar a las demás.
  // De paso, este es el único recorrido garantizado del árbol completo del
  // modelo, así que aquí mismo se arma el inventario de nombres crudos que
  // usa el Modo Debug, y a qué grupo (especimen real / atlas) pertenece
  // cada malla, caminando hacia arriba hasta encontrar un nodo-grupo
  // conocido — sin esto habría que pasar mesh por mesh a mano.
  useEffect(() => {
    const counts = new Map();
    // Primero se junta la lista de mallas reales, SIN tocar el árbol
    // todavía — agregar el contorno como hijo durante el propio
    // scene.traverse() hace que ese mismo recorrido baje también al hijo
    // recién agregado (que también es un Mesh) y arme un contorno para el
    // contorno, infinitamente. Por eso la mutación del árbol va en un
    // segundo paso, después de que el recorrido ya terminó.
    const meshes = [];
    scene.traverse((child) => {
      if (!child.isMesh) return;
      meshes.push(child);
      meshGroups.current.set(child.uuid, findGroupName(child));
      counts.set(child.name, (counts.get(child.name) ?? 0) + 1);
    });

    meshes.forEach((child) => {
      child.material = child.material.clone();
      const outlineMesh = buildOutlineMesh(child);
      child.add(outlineMesh);
      outlineMeshes.current.set(child.uuid, outlineMesh);
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
      if (!child.isMesh || child.userData.isOutline) return;
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
    cameraGoalRef.current = computeFrameForVisible(camera, scene);
  }, [activeGroupNodeName, selectedMeshName, relatedMeshNames, scene, camera, controlsRef]);

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
    hoveredMeshRef.current = event.object;
    setHoveredName(event.object.name);
    onHoverChange?.(event.object.name);
  };

  const handlePointerOut = (event) => {
    event.stopPropagation();
    hoveredMeshRef.current = null;
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
