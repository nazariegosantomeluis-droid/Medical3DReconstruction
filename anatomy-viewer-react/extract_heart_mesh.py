"""
Extrae la malla del corazon (posiciones/normales/indices en base64) del
VIEWER_DATA embebido en docs/index.html -- el visor original de este mismo
repositorio, ya construido con scripts/build_interactive_artifact.py a
partir de un especimen ex-vivo real (LADAF-2021-17, micro-CT sincrotron).

Corre esto desde dentro de anatomy-viewer-react/:
    python3 extract_heart_mesh.py
Genera heart_mesh.json, que despues usa merge_real_heart.py.
"""

import json
import os

HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "index.html")
OUT_PATH = os.path.join(os.path.dirname(__file__), "heart_mesh.json")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

marker = "const VIEWER_DATA = "
start = html.index(marker) + len(marker)
assert html[start] == "{"

depth = 0
in_str = False
esc = False
end = None
for i in range(start, len(html)):
    ch = html[i]
    if in_str:
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            in_str = False
    else:
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

assert end is not None, "no se encontro el cierre del objeto VIEWER_DATA"
raw = html[start:end]
print("extracted length:", len(raw))

data = json.loads(raw)
print("organ keys:", list(data.keys()))

heart = data["heart"]
print("heart top-level keys:", list(heart.keys()))
mesh = heart["mesh"]
print("heart.mesh keys:", list(mesh.keys()))
print("center:", mesh.get("center"))
print("color:", heart.get("color"))

with open(OUT_PATH, "w") as f:
    json.dump(mesh, f)

print("saved to", OUT_PATH)
