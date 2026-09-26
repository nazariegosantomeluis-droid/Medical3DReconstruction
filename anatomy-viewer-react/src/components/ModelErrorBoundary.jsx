import { Component } from "react";

// El fallo más común no es un bug de React: es que MODEL_URL en App.jsx
// todavía no apunta a un archivo que exista en public/models/. Sin este
// límite, ese 404 tumba silenciosamente todo el árbol de React Three Fiber
// y deja una pantalla en blanco sin ninguna pista.
export default class ModelErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    // eslint-disable-next-line no-console
    console.error("No se pudo cargar el modelo 3D:", error);
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
