#!/usr/bin/env python3
"""Build the published interactive HTML demo (5 organs, real data where the
repository has it) from the payload produced by build_demo_payload.py.

Usage:
    python scripts/build_demo_payload.py --output /tmp/payload.json
    python scripts/build_interactive_artifact.py --payload /tmp/payload.json --output /tmp/medical3d_viewer.html

This is a dev utility for the chat-published demo artifact, kept separate
from the CLI's own single-organ export (medical3d.core.html_viewer, used by
``main.py --visualize html``) because the demo's scope — five organs
switchable in one page, all within the ~16MB artifact-publishing budget —
is specific to that presentation context, not a pipeline output.
"""

from __future__ import annotations

import argparse
import json
import os

ORGAN_ORDER = ["lungs", "heart", "liver", "kidneys", "brain"]

ORGAN_META = {
    "lungs": {
        "label": "Pulmones",
        "algo": "Umbral + componentes conectados",
        "study_type": "CT clínica",
        "orientation_note": (
            "Orientación real verificada: coordenadas físicas DICOM (paciente "
            "left-posterior-superior) tomadas directamente de la TC de tórax. Los "
            "botones Ant/Post/Izq/Der/Sup/Inf muestran la dirección anatómica real."
        ),
        "color_hex": "#e8b4b8",
        "source_note": (
            "Reconstruido a partir de una tomografía de tórax real incluida en el "
            "repositorio (data/volumes/CTChest.nrrd)."
        ),
        "caveat": (
            "Alta fidelidad: el pulmón aireado supera los 500 HU, claramente separado "
            "de todo tejido circundante, por lo que el límite segmentado es la "
            "superficie anatómica real, no una aproximación."
        ),
        "anatomy": (
            "<h3>Estructura</h3>"
            "<p>El aire entra por la tráquea, que se divide en dos bronquios principales "
            "(uno por pulmón) y luego se ramifica una y otra vez, como las ramas de un "
            "árbol, en bronquios cada vez más pequeños y después bronquiolos. El pulmón "
            "derecho tiene tres lóbulos y el izquierdo solo dos, porque le cede espacio "
            "al corazón. Una membrana doble llamada pleura envuelve cada pulmón y lo "
            "separa de la pared torácica, permitiendo que se deslice al respirar.</p>"
            "<h3>Dónde ocurre el intercambio de gases</h3>"
            "<p>Cada bronquiolo termina en un racimo de sacos diminutos llamados alvéolos "
            "— entre 300 y 500 millones en total — rodeados por una red de capilares "
            "sanguíneos. Sus paredes son tan delgadas (una sola célula) que el oxígeno "
            "pasa directo a la sangre y el dióxido de carbono sale de ella, en cuestión "
            "de una fracción de segundo. Esa superficie total de intercambio, si se "
            "desdoblara, cubriría casi una cancha de tenis.</p>"
            "<h3>Cómo se mueve el aire</h3>"
            "<p>Los pulmones no tienen músculo propio para expandirse: el diafragma (un "
            "músculo en forma de cúpula bajo ellos) se contrae y baja, y los músculos "
            "intercostales expanden la caja torácica, generando una presión negativa que "
            "\"succiona\" el aire hacia adentro. El ritmo de la respiración lo controla "
            "automáticamente el tronco encefálico, que mide el nivel de CO2 en la sangre "
            "mucho más que el de oxígeno.</p>"
            "<h3>Cuando algo falla</h3>"
            "<p>El <b>asma</b> es una inflamación que estrecha los bronquios y dificulta "
            "sacar el aire. La <b>bronquitis</b> y la <b>neumonía</b> son infecciones o "
            "inflamaciones de las vías respiratorias o de los propios alvéolos, que se "
            "llenan de moco o líquido. La <b>EPOC</b> (enfermedad pulmonar obstructiva "
            "crónica), ligada casi siempre al tabaco, destruye poco a poco las paredes "
            "de los alvéolos y reduce la superficie disponible para respirar.</p>"
        ),
        "threshold_native": -320,
        "threshold_below": True,
        "threshold_label": "-320 HU (aire = menor que el umbral)",
        "fun_facts": [
            "Frecuencia respiratoria en reposo: 12–20 respiraciones por minuto en un adulto.",
            "Capacidad pulmonar total: alrededor de 6 litros de aire.",
            "Si se desdoblara toda la superficie de intercambio alveolar, cubriría un área similar a una cancha de tenis (~70 m²).",
            "El pulmón derecho es más grande que el izquierdo porque el corazón ocupa parte del espacio del lado izquierdo del tórax.",
            "Condiciones comunes: asma, bronquitis, neumonía, EPOC (enfermedad pulmonar obstructiva crónica).",
        ],
        "quiz": [
            {"q": "¿Cuántas respiraciones por minuto son normales en reposo para un adulto?",
             "options": ["12–20", "40–60", "2–5", "80–100"], "correct": "12–20",
             "explain": "En reposo, un adulto respira típicamente entre 12 y 20 veces por minuto."},
            {"q": "¿Por qué el pulmón derecho tiene tres lóbulos y el izquierdo solo dos?",
             "options": ["Por el tamaño del hígado", "Porque el corazón ocupa espacio del lado izquierdo del tórax", "Por asimetría genética aleatoria", "Porque el izquierdo deja de crecer antes"],
             "correct": "Porque el corazón ocupa espacio del lado izquierdo del tórax",
             "explain": "El corazón se ubica hacia el lado izquierdo del tórax, así que el pulmón izquierdo cede espacio y tiene un lóbulo menos."},
            {"q": "Si se desdoblara toda la superficie de intercambio alveolar, ¿a qué se parecería en tamaño?",
             "options": ["Una cancha de tenis", "Una hoja de papel carta", "Una alberca olímpica", "Un campo de fútbol"],
             "correct": "Una cancha de tenis",
             "explain": "Los ~300–500 millones de alvéolos suman cerca de 70 m² de superficie — parecido a una cancha de tenis."},
            {"q": "¿Cuál de estas NO es una enfermedad pulmonar común?",
             "options": ["Asma", "Neumonía", "Cirrosis", "EPOC"], "correct": "Cirrosis",
             "explain": "La cirrosis es una enfermedad del hígado, no de los pulmones."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">'
            '<line x1="160" y1="8" x2="160" y2="70" stroke="var(--text-dim)" stroke-width="9"/>'
            '<text x="176" y="42" font-size="11" fill="var(--text-dim)">Tráquea</text>'
            '<line x1="160" y1="70" x2="112" y2="102" stroke="var(--text-dim)" stroke-width="6"/>'
            '<line x1="160" y1="70" x2="208" y2="102" stroke="var(--text-dim)" stroke-width="6"/>'
            '<text x="58" y="96" font-size="9" fill="var(--text-dim)">Bronquio izq.</text>'
            '<text x="220" y="96" font-size="9" fill="var(--text-dim)">Bronquio der.</text>'
            '<path d="M100,102 C42,112 30,180 55,228 C75,258 122,254 130,220 L130,106 Z" fill="#e8b4b8" fill-opacity="0.9" stroke="var(--border)"/>'
            '<line x1="58" y1="150" x2="128" y2="150" stroke="var(--bg)" stroke-width="3"/>'
            '<line x1="53" y1="195" x2="128" y2="195" stroke="var(--bg)" stroke-width="3"/>'
            '<text x="90" y="132" font-size="9" text-anchor="middle" fill="#3a2a2c">Lób. superior</text>'
            '<text x="88" y="175" font-size="9" text-anchor="middle" fill="#3a2a2c">Lób. medio</text>'
            '<text x="90" y="218" font-size="9" text-anchor="middle" fill="#3a2a2c">Lób. inferior</text>'
            '<text x="88" y="272" font-size="10" text-anchor="middle" fill="var(--text-dim)">Pulmón derecho</text>'
            '<path d="M220,102 C278,112 290,180 265,228 C245,258 198,254 190,220 L190,106 Z" fill="#e8b4b8" fill-opacity="0.9" stroke="var(--border)"/>'
            '<line x1="192" y1="172" x2="262" y2="172" stroke="var(--bg)" stroke-width="3"/>'
            '<text x="230" y="145" font-size="9" text-anchor="middle" fill="#3a2a2c">Lób. superior</text>'
            '<text x="228" y="200" font-size="9" text-anchor="middle" fill="#3a2a2c">Lób. inferior</text>'
            '<text x="230" y="272" font-size="10" text-anchor="middle" fill="var(--text-dim)">Pulmón izquierdo</text>'
            '</svg><div class="diagram-card-label">Vías aéreas y lóbulos de cada pulmón</div></div>'
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 220 210" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="110" cy="100" r="52" fill="#e8b4b8" fill-opacity="0.45" stroke="var(--border)"/>'
            '<circle cx="110" cy="100" r="52" fill="none" stroke="#c0392b" stroke-width="4" stroke-dasharray="10 7" opacity="0.85"/>'
            '<circle cx="110" cy="100" r="30" fill="var(--bg)" fill-opacity="0.35"/>'
            '<text x="110" y="104" font-size="9" text-anchor="middle" fill="var(--text-dim)">alvéolo</text>'
            '<path d="M18,60 L60,84" stroke="#3d8fd6" stroke-width="2.5" marker-end="url(#lungArrowO2)"/>'
            '<text x="6" y="54" font-size="11" fill="#3d8fd6">O&#8322;</text>'
            '<path d="M160,140 L120,116" stroke="#c0392b" stroke-width="2.5" marker-end="url(#lungArrowCO2)"/>'
            '<text x="164" y="152" font-size="11" fill="#c0392b">CO&#8322;</text>'
            '<defs>'
            '<marker id="lungArrowO2" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#3d8fd6"/></marker>'
            '<marker id="lungArrowCO2" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#c0392b"/></marker>'
            '</defs>'
            '</svg><div class="diagram-card-label">Un alvéolo envuelto en capilares: así pasa el O&#8322; a la sangre y el CO&#8322; sale de ella</div></div>'
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
    "heart": {
        "label": "Corazón",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "study_type": "Micro-CT sincrotrón (ex-vivo)",
        "orientation_note": (
            "Este espécimen ex-vivo no tiene metadatos de orientación del paciente — "
            "fue montado en el tubo del escáner de la forma que resultó conveniente. "
            "Los botones Ant/Post/Izq/Der son una vista de exhibición fija, no "
            "direcciones anatómicas verificadas. Sup/Inf sí están calibrados sobre un "
            "dato real y específico de este órgano: el eje ápex–base detectado "
            "geométricamente (el ápex, la punta más alejada del centro de la malla, "
            "se muestra hacia \"Inf\")."
        ),
        "color_hex": "#c0392b",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (LADAF-2021-17, "
            "resolución 169.36µm) del proyecto ESRF Human Organ Atlas / HiP-CT — "
            "tomografía sincrotrón de contraste de fase, no una tomografía clínica."
        ),
        "caveat": (
            "Este pipeline también admite tomografía clínica (in-vivo) mediante un "
            "level set sensible a bordes, usado porque la CT clínica sin contraste "
            "carece del contraste de tejido blando que sí tiene este escaneo ex-vivo. "
            "El volumen reconstruido refleja un espécimen fijado/preservado, más "
            "pequeño que un corazón vivo — esperado, no un error."
        ),
        "anatomy": (
            "<h3>Estructura</h3>"
            "<p>El corazón tiene cuatro cámaras: dos aurículas arriba (reciben sangre) y "
            "dos ventrículos abajo (la expulsan). Entre ellas hay cuatro válvulas de una "
            "sola vía — tricúspide, pulmonar, mitral y aórtica — que se abren y cierran "
            "con cada latido para que la sangre solo avance en un sentido; el sonido "
            "\"lub-dub\" del latido es justamente el golpe de cierre de esas válvulas. "
            "Un tabique muscular separa por completo el lado derecho del izquierdo, y "
            "la pared del ventrículo izquierdo es mucho más gruesa porque debe bombear "
            "sangre a todo el cuerpo, mientras el derecho solo la envía a los pulmones.</p>"
            "<h3>Dos circuitos en un solo bombeo</h3>"
            "<p>El lado derecho recibe sangre pobre en oxígeno del cuerpo y la manda a "
            "los pulmones (circuito pulmonar); el lado izquierdo recibe esa sangre ya "
            "oxigenada y la impulsa a todo el organismo a través de la aorta (circuito "
            "sistémico). Ambos circuitos laten de forma sincronizada en cada ciclo "
            "cardíaco, aunque son anatómicamente independientes.</p>"
            "<h3>Qué lo hace latir</h3>"
            "<p>El corazón genera su propio impulso eléctrico: nace en el nodo sinusal "
            "(la \"pila\" natural, en la aurícula derecha), pasa al nodo auriculoventricular "
            "y baja por el haz de His hasta las fibras de Purkinje, que hacen que los "
            "ventrículos se contraigan casi al unísono. Por eso un corazón extraído del "
            "cuerpo puede seguir latiendo un tiempo si se mantiene con oxígeno y nutrientes.</p>"
            "<h3>Cuando algo falla</h3>"
            "<p>La <b>hipertensión</b> obliga al corazón a bombear contra más resistencia "
            "de la que debería, engrosando el músculo con el tiempo. La <b>enfermedad "
            "coronaria</b> ocurre cuando las arterias que alimentan al propio músculo "
            "cardíaco se obstruyen con placas de grasa — si se bloquean del todo, esa "
            "zona del músculo muere (infarto). Una <b>arritmia</b> es una falla en el "
            "sistema eléctrico que altera el ritmo, y la <b>insuficiencia cardíaca</b> es "
            "cuando el corazón ya no logra bombear con la fuerza suficiente para las "
            "necesidades del cuerpo.</p>"
        ),
        "threshold_native": 27000,
        "threshold_below": False,
        "threshold_label": "27000 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Frecuencia cardiaca en reposo: 60–100 latidos por minuto en un adulto (deportistas de resistencia pueden bajar de 40–50).",
            "Late en promedio unas 100,000 veces al día — más de 2,500 millones de veces en una vida.",
            "Bombea alrededor de 5 litros de sangre por minuto en reposo.",
            "Todos los vasos sanguíneos del cuerpo, estirados en línea, medirían más de 100,000 km.",
            "Condiciones comunes: hipertensión arterial, enfermedad coronaria, arritmias, insuficiencia cardiaca.",
        ],
        "quiz": [
            {"q": "¿Cuál es la frecuencia cardiaca normal en reposo de un adulto?",
             "options": ["60–100 lpm", "20–40 lpm", "150–180 lpm", "5–10 lpm"], "correct": "60–100 lpm",
             "explain": "60–100 latidos por minuto es el rango normal en reposo (deportistas de resistencia pueden bajar de eso)."},
            {"q": "¿Qué estructura genera el impulso eléctrico natural del corazón?",
             "options": ["El nodo sinusal", "El diafragma", "La vena porta", "El cerebelo"], "correct": "El nodo sinusal",
             "explain": "El nodo sinusal, en la aurícula derecha, es el marcapasos natural del corazón."},
            {"q": "¿Cuántos litros de sangre bombea el corazón por minuto en reposo, aproximadamente?",
             "options": ["5 litros", "50 litros", "0.5 litros", "20 litros"], "correct": "5 litros",
             "explain": "En reposo, el corazón bombea alrededor de 5 litros de sangre por minuto."},
            {"q": "¿Cuántas cámaras tiene el corazón?",
             "options": ["2", "3", "4", "6"], "correct": "4",
             "explain": "Dos aurículas arriba y dos ventrículos abajo — cuatro cámaras en total."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">'
            '<rect x="98" y="24" width="20" height="32" rx="6" fill="#8aa0c9"/>'
            '<text x="108" y="18" font-size="10" text-anchor="middle" fill="var(--text-dim)">Art. pulmonar</text>'
            '<rect x="202" y="24" width="20" height="32" rx="6" fill="#c0392b"/>'
            '<text x="212" y="18" font-size="10" text-anchor="middle" fill="var(--text-dim)">Aorta</text>'
            '<rect x="60" y="54" width="200" height="180" rx="26" fill="#c0392b" fill-opacity="0.82" stroke="var(--border)" stroke-width="2"/>'
            '<line x1="160" y1="54" x2="160" y2="234" stroke="var(--bg)" stroke-width="5"/>'
            '<line x1="60" y1="150" x2="260" y2="150" stroke="var(--bg)" stroke-width="5"/>'
            '<text x="110" y="102" font-size="11" text-anchor="middle" fill="#fff">Aurícula<tspan x="110" dy="13">derecha</tspan></text>'
            '<text x="210" y="102" font-size="11" text-anchor="middle" fill="#fff">Aurícula<tspan x="210" dy="13">izquierda</tspan></text>'
            '<text x="110" y="192" font-size="11" text-anchor="middle" fill="#fff">Ventrículo<tspan x="110" dy="13">derecho</tspan></text>'
            '<text x="210" y="192" font-size="11" text-anchor="middle" fill="#fff">Ventrículo<tspan x="210" dy="13">izquierdo</tspan></text>'
            '</svg><div class="diagram-card-label">Las cuatro cámaras y los grandes vasos</div></div>'
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 240 260" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M120,36 C64,8 14,48 18,98 C22,150 78,192 120,232 C162,192 218,150 222,98 C226,48 176,8 120,36 Z" fill="#c0392b" fill-opacity="0.18" stroke="var(--border)" stroke-width="1.5"/>'
            '<path d="M150,66 Q124,104 122,118 L122,178 M122,178 Q95,205 70,190 M122,178 Q149,205 174,190" fill="none" stroke="#f2a53c" stroke-width="3" stroke-linecap="round"/>'
            '<circle cx="150" cy="66" r="7" fill="#f2a53c"/><text x="163" y="63" font-size="11" fill="var(--text-dim)">1</text>'
            '<circle cx="122" cy="118" r="7" fill="#f2a53c"/><text x="135" y="123" font-size="11" fill="var(--text-dim)">2</text>'
            '<circle cx="122" cy="178" r="6" fill="#f2a53c"/><text x="132" y="183" font-size="11" fill="var(--text-dim)">3</text>'
            '<circle cx="70" cy="190" r="5" fill="#f2a53c"/><circle cx="174" cy="190" r="5" fill="#f2a53c"/>'
            '<text x="70" y="212" font-size="10" text-anchor="middle" fill="var(--text-dim)">4</text><text x="174" y="212" font-size="10" text-anchor="middle" fill="var(--text-dim)">4</text>'
            '</svg><div class="diagram-card-label">Sistema eléctrico: 1 nodo sinusal · 2 nodo AV · 3 haz de His · 4 fibras de Purkinje</div></div>'
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
    "liver": {
        "label": "Hígado",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "study_type": "Micro-CT sincrotrón (ex-vivo)",
        "orientation_note": (
            "Este espécimen ex-vivo no tiene metadatos de orientación del paciente — "
            "fue montado en el tubo del escáner de la forma que resultó conveniente, "
            "así que los botones Ant/Post/Izq/Der/Sup/Inf son solo una vista de "
            "exhibición fija, no direcciones anatómicas verificadas. Las etiquetas de "
            "\"lóbulo mayor/menor\" sobre el modelo sí están calculadas de forma real, "
            "a partir de la partición de volumen de la malla — no de la orientación."
        ),
        "color_hex": "#b9793f",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (LADAF-2021-17, "
            "resolución 180.48µm) del proyecto ESRF Human Organ Atlas / HiP-CT."
        ),
        "caveat": (
            "Este pipeline también admite tomografía clínica (in-vivo) mediante "
            "crecimiento de región con semilla (ConfidenceConnected). El volumen "
            "ex-vivo puede caer fuera del rango fisiológico en vivo por la misma razón "
            "que el corazón: un espécimen fijado no tiene el mismo volumen que el "
            "órgano en un paciente vivo."
        ),
        "anatomy": (
            "<h3>Estructura</h3>"
            "<p>El hígado es el órgano sólido interno más grande del cuerpo, ubicado en "
            "el cuadrante superior derecho del abdomen, justo bajo el diafragma. Tiene "
            "dos lóbulos principales muy asimétricos — el derecho mucho más grande que "
            "el izquierdo — y los cirujanos lo dividen además en ocho segmentos "
            "independientes (segmentos de Couinaud), cada uno con su propio riego "
            "sanguíneo, lo que permite operar o incluso trasplantar solo una parte.</p>"
            "<h3>Una doble entrada de sangre</h3>"
            "<p>A diferencia de casi todos los órganos, el hígado recibe sangre de dos "
            "fuentes distintas: la vena porta (cerca del 75%), que trae sangre rica en "
            "nutrientes directo desde el intestino, y la arteria hepática (25%), que "
            "trae sangre oxigenada como cualquier otro órgano. Ambas se mezclan dentro "
            "de unidades microscópicas llamadas lobulillos hepáticos, donde los "
            "hepatocitos (las células del hígado) procesan la sangre antes de que "
            "salga por las venas hepáticas hacia la circulación general.</p>"
            "<h3>Función</h3>"
            "<p>Es la fábrica química del cuerpo: sintetiza proteínas de la sangre como "
            "la albúmina y los factores de coagulación, almacena glucosa en forma de "
            "glucógeno para liberarla cuando hace falta energía, neutraliza toxinas y "
            "medicamentos, y produce la bilis que se almacena en la vesícula biliar y "
            "ayuda a digerir las grasas en el intestino. En total se le atribuyen más "
            "de 500 funciones metabólicas distintas.</p>"
            "<h3>Capacidad de regenerarse</h3>"
            "<p>Es el único órgano interno humano capaz de regenerar su tamaño "
            "funcional incluso después de perder hasta el 70% de su tejido — una "
            "propiedad que hace posible el trasplante de hígado de donante vivo, donde "
            "tanto la porción donada como la que queda en el donante vuelven a crecer.</p>"
            "<h3>Cuando algo falla</h3>"
            "<p>El <b>hígado graso</b> es la acumulación de grasa en los hepatocitos, "
            "muchas veces sin síntomas al inicio. La <b>hepatitis</b> es la inflamación "
            "del hígado, causada por virus, alcohol u otras sustancias. Si el daño se "
            "repite durante años, el tejido sano se reemplaza por cicatrices "
            "(<b>cirrosis</b>), lo que reduce progresivamente sus cientos de funciones.</p>"
        ),
        "threshold_native": 18300,
        "threshold_below": False,
        "threshold_label": "18300 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Es el único órgano interno humano capaz de regenerarse: puede recuperar su tamaño funcional incluso tras perder hasta el 70% de su tejido.",
            "Realiza más de 500 funciones metabólicas distintas conocidas.",
            "Toda la sangre del cuerpo pasa por el hígado aproximadamente cada 2–3 minutos para ser filtrada.",
            "Condiciones comunes: hígado graso, hepatitis, cirrosis.",
        ],
        "quiz": [
            {"q": "¿Qué porcentaje de su tejido puede perder el hígado y aun así regenerarse?",
             "options": ["Hasta 70%", "Hasta 10%", "Hasta 95%", "No se regenera"], "correct": "Hasta 70%",
             "explain": "El hígado puede recuperar su tamaño funcional incluso tras perder hasta el 70% de su tejido."},
            {"q": "¿De dónde recibe la mayor parte de su sangre el hígado?",
             "options": ["La vena porta (desde el intestino)", "El corazón directamente", "Los riñones", "Los pulmones"],
             "correct": "La vena porta (desde el intestino)",
             "explain": "Cerca del 75% de la sangre que recibe el hígado llega por la vena porta, desde el intestino."},
            {"q": "¿Cuántas funciones metabólicas distintas se le atribuyen al hígado?",
             "options": ["Más de 500", "Cerca de 10", "Exactamente 100", "Menos de 5"], "correct": "Más de 500",
             "explain": "Se le conocen más de 500 funciones metabólicas distintas."},
            {"q": "¿En cuántos segmentos independientes dividen los cirujanos al hígado?",
             "options": ["8", "2", "20", "4"], "correct": "8",
             "explain": "Los segmentos de Couinaud dividen el hígado en 8 partes, cada una con su propio riego sanguíneo."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="-40 0 360 280" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M40,85 C40,62 85,50 145,54 C220,58 280,80 280,132 C280,182 218,212 148,206 C88,201 40,168 40,122 Z" fill="#b9793f" fill-opacity="0.88" stroke="var(--border)" stroke-width="2"/>'
            '<line x1="172" y1="58" x2="150" y2="204" stroke="var(--bg)" stroke-width="4"/>'
            '<text x="220" y="128" font-size="12" text-anchor="middle" fill="#fff">Lóbulo derecho</text>'
            '<text x="100" y="98" font-size="11" text-anchor="middle" fill="#fff">Lóbulo<tspan x="100" dy="13">izquierdo</tspan></text>'
            '<ellipse cx="192" cy="192" rx="13" ry="9" fill="#6b8e4e"/>'
            '<text x="192" y="222" font-size="9" text-anchor="middle" fill="var(--text-dim)">Vesícula biliar</text>'
            '<line x1="60" y1="150" x2="16" y2="150" stroke="var(--text-dim)" stroke-width="2"/>'
            '<text x="14" y="145" font-size="9" text-anchor="end" fill="var(--text-dim)">Vena porta</text>'
            '</svg><div class="diagram-card-label">Los dos lóbulos principales y la vesícula biliar</div></div>'
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 220 210" xmlns="http://www.w3.org/2000/svg">'
            '<polygon points="110,20 170,55 170,125 110,160 50,125 50,55" fill="#b9793f" fill-opacity="0.22" stroke="var(--border)"/>'
            '<circle cx="110" cy="90" r="16" fill="#b9793f"/>'
            '<text x="110" y="93" font-size="7.5" text-anchor="middle" fill="#fff">v. central</text>'
            '<circle cx="50" cy="55" r="5" fill="#3d8fd6"/><circle cx="58" cy="48" r="5" fill="#c0392b"/><circle cx="46" cy="46" r="5" fill="#6b8e4e"/>'
            '<text x="14" y="34" font-size="9" fill="var(--text-dim)">Tríada portal</text>'
            '</svg><div class="diagram-card-label">Un lobulillo hepático: sangre de la vena porta (azul) y la arteria hepática (rojo) se mezclan y drenan a la vena central; la bilis (verde) sale por el conducto biliar</div></div>'
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
    "kidneys": {
        "label": "Riñones",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "study_type": "Micro-CT sincrotrón (ex-vivo)",
        "orientation_note": (
            "Este espécimen ex-vivo (un riñón individual excisado, no el par "
            "bilateral) no tiene metadatos de orientación del paciente, así que los "
            "botones Ant/Post/Izq/Der/Sup/Inf son solo una vista de exhibición fija. "
            "El hilio renal marcado sobre el modelo se detecta por concavidad real de "
            "la malla, pero en este espécimen esa concavidad no se distingue con "
            "certeza de otras hendiduras de la superficie — trátalo como aproximado."
        ),
        "color_hex": "#a8447a",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (K292, resolución "
            "163.52µm) del proyecto ESRF Human Organ Atlas / HiP-CT — un único riñón "
            "excisado, no un par bilateral in-situ."
        ),
        "caveat": (
            "Este pipeline también admite tomografía clínica (in-vivo) mediante un "
            "level set bilateral (busca ambos riñones a la vez). El espécimen real "
            "usado aquí es un solo riñón, así que la variante ex-vivo simplifica esa "
            "lógica bilateral: hay exactamente un objeto que encontrar."
        ),
        "anatomy": (
            "<h3>Estructura</h3>"
            "<p>Cada riñón tiene forma de frijol y se organiza en dos grandes zonas: la "
            "corteza renal (la capa externa) y la médula renal (la interna, dividida en "
            "pirámides). La orina que se va formando gotea desde las pirámides hacia la "
            "pelvis renal, una especie de embudo colector que conecta con el uréter, el "
            "tubo que la lleva hasta la vejiga. El hilio renal es el punto por donde "
            "entran y salen los vasos sanguíneos, los nervios y el propio uréter.</p>"
            "<h3>La nefrona: la unidad de filtrado</h3>"
            "<p>Cada riñón contiene cerca de un millón de nefronas microscópicas, y cada "
            "una hace el trabajo completo por sí sola. Empieza en el glomérulo, un ovillo "
            "de capilares donde el agua y las moléculas pequeñas de la sangre se filtran "
            "hacia una cápsula (cápsula de Bowman); ese filtrado inicial recorre un largo "
            "túbulo (el asa de Henle y los túbulos contorneados) que va recuperando el "
            "agua, la glucosa y las sales que el cuerpo todavía necesita, y deja pasar "
            "el resto — que se convierte en orina — hacia el conducto colector.</p>"
            "<h3>Más que un filtro</h3>"
            "<p>Además de eliminar desechos, los riñones regulan la presión arterial "
            "(liberando una hormona llamada renina cuando detectan que la presión baja), "
            "producen la hormona que estimula la médula ósea a fabricar glóbulos rojos "
            "(eritropoyetina), activan la vitamina D, y mantienen estable el balance de "
            "sodio, potasio y otros electrolitos indispensables para el funcionamiento "
            "de los músculos y las neuronas.</p>"
            "<h3>Cuando algo falla</h3>"
            "<p>Los <b>cálculos renales</b> (piedras) son cristales que se forman cuando "
            "hay demasiada concentración de ciertas sales en la orina. Las "
            "<b>infecciones urinarias</b> pueden subir desde la vejiga hasta el propio "
            "riñón. La <b>enfermedad renal crónica</b> es la pérdida progresiva y a "
            "veces silenciosa de nefronas funcionales; cuando ya queda muy poca función, "
            "la diálisis hace artificialmente el trabajo de filtrado que el riñón ya no "
            "puede hacer.</p>"
        ),
        "threshold_native": 44300,
        "threshold_below": False,
        "threshold_label": "44300 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Filtran alrededor de 180 litros de sangre al día, aunque solo producen 1–2 litros de orina.",
            "Cada riñón contiene cerca de un millón de nefronas, sus unidades de filtrado.",
            "Es posible llevar una vida normal con un solo riñón funcional.",
            "Condiciones comunes: cálculos renales (piedras), infecciones urinarias, enfermedad renal crónica.",
        ],
        "quiz": [
            {"q": "¿Cuántos litros de sangre filtran los riñones al día, aproximadamente?",
             "options": ["180 litros", "18 litros", "1800 litros", "5 litros"], "correct": "180 litros",
             "explain": "Filtran unos 180 litros de sangre al día, aunque solo producen 1–2 litros de orina."},
            {"q": "¿Cuántas nefronas tiene aproximadamente cada riñón?",
             "options": ["Un millón", "Cien", "Mil millones", "Diez mil"], "correct": "Un millón",
             "explain": "Cada riñón contiene cerca de un millón de nefronas, su unidad de filtrado."},
            {"q": "¿Es posible vivir con un solo riñón funcional?",
             "options": ["Sí, con vida normal", "No, es imposible", "Solo unos meses", "Solo en la infancia"],
             "correct": "Sí, con vida normal",
             "explain": "Es posible llevar una vida normal con un solo riñón funcional."},
            {"q": "¿Dónde comienza el filtrado de la sangre dentro de una nefrona?",
             "options": ["En el glomérulo", "En el uréter", "En la vejiga", "En la vena porta"], "correct": "En el glomérulo",
             "explain": "El glomérulo, un ovillo de capilares, es donde comienza el filtrado inicial de la sangre."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M120,40 C182,28 232,60 230,120 C229,150 200,150 200,180 C199,222 168,252 128,246 C88,240 68,198 75,150 C81,100 70,52 120,40 Z" fill="#a8447a" fill-opacity="0.88" stroke="var(--border)" stroke-width="2"/>'
            '<path d="M138,70 C174,64 206,90 200,130 C197,155 176,155 172,176 C167,206 146,220 124,214 C102,208 92,183 98,150 C104,110 104,80 138,70 Z" fill="#c97ba8" fill-opacity="0.95"/>'
            '<ellipse cx="150" cy="145" rx="20" ry="28" fill="#7a2f57"/>'
            '<line x1="150" y1="173" x2="150" y2="250" stroke="var(--text-dim)" stroke-width="6"/>'
            '<text x="250" y="55" font-size="10" fill="var(--text-dim)">Corteza renal</text>'
            '<line x1="210" y1="62" x2="246" y2="58" stroke="var(--text-dim)" stroke-width="1"/>'
            '<text x="250" y="98" font-size="10" fill="var(--text-dim)">Médula renal</text>'
            '<line x1="185" y1="105" x2="246" y2="96" stroke="var(--text-dim)" stroke-width="1"/>'
            '<text x="250" y="142" font-size="10" fill="var(--text-dim)">Pelvis renal</text>'
            '<line x1="168" y1="145" x2="246" y2="140" stroke="var(--text-dim)" stroke-width="1"/>'
            '<text x="250" y="186" font-size="10" fill="var(--text-dim)">Hilio renal</text>'
            '<line x1="202" y1="176" x2="246" y2="184" stroke="var(--text-dim)" stroke-width="1"/>'
            '<text x="155" y="272" font-size="10" text-anchor="middle" fill="var(--text-dim)">Uréter</text>'
            '</svg><div class="diagram-card-label">Corteza, médula y pelvis renal de un riñón</div></div>'
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M40,30 Q50,15 65,25 Q78,15 85,32 Q95,45 80,55 Q70,65 55,58 Q40,50 40,30 Z" fill="#a8447a" fill-opacity="0.55" stroke="var(--border)"/>'
            '<text x="6" y="18" font-size="9" fill="var(--text-dim)">Glomérulo</text>'
            '<path d="M62,60 C62,80 30,85 30,110 C30,140 30,170 70,170 C110,170 110,140 110,110 C110,90 90,85 90,65" fill="none" stroke="#c97ba8" stroke-width="4"/>'
            '<text x="0" y="126" font-size="9" fill="var(--text-dim)">Asa de<tspan x="0" dy="10">Henle</tspan></text>'
            '<line x1="70" y1="170" x2="70" y2="198" stroke="var(--text-dim)" stroke-width="4" marker-end="url(#kidArrow)"/>'
            '<text x="78" y="205" font-size="9" fill="var(--text-dim)">a la orina</text>'
            '<defs><marker id="kidArrow" markerWidth="8" markerHeight="8" refX="4" refY="7" orient="auto"><path d="M0,0 L8,0 L4,8 Z" fill="var(--text-dim)"/></marker></defs>'
            '</svg><div class="diagram-card-label">Una nefrona: el glomérulo filtra la sangre y el túbulo recupera lo que el cuerpo todavía necesita</div></div>'
        ),
        "initial_theta": 3.14,
        "initial_phi": 1.15,
    },
    "brain": {
        "label": "Cerebro",
        "algo": "Umbral + componente conectado (ex-vivo)",
        "study_type": "Micro-CT sincrotrón (ex-vivo)",
        "orientation_note": (
            "Este espécimen ex-vivo no tiene metadatos de orientación del paciente. "
            "El modelo se rotó para mostrar la bóveda craneal lisa hacia arriba (en "
            "vez de la base irregular), una corrección puramente de exhibición hecha "
            "a partir de la forma real de este espécimen — no una reconstrucción de "
            "su orientación real en el cuerpo. Por eso \"Hemisferio 1/2\" no lleva "
            "etiqueta de izquierdo/derecho: externamente son casi simétricos y no hay "
            "forma honesta de distinguirlos solo con esta malla."
        ),
        "color_hex": "#c9a0dc",
        "source_note": (
            "Reconstruido a partir de un espécimen ex-vivo real (LADAF-2021-17, "
            "resolución 169.6µm) del proyecto ESRF Human Organ Atlas / HiP-CT."
        ),
        "caveat": (
            "Este proyecto NO incluye un pipeline clínico de CT/MRI para cerebro: la "
            "segmentación de tejido cerebral (skull-stripping + parénquima) a partir de "
            "imagen clínica es un problema bien estudiado por sí mismo, y construir uno "
            "sin datos etiquetados contra los cuales validarlo no cumpliría el estándar "
            "de rigor de este proyecto. El cerebro solo se reconstruye a partir de "
            "tomografía sincrotrón ex-vivo."
        ),
        "anatomy": (
            "<h3>Estructura</h3>"
            "<p>La corteza cerebral —la capa externa, muy plegada, de \"materia gris\"— "
            "se divide en cuatro lóbulos por lado: el frontal (razonamiento, "
            "planificación, movimiento voluntario), el parietal (procesa el tacto y la "
            "orientación espacial), el temporal (audición y memoria) y el occipital "
            "(visión). Debajo de la corteza está la sustancia blanca, formada por los "
            "cables (axones) que conectan unas zonas con otras; el cuerpo calloso es el "
            "haz de fibras que comunica el hemisferio izquierdo con el derecho.</p>"
            "<h3>Cerebelo y tronco encefálico</h3>"
            "<p>Debajo y detrás de los hemisferios cerebrales está el cerebelo, que "
            "afina la coordinación motora, el equilibrio y la precisión de los "
            "movimientos aunque no los origine. El tronco encefálico (bulbo raquídeo, "
            "protuberancia y mesencéfalo) conecta el cerebro con la médula espinal y "
            "controla funciones automáticas de las que ni siquiera somos conscientes: "
            "la respiración, el ritmo cardíaco y la presión arterial.</p>"
            "<h3>Cómo se comunican las neuronas</h3>"
            "<p>El cerebro humano tiene alrededor de 86 mil millones de neuronas, cada "
            "una conectada con miles de otras a través de sinapsis. La señal viaja como "
            "un impulso eléctrico dentro de la neurona — hasta 120 metros por segundo en "
            "las fibras más rápidas — y al llegar al final salta a la siguiente neurona "
            "mediante mensajeros químicos llamados neurotransmisores.</p>"
            "<h3>Cómo está protegido</h3>"
            "<p>Tres membranas (las meninges) envuelven el cerebro, y entre ellas circula "
            "el líquido cefalorraquídeo, que lo amortigua como un cojín líquido dentro "
            "del cráneo. Además, una \"barrera hematoencefálica\" filtra qué sustancias "
            "de la sangre pueden entrar al tejido cerebral, protegiéndolo de toxinas.</p>"
            "<h3>Cuando algo falla</h3>"
            "<p>Una <b>migraña</b> es un dolor de cabeza intenso ligado a cambios en los "
            "vasos sanguíneos y la actividad neuronal. La <b>epilepsia</b> ocurre cuando "
            "grupos de neuronas disparan de forma descontrolada y sincronizada. Un "
            "<b>ACV (accidente cerebrovascular)</b> sucede cuando se corta el riego "
            "sanguíneo a una zona del cerebro y esas neuronas empiezan a morir en "
            "minutos. El <b>Alzheimer</b> y el <b>Parkinson</b> son enfermedades "
            "neurodegenerativas en las que ciertos grupos de neuronas se van perdiendo "
            "de forma progresiva con la edad.</p>"
        ),
        "threshold_native": 5000,
        "threshold_below": False,
        "threshold_label": "5000 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Consume cerca del 20% de la energía total del cuerpo, aunque representa solo ~2% del peso corporal.",
            "Contiene aproximadamente 86 mil millones de neuronas.",
            "Las señales nerviosas pueden viajar hasta 120 metros por segundo.",
            "El propio tejido cerebral no tiene receptores de dolor — por eso algunas cirugías cerebrales se hacen con el paciente consciente.",
            "Condiciones comunes: migraña, epilepsia; en edad avanzada, Alzheimer y Parkinson.",
        ],
        "quiz": [
            {"q": "¿Qué porcentaje de la energía del cuerpo consume el cerebro, aunque es solo ~2% del peso corporal?",
             "options": ["~20%", "~2%", "~50%", "~5%"], "correct": "~20%",
             "explain": "El cerebro consume cerca del 20% de la energía total del cuerpo."},
            {"q": "¿Aproximadamente cuántas neuronas tiene el cerebro humano?",
             "options": ["86 mil millones", "86 millones", "8.6 mil", "860 mil millones"], "correct": "86 mil millones",
             "explain": "Se estima que el cerebro humano contiene unos 86 mil millones de neuronas."},
            {"q": "¿Por qué algunas cirugías cerebrales se hacen con el paciente consciente?",
             "options": ["El tejido cerebral no tiene receptores de dolor", "Para que el paciente ayude a operar", "La anestesia no funciona en el cerebro", "Es un mito, nunca se hace"],
             "correct": "El tejido cerebral no tiene receptores de dolor",
             "explain": "El propio tejido cerebral no tiene receptores de dolor, así que puede operarse sin anestesia general en esa zona."},
            {"q": "¿Qué estructura controla funciones automáticas como la respiración y el ritmo cardiaco?",
             "options": ["El tronco encefálico", "El cerebelo", "La corteza cerebral", "El cuerpo calloso"],
             "correct": "El tronco encefálico",
             "explain": "El tronco encefálico conecta el cerebro con la médula espinal y regula funciones automáticas vitales."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 380 280" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M60,140 C55,90 100,50 170,50 C230,50 260,85 255,120 C275,125 280,150 265,165 C270,190 245,200 230,195 C220,220 180,230 155,220 C120,235 80,220 70,190 C45,185 40,155 60,140 Z" fill="#c9a0dc" fill-opacity="0.88" stroke="var(--border)" stroke-width="2"/>'
            '<path d="M78,150 Q95,118 132,113 Q104,140 104,168 Q82,175 78,150 Z" fill="none" stroke="var(--bg)" stroke-width="1.5" opacity="0.5"/>'
            '<text x="150" y="42" font-size="11" text-anchor="middle" fill="var(--text-dim)">Corteza cerebral</text>'
            '<ellipse cx="235" cy="175" rx="30" ry="20" fill="#8f6bb0"/>'
            '<text x="292" y="180" font-size="10" fill="var(--text-dim)">Cerebelo</text>'
            '<line x1="262" y1="176" x2="288" y2="178" stroke="var(--text-dim)" stroke-width="1"/>'
            '<rect x="185" y="195" width="18" height="45" rx="9" fill="#7a5599"/>'
            '<text x="220" y="258" font-size="10" fill="var(--text-dim)">Tronco encefálico</text>'
            '<line x1="198" y1="232" x2="222" y2="252" stroke="var(--text-dim)" stroke-width="1"/>'
            '<line x1="132" y1="113" x2="132" y2="88" stroke="var(--text-dim)" stroke-width="1"/>'
            '<text x="132" y="78" font-size="10" text-anchor="middle" fill="var(--text-dim)">Cuerpo calloso</text>'
            '</svg><div class="diagram-card-label">Corteza, cerebelo y tronco encefálico</div></div>'
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 240 170" xmlns="http://www.w3.org/2000/svg">'
            '<ellipse cx="55" cy="85" rx="24" ry="19" fill="#8f6bb0"/><text x="55" y="89" font-size="9" text-anchor="middle" fill="#fff">1</text>'
            '<path d="M35,72 L14,58 M32,85 L8,85 M35,98 L14,114 M48,66 L38,48" stroke="#8f6bb0" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            '<text x="10" y="40" font-size="10" fill="var(--text-dim)">2</text>'
            '<path d="M79,85 L165,85" stroke="#8f6bb0" stroke-width="3"/>'
            '<text x="120" y="78" font-size="10" text-anchor="middle" fill="var(--text-dim)">3</text>'
            '<path d="M165,85 L182,75 M165,85 L182,95" stroke="#8f6bb0" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            '<circle cx="184" cy="73" r="3" fill="#f2a53c"/><circle cx="190" cy="80" r="3" fill="#f2a53c"/><circle cx="184" cy="97" r="3" fill="#f2a53c"/>'
            '<path d="M205,60 L225,50 M205,85 L232,85 M205,110 L225,120" stroke="#5a3d78" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
            '<text x="200" y="45" font-size="10" fill="var(--text-dim)">4</text>'
            '</svg><div class="diagram-card-label">Una sinapsis entre dos neuronas: 1 soma · 2 dendritas · 3 axón · 4 neurotransmisores cruzando el espacio sináptico</div></div>'
        ),
        "initial_theta": 0.6,
        "initial_phi": 1.15,
    },
}


def build(payload: dict) -> str:
    viewer_data = {}
    for organ in ORGAN_ORDER:
        if organ not in payload:
            continue
        entry = payload[organ]
        viewer_data[organ] = {
            "mesh": entry["mesh"],
            "slices": entry["slices"],
            "metrics": entry["metrics"],
            "validation": entry["validation"],
        }

    available_organs = [o for o in ORGAN_ORDER if o in viewer_data]

    html = _TEMPLATE
    html = html.replace("__ORGAN_ORDER_JSON__", json.dumps(available_organs))
    html = html.replace("__ORGAN_META_JSON__", json.dumps({k: ORGAN_META[k] for k in available_organs}))
    html = html.replace("__VIEWER_DATA_JSON__", json.dumps(viewer_data))
    return html


_TEMPLATE = r"""<!doctype html>
<title>Medical3DReconstruction — Visor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #17181a; --surface: #1d1f22; --surface-raised: #26282c; --border: #35373b;
    --text: #e8e9eb; --text-dim: #9a9da2; --text-faint: #656870;
    --accent: #a5434b; --accent-soft: rgba(165,67,75,0.16); --accent-strong: #c0525b;
    --accent-ink: #f3e4e2;
    --warn: #c9974a; --ok: #5da868;
    --font-ui: "Inter", ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
    --font-serif: ui-serif, Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
    --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", "Consolas", monospace;
    --radius-sm: 3px; --radius-md: 4px; --radius-lg: 6px;
  }
  :root[data-theme="light"] {
    --bg: #f4f3f1; --surface: #ffffff; --surface-raised: #eceae6; --border: #d7d3cc;
    --text: #1c1b19; --text-dim: #5c574f; --text-faint: #938c80;
    --accent: #8c2f39; --accent-soft: rgba(140,47,57,0.09); --accent-strong: #6b232b;
    --accent-ink: #fbeeee;
  }
  @media (prefers-color-scheme: light) {
    :root:not([data-theme="dark"]) {
      --bg: #f4f3f1; --surface: #ffffff; --surface-raised: #eceae6; --border: #d7d3cc;
      --text: #1c1b19; --text-dim: #5c574f; --text-faint: #938c80;
      --accent: #8c2f39; --accent-soft: rgba(140,47,57,0.09); --accent-strong: #6b232b;
      --accent-ink: #fbeeee;
    }
  }
  * { box-sizing: border-box; }
  .hidden { display: none; }
  html, body { height: 100%; margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-ui); overflow: hidden; }
  body { display: flex; flex-direction: column; }
  header { display: flex; align-items: center; gap: 0.75rem; padding: 0.55rem 1rem; background: var(--surface-raised); border-bottom: 1px solid var(--border); flex-shrink: 0; }
  header .mark { width: 19px; height: 19px; flex-shrink: 0; color: var(--accent); }
  header h1 { font-family: var(--font-ui); font-size: 0.88rem; margin: 0; font-weight: 650; letter-spacing: -0.01em; white-space: nowrap; }
  header .spacer { flex: 1; }
  .topbar-divider { width: 1px; align-self: stretch; background: var(--border); margin: 0 0.15rem; }
  .topbar-study { display: flex; align-items: center; gap: 0.55rem; min-width: 0; }
  .topbar-study .study-name { font-size: 0.8rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 12rem; }
  .badge { display: inline-flex; align-items: center; gap: 0.32rem; font-size: 0.66rem; font-weight: 650; letter-spacing: 0.01em; padding: 0.16rem 0.5rem; border-radius: 999px; border: 1px solid var(--border); color: var(--text-dim); background: var(--surface); white-space: nowrap; }
  .badge-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .badge-dot.ok { background: var(--ok); }
  .badge-dot.warn { background: var(--warn); }
  .tab-switch { display: flex; gap: 0.15rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 0.18rem; }
  .tab-btn { display: inline-flex; align-items: center; gap: 0.32rem; font-size: 0.73rem; font-weight: 600; padding: 0.32rem 0.65rem; border-radius: var(--radius-sm); border: none; background: transparent; color: var(--text-dim); cursor: pointer; font-family: inherit; }
  .tab-btn svg { width: 13px; height: 13px; flex-shrink: 0; opacity: 0.85; }
  .tab-btn[aria-selected="true"] { background: var(--accent-soft); color: var(--text); }
  .icon-btn-flat { padding: 0.32rem 0.6rem; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); font-size: 0.7rem; cursor: pointer; font-family: inherit; }
  main { flex: 1; display: grid; grid-template-columns: 280px 1fr; min-height: 0; }
  main.hidden { display: none; }
  aside { border-right: 1px solid var(--border); background: var(--surface); overflow-y: auto; padding: 0.9rem; display: flex; flex-direction: column; gap: 0; }
  .panel-group { padding: 0.85rem 0; border-bottom: 1px solid var(--border); }
  .panel-group:first-child { padding-top: 0; }
  .panel-group:last-child { border-bottom: none; padding-bottom: 0; }
  .eyebrow { font-size: 0.64rem; font-weight: 650; letter-spacing: 0.07em; text-transform: uppercase; color: var(--text-faint); margin: 0 0 0.55rem; }
  .organ-list { display: flex; flex-direction: column; gap: 0.3rem; }
  .organ-btn { display: flex; align-items: center; gap: 0.5rem; text-align: left; padding: 0.45rem 0.55rem; border-radius: var(--radius-md); border: 1px solid var(--border); background: var(--surface-raised); color: var(--text); cursor: pointer; font-family: inherit; }
  .organ-btn[aria-pressed="true"] { border-color: var(--accent-strong); background: var(--accent-soft); }
  .organ-swatch { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .label-group { display: flex; flex-direction: column; flex: 1; min-width: 0; }
  .label-group .name { font-size: 0.8rem; font-weight: 600; }
  .label-group .algo { font-size: 0.66rem; color: var(--text-dim); }
  .structure-status { display: flex; align-items: center; gap: 0.3rem; font-size: 0.64rem; font-weight: 650; white-space: nowrap; color: var(--text-faint); }
  .structure-status .dot { width: 7px; height: 7px; border-radius: 50%; border: 1.4px solid var(--text-faint); flex-shrink: 0; }
  .organ-btn[aria-pressed="true"] .structure-status { color: var(--ok); }
  .organ-btn[aria-pressed="true"] .structure-status .dot { background: var(--ok); border-color: var(--ok); }
  .inspector-row { display: flex; justify-content: space-between; gap: 0.6rem; padding: 0.32rem 0; border-bottom: 1px solid var(--border); font-size: 0.76rem; }
  .inspector-row .k { color: var(--text-dim); }
  .inspector-row .v { font-family: var(--font-mono); font-variant-numeric: tabular-nums; text-align: right; }
  .inspector-subhead { font-size: 0.7rem; font-weight: 650; color: var(--text); margin: 0.7rem 0 0.15rem; }
  .inspector-subhead:first-child { margin-top: 0; }
  .details-toggle { display: flex; align-items: center; justify-content: space-between; width: 100%; background: none; border: none; padding: 0.5rem 0; cursor: pointer; font-family: inherit; color: var(--text-dim); font-size: 0.68rem; font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; border-top: 1px solid var(--border); margin-top: 0.4rem; }
  .details-toggle svg { width: 12px; height: 12px; transition: transform 0.12s ease; }
  .details-toggle[aria-expanded="true"] svg { transform: rotate(180deg); }
  .validation-line { display: flex; align-items: center; gap: 0.4rem; font-size: 0.74rem; padding: 0.45rem 0.55rem; border-radius: var(--radius-md); background: var(--surface-raised); border: 1px solid var(--border); }
  .validation-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
  .validation-dot.pass { background: var(--ok); }
  .validation-dot.fail { background: var(--warn); }
  .note { font-size: 0.71rem; line-height: 1.45; color: var(--text-dim); margin: 0; }
  .stage { position: relative; background: var(--bg); }
  #gl-canvas, #room-canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
  .stage-hud { position: absolute; left: 0.85rem; bottom: 0.75rem; font-size: 0.68rem; color: var(--text-faint); font-family: var(--font-mono); }
  .icon-btn { position: absolute; top: 0.85rem; right: 0.85rem; padding: 0.32rem 0.58rem; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); font-size: 0.7rem; cursor: pointer; font-family: inherit; }

  /* ---- viewport toolbar / gizmo ---- */
  .viewport-toolbar { position: absolute; top: 0.85rem; right: 0.85rem; display: flex; align-items: center; gap: 0.15rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 0.22rem; }
  .viewport-toolbar button { display: flex; align-items: center; justify-content: center; min-width: 1.9rem; height: 1.7rem; padding: 0 0.4rem; border: none; background: transparent; border-radius: var(--radius-sm); color: var(--text-dim); font-size: 0.66rem; font-weight: 650; cursor: pointer; font-family: inherit; }
  .viewport-toolbar button svg { width: 14px; height: 14px; }
  .viewport-toolbar button:hover { background: var(--surface-raised); color: var(--text); }
  .viewport-toolbar button[aria-pressed="true"] { background: var(--accent-soft); color: var(--text); }
  .viewport-toolbar .vt-divider { width: 1px; align-self: stretch; margin: 0 0.2rem; background: var(--border); }
  .axis-gizmo-wrap { position: absolute; left: 0.85rem; top: 0.85rem; width: 64px; height: 64px; pointer-events: none; opacity: 0.85; }
  .measure-dot { position: absolute; width: 8px; height: 8px; margin: -4px; border-radius: 50%; background: var(--accent); border: 1.5px solid #fff; }
  .measure-label { position: absolute; transform: translate(-50%, -50%); font-family: var(--font-mono); font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.5rem; border-radius: var(--radius-sm); background: var(--surface); border: 1px solid var(--accent-strong); color: var(--text); white-space: nowrap; }
  .export-btn { flex: 1; font-size: 0.72rem; padding: 0.4rem 0.5rem; border: none; background: var(--surface-raised); color: var(--text); cursor: pointer; font-family: inherit; border-right: 1px solid var(--border); }
  .export-btn:last-child { border-right: none; }
  .export-btn:hover { background: var(--accent-soft); }
  .slice-stage { position: relative; display: flex; align-items: center; justify-content: center; background: #000; }
  #slice-canvas { image-rendering: pixelated; cursor: crosshair; box-shadow: 0 0 0 1px rgba(255,255,255,0.06); }
  .slider-row { display: flex; align-items: center; gap: 0.5rem; }
  .slider-row input[type="range"] { flex: 1; accent-color: var(--accent); }
  .preset-row { display: flex; gap: 0.35rem; flex-wrap: wrap; }
  .preset-btn { font-size: 0.7rem; padding: 0.28rem 0.55rem; border-radius: 4px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text-dim); cursor: pointer; font-family: inherit; }
  .preset-btn[aria-pressed="true"] { border-color: var(--accent-strong); color: var(--text); background: var(--accent-soft); }
  .hu-readout { position: absolute; left: 1rem; top: 1rem; font-family: var(--font-mono); font-size: 0.72rem; color: #dce8f2; background: rgba(0,0,0,0.45); padding: 0.25rem 0.5rem; border-radius: 4px; }
  .anatomy-panel { padding: 1.4rem 1.8rem; overflow-y: auto; max-width: 62rem; }
  .anatomy-panel h2 { font-family: var(--font-serif); font-weight: 600; font-size: 1.5rem; margin: 0 0 0.3rem; text-transform: capitalize; }
  .anatomy-panel .algo-line { font-size: 0.78rem; color: var(--text-dim); margin: 0 0 1.1rem; }
  .anatomy-panel p { font-size: 0.88rem; line-height: 1.65; color: var(--text); }
  .anatomy-panel .anatomy-detail h3 { font-family: var(--font-serif); font-weight: 600; font-size: 1.05rem; margin: 1.15rem 0 0.35rem; color: var(--accent-strong); }
  .anatomy-panel .anatomy-detail h3:first-child { margin-top: 0; }
  .anatomy-panel .anatomy-detail p { margin: 0 0 0.15rem; }
  .anatomy-panel .source-box { margin-top: 1.2rem; padding: 0.8rem 1rem; border-radius: 7px; background: var(--surface-raised); border: 1px solid var(--border); font-size: 0.78rem; line-height: 1.55; color: var(--text-dim); }
  .anatomy-panel .source-box b { color: var(--text); }
  .fun-facts-list { margin: 0; padding-left: 1.1rem; display: flex; flex-direction: column; gap: 0.55rem; }
  .fun-facts-list li { font-size: 0.85rem; line-height: 1.55; color: var(--text); }
  .anatomy-diagram { display: flex; flex-wrap: wrap; justify-content: center; align-items: flex-start; gap: 1.6rem; padding: 0.4rem 0 0.8rem; }
  .anatomy-diagram .diagram-card { display: flex; flex-direction: column; align-items: center; gap: 0.4rem; }
  .anatomy-diagram .diagram-card svg { width: 100%; height: auto; display: block; }
  .anatomy-diagram .diagram-main svg { max-width: 290px; }
  .anatomy-diagram .diagram-inset svg { max-width: 190px; }
  .anatomy-diagram .diagram-card-label { font-size: 0.72rem; color: var(--text-dim); text-align: center; max-width: 220px; line-height: 1.4; }
  .diagram-caveat { font-size: 0.7rem; color: var(--text-faint); text-align: center; margin: -0.3rem 0 0.8rem; }

  /* ---- 3D landmark labels ---- */
  .label-layer { position: absolute; inset: 0; pointer-events: none; }
  .label-layer.hidden { display: none; }
  .landmark-label {
    position: absolute; transform: translate(-50%, -130%);
    font-size: 0.71rem; font-weight: 600; white-space: nowrap;
    padding: 0.2rem 0.5rem; border-radius: var(--radius-sm);
    background: var(--surface);
    border: 1px solid var(--accent-strong); color: var(--text);
  }
  .landmark-label::after {
    content: ""; position: absolute; left: 50%; bottom: -5px; width: 6px; height: 6px;
    background: var(--accent); border-radius: 50%; transform: translateX(-50%);
  }

  /* ---- view mode / clipping controls ---- */
  .segmented-row { display: flex; border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }
  .segmented-row button { flex: 1; font-size: 0.72rem; padding: 0.4rem 0.3rem; border: none; background: var(--surface-raised); color: var(--text-dim); cursor: pointer; font-family: inherit; border-right: 1px solid var(--border); }
  .segmented-row button:last-child { border-right: none; }
  .segmented-row button[aria-pressed="true"] { background: var(--accent-soft); color: var(--text); font-weight: 650; }
  .toggle-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.78rem; }
  .toggle-row input[type="checkbox"] { accent-color: var(--accent); width: 14px; height: 14px; }
  .clip-controls { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.6rem; }
  .clip-controls[data-enabled="false"] { opacity: 0.4; pointer-events: none; }

  /* ---- laboratorio tab ---- */
  .lab-panel { padding: 1.2rem 1.6rem; overflow-y: auto; display: flex; flex-direction: column; gap: 1.1rem; max-width: 46rem; }
  .lab-subtabs { display: flex; gap: 0.3rem; }
  .lab-subtabs button { font-size: 0.76rem; font-weight: 600; padding: 0.4rem 0.85rem; border-radius: 5px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text-dim); cursor: pointer; font-family: inherit; }
  .lab-subtabs button[aria-pressed="true"] { background: var(--accent-soft); color: var(--text); border-color: var(--accent-strong); }
  .lab-canvas-row { display: flex; gap: 1.2rem; align-items: flex-start; flex-wrap: wrap; }
  #lab-canvas { image-rendering: pixelated; border-radius: 6px; border: 1px solid var(--border); background: #000; }
  .lab-stage-caption { flex: 1; min-width: 14rem; }
  .lab-stage-caption h4 { font-family: var(--font-serif); font-weight: 600; margin: 0 0 0.4rem; font-size: 0.98rem; }
  .lab-stage-caption p { margin: 0; font-size: 0.8rem; line-height: 1.55; color: var(--text-dim); }
  .lab-stepper { display: flex; align-items: center; gap: 0.6rem; }
  .lab-stepper button { padding: 0.4rem 0.7rem; border-radius: 5px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text); cursor: pointer; font-family: inherit; font-size: 0.8rem; }
  .lab-stepper button:disabled { opacity: 0.35; cursor: default; }
  .lab-dots { display: flex; gap: 0.35rem; }
  .lab-dots span { width: 8px; height: 8px; border-radius: 50%; background: var(--border); }
  .lab-dots span[data-active="true"] { background: var(--accent); }
  .lab-field { display: flex; flex-direction: column; gap: 0.35rem; }
  .lab-field .label-row { display: flex; justify-content: space-between; font-size: 0.76rem; color: var(--text-dim); }
  .lab-field input[type="range"] { accent-color: var(--accent); }
  .mpr-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.35rem; vertical-align: 1px; }
  .lab-tick-note { font-size: 0.72rem; color: var(--text-faint); }
  .lab-histogram-wrap { display: flex; flex-direction: column; gap: 0.25rem; }
  #lab-histogram-canvas { width: 100%; height: 84px; display: block; border-radius: 4px; border: 1px solid var(--border); background: var(--surface-raised); }
  .lab-match { font-size: 0.76rem; color: var(--ok); font-weight: 600; min-height: 1.1em; }

  /* ---- welcome overlay ---- */
  #welcome-overlay { position: fixed; inset: 0; z-index: 200; display: flex; align-items: center; justify-content: center; background: var(--bg); transition: opacity 0.4s ease; padding: 1.5rem; box-sizing: border-box; }
  #welcome-overlay.hidden { opacity: 0; pointer-events: none; }
  .welcome-card { max-width: 26rem; width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 2rem 1.9rem; box-shadow: 0 12px 32px rgba(0,0,0,0.18); text-align: center; }
  .welcome-card .mark { width: 34px; height: 34px; color: var(--accent); display: block; margin: 0 auto 1.1rem; }
  .welcome-card h2 { font-family: var(--font-serif); font-weight: 600; margin: 0 0 0.5rem; font-size: 1.3rem; }
  .welcome-card p.sub { margin: 0 0 1.4rem; font-size: 0.85rem; color: var(--text-dim); line-height: 1.55; }
  .welcome-card input[type="text"] { width: 100%; box-sizing: border-box; padding: 0.65rem 0.8rem; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text); font-family: inherit; font-size: 0.92rem; margin-bottom: 0.9rem; }
  .welcome-card input[type="text"]:focus { outline: none; border-color: var(--accent-strong); }
  .welcome-card .welcome-btn { width: 100%; padding: 0.7rem 0.8rem; border-radius: 6px; border: none; background: var(--accent-strong); color: #fff; font-family: inherit; font-size: 0.9rem; font-weight: 650; cursor: pointer; }
  .welcome-card .welcome-btn:hover { filter: brightness(1.08); }
  .welcome-step { display: none; }
  .welcome-step[data-active="true"] { display: block; }
  .welcome-greet-name { color: var(--accent-strong); }
  .welcome-special { margin: 0.7rem 0 1.4rem; padding: 1rem 1.1rem; border-radius: 9px; background: var(--accent-soft); border: 1px solid var(--accent-strong); font-size: 0.95rem; line-height: 1.6; color: var(--text); }

  /* ---- trivia ---- */
  .trivia-panel { padding: 1.4rem 1.8rem; overflow-y: auto; max-width: 38rem; display: flex; flex-direction: column; gap: 0.9rem; }
  .trivia-panel h3 { font-family: var(--font-serif); font-weight: 600; font-size: 1.15rem; margin: 0 0 0.2rem; }
  .trivia-options { display: flex; flex-direction: column; gap: 0.5rem; }
  .trivia-option-btn { text-align: left; padding: 0.65rem 0.9rem; border-radius: 6px; border: 1px solid var(--border); background: var(--surface-raised); color: var(--text); cursor: pointer; font-family: inherit; font-size: 0.88rem; }
  .trivia-option-btn:hover:not(:disabled) { border-color: var(--accent-strong); }
  .trivia-option-btn:disabled { cursor: default; }
  .trivia-option-btn[data-state="correct"] { border-color: var(--ok); background: color-mix(in srgb, var(--ok) 18%, var(--surface-raised)); }
  .trivia-option-btn[data-state="wrong"] { border-color: var(--warn); background: color-mix(in srgb, var(--warn) 18%, var(--surface-raised)); }
  .trivia-explain { font-size: 0.85rem; color: var(--text-dim); line-height: 1.55; padding: 0.7rem 0.9rem; border-radius: 6px; background: var(--surface-raised); border: 1px solid var(--border); margin: 0; }
  .trivia-action-btn { width: auto; align-self: flex-start; padding: 0.55rem 1.3rem; margin-top: 0.2rem; }

  /* ---- responsive: keep the viewport dominant, shrink chrome first ---- */
  @media (max-width: 1180px) {
    .topbar-study .badge:not(:first-of-type) { display: none; }
  }
  @media (max-width: 1000px) {
    header h1 { display: none; }
    .topbar-study .study-name { max-width: 6rem; }
  }
  @media (max-width: 860px) {
    .tab-label { display: none; }
    .tab-btn { padding: 0.4rem 0.5rem; }
    .tab-btn svg { width: 15px; height: 15px; }
    .topbar-study .badge { display: none; }
  }
  @media (max-width: 700px) {
    main { grid-template-columns: 220px 1fr; }
    aside { padding: 0.6rem; }
    .viewport-toolbar button { min-width: 1.6rem; height: 1.5rem; font-size: 0.6rem; padding: 0 0.25rem; }
  }
</style>
<body>
<div id="welcome-overlay">
  <div class="welcome-card">
    <svg class="mark" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="13" r="8.4" stroke="currentColor" stroke-width="1.3"/><circle cx="12" cy="13" r="5" stroke="currentColor" stroke-width="1.3" opacity="0.6"/><circle cx="12" cy="13" r="1.6" fill="currentColor"/><path d="M4.2 6 L19.8 6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
    <div class="welcome-step" id="welcome-step-name" data-active="true">
      <h2>Bienvenido al reconstructor de órganos en 3D</h2>
      <p class="sub">Reconstrucciones reales de pulmones, corazón, hígado, riñones y cerebro a partir de tomografías reales. ¿Cómo te llamas?</p>
      <input type="text" id="welcome-name-input" placeholder="Tu nombre" autocomplete="off" maxlength="40"/>
      <button class="welcome-btn" id="welcome-name-btn">Entrar</button>
    </div>
    <div class="welcome-step" id="welcome-step-greet">
      <h2>¡Bienvenido/a, <span class="welcome-greet-name" id="welcome-greet-name"></span>!</h2>
      <div id="welcome-special" style="display:none;"></div>
      <p class="sub">Explora 5 órganos reconstruidos en 3D a partir de datos reales, con cortes, laboratorio de segmentación y más.</p>
      <button class="welcome-btn" id="welcome-enter-btn">Comenzar</button>
    </div>
  </div>
</div>
<header>
  <svg class="mark" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="13" r="8.4" stroke="currentColor" stroke-width="1.3"/><circle cx="12" cy="13" r="5" stroke="currentColor" stroke-width="1.3" opacity="0.6"/><circle cx="12" cy="13" r="1.6" fill="currentColor"/><path d="M4.2 6 L19.8 6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
  <h1>Medical3DReconstruction</h1>
  <div class="topbar-divider"></div>
  <div class="topbar-study">
    <span class="study-name" id="topbar-study-name"></span>
    <span class="badge" id="topbar-study-type"></span>
    <span class="badge" id="topbar-status"><span class="badge-dot ok"></span><span id="topbar-status-text">Listo</span></span>
  </div>
  <span class="spacer"></span>
  <div class="tab-switch">
    <button class="tab-btn" id="tab-btn-3d" aria-selected="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2 4 6.5v11L12 22l8-4.5v-11L12 2Z"/><path d="M4 6.5 12 11l8-4.5"/><path d="M12 11v11"/></svg><span class="tab-label">Reconstrucción 3D</span></button>
    <button class="tab-btn" id="tab-btn-slices" aria-selected="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="1.5"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg><span class="tab-label">Cortes CT</span></button>
    <button class="tab-btn" id="tab-btn-lab" aria-selected="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M9 2v6.5L4.5 17a2 2 0 0 0 1.8 3h11.4a2 2 0 0 0 1.8-3L15 8.5V2"/><path d="M9 2h6"/><path d="M7.5 14h9"/></svg><span class="tab-label">Laboratorio</span></button>
    <button class="tab-btn" id="tab-btn-anatomy" aria-selected="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5V5.5A2.5 2.5 0 0 1 6.5 3H20v15.5"/><path d="M6.5 21A2.5 2.5 0 0 1 4 18.5H20V21H6.5Z"/></svg><span class="tab-label">Anatomía</span></button>
    <button class="tab-btn" id="tab-btn-room" aria-selected="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg><span class="tab-label">Sala de órganos</span></button>
    <button class="tab-btn" id="tab-btn-trivia" aria-selected="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M9.2 9.3a2.8 2.8 0 1 1 3.9 2.6c-.9.4-1.6 1-1.6 2.1"/><path d="M12 17.5h.01"/></svg><span class="tab-label">Trivia</span></button>
  </div>
  <span class="spacer"></span>
  <button class="icon-btn-flat" id="theme-btn">Tema</button>
</header>

<main id="panel-3d">
  <aside>
    <div class="panel-group">
      <p class="eyebrow">Estructuras</p>
      <div class="organ-list" id="organ-list"></div>
      <label class="toggle-row" style="margin-top:0.6rem"><input type="checkbox" id="heartbeat-toggle"> <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:-2px" xmlns="http://www.w3.org/2000/svg"><path d="M4 9v6h4l5 5V4L8 9H4z" fill="currentColor"/><path d="M17 8a5 5 0 0 1 0 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M19.5 5.5a9 9 0 0 1 0 13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.55"/></svg> Sonido del latido (solo corazón)</label>
    </div>
    <div class="panel-group">
      <p class="eyebrow">Orientación</p>
      <p class="note" id="orientation-note"></p>
    </div>
    <div class="panel-group">
      <p class="eyebrow">Modo de visualización</p>
      <div class="segmented-row" id="view-mode-row">
        <button data-mode="solid" aria-pressed="true">Sólido</button>
        <button data-mode="xray" aria-pressed="false">Rayos-X</button>
        <button data-mode="wire" aria-pressed="false">Alambre</button>
        <button data-mode="mpr" aria-pressed="false">Cortes MPR</button>
        <button data-mode="fly" aria-pressed="false">Vuelo interior</button>
      </div>
      <div id="mpr-section" class="hidden" style="margin-top:0.7rem">
        <p class="note">Los 3 planos reales (axial/coronal/sagital) del mismo volumen que ves en "Cortes CT", flotando en 3D como una caja que puedes rotar.</p>
        <div class="lab-field">
          <div class="label-row"><span><span class="mpr-dot" style="background:#5c8fbd"></span>Axial (Z)</span><span id="mpr-axial-value"></span></div>
          <input type="range" id="mpr-axial-slider" min="0" max="100" value="50">
        </div>
        <div class="lab-field">
          <div class="label-row"><span><span class="mpr-dot" style="background:#789e61"></span>Coronal (Y)</span><span id="mpr-coronal-value"></span></div>
          <input type="range" id="mpr-coronal-slider" min="0" max="100" value="50">
        </div>
        <div class="lab-field">
          <div class="label-row"><span><span class="mpr-dot" style="background:#c76b5c"></span>Sagital (X)</span><span id="mpr-sagittal-value"></span></div>
          <input type="range" id="mpr-sagittal-slider" min="0" max="100" value="50">
        </div>
        <label class="toggle-row" style="margin-top:0.3rem"><input type="checkbox" id="mpr-gradient-toggle"> Campo de orientación (aproximado)</label>
        <p class="diagram-caveat" style="margin:0.3rem 0 0;text-align:left">No es tractografía DTI real — este proyecto no tiene datos de difusión. Son líneas cortas siguiendo el gradiente de intensidad real de este escaneo (dirección de mayor cambio de densidad), coloreadas por eje solo como referencia visual.</p>
      </div>
      <div id="fly-section" class="hidden" style="margin-top:0.7rem">
        <p class="note">Una cámara en primera persona recorre el interior real del órgano, siguiendo el eje central de la máscara segmentada — no una animación decorativa, es la geometría de este espécimen.</p>
        <div class="toggle-row" style="gap:0.5rem">
          <button class="preset-btn" id="fly-play-btn" aria-pressed="true">Pausar</button>
          <span id="fly-progress-note" class="lab-tick-note"></span>
        </div>
        <div class="lab-field" style="margin-top:0.5rem">
          <div class="label-row"><span>Velocidad</span></div>
          <input type="range" id="fly-speed-slider" min="20" max="200" value="70">
        </div>
      </div>
    </div>
    <div class="panel-group">
      <p class="eyebrow">Reconstrucción</p>
      <div id="opacity-row">
        <div class="label-row"><span style="font-size:0.76rem;color:var(--text-dim)">Opacidad</span><span id="opacity-value" style="font-size:0.72rem;color:var(--text-dim)">100%</span></div>
        <input type="range" id="opacity-slider" min="5" max="100" value="100">
      </div>
      <div id="clip-section" style="margin-top:0.7rem">
        <label class="toggle-row"><input type="checkbox" id="clip-enabled"> Clipping (corte virtual)</label>
        <div class="clip-controls" id="clip-controls" data-enabled="false">
          <div class="label-row" style="margin-top:0.3rem"><span>Plano</span></div>
          <div class="segmented-row" id="clip-axis-row">
            <button data-axis="0" aria-pressed="true">X</button>
            <button data-axis="1" aria-pressed="false">Y</button>
            <button data-axis="2" aria-pressed="false">Z</button>
          </div>
          <div class="label-row" style="margin-top:0.3rem"><span>Posición</span></div>
          <input type="range" id="clip-slider" min="0" max="100" value="50">
        </div>
      </div>
    </div>
    <div class="panel-group" id="measure-group">
      <p class="eyebrow">Medición</p>
      <label class="toggle-row"><input type="checkbox" id="measure-enabled"> Activar herramienta de medición</label>
      <p class="note" style="margin-top:0.4rem">Con la herramienta activa, haz clic en dos puntos de la superficie del modelo. La distancia se calcula en milímetros reales, sobre las mismas coordenadas de la malla exportada.</p>
      <div class="inspector-row" id="measure-readout-row" style="display:none">
        <span class="k">Distancia</span><span class="v" id="measure-readout-value"></span>
      </div>
      <button class="preset-btn" id="measure-clear-btn" style="margin-top:0.4rem;display:none">Borrar medición</button>
    </div>
    <div class="panel-group">
      <p class="eyebrow">Anatomy Inspector</p>
      <p class="inspector-subhead">Malla</p>
      <div id="metrics-panel"></div>
      <p class="inspector-subhead">Validación</p>
      <div id="validation-panel"></div>
      <button class="details-toggle" id="details-toggle-btn" aria-expanded="false">Technical details<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg></button>
      <div id="technical-details-panel" class="hidden">
        <div id="technical-details-rows"></div>
      </div>
      <p class="inspector-subhead">Fuente de datos</p>
      <p class="note" id="source-note"></p>
      <p class="note" id="caveat-note" style="margin-top:0.5rem"></p>
    </div>
    <div class="panel-group">
      <p class="eyebrow">Exportar</p>
      <p class="note">Descarga la malla tal como está cargada ahora mismo en el visor (misma geometría que ves, ya decimada para la web).</p>
      <div class="segmented-row" style="margin-top:0.5rem">
        <button class="export-btn" id="export-stl-btn">STL</button>
        <button class="export-btn" id="export-obj-btn">OBJ</button>
      </div>
      <p class="lab-tick-note" id="export-status" style="margin-top:0.4rem"></p>
    </div>
  </aside>
  <div class="stage">
    <canvas id="gl-canvas"></canvas>
    <div class="label-layer" id="label-layer"></div>
    <div class="label-layer" id="measure-layer"></div>
    <div class="axis-gizmo-wrap"><canvas id="axis-gizmo-canvas" width="64" height="64"></canvas></div>
    <div class="viewport-toolbar" id="viewport-toolbar">
      <button data-view="front" title="Vista frontal (Anterior)">Ant</button>
      <button data-view="back" title="Vista posterior">Post</button>
      <button data-view="left" title="Vista izquierda">Izq</button>
      <button data-view="right" title="Vista derecha">Der</button>
      <button data-view="top" title="Vista superior">Sup</button>
      <button data-view="bottom" title="Vista inferior">Inf</button>
      <button data-view="iso" title="Vista isométrica">Iso</button>
      <span class="vt-divider"></span>
      <button id="fit-btn" title="Encuadrar modelo (Fit)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
      </button>
      <button id="labels-toggle-btn" aria-pressed="true" title="Mostrar/ocultar etiquetas anatómicas">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M11 3H4a1 1 0 0 0-1 1v7a1 1 0 0 0 .3.7l9 9a1 1 0 0 0 1.4 0l7-7a1 1 0 0 0 0-1.4l-9-9A1 1 0 0 0 11 3Z"/><circle cx="7.5" cy="7.5" r="1"/></svg>
      </button>
    </div>
    <div class="stage-hud">arrastra para rotar &middot; desplaza para hacer zoom</div>
  </div>
</main>

<main id="panel-slices" class="hidden">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-slices"></div>
    </div>
    <div>
      <p class="eyebrow">Corte</p>
      <div class="slider-row">
        <input type="range" id="slice-slider" min="0" max="0" value="0">
        <span id="slice-readout" style="font-family:var(--font-mono);font-size:0.74rem;min-width:7rem;text-align:right"></span>
      </div>
    </div>
    <div>
      <p class="eyebrow">Preajuste de ventana</p>
      <div class="preset-row" id="preset-row"></div>
    </div>
    <div>
      <p class="eyebrow">Nivel / ancho de ventana</p>
      <div class="slider-row"><input type="range" id="level-slider" min="0" max="255" value="128"><span id="level-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
      <div class="slider-row"><input type="range" id="width-slider" min="1" max="510" value="255"><span id="width-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
    </div>
    <p class="note" id="slice-source-note"></p>
  </aside>
  <div class="slice-stage">
    <canvas id="slice-canvas"></canvas>
    <div class="hu-readout" id="hu-readout">&mdash;</div>
  </div>
</main>

<main id="panel-anatomy" class="hidden" style="grid-template-columns: 300px 1fr;">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-anatomy"></div>
    </div>
  </aside>
  <div class="anatomy-panel">
    <h2 id="anatomy-title"></h2>
    <p class="algo-line" id="anatomy-algo"></p>
    <div id="anatomy-text" class="anatomy-detail"></div>

    <p class="eyebrow" style="margin-top:1.3rem">Diagrama anatómico (esquemático)</p>
    <div class="anatomy-diagram" id="anatomy-diagram"></div>
    <p class="diagram-caveat">Esquema educativo general — no una anotación de este espécimen exacto.</p>

    <p class="eyebrow" style="margin-top:0.6rem">Datos y curiosidades</p>
    <ul class="fun-facts-list" id="anatomy-facts"></ul>

    <div class="source-box">
      <p><b>Fuente de datos:</b> <span id="anatomy-source"></span></p>
      <p style="margin-top:0.5rem"><b>Advertencia / alcance:</b> <span id="anatomy-caveat"></span></p>
    </div>
  </div>
</main>

<main id="panel-lab" class="hidden">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-lab"></div>
    </div>
    <div>
      <p class="eyebrow">Modo</p>
      <div class="lab-subtabs">
        <button data-lab-mode="timeline" aria-pressed="true">Línea de tiempo</button>
        <button data-lab-mode="free" aria-pressed="false">Modo libre</button>
      </div>
    </div>
    <p class="note">
      Este laboratorio reconstruye, en 2D y sobre el mismo corte real que ves
      en "Cortes CT", los mismos pasos que el pipeline aplicó de verdad en 3D
      para este órgano: umbral de intensidad, limpieza morfológica, y
      relleno de huecos.
    </p>
  </aside>
  <div class="lab-panel">
    <div id="lab-timeline-view">
      <div class="lab-canvas-row">
        <canvas id="lab-canvas"></canvas>
        <div class="lab-stage-caption">
          <h4 id="lab-stage-title"></h4>
          <p id="lab-stage-text"></p>
        </div>
      </div>
      <div class="lab-stepper">
        <button id="lab-prev">&larr; Anterior</button>
        <div class="lab-dots" id="lab-dots"></div>
        <button id="lab-next">Siguiente &rarr;</button>
      </div>
    </div>
    <div id="lab-free-view" class="hidden">
      <div class="lab-canvas-row">
        <canvas id="lab-free-canvas"></canvas>
        <div class="lab-stage-caption">
          <h4>Arma tu propio pipeline</h4>
          <p>Ajusta el umbral y activa o desactiva los pasos de limpieza — el mismo corte real, tus propias decisiones.</p>
          <p class="lab-match" id="lab-free-match"></p>
        </div>
      </div>
      <div class="lab-field">
        <div class="label-row"><span>Umbral</span><span id="lab-threshold-value"></span></div>
        <input type="range" id="lab-threshold-slider" min="0" max="255" value="128">
        <span class="lab-tick-note" id="lab-threshold-real"></span>
      </div>
      <div class="lab-histogram-wrap">
        <p class="eyebrow" style="margin-bottom:0.3rem">Histograma real de densidades (todo el volumen)</p>
        <canvas id="lab-histogram-canvas" width="460" height="100"></canvas>
        <p class="lab-tick-note" id="lab-histogram-note"></p>
      </div>
      <label class="toggle-row"><input type="checkbox" id="lab-opening-toggle" checked> Apertura morfológica (quita ruido de la segmentación)</label>
      <label class="toggle-row"><input type="checkbox" id="lab-cleanup-toggle" checked> Quedarse con la forma más grande y rellenar huecos</label>
    </div>
  </div>
</main>

<main id="panel-room" class="hidden" style="grid-template-columns: 300px 1fr;">
  <aside>
    <p class="eyebrow">Sala de órganos</p>
    <p class="note">
      Los cinco órganos reconstruidos, juntos en una sola escena, cada uno
      en las coordenadas físicas (milímetros) reales que produjo su
      propio pipeline — sin reescalar. El tamaño relativo entre ellos es
      real, no artístico.
    </p>
  </aside>
  <div class="stage">
    <canvas id="room-canvas"></canvas>
    <div class="label-layer" id="room-label-layer"></div>
    <button class="icon-btn" id="room-reset-btn">Restablecer vista</button>
    <div class="stage-hud">arrastra para rotar &middot; desplaza para hacer zoom</div>
  </div>
</main>

<main id="panel-trivia" class="hidden" style="grid-template-columns: 300px 1fr;">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-trivia"></div>
    </div>
    <p class="note">
      Preguntas de opción múltiple con los mismos datos reales de la
      pestaña "Anatomía" — para poner a prueba lo que aprendiste.
    </p>
  </aside>
  <div class="trivia-panel">
    <p class="eyebrow" id="trivia-progress"></p>
    <div id="trivia-question-card">
      <h3 id="trivia-question-text"></h3>
      <div id="trivia-options" class="trivia-options"></div>
      <p id="trivia-explain" class="trivia-explain hidden"></p>
      <button id="trivia-next-btn" class="welcome-btn trivia-action-btn hidden">Siguiente &rarr;</button>
    </div>
    <div id="trivia-result" class="hidden">
      <h3 id="trivia-result-title"></h3>
      <p id="trivia-result-text"></p>
      <button id="trivia-restart-btn" class="welcome-btn trivia-action-btn">Reintentar</button>
    </div>
  </div>
</main>

<script>
  const ORGAN_ORDER = __ORGAN_ORDER_JSON__;
  const ORGAN_META = __ORGAN_META_JSON__;
  const VIEWER_DATA = __VIEWER_DATA_JSON__;

  function decodeB64(b64) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
  }
  function hexToRgb01(hex) {
    const v = parseInt(hex.replace("#", ""), 16);
    return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255];
  }
  function fmt(n, d) { return Number(n).toLocaleString(undefined, {maximumFractionDigits: d, minimumFractionDigits: d}); }

  // ---------- tabs ----------
  const tabBtn3d = document.getElementById("tab-btn-3d");
  const tabBtnSlices = document.getElementById("tab-btn-slices");
  const tabBtnLab = document.getElementById("tab-btn-lab");
  const tabBtnAnatomy = document.getElementById("tab-btn-anatomy");
  const panel3d = document.getElementById("panel-3d");
  const panelSlices = document.getElementById("panel-slices");
  const panelLab = document.getElementById("panel-lab");
  const panelAnatomy = document.getElementById("panel-anatomy");

  const tabBtnRoom = document.getElementById("tab-btn-room");
  const panelRoom = document.getElementById("panel-room");
  const tabBtnTrivia = document.getElementById("tab-btn-trivia");
  const panelTrivia = document.getElementById("panel-trivia");

  function activateTab(which) {
    tabBtn3d.setAttribute("aria-selected", String(which === "3d"));
    tabBtnSlices.setAttribute("aria-selected", String(which === "slices"));
    tabBtnLab.setAttribute("aria-selected", String(which === "lab"));
    tabBtnAnatomy.setAttribute("aria-selected", String(which === "anatomy"));
    tabBtnRoom.setAttribute("aria-selected", String(which === "room"));
    tabBtnTrivia.setAttribute("aria-selected", String(which === "trivia"));
    panel3d.classList.toggle("hidden", which !== "3d");
    panelSlices.classList.toggle("hidden", which !== "slices");
    panelLab.classList.toggle("hidden", which !== "lab");
    panelAnatomy.classList.toggle("hidden", which !== "anatomy");
    panelRoom.classList.toggle("hidden", which !== "room");
    panelTrivia.classList.toggle("hidden", which !== "trivia");
    if (which === "slices") { resizeSliceCanvasDisplay(); drawSlice(); }
    if (which === "lab") { labRender(); }
    if (which === "room") { buildRoom(); }
    if (which === "trivia") { initTriviaTabIfNeeded(); }
  }
  tabBtn3d.addEventListener("click", () => activateTab("3d"));
  tabBtnSlices.addEventListener("click", () => activateTab("slices"));
  tabBtnLab.addEventListener("click", () => activateTab("lab"));
  tabBtnAnatomy.addEventListener("click", () => activateTab("anatomy"));
  tabBtnRoom.addEventListener("click", () => activateTab("room"));
  tabBtnTrivia.addEventListener("click", () => activateTab("trivia"));

  // ---------- theme ----------
  document.getElementById("theme-btn").addEventListener("click", () => {
    const root = document.documentElement;
    const current = root.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.setAttribute("data-theme", current === "dark" ? "light" : "dark");
  });

  // ---------- welcome screen ----------
  (function initWelcome() {
    const overlay = document.getElementById("welcome-overlay");
    const stepName = document.getElementById("welcome-step-name");
    const stepGreet = document.getElementById("welcome-step-greet");
    const nameInput = document.getElementById("welcome-name-input");
    const nameBtn = document.getElementById("welcome-name-btn");
    const greetNameEl = document.getElementById("welcome-greet-name");
    const specialEl = document.getElementById("welcome-special");
    const enterBtn = document.getElementById("welcome-enter-btn");

    function showGreeting(rawName) {
      const name = rawName.trim();
      greetNameEl.textContent = name || "amigo/a";
      if (name.toLowerCase() === "hillary") {
        specialEl.textContent = "Sé que serás una gran doctora algún día. Estoy orgulloso de ti, Laly <3";
        specialEl.style.display = "block";
      } else {
        specialEl.style.display = "none";
      }
      stepName.setAttribute("data-active", "false");
      stepGreet.setAttribute("data-active", "true");
      try { localStorage.setItem("medical3d_visitor_name", name); } catch (e) {}
    }

    nameBtn.addEventListener("click", () => showGreeting(nameInput.value));
    nameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") showGreeting(nameInput.value); });
    enterBtn.addEventListener("click", () => overlay.classList.add("hidden"));

    let savedName = "";
    try { savedName = localStorage.getItem("medical3d_visitor_name") || ""; } catch (e) {}
    if (savedName) nameInput.value = savedName;
    nameInput.focus();
  })();

  /* =========================================================
     3D reconstruction viewer
     ========================================================= */
  // Ex-vivo specimens were scanned/mounted in whatever orientation was
  // physically convenient, not a standardized "patient up" pose (see
  // load_volume()'s own docstring: slice-image archives carry no direction/
  // origin metadata at all). Most organs don't have an obvious visual "up",
  // so this goes unnoticed — but some do, and this is purely a DISPLAY
  // correction based on this specimen's own real shape, not a recovery of
  // its true in-vivo orientation (which the data simply doesn't encode).
  // Both named fixes below are proper 180°/90° rotations (det=+1, not a
  // mirror), so winding/normals stay valid.
  //   flipY  — brain: this specimen renders smooth vault down / irregular
  //            base up; 180° about the mesh's own vertical (Z) axis fixes it.
  //   rotXdown — heart: apex (the tapered extremity, farthest mesh point
  //            from centroid — see computeHeartLandmarks below) sits at
  //            +Z in the raw mesh, base at -Z (verified: the apex→base
  //            vector is >99.8% aligned with the Z axis for this specimen).
  //            A 90° rotation about X sends apex to -Y so it renders
  //            pointing down, base up — the conventional heart-illustration
  //            pose, exactly the same "purely for display" idea as flipY.
  const ORGAN_DISPLAY_FIX = { brain: "flipY", heart: "rotXdown" };
  function decodeMesh(meshData, organKey) {
    const positions = new Float32Array(decodeB64(meshData.positions_b64));
    const normals = new Float32Array(decodeB64(meshData.normals_b64));
    const fix = ORGAN_DISPLAY_FIX[organKey];
    if (fix === "flipY") {
      const cx = meshData.center[0], cy = meshData.center[1];
      for (let i = 0; i < positions.length; i += 3) {
        positions[i] = 2 * cx - positions[i];
        positions[i + 1] = 2 * cy - positions[i + 1];
        normals[i] = -normals[i];
        normals[i + 1] = -normals[i + 1];
      }
    } else if (fix === "rotXdown") {
      const [cx, cy, cz] = meshData.center;
      for (let i = 0; i < positions.length; i += 3) {
        const y = positions[i + 1], z = positions[i + 2];
        positions[i + 1] = cy - (z - cz);
        positions[i + 2] = cz + (y - cy);
        const ny = normals[i + 1], nz = normals[i + 2];
        normals[i + 1] = -nz;
        normals[i + 2] = ny;
      }
    }
    return {
      positions,
      normals,
      indices: new Uint32Array(decodeB64(meshData.indices_b64)),
      numVertices: meshData.num_vertices,
      numTriangles: meshData.num_triangles,
      center: meshData.center,
    };
  }

  const canvas = document.getElementById("gl-canvas");
  const gl = canvas.getContext("webgl", {antialias: true, alpha: false});

  const CLIP_UNIFORMS_FS = `
    uniform vec3 uClipNormal; uniform float uClipValue; uniform float uClipEnabled;
    bool clipDiscard(vec3 worldPos) {
      return uClipEnabled > 0.5 && dot(worldPos, uClipNormal) > uClipValue;
    }`;
  const VS = `attribute vec3 aPosition; attribute vec3 aNormal;
    uniform mat4 uModelView; uniform mat4 uProjection; uniform mat3 uNormalMatrix;
    uniform vec3 uOffset;
    varying vec3 vNormal; varying vec3 vViewPos; varying vec3 vWorldPos;
    void main() {
      vec3 worldPos = aPosition + uOffset;
      vec4 vp = uModelView * vec4(worldPos, 1.0);
      vViewPos = vp.xyz;
      vWorldPos = worldPos;
      vNormal = normalize(uNormalMatrix * aNormal);
      gl_Position = uProjection * vp;
    }`;
  const FS = `precision highp float; varying vec3 vNormal; varying vec3 vViewPos; varying vec3 vWorldPos;
    uniform vec3 uColor; uniform float uAlpha;
    ${CLIP_UNIFORMS_FS}
    void main() {
      if (clipDiscard(vWorldPos)) discard;
      vec3 N = normalize(vNormal); if (!gl_FrontFacing) N = -N;
      vec3 V = normalize(-vViewPos);
      vec3 keyDir = normalize(vec3(0.55, 0.65, 0.85));
      vec3 fillDir = normalize(vec3(-0.6, -0.2, 0.5));
      float key = max(dot(N, keyDir), 0.0);
      float fill = max(dot(N, fillDir), 0.0);
      vec3 halfV = normalize(keyDir + V);
      float spec = pow(max(dot(N, halfV), 0.0), 28.0) * 0.22;
      vec3 color = uColor * (0.32 + key * 0.72 + fill * 0.22) + vec3(spec);
      gl_FragColor = vec4(color, uAlpha);
    }`;
  const VS_WIRE = `attribute vec3 aPosition;
    uniform mat4 uModelView; uniform mat4 uProjection;
    varying vec3 vWorldPos;
    void main() {
      vWorldPos = aPosition;
      gl_Position = uProjection * uModelView * vec4(aPosition, 1.0);
    }`;
  const FS_WIRE = `precision highp float; varying vec3 vWorldPos;
    uniform vec3 uColor; uniform float uAlpha;
    ${CLIP_UNIFORMS_FS}
    void main() {
      if (clipDiscard(vWorldPos)) discard;
      gl_FragColor = vec4(uColor, uAlpha);
    }`;
  function compile(type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  function linkProgram(vsSrc, fsSrc) {
    const p = gl.createProgram();
    gl.attachShader(p, compile(gl.VERTEX_SHADER, vsSrc));
    gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fsSrc));
    gl.linkProgram(p);
    return p;
  }
  const program = linkProgram(VS, FS);
  gl.useProgram(program);
  const aPosition = gl.getAttribLocation(program, "aPosition");
  const aNormal = gl.getAttribLocation(program, "aNormal");
  const uModelView = gl.getUniformLocation(program, "uModelView");
  const uProjection = gl.getUniformLocation(program, "uProjection");
  const uNormalMatrix = gl.getUniformLocation(program, "uNormalMatrix");
  const uColor = gl.getUniformLocation(program, "uColor");
  const uAlpha = gl.getUniformLocation(program, "uAlpha");
  const uClipNormal = gl.getUniformLocation(program, "uClipNormal");
  const uClipValue = gl.getUniformLocation(program, "uClipValue");
  const uClipEnabled = gl.getUniformLocation(program, "uClipEnabled");
  const uOffset = gl.getUniformLocation(program, "uOffset");

  const wireProgram = linkProgram(VS_WIRE, FS_WIRE);
  const aPositionW = gl.getAttribLocation(wireProgram, "aPosition");
  const uModelViewW = gl.getUniformLocation(wireProgram, "uModelView");
  const uProjectionW = gl.getUniformLocation(wireProgram, "uProjection");
  const uColorW = gl.getUniformLocation(wireProgram, "uColor");
  const uAlphaW = gl.getUniformLocation(wireProgram, "uAlpha");
  const uClipNormalW = gl.getUniformLocation(wireProgram, "uClipNormal");
  const uClipValueW = gl.getUniformLocation(wireProgram, "uClipValue");
  const uClipEnabledW = gl.getUniformLocation(wireProgram, "uClipEnabled");

  // ---------- MPR textured plane shader ----------
  const VS_PLANE = `attribute vec3 aPosition; attribute vec2 aTexCoord;
    uniform mat4 uModelView; uniform mat4 uProjection;
    varying vec2 vTexCoord;
    void main() {
      vTexCoord = aTexCoord;
      gl_Position = uProjection * uModelView * vec4(aPosition, 1.0);
    }`;
  const FS_PLANE = `precision highp float; varying vec2 vTexCoord;
    uniform sampler2D uTexture;
    void main() { gl_FragColor = texture2D(uTexture, vTexCoord); }`;
  const planeProgram = linkProgram(VS_PLANE, FS_PLANE);
  const aPositionP = gl.getAttribLocation(planeProgram, "aPosition");
  const aTexCoordP = gl.getAttribLocation(planeProgram, "aTexCoord");
  const uModelViewP = gl.getUniformLocation(planeProgram, "uModelView");
  const uProjectionP = gl.getUniformLocation(planeProgram, "uProjection");
  const uTextureP = gl.getUniformLocation(planeProgram, "uTexture");

  // ---------- colored line shader (gradient-orientation field) ----------
  const VS_LINEC = `attribute vec3 aPosition; attribute vec3 aColor;
    uniform mat4 uModelView; uniform mat4 uProjection;
    varying vec3 vColor;
    void main() {
      vColor = aColor;
      gl_Position = uProjection * uModelView * vec4(aPosition, 1.0);
    }`;
  const FS_LINEC = `precision highp float; varying vec3 vColor; uniform float uAlpha;
    void main() { gl_FragColor = vec4(vColor, uAlpha); }`;
  const lineColorProgram = linkProgram(VS_LINEC, FS_LINEC);
  const aPositionLC = gl.getAttribLocation(lineColorProgram, "aPosition");
  const aColorLC = gl.getAttribLocation(lineColorProgram, "aColor");
  const uModelViewLC = gl.getUniformLocation(lineColorProgram, "uModelView");
  const uProjectionLC = gl.getUniformLocation(lineColorProgram, "uProjection");
  const uAlphaLC = gl.getUniformLocation(lineColorProgram, "uAlpha");

  // ---- thick "ribbon" shader for the gradient-orientation field ----
  // Plain GL_LINES render as near-invisible 1px hairlines in WebGL1 (line
  // width is unreliable across GPUs). Instead, expand each segment into a
  // camera-facing quad in the vertex shader: cross(segmentDir, Z-in-view-
  // space) is always perpendicular to both the segment and the view
  // direction, so offsetting by it in view space gives a billboard with
  // no per-frame CPU work and no viewport/aspect uniform needed.
  const VS_RIBBON = `attribute vec3 aPosition; attribute vec3 aOther; attribute float aSide; attribute vec3 aColor;
    uniform mat4 uModelView; uniform mat4 uProjection; uniform float uWidth;
    varying vec3 vColor;
    void main() {
      vec4 vp0 = uModelView * vec4(aPosition, 1.0);
      vec4 vp1 = uModelView * vec4(aOther, 1.0);
      vec3 dir = vp1.xyz - vp0.xyz;
      float dl = length(dir);
      vec3 dirN = dl > 0.0001 ? dir / dl : vec3(1.0, 0.0, 0.0);
      vec3 perp = normalize(cross(dirN, vec3(0.0, 0.0, 1.0)));
      vec3 offsetPos = vp0.xyz + perp * aSide * uWidth;
      vColor = aColor;
      gl_Position = uProjection * vec4(offsetPos, 1.0);
    }`;
  const FS_RIBBON = `precision highp float; varying vec3 vColor; uniform float uAlpha;
    void main() { gl_FragColor = vec4(vColor, uAlpha); }`;
  const ribbonProgram = linkProgram(VS_RIBBON, FS_RIBBON);
  const aPositionR = gl.getAttribLocation(ribbonProgram, "aPosition");
  const aOtherR = gl.getAttribLocation(ribbonProgram, "aOther");
  const aSideR = gl.getAttribLocation(ribbonProgram, "aSide");
  const aColorR = gl.getAttribLocation(ribbonProgram, "aColor");
  const uModelViewR = gl.getUniformLocation(ribbonProgram, "uModelView");
  const uProjectionR = gl.getUniformLocation(ribbonProgram, "uProjection");
  const uWidthR = gl.getUniformLocation(ribbonProgram, "uWidth");
  const uAlphaR = gl.getUniformLocation(ribbonProgram, "uAlpha");

  const posBuf = gl.createBuffer(), normBuf = gl.createBuffer(), idxBuf = gl.createBuffer(), edgeBuf = gl.createBuffer();
  let edgeCount = 0;
  gl.enable(gl.DEPTH_TEST); gl.enable(gl.CULL_FACE); gl.cullFace(gl.BACK);
  gl.getExtension("OES_element_index_uint");

  // ---------- view mode + clipping plane state ----------
  let viewMode = "solid"; // "solid" | "xray" | "wire"
  let clipEnabled = false, clipAxis = 0, clipFraction = 0.5;
  let measureEnabled = false, measurePoints = [];
  let meshBoundsMin = [0,0,0], meshBoundsMax = [0,0,0];

  function buildEdgeIndices(indices) {
    const seen = new Set();
    const edges = [];
    function addEdge(a, b) {
      const lo = Math.min(a, b), hi = Math.max(a, b);
      const key = lo + "_" + hi;
      if (seen.has(key)) return;
      seen.add(key);
      edges.push(lo, hi);
    }
    for (let i = 0; i < indices.length; i += 3) {
      addEdge(indices[i], indices[i+1]);
      addEdge(indices[i+1], indices[i+2]);
      addEdge(indices[i+2], indices[i]);
    }
    return new Uint32Array(edges);
  }

  function clipUniformValues() {
    const normal = clipAxis === 0 ? [1,0,0] : clipAxis === 1 ? [0,1,0] : [0,0,1];
    const lo = meshBoundsMin[clipAxis], hi = meshBoundsMax[clipAxis];
    return {normal, value: lo + (hi - lo) * clipFraction};
  }

  let alphaValue = 1.0;
  const opacitySlider = document.getElementById("opacity-slider");
  const opacityValueEl = document.getElementById("opacity-value");
  function setOpacity(pct) {
    alphaValue = pct / 100;
    opacitySlider.value = String(pct);
    opacityValueEl.textContent = pct + "%";
  }
  opacitySlider.addEventListener("input", () => setOpacity(Number(opacitySlider.value)));

  const opacityRowEl = document.getElementById("opacity-row");
  const clipSectionEl = document.getElementById("clip-section");
  const mprSectionEl = document.getElementById("mpr-section");
  const flySectionEl = document.getElementById("fly-section");
  const viewModeRow = document.getElementById("view-mode-row");
  viewModeRow.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-mode]");
    if (!btn) return;
    viewMode = btn.dataset.mode;
    for (const b of viewModeRow.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === btn));
    if (viewMode === "xray") setOpacity(35);
    else if (viewMode === "solid") setOpacity(100);
    const isMpr = viewMode === "mpr";
    const isFly = viewMode === "fly";
    mprSectionEl.classList.toggle("hidden", !isMpr);
    flySectionEl.classList.toggle("hidden", !isFly);
    opacityRowEl.classList.toggle("hidden", isMpr || isFly);
    clipSectionEl.classList.toggle("hidden", isMpr || isFly);
    labelLayerEl.classList.toggle("hidden", isMpr || isFly || !labelsVisible);
    if (isMpr || isFly) { measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = ""; }
    if (isMpr) {
      rebuildMprPlanes();
      if (showGradientField) computeGradientField();
      targetRadius = boundingRadius * 2.1; // a bit closer: more of the scene now, worth framing tighter
    }
    if (isFly) {
      if (!flyPath) computeFlyPath();
      flyPlaying = true;
      flyPlayBtn.textContent = "Pausar";
      flyPlayBtn.setAttribute("aria-pressed", "true");
    }
  });

  const clipEnabledEl = document.getElementById("clip-enabled");
  const clipControlsEl = document.getElementById("clip-controls");
  const clipAxisRow = document.getElementById("clip-axis-row");
  const clipSliderEl = document.getElementById("clip-slider");
  clipEnabledEl.addEventListener("change", () => {
    clipEnabled = clipEnabledEl.checked;
    clipControlsEl.dataset.enabled = String(clipEnabled);
  });
  clipAxisRow.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-axis]");
    if (!btn) return;
    clipAxis = Number(btn.dataset.axis);
    for (const b of clipAxisRow.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === btn));
  });
  clipSliderEl.addEventListener("input", () => {
    clipFraction = Number(clipSliderEl.value) / 100;
  });

  // =========================================================
  // Cortes MPR: the same real slice volume shown as 3 rotatable
  // orthogonal planes (axial/coronal/sagittal), like a clinical
  // multiplanar-reconstruction viewer. Optional gradient-orientation
  // overlay: NOT diffusion tractography (this project has no DTI data)
  // — short line segments following the real intensity gradient of
  // the scan, colored by axis only as a visual reference.
  // =========================================================
  function applyDisplayFixPoint(key, x, y, z) {
    const fix = ORGAN_DISPLAY_FIX[key];
    if (!currentMesh) return [x, y, z];
    if (fix === "flipY") {
      const cx = currentMesh.center[0], cy = currentMesh.center[1];
      return [2 * cx - x, 2 * cy - y, z];
    }
    if (fix === "rotXdown") {
      const [cx, cy, cz] = currentMesh.center;
      return [x, cy - (z - cz), cz + (y - cy)];
    }
    return [x, y, z];
  }

  let mprAxialFrac = 0.5, mprCoronalFrac = 0.5, mprSagittalFrac = 0.5;
  let showGradientField = false;
  const mprTexAxial = gl.createTexture(), mprTexCoronal = gl.createTexture(), mprTexSagittal = gl.createTexture();
  for (const tex of [mprTexAxial, mprTexCoronal, mprTexSagittal]) {
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  }
  const mprPosBuf = gl.createBuffer(), mprUvBuf = gl.createBuffer();
  let mprPlaneGeo = { axial: null, coronal: null, sagittal: null };

  function windowedTexel(raw) {
    const lo = windowLevel - windowWidth / 2, scale = 255 / windowWidth;
    let val = (raw - lo) * scale;
    return val < 0 ? 0 : val > 255 ? 255 : val;
  }
  function buildAxialTexture(zIndex) {
    const [nz, ny, nx] = sv.shape;
    const off = zIndex * ny * nx;
    const data = new Uint8Array(nx * ny * 4);
    for (let i = 0; i < nx * ny; i++) {
      const val = windowedTexel(sv.voxels[off + i]);
      const o = i * 4; data[o] = val; data[o + 1] = val; data[o + 2] = val; data[o + 3] = 255;
    }
    return { data, w: nx, h: ny };
  }
  function buildCoronalTexture(yIndex) {
    const [nz, ny, nx] = sv.shape;
    const data = new Uint8Array(nx * nz * 4);
    for (let z = 0; z < nz; z++) {
      for (let x = 0; x < nx; x++) {
        const val = windowedTexel(sv.voxels[z * ny * nx + yIndex * nx + x]);
        const o = (z * nx + x) * 4; data[o] = val; data[o + 1] = val; data[o + 2] = val; data[o + 3] = 255;
      }
    }
    return { data, w: nx, h: nz };
  }
  function buildSagittalTexture(xIndex) {
    const [nz, ny, nx] = sv.shape;
    const data = new Uint8Array(ny * nz * 4);
    for (let z = 0; z < nz; z++) {
      for (let y = 0; y < ny; y++) {
        const val = windowedTexel(sv.voxels[z * ny * nx + y * nx + xIndex]);
        const o = (z * ny + y) * 4; data[o] = val; data[o + 1] = val; data[o + 2] = val; data[o + 3] = 255;
      }
    }
    return { data, w: ny, h: nz };
  }

  function rebuildMprPlanes() {
    if (!sv) return;
    const [nz, ny, nx] = sv.shape;
    const [ox, oy, oz] = sv.origin;
    const [sx, sy, sz] = sv.spacing;
    const x0 = ox, x1 = ox + sx * (nx - 1);
    const y0 = oy, y1 = oy + sy * (ny - 1);
    const z0 = oz, z1 = oz + sz * (nz - 1);

    const zIndex = Math.max(0, Math.min(nz - 1, Math.round(mprAxialFrac * (nz - 1))));
    const yIndex = Math.max(0, Math.min(ny - 1, Math.round(mprCoronalFrac * (ny - 1))));
    const xIndex = Math.max(0, Math.min(nx - 1, Math.round(mprSagittalFrac * (nx - 1))));
    const zMm = oz + zIndex * sz, yMm = oy + yIndex * sy, xMm = ox + xIndex * sx;

    const key = currentOrganKey;
    const fix = (p) => applyDisplayFixPoint(key, p[0], p[1], p[2]);

    mprPlaneGeo.axial = {
      positions: new Float32Array([...fix([x0, y0, zMm]), ...fix([x1, y0, zMm]), ...fix([x0, y1, zMm]), ...fix([x1, y1, zMm])]),
      uv: new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]),
      tex: buildAxialTexture(zIndex),
    };
    mprPlaneGeo.coronal = {
      positions: new Float32Array([...fix([x0, yMm, z0]), ...fix([x1, yMm, z0]), ...fix([x0, yMm, z1]), ...fix([x1, yMm, z1])]),
      uv: new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]),
      tex: buildCoronalTexture(yIndex),
    };
    mprPlaneGeo.sagittal = {
      positions: new Float32Array([...fix([xMm, y0, z0]), ...fix([xMm, y1, z0]), ...fix([xMm, y0, z1]), ...fix([xMm, y1, z1])]),
      uv: new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]),
      tex: buildSagittalTexture(xIndex),
    };

    document.getElementById("mpr-axial-value").textContent = zMm.toFixed(0) + " mm";
    document.getElementById("mpr-coronal-value").textContent = yMm.toFixed(0) + " mm";
    document.getElementById("mpr-sagittal-value").textContent = xMm.toFixed(0) + " mm";

    for (const [tex, geo] of [[mprTexAxial, mprPlaneGeo.axial], [mprTexCoronal, mprPlaneGeo.coronal], [mprTexSagittal, mprPlaneGeo.sagittal]]) {
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, geo.tex.w, geo.tex.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, geo.tex.data);
    }
  }

  // Three mutually perpendicular planes meet along 1-pixel-wide lines; at
  // grazing angles that seam z-fights (flickers/staircases) because the
  // depth buffer can't tell the crossing planes apart. A small, distinct
  // polygonOffset per plane gives their intersection a stable, consistent
  // winner instead of a coin-flip per pixel — the standard fix for this in
  // any multiplanar-reconstruction renderer.
  const MPR_PLANE_ORDER = [
    ["axial", mprTexAxial, 1],
    ["coronal", mprTexCoronal, 2],
    ["sagittal", mprTexSagittal, 3],
  ];
  const MPR_PLANE_COLORS = {
    axial: [0.36, 0.56, 0.74],
    coronal: [0.47, 0.62, 0.38],
    sagittal: [0.78, 0.42, 0.36],
  };
  const mprBorderPosBuf = gl.createBuffer(), mprBorderColorBuf = gl.createBuffer();

  function drawMprPlanes(view, proj) {
    if (!mprPlaneGeo.axial) return;
    gl.useProgram(planeProgram);
    gl.uniformMatrix4fv(uModelViewP, false, view);
    gl.uniformMatrix4fv(uProjectionP, false, proj);
    gl.disable(gl.CULL_FACE);
    gl.enable(gl.DEPTH_TEST); gl.depthMask(true); gl.disable(gl.BLEND);
    gl.enable(gl.POLYGON_OFFSET_FILL);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(uTextureP, 0);
    for (const [name, tex, offsetUnits] of MPR_PLANE_ORDER) {
      const geo = mprPlaneGeo[name];
      gl.polygonOffset(0, offsetUnits);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.bindBuffer(gl.ARRAY_BUFFER, mprPosBuf);
      gl.bufferData(gl.ARRAY_BUFFER, geo.positions, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(aPositionP);
      gl.vertexAttribPointer(aPositionP, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, mprUvBuf);
      gl.bufferData(gl.ARRAY_BUFFER, geo.uv, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(aTexCoordP);
      gl.vertexAttribPointer(aTexCoordP, 2, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);
    gl.enable(gl.CULL_FACE);
    drawMprPlaneBorders(view, proj);
  }

  function drawMprPlaneBorders(view, proj) {
    gl.useProgram(lineColorProgram);
    gl.uniformMatrix4fv(uModelViewLC, false, view);
    gl.uniformMatrix4fv(uProjectionLC, false, proj);
    gl.uniform1f(uAlphaLC, 0.95);
    gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(0, -1);
    for (const name of ["axial", "coronal", "sagittal"]) {
      const geo = mprPlaneGeo[name];
      const p = geo.positions;
      // TRIANGLE_STRIP order is TL,TR,BL,BR; walk the perimeter TL->TR->BR->BL.
      const loop = new Float32Array([
        p[0], p[1], p[2], p[3], p[4], p[5], p[9], p[10], p[11], p[6], p[7], p[8],
      ]);
      const c = MPR_PLANE_COLORS[name];
      const colors = new Float32Array([c[0], c[1], c[2], c[0], c[1], c[2], c[0], c[1], c[2], c[0], c[1], c[2]]);
      gl.bindBuffer(gl.ARRAY_BUFFER, mprBorderPosBuf);
      gl.bufferData(gl.ARRAY_BUFFER, loop, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(aPositionLC);
      gl.vertexAttribPointer(aPositionLC, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, mprBorderColorBuf);
      gl.bufferData(gl.ARRAY_BUFFER, colors, gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(aColorLC);
      gl.vertexAttribPointer(aColorLC, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.LINE_LOOP, 0, 4);
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);
  }

  // Ghostly translucent mesh drawn around the MPR box for context — the
  // same layered look as the reference video (the organ's silhouette
  // visible around the slice planes and fiber-like lines inside it).
  function drawMprGhostMesh(view, proj) {
    if (!currentMesh) return;
    gl.useProgram(program);
    gl.uniformMatrix4fv(uModelView, false, view);
    gl.uniformMatrix4fv(uProjection, false, proj);
    gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
    gl.uniform3fv(uColor, currentColor);
    gl.uniform3fv(uOffset, [0, 0, 0]);
    gl.uniform3fv(uClipNormal, [1, 0, 0]);
    gl.uniform1f(uClipValue, 1e9);
    gl.uniform1f(uClipEnabled, 0.0);
    gl.uniform1f(uAlpha, 0.15);
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.depthMask(false); gl.disable(gl.CULL_FACE); gl.enable(gl.DEPTH_TEST);
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);
    gl.depthMask(true); gl.enable(gl.CULL_FACE); gl.disable(gl.BLEND);
  }

  // ---- gradient-orientation field (approximate, NOT tractography) ----
  let gradientLineData = null;
  const gradRibbonBuf = gl.createBuffer();
  const RIBBON_STRIDE = 10; // px,py,pz, ox,oy,oz, side, r,g,b
  let gradRibbonWidthMm = 0.5;
  function pushRibbonSegment(arr, p0, p1, r, g, b) {
    const verts = [[p0, -1], [p0, 1], [p1, -1], [p0, 1], [p1, 1], [p1, -1]];
    for (const [p, side] of verts) {
      const other = p === p0 ? p1 : p0;
      arr.push(p[0], p[1], p[2], other[0], other[1], other[2], side, r, g, b);
    }
  }

  function computeGradientField() {
    if (!sv) { gradientLineData = null; return; }
    const meta = ORGAN_META[currentOrganKey];
    const [nz, ny, nx] = sv.shape;
    const [ox, oy, oz] = sv.origin;
    const [sx, sy, sz] = sv.spacing;
    const frac = (meta.threshold_native - sv.valueMin) / (sv.valueMax - sv.valueMin);
    const quantThreshold = Math.max(0, Math.min(255, Math.round(frac * 255)));
    const below = meta.threshold_below;
    const key = currentOrganKey;

    const strideX = Math.max(1, Math.round(nx / 28));
    const strideY = Math.max(1, Math.round(ny / 28));
    const strideZ = Math.max(1, Math.round(nz / 28));
    const stepMm = Math.max(sx, sy, sz) * 0.75;
    const STEPS = 6; // per direction from the seed, so up to 12 short segments form one flowing streamline
    gradRibbonWidthMm = stepMm * 0.16; // thin relative to segment length, or it reads as confetti instead of a strand

    function isTissueAt(xi, yi, zi) {
      const v = sv.voxels[zi * ny * nx + yi * nx + xi];
      return below ? v < quantThreshold : v > quantThreshold;
    }
    function gradAt(xi, yi, zi) {
      const idx = zi * ny * nx + yi * nx + xi;
      const drx = sv.voxels[idx + 1] - sv.voxels[idx - 1];
      const dry = sv.voxels[idx + nx] - sv.voxels[idx - nx];
      const drz = sv.voxels[idx + ny * nx] - sv.voxels[idx - ny * nx];
      return [drx, dry, drz, Math.hypot(drx, dry, drz)];
    }

    // Short traced streamlets, not single straight spikes: from each seed,
    // step a few times each way following the *local* gradient at every
    // step (recomputed per step, so the path curves with the real data)
    // instead of one straight segment along the seed's own gradient.
    const ribbon = [];
    for (let z = strideZ; z < nz - strideZ; z += strideZ) {
      for (let y = strideY; y < ny - strideY; y += strideY) {
        for (let x = strideX; x < nx - strideX; x += strideX) {
          if (!isTissueAt(x, y, z)) continue;
          const [drx0, dry0, drz0, rawMag0] = gradAt(x, y, z);
          if (rawMag0 < 14) continue;
          const gx0 = drx0 / (2 * sx), gy0 = dry0 / (2 * sy), gz0 = drz0 / (2 * sz);
          const mag0 = Math.hypot(gx0, gy0, gz0) || 1;
          const r = Math.abs(gx0 / mag0), g = Math.abs(gy0 / mag0), b = Math.abs(gz0 / mag0);

          for (const sign of [1, -1]) {
            let fx = x, fy = y, fz = z;
            let prev = [ox + fx * sx, oy + fy * sy, oz + fz * sz];
            for (let step = 0; step < STEPS; step++) {
              const xi = Math.max(1, Math.min(nx - 2, Math.round(fx)));
              const yi = Math.max(1, Math.min(ny - 2, Math.round(fy)));
              const zi = Math.max(1, Math.min(nz - 2, Math.round(fz)));
              if (!isTissueAt(xi, yi, zi)) break;
              const [drx, dry, drz, rawMag] = gradAt(xi, yi, zi);
              if (rawMag < 8) break;
              const gx = drx / (2 * sx), gy = dry / (2 * sy), gz = drz / (2 * sz);
              const mag = Math.hypot(gx, gy, gz) || 1;
              const dx = sign * gx / mag, dy = sign * gy / mag, dz = sign * gz / mag;
              const next = [prev[0] + dx * stepMm, prev[1] + dy * stepMm, prev[2] + dz * stepMm];
              const p0 = applyDisplayFixPoint(key, prev[0], prev[1], prev[2]);
              const p1 = applyDisplayFixPoint(key, next[0], next[1], next[2]);
              pushRibbonSegment(ribbon, p0, p1, r, g, b);
              prev = next;
              fx += dx * stepMm / sx; fy += dy * stepMm / sy; fz += dz * stepMm / sz;
              if (fx < 1 || fy < 1 || fz < 1 || fx > nx - 2 || fy > ny - 2 || fz > nz - 2) break;
            }
          }
        }
      }
    }
    const data = new Float32Array(ribbon);
    gradientLineData = { data, count: data.length / RIBBON_STRIDE };
    gl.bindBuffer(gl.ARRAY_BUFFER, gradRibbonBuf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
  }

  function drawGradientField(view, proj) {
    if (!gradientLineData || gradientLineData.count === 0) return;
    gl.useProgram(ribbonProgram);
    gl.uniformMatrix4fv(uModelViewR, false, view);
    gl.uniformMatrix4fv(uProjectionR, false, proj);
    gl.uniform1f(uAlphaR, 0.62);
    gl.uniform1f(uWidthR, gradRibbonWidthMm);
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE); // additive: crossing strands glow instead of just occluding
    gl.depthMask(false); gl.enable(gl.DEPTH_TEST);
    const stride = RIBBON_STRIDE * 4;
    gl.bindBuffer(gl.ARRAY_BUFFER, gradRibbonBuf);
    gl.enableVertexAttribArray(aPositionR); gl.vertexAttribPointer(aPositionR, 3, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(aOtherR); gl.vertexAttribPointer(aOtherR, 3, gl.FLOAT, false, stride, 12);
    gl.enableVertexAttribArray(aSideR); gl.vertexAttribPointer(aSideR, 1, gl.FLOAT, false, stride, 24);
    gl.enableVertexAttribArray(aColorR); gl.vertexAttribPointer(aColorR, 3, gl.FLOAT, false, stride, 28);
    gl.drawArrays(gl.TRIANGLES, 0, gradientLineData.count);
    gl.depthMask(true); gl.disable(gl.BLEND);
  }

  const mprAxialSlider = document.getElementById("mpr-axial-slider");
  const mprCoronalSlider = document.getElementById("mpr-coronal-slider");
  const mprSagittalSlider = document.getElementById("mpr-sagittal-slider");
  const mprGradientToggle = document.getElementById("mpr-gradient-toggle");
  mprAxialSlider.addEventListener("input", () => { mprAxialFrac = Number(mprAxialSlider.value) / 100; rebuildMprPlanes(); });
  mprCoronalSlider.addEventListener("input", () => { mprCoronalFrac = Number(mprCoronalSlider.value) / 100; rebuildMprPlanes(); });
  mprSagittalSlider.addEventListener("input", () => { mprSagittalFrac = Number(mprSagittalSlider.value) / 100; rebuildMprPlanes(); });
  mprGradientToggle.addEventListener("change", () => {
    showGradientField = mprGradientToggle.checked;
    if (showGradientField) computeGradientField();
  });

  // =========================================================
  // Vuelo interior: a first-person camera auto-flies through the
  // real interior of the segmented mesh, following the tissue
  // centroid of each Z-slice of the actual volume — a genuine
  // (if approximate) central axis of this specimen, not a scripted
  // decorative path. The mesh is rendered front-face-culled so the
  // camera, sitting inside a closed surface, sees its interior wall.
  // =========================================================
  let flyPath = null, flyT = 0, flyDir = 1, flyPlaying = true;
  const flyPlayBtn = document.getElementById("fly-play-btn");
  const flySpeedSlider = document.getElementById("fly-speed-slider");
  const flyProgressNoteEl = document.getElementById("fly-progress-note");

  function computeFlyPath() {
    flyPath = null;
    if (!sv) return;
    const meta = ORGAN_META[currentOrganKey];
    const [nz, ny, nx] = sv.shape;
    const [ox, oy, oz] = sv.origin;
    const [sx, sy, sz] = sv.spacing;
    const frac = (meta.threshold_native - sv.valueMin) / (sv.valueMax - sv.valueMin);
    const quantThreshold = Math.max(0, Math.min(255, Math.round(frac * 255)));
    const below = meta.threshold_below;
    const key = currentOrganKey;

    const rawPts = [];
    for (let z = 0; z < nz; z++) {
      let sumX = 0, sumY = 0, count = 0;
      const zOff = z * ny * nx;
      for (let y = 0; y < ny; y++) {
        const rowOff = zOff + y * nx;
        for (let x = 0; x < nx; x++) {
          const v = sv.voxels[rowOff + x];
          if (below ? v < quantThreshold : v > quantThreshold) { sumX += x; sumY += y; count++; }
        }
      }
      if (count < 12) continue; // too little real tissue on this slice to trust a centroid
      const cx = ox + (sumX / count) * sx, cy = oy + (sumY / count) * sy, cz = oz + z * sz;
      rawPts.push(applyDisplayFixPoint(key, cx, cy, cz));
    }
    if (rawPts.length < 3) return;
    // light 3-point smoothing so the camera doesn't jitter slice-to-slice
    flyPath = rawPts.map((p, i) => {
      const a = rawPts[Math.max(0, i - 1)], b = rawPts[Math.min(rawPts.length - 1, i + 1)];
      return [(a[0] + p[0] + b[0]) / 3, (a[1] + p[1] + b[1]) / 3, (a[2] + p[2] + b[2]) / 3];
    });
    flyT = 0; flyDir = 1;
  }

  function flyEyeLook() {
    const path = flyPath, n = path.length;
    const f = flyT * (n - 1);
    const i0 = Math.max(0, Math.min(n - 2, Math.floor(f)));
    const frac = f - i0;
    const p0 = path[i0], p1 = path[i0 + 1];
    const eye = [p0[0] + (p1[0]-p0[0])*frac, p0[1] + (p1[1]-p0[1])*frac, p0[2] + (p1[2]-p0[2])*frac];
    const look = path[Math.min(n - 1, i0 + 2)];
    return { eye, look };
  }

  function updateFlyProgress() {
    if (!flyPlaying || !flyPath) return;
    const fracPerFrame = (Number(flySpeedSlider.value) / 100) * 0.00167;
    flyT += flyDir * fracPerFrame;
    if (flyT >= 1) { flyT = 1; flyDir = -1; } else if (flyT <= 0) { flyT = 0; flyDir = 1; }
    flyProgressNoteEl.textContent = flyDir > 0 ? "recorriendo →" : "← de regreso";
  }

  function drawFlyInterior(view, proj) {
    gl.useProgram(program);
    gl.uniformMatrix4fv(uModelView, false, view);
    gl.uniformMatrix4fv(uProjection, false, proj);
    gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
    gl.uniform3fv(uColor, currentColor);
    gl.uniform3fv(uOffset, [0, 0, 0]);
    gl.uniform3fv(uClipNormal, [1, 0, 0]);
    gl.uniform1f(uClipValue, 1e9);
    gl.uniform1f(uClipEnabled, 0.0);
    gl.uniform1f(uAlpha, 1.0);
    gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE); gl.cullFace(gl.FRONT); // camera sits inside a closed mesh: show its interior wall
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);
    gl.cullFace(gl.BACK);
  }

  flyPlayBtn.addEventListener("click", () => {
    flyPlaying = !flyPlaying;
    flyPlayBtn.textContent = flyPlaying ? "Pausar" : "Reanudar";
    flyPlayBtn.setAttribute("aria-pressed", String(flyPlaying));
  });

  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return new Float32Array([f/aspect,0,0,0, 0,f,0,0, 0,0,(far+near)*nf,-1, 0,0,2*far*near*nf,0]);
  }
  function lookAt(eye, target, up) {
    let zx=eye[0]-target[0], zy=eye[1]-target[1], zz=eye[2]-target[2];
    let zl=Math.hypot(zx,zy,zz)||1; zx/=zl; zy/=zl; zz/=zl;
    let xx=up[1]*zz-up[2]*zy, xy=up[2]*zx-up[0]*zz, xz=up[0]*zy-up[1]*zx;
    let xl=Math.hypot(xx,xy,xz)||1; xx/=xl; xy/=xl; xz/=xl;
    const yx=zy*xz-zz*xy, yy=zz*xx-zx*xz, yz=zx*xy-zy*xx;
    return new Float32Array([xx,yx,zx,0, xy,yy,zy,0, xz,yz,zz,0,
      -(xx*eye[0]+xy*eye[1]+xz*eye[2]), -(yx*eye[0]+yy*eye[1]+yz*eye[2]), -(zx*eye[0]+zy*eye[1]+zz*eye[2]), 1]);
  }
  function normalMat3(m) { return new Float32Array([m[0],m[1],m[2], m[4],m[5],m[6], m[8],m[9],m[10]]); }

  let currentMesh = null, currentColor = [0.7,0.7,0.7], boundingRadius = 1;
  let theta = 0.6, phi = 1.15, radius = 1, targetRadius = 1;
  let reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let autoRotate = !reduceMotion;
  let dragging = false, lastX = 0, lastY = 0;

  function frameCamera(mesh) {
    boundingRadius = 1;
    const c = mesh.center;
    meshBoundsMin = [Infinity, Infinity, Infinity];
    meshBoundsMax = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < mesh.positions.length; i += 3) {
      const x = mesh.positions[i], y = mesh.positions[i+1], z = mesh.positions[i+2];
      const d = Math.hypot(x-c[0], y-c[1], z-c[2]);
      if (d > boundingRadius) boundingRadius = d;
      if (x < meshBoundsMin[0]) meshBoundsMin[0] = x; if (x > meshBoundsMax[0]) meshBoundsMax[0] = x;
      if (y < meshBoundsMin[1]) meshBoundsMin[1] = y; if (y > meshBoundsMax[1]) meshBoundsMax[1] = y;
      if (z < meshBoundsMin[2]) meshBoundsMin[2] = z; if (z > meshBoundsMax[2]) meshBoundsMax[2] = z;
    }
    radius = boundingRadius * 2.6; targetRadius = radius;
  }
  function uploadMesh(mesh) {
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.bufferData(gl.ARRAY_BUFFER, mesh.positions, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.bufferData(gl.ARRAY_BUFFER, mesh.normals, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);
    const edges = buildEdgeIndices(mesh.indices);
    edgeCount = edges.length;
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, edgeBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, edges, gl.STATIC_DRAW);
  }

  /* =========================================================
     3D anatomical landmarks — computed from the mesh's own
     geometry (connected components, extremities, local surface
     concavity), never from a fixed/guessed coordinate. Where no
     reliable geometric signal exists (liver), no landmark is shown
     rather than a fabricated one — see the chat discussion this
     scope came out of.
     ========================================================= */
  function vertexPos(positions, i) { return [positions[i*3], positions[i*3+1], positions[i*3+2]]; }

  function adjacencyFromEdges(edges, numVertices) {
    const adj = new Array(numVertices);
    for (let i = 0; i < numVertices; i++) adj[i] = [];
    for (let i = 0; i < edges.length; i += 2) {
      const a = edges[i], b = edges[i+1];
      adj[a].push(b); adj[b].push(a);
    }
    return adj;
  }

  function centroidOf(positions, verts) {
    let sx = 0, sy = 0, sz = 0;
    for (const v of verts) { sx += positions[v*3]; sy += positions[v*3+1]; sz += positions[v*3+2]; }
    const n = verts.length || 1;
    return [sx/n, sy/n, sz/n];
  }

  // Lungs: the pipeline finds left and right lung as genuinely separate
  // components, but the demo's decimated preview mesh (heavily reduced
  // for a lighter file) can bridge them back into one connected surface,
  // so component-splitting isn't reliable here. Instead, split vertices
  // by the DICOM/ITK coordinate convention this project already documents
  // (X increases toward the patient's LEFT) — real measurement, not a
  // guess, and robust to how the preview mesh happens to be connected.
  function computeLungLandmarks(mesh) {
    const numVerts = mesh.positions.length / 3;
    const midX = (meshBoundsMin[0] + meshBoundsMax[0]) / 2;
    const vertsLeft = [], vertsRight = [];
    for (let i = 0; i < numVerts; i++) {
      (mesh.positions[i*3] > midX ? vertsLeft : vertsRight).push(i);
    }
    if (!vertsLeft.length || !vertsRight.length) return [];
    return [
      {label: "Pulmón izquierdo", pos: centroidOf(mesh.positions, vertsLeft)},
      {label: "Pulmón derecho", pos: centroidOf(mesh.positions, vertsRight)},
    ];
  }

  // Heart: apex (the tapered extremity) is the point farthest from the
  // mesh centroid; base (broad end, where the great vessels attach) is
  // taken as the point farthest from the apex. Both are shape-intrinsic —
  // they don't depend on knowing the scanner's mounting orientation,
  // which for an ex-vivo specimen we don't have ground truth for.
  function computeHeartLandmarks(mesh) {
    const numVerts = mesh.positions.length / 3;
    const c = mesh.center;
    let apexIdx = 0, apexDist = -1;
    for (let i = 0; i < numVerts; i++) {
      const dx = mesh.positions[i*3]-c[0], dy = mesh.positions[i*3+1]-c[1], dz = mesh.positions[i*3+2]-c[2];
      const d = dx*dx + dy*dy + dz*dz;
      if (d > apexDist) { apexDist = d; apexIdx = i; }
    }
    const apex = vertexPos(mesh.positions, apexIdx);
    let baseIdx = 0, baseDist = -1;
    for (let i = 0; i < numVerts; i++) {
      const dx = mesh.positions[i*3]-apex[0], dy = mesh.positions[i*3+1]-apex[1], dz = mesh.positions[i*3+2]-apex[2];
      const d = dx*dx + dy*dy + dz*dz;
      if (d > baseDist) { baseDist = d; baseIdx = i; }
    }
    return [{label: "Ápex (punta)", pos: apex}, {label: "Base", pos: vertexPos(mesh.positions, baseIdx)}];
  }

  // Kidney: the hilum is the concave notch where vessels/ureter enter —
  // geometrically, a point whose neighbors sit consistently farther from
  // the centroid than it does (a local dimple). Found directly from mesh
  // adjacency, not placed by hand.
  function computeKidneyLandmarks(mesh) {
    const numVerts = mesh.positions.length / 3;
    const adj = adjacencyFromEdges(buildEdgeIndices(mesh.indices), numVerts);
    const c = mesh.center;
    const dist = new Float32Array(numVerts);
    for (let i = 0; i < numVerts; i++) {
      const dx = mesh.positions[i*3]-c[0], dy = mesh.positions[i*3+1]-c[1], dz = mesh.positions[i*3+2]-c[2];
      dist[i] = Math.sqrt(dx*dx + dy*dy + dz*dz);
    }
    let bestIdx = -1, bestScore = -Infinity;
    for (let i = 0; i < numVerts; i++) {
      const nbrs = adj[i];
      if (nbrs.length < 4) continue;
      let sum = 0;
      for (const nb of nbrs) sum += dist[nb];
      const concavity = (sum / nbrs.length) - dist[i];
      if (concavity > bestScore) { bestScore = concavity; bestIdx = i; }
    }
    const landmarks = [];
    if (bestIdx !== -1) landmarks.push({label: "Hilio renal (aprox.)", pos: vertexPos(mesh.positions, bestIdx)});

    // Poles: the two extremities along the mesh's longest axis — a kidney
    // is reliably elongated pole-to-pole, so this is shape-intrinsic, same
    // idea as the heart's apex/base. Not labeled superior/inferior: unlike
    // the heart's apex (a single unambiguous point), both kidney poles look
    // similar, so there's no honest way to tell which is which from shape
    // alone on an isolated ex-vivo specimen.
    const extent = [meshBoundsMax[0]-meshBoundsMin[0], meshBoundsMax[1]-meshBoundsMin[1], meshBoundsMax[2]-meshBoundsMin[2]];
    let axis = 0;
    if (extent[1] > extent[axis]) axis = 1;
    if (extent[2] > extent[axis]) axis = 2;
    let loIdx = 0, loVal = Infinity, hiIdx = 0, hiVal = -Infinity;
    for (let i = 0; i < numVerts; i++) {
      const v = mesh.positions[i*3 + axis];
      if (v < loVal) { loVal = v; loIdx = i; }
      if (v > hiVal) { hiVal = v; hiIdx = i; }
    }
    landmarks.push({label: "Polo A", pos: vertexPos(mesh.positions, loIdx)});
    landmarks.push({label: "Polo B", pos: vertexPos(mesh.positions, hiIdx)});
    return landmarks;
  }

  // Liver: split into two halves along the mesh's longest bounding-box
  // axis (verified for this specimen to be its left-right axis — see the
  // per-axis mass-asymmetry analysis in the redesign notes) and label the
  // bigger half "right lobe": the liver's right lobe being markedly larger
  // than the left is one of the most consistent facts in gross anatomy, so
  // this infers WHICH part is which from a real, well-established size
  // relationship — not from trusting an unverified mount direction.
  function computeLiverLandmarks(mesh) {
    const numVerts = mesh.positions.length / 3;
    const extent = [meshBoundsMax[0]-meshBoundsMin[0], meshBoundsMax[1]-meshBoundsMin[1], meshBoundsMax[2]-meshBoundsMin[2]];
    let axis = 0;
    if (extent[1] > extent[axis]) axis = 1;
    if (extent[2] > extent[axis]) axis = 2;
    const mid = (meshBoundsMin[axis] + meshBoundsMax[axis]) / 2;
    const vertsA = [], vertsB = [];
    for (let i = 0; i < numVerts; i++) {
      (mesh.positions[i*3 + axis] < mid ? vertsA : vertsB).push(i);
    }
    if (!vertsA.length || !vertsB.length) return [];
    const [bigger, smaller] = vertsA.length >= vertsB.length ? [vertsA, vertsB] : [vertsB, vertsA];
    return [
      {label: "Lóbulo derecho (mayor)", pos: centroidOf(mesh.positions, bigger)},
      {label: "Lóbulo izquierdo (menor)", pos: centroidOf(mesh.positions, smaller)},
    ];
  }

  // Brain: split into two halves along whichever bounding-box axis is
  // narrowest (for a brain, that's reliably the left-right axis,
  // regardless of how the specimen happened to sit in the scanner) —
  // labeled generically since we don't have verified orientation for
  // this ex-vivo mount to claim which half is anatomically left vs right.
  function computeBrainLandmarks(mesh) {
    const numVerts = mesh.positions.length / 3;
    const extent = [meshBoundsMax[0]-meshBoundsMin[0], meshBoundsMax[1]-meshBoundsMin[1], meshBoundsMax[2]-meshBoundsMin[2]];
    let axis = 0;
    if (extent[1] < extent[axis]) axis = 1;
    if (extent[2] < extent[axis]) axis = 2;
    const mid = (meshBoundsMin[axis] + meshBoundsMax[axis]) / 2;
    const vertsA = [], vertsB = [];
    for (let i = 0; i < numVerts; i++) {
      (mesh.positions[i*3 + axis] < mid ? vertsA : vertsB).push(i);
    }
    return [
      {label: "Hemisferio 1", pos: centroidOf(mesh.positions, vertsA)},
      {label: "Hemisferio 2", pos: centroidOf(mesh.positions, vertsB)},
    ];
  }

  function computeLandmarksFor(key, mesh) {
    if (key === "lungs") return computeLungLandmarks(mesh);
    if (key === "heart") return computeHeartLandmarks(mesh);
    if (key === "kidneys") return computeKidneyLandmarks(mesh);
    if (key === "brain") return computeBrainLandmarks(mesh);
    if (key === "liver") return computeLiverLandmarks(mesh);
    return [];
  }

  let currentLandmarks = [];
  let labelEls = [];
  let labelsVisible = true;
  const labelLayerEl = document.getElementById("label-layer");
  const labelsToggleBtn = document.getElementById("labels-toggle-btn");
  labelsToggleBtn.addEventListener("click", () => {
    labelsVisible = !labelsVisible;
    labelsToggleBtn.setAttribute("aria-pressed", String(labelsVisible));
    labelsToggleBtn.title = "Etiquetas anatómicas: " + (labelsVisible ? "visibles" : "ocultas");
    labelLayerEl.classList.toggle("hidden", !labelsVisible);
  });

  function rebuildLabelEls() {
    labelLayerEl.innerHTML = "";
    labelEls = currentLandmarks.map((lm) => {
      const el = document.createElement("div");
      el.className = "landmark-label";
      el.textContent = lm.label;
      labelLayerEl.appendChild(el);
      return el;
    });
  }

  function projectToScreen(pos, view, proj) {
    const vx = view[0]*pos[0]+view[4]*pos[1]+view[8]*pos[2]+view[12];
    const vy = view[1]*pos[0]+view[5]*pos[1]+view[9]*pos[2]+view[13];
    const vz = view[2]*pos[0]+view[6]*pos[1]+view[10]*pos[2]+view[14];
    const vw = view[3]*pos[0]+view[7]*pos[1]+view[11]*pos[2]+view[15];
    const cx = proj[0]*vx+proj[4]*vy+proj[8]*vz+proj[12]*vw;
    const cy = proj[1]*vx+proj[5]*vy+proj[9]*vz+proj[13]*vw;
    const cw = proj[3]*vx+proj[7]*vy+proj[11]*vz+proj[15]*vw;
    if (cw <= 0.001) return null;
    const ndcX = cx / cw, ndcY = cy / cw;
    if (ndcX < -1.3 || ndcX > 1.3 || ndcY < -1.3 || ndcY > 1.3) return null;
    return [(ndcX*0.5+0.5) * canvas.clientWidth, (1-(ndcY*0.5+0.5)) * canvas.clientHeight];
  }

  canvas.addEventListener("pointerdown", e => {
    if (measureEnabled) { handleMeasureClick(e); return; }
    dragging = true; autoRotate = false; lastX = e.clientX; lastY = e.clientY; canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointerup", () => dragging = false);
  canvas.addEventListener("pointermove", e => {
    if (!dragging) return;
    theta -= (e.clientX - lastX) * 0.008; phi -= (e.clientY - lastY) * 0.008;
    phi = Math.max(0.15, Math.min(Math.PI - 0.15, phi));
    lastX = e.clientX; lastY = e.clientY;
  });
  canvas.addEventListener("wheel", e => {
    e.preventDefault();
    targetRadius = Math.max(boundingRadius*1.15, Math.min(boundingRadius*6, targetRadius * Math.pow(1.0012, e.deltaY)));
  }, {passive: false});

  // ---- camera view presets (Anterior/Posterior/Left/Right/Superior/Inferior/Isometric) ----
  // theta/phi are spherical angles of the orbit camera around the mesh
  // center (see the eye computation in render3d): phi is polar angle from
  // +Y, theta is azimuth around Y.
  //
  // For LUNGS these targets are real, verified patient-anatomical
  // directions: the source CTChest.nrrd carries a real DICOM-style
  // direction/origin (confirmed from its NRRD header: "space:
  // left-posterior-superior", identity direction matrix), which the
  // pipeline's index_to_world carries straight through to mesh vertex
  // coordinates (see core/mesh.py). So in mesh space: +X = patient Left,
  // +Y = Posterior, +Z = Superior — the mapping below inverts that to give
  // each button's eye position (the camera sits on the named side,
  // looking back toward the center).
  //
  // For the ex-vivo synchrotron organs (heart/liver/kidneys/brain) this
  // metadata does not exist — those specimens were physically mounted in
  // the scanner's sample tube however was convenient, not in a documented
  // patient pose (see docs/ORGAN_PIPELINES.md and the load_volume()
  // docstring). For those, the same buttons are a fixed *display*
  // convention, not a verified direction — the UI caveats this explicitly
  // per organ (see caveatOrientationNote below).
  const CAMERA_VIEWS = {
    front:  {theta: 0.001,        phi: Math.PI - 0.08}, // Anterior: mesh -Y
    back:   {theta: 0.001,        phi: 0.08},            // Posterior: mesh +Y
    left:   {theta: Math.PI / 2,  phi: Math.PI / 2},      // Left: mesh +X
    right:  {theta: -Math.PI / 2, phi: Math.PI / 2},      // Right: mesh -X
    top:    {theta: 0,            phi: Math.PI / 2},      // Superior: mesh +Z
    bottom: {theta: Math.PI,      phi: Math.PI / 2},      // Inferior: mesh -Z
    iso:    {theta: -Math.PI / 4, phi: 1.15},
  };
  function setCameraView(name) {
    const v = CAMERA_VIEWS[name];
    if (!v) return;
    theta = v.theta; phi = v.phi; targetRadius = boundingRadius * 2.6;
    autoRotate = false;
  }
  function fitAndReset() {
    const meta = ORGAN_META[currentOrganKey];
    theta = meta.initial_theta; phi = meta.initial_phi; targetRadius = boundingRadius * 2.6;
    autoRotate = !reduceMotion;
  }
  document.getElementById("fit-btn").addEventListener("click", fitAndReset);
  document.getElementById("viewport-toolbar").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-view]");
    if (!btn) return;
    setCameraView(btn.dataset.view);
  });

  // ---- axis gizmo: small always-on corner indicator of X/Y/Z orientation ----
  const gizmoCanvas = document.getElementById("axis-gizmo-canvas");
  const gizmoCtx = gizmoCanvas.getContext("2d");
  function drawAxisGizmo(view) {
    const cx = 32, cy = 32, len = 20;
    gizmoCtx.clearRect(0, 0, 64, 64);
    const axes = [
      {v: [1,0,0], color: "#c76b5c", label: "X"},
      {v: [0,1,0], color: "#789e61", label: "Y"},
      {v: [0,0,1], color: "#5c8fbd", label: "Z"},
    ];
    const projected = axes.map(a => {
      const vx = view[0]*a.v[0]+view[4]*a.v[1]+view[8]*a.v[2];
      const vy = view[1]*a.v[0]+view[5]*a.v[1]+view[9]*a.v[2];
      const vz = view[2]*a.v[0]+view[6]*a.v[1]+view[10]*a.v[2];
      return {...a, sx: cx + vx*len, sy: cy - vy*len, z: vz};
    }).sort((a,b) => a.z - b.z);
    for (const a of projected) {
      gizmoCtx.strokeStyle = a.color; gizmoCtx.lineWidth = 2;
      gizmoCtx.beginPath(); gizmoCtx.moveTo(cx, cy); gizmoCtx.lineTo(a.sx, a.sy); gizmoCtx.stroke();
      gizmoCtx.fillStyle = a.color;
      gizmoCtx.beginPath(); gizmoCtx.arc(a.sx, a.sy, 4.5, 0, Math.PI*2); gizmoCtx.fill();
      gizmoCtx.fillStyle = "#fff"; gizmoCtx.font = "9px sans-serif"; gizmoCtx.textAlign = "center"; gizmoCtx.textBaseline = "middle";
      gizmoCtx.fillText(a.label, a.sx, a.sy);
    }
  }

  // ---- export: serialize the mesh already loaded in the browser to STL/OBJ ----
  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  function meshToStlBlob(mesh) {
    const triCount = mesh.indices.length / 3;
    const buf = new ArrayBuffer(84 + triCount * 50);
    const view = new DataView(buf);
    const header = "Medical3DReconstruction export";
    for (let i = 0; i < header.length; i++) view.setUint8(i, header.charCodeAt(i));
    view.setUint32(80, triCount, true);
    let off = 84;
    const p = mesh.positions;
    for (let t = 0; t < triCount; t++) {
      const i0 = mesh.indices[t*3] * 3, i1 = mesh.indices[t*3+1] * 3, i2 = mesh.indices[t*3+2] * 3;
      const ax = p[i0], ay = p[i0+1], az = p[i0+2];
      const bx = p[i1], by = p[i1+1], bz = p[i1+2];
      const cx = p[i2], cy = p[i2+1], cz = p[i2+2];
      const ux = bx-ax, uy = by-ay, uz = bz-az;
      const vx = cx-ax, vy = cy-ay, vz = cz-az;
      let nx = uy*vz - uz*vy, ny = uz*vx - ux*vz, nz = ux*vy - uy*vx;
      const nl = Math.hypot(nx, ny, nz) || 1;
      nx /= nl; ny /= nl; nz /= nl;
      view.setFloat32(off, nx, true); view.setFloat32(off+4, ny, true); view.setFloat32(off+8, nz, true);
      view.setFloat32(off+12, ax, true); view.setFloat32(off+16, ay, true); view.setFloat32(off+20, az, true);
      view.setFloat32(off+24, bx, true); view.setFloat32(off+28, by, true); view.setFloat32(off+32, bz, true);
      view.setFloat32(off+36, cx, true); view.setFloat32(off+40, cy, true); view.setFloat32(off+44, cz, true);
      view.setUint16(off+48, 0, true);
      off += 50;
    }
    return new Blob([buf], {type: "model/stl"});
  }
  function meshToObjString(mesh) {
    const lines = ["# Medical3DReconstruction export", `# ${ORGAN_META[currentOrganKey].label} — ${mesh.numVertices} vértices, ${mesh.numTriangles} triángulos`];
    const p = mesh.positions, n = mesh.normals;
    for (let i = 0; i < p.length; i += 3) lines.push(`v ${p[i]} ${p[i+1]} ${p[i+2]}`);
    for (let i = 0; i < n.length; i += 3) lines.push(`vn ${n[i]} ${n[i+1]} ${n[i+2]}`);
    for (let t = 0; t < mesh.indices.length; t += 3) {
      const a = mesh.indices[t]+1, b = mesh.indices[t+1]+1, c = mesh.indices[t+2]+1;
      lines.push(`f ${a}//${a} ${b}//${b} ${c}//${c}`);
    }
    return lines.join("\n");
  }
  const exportStatusEl = document.getElementById("export-status");
  function fmtBytes(n) { return n > 1e6 ? (n/1e6).toFixed(1)+" MB" : (n/1e3).toFixed(0)+" KB"; }
  document.getElementById("export-stl-btn").addEventListener("click", () => {
    if (!currentMesh) return;
    const blob = meshToStlBlob(currentMesh);
    downloadBlob(blob, `${currentOrganKey}.stl`);
    exportStatusEl.textContent = `Exportado: ${currentOrganKey}.stl (${fmtBytes(blob.size)})`;
  });
  document.getElementById("export-obj-btn").addEventListener("click", () => {
    if (!currentMesh) return;
    const text = meshToObjString(currentMesh);
    const blob = new Blob([text], {type: "text/plain"});
    downloadBlob(blob, `${currentOrganKey}.obj`);
    exportStatusEl.textContent = `Exportado: ${currentOrganKey}.obj (${fmtBytes(blob.size)})`;
  });

  // ---- measurement: point-to-point distance via CPU ray/triangle picking ----
  // The mesh's own vertex coordinates are already real millimeters (same
  // space as the "Centroide (mm)"/bounding box readouts), so a distance
  // between two picked surface points is a real physical measurement, not
  // an approximation from screen pixels.
  function rayTriangleHit(ox, oy, oz, dx, dy, dz, v0, v1, v2) {
    const EPS = 1e-7;
    const e1x = v1[0]-v0[0], e1y = v1[1]-v0[1], e1z = v1[2]-v0[2];
    const e2x = v2[0]-v0[0], e2y = v2[1]-v0[1], e2z = v2[2]-v0[2];
    const hx = dy*e2z - dz*e2y, hy = dz*e2x - dx*e2z, hz = dx*e2y - dy*e2x;
    const a = e1x*hx + e1y*hy + e1z*hz;
    if (Math.abs(a) < EPS) return null;
    const f = 1 / a;
    const sx = ox-v0[0], sy = oy-v0[1], sz = oz-v0[2];
    const u = f * (sx*hx + sy*hy + sz*hz);
    if (u < 0 || u > 1) return null;
    const qx = sy*e1z - sz*e1y, qy = sz*e1x - sx*e1z, qz = sx*e1y - sy*e1x;
    const v = f * (dx*qx + dy*qy + dz*qz);
    if (v < 0 || u+v > 1) return null;
    const t = f * (e2x*qx + e2y*qy + e2z*qz);
    return t > EPS ? t : null;
  }
  function pickMeshPoint(originArr, dirArr) {
    if (!currentMesh) return null;
    const [ox, oy, oz] = originArr, [dx, dy, dz] = dirArr;
    const p = currentMesh.positions, idx = currentMesh.indices;
    let bestT = Infinity;
    const v0 = [0,0,0], v1 = [0,0,0], v2 = [0,0,0];
    for (let t = 0; t < idx.length; t += 3) {
      const i0 = idx[t]*3, i1 = idx[t+1]*3, i2 = idx[t+2]*3;
      v0[0]=p[i0]; v0[1]=p[i0+1]; v0[2]=p[i0+2];
      v1[0]=p[i1]; v1[1]=p[i1+1]; v1[2]=p[i1+2];
      v2[0]=p[i2]; v2[1]=p[i2+1]; v2[2]=p[i2+2];
      const hit = rayTriangleHit(ox,oy,oz, dx,dy,dz, v0,v1,v2);
      if (hit !== null && hit < bestT) bestT = hit;
    }
    if (!isFinite(bestT)) return null;
    return [ox+dx*bestT, oy+dy*bestT, oz+dz*bestT];
  }
  function handleMeasureClick(e) {
    if (!currentMesh || (viewMode !== "solid" && viewMode !== "xray" && viewMode !== "wire")) return;
    const rect = canvas.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    const my = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    const c = currentMesh.center;
    const eye = [c[0]+radius*Math.sin(phi)*Math.sin(theta), c[1]+radius*Math.cos(phi), c[2]+radius*Math.sin(phi)*Math.cos(theta)];
    // camera basis, matching lookAt(eye, c, [0,1,0])
    let zx=eye[0]-c[0], zy=eye[1]-c[1], zz=eye[2]-c[2];
    let zl=Math.hypot(zx,zy,zz)||1; zx/=zl; zy/=zl; zz/=zl;
    let xx=1*zz-0*zy, xy=0*zx-0*zz, xz=0*zy-1*zx;
    let xl=Math.hypot(xx,xy,xz)||1; xx/=xl; xy/=xl; xz/=xl;
    const yx=zy*xz-zz*xy, yy=zz*xx-zx*xz, yz=zx*xy-zy*xx;
    const aspect = canvas.width / Math.max(1, canvas.height);
    const tanHalf = Math.tan((Math.PI/4.2) / 2);
    const dvx = mx*aspect*tanHalf, dvy = my*tanHalf, dvz = -1;
    let dirx = dvx*xx + dvy*yx + dvz*zx;
    let diry = dvx*xy + dvy*yy + dvz*zy;
    let dirz = dvx*xz + dvy*yz + dvz*zz;
    const dl = Math.hypot(dirx,diry,dirz)||1; dirx/=dl; diry/=dl; dirz/=dl;
    const hitPoint = pickMeshPoint(eye, [dirx, diry, dirz]);
    if (!hitPoint) return;
    if (measurePoints.length >= 2) measurePoints = [];
    measurePoints.push(hitPoint);
    updateMeasureReadout();
  }
  const measureLayerEl = document.getElementById("measure-layer");
  function dist3(a, b) { return Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]); }
  function updateMeasureOverlay(view, proj) {
    if (measurePoints.length === 0) { measureLayerEl.innerHTML = ""; return; }
    const screenPts = measurePoints.map((p) => projectToScreen(p, view, proj));
    let html = "";
    if (screenPts[0] && screenPts[1]) {
      html += `<svg style="position:absolute;inset:0;width:100%;height:100%;overflow:visible"><line x1="${screenPts[0][0]}" y1="${screenPts[0][1]}" x2="${screenPts[1][0]}" y2="${screenPts[1][1]}" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="4 3"/></svg>`;
    }
    for (const sp of screenPts) if (sp) html += `<div class="measure-dot" style="left:${sp[0]}px;top:${sp[1]}px"></div>`;
    if (screenPts[0] && screenPts[1]) {
      const mx = (screenPts[0][0]+screenPts[1][0])/2, my = (screenPts[0][1]+screenPts[1][1])/2;
      html += `<div class="measure-label" style="left:${mx}px;top:${my}px">${dist3(measurePoints[0], measurePoints[1]).toFixed(1)} mm</div>`;
    }
    measureLayerEl.innerHTML = html;
  }
  const measureReadoutRowEl = document.getElementById("measure-readout-row");
  const measureReadoutValueEl = document.getElementById("measure-readout-value");
  const measureClearBtn = document.getElementById("measure-clear-btn");
  function updateMeasureReadout() {
    if (measurePoints.length === 2) {
      measureReadoutRowEl.style.display = "";
      measureReadoutValueEl.textContent = dist3(measurePoints[0], measurePoints[1]).toFixed(1) + " mm";
      measureClearBtn.style.display = "";
    } else {
      measureReadoutRowEl.style.display = "none";
      measureClearBtn.style.display = measurePoints.length > 0 ? "" : "none";
    }
  }
  document.getElementById("measure-enabled").addEventListener("change", (e) => {
    measureEnabled = e.target.checked;
    if (!measureEnabled) { measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = ""; }
  });
  measureClearBtn.addEventListener("click", () => { measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = ""; });

  function resizeGl() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  function render3d() {
    resizeGl();
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.039, 0.055, 0.075, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    if (currentMesh) {
      radius += (targetRadius - radius) * 0.12;
      if (autoRotate) theta += 0.0022;
      const c = currentMesh.center;
      let eye, view, proj;
      if (viewMode === "fly" && flyPath) {
        updateFlyProgress();
        const fl = flyEyeLook();
        eye = fl.eye;
        view = lookAt(eye, fl.look, [0, 1, 0]);
        proj = perspective(Math.PI / 2.3, canvas.width / Math.max(1, canvas.height), Math.max(0.05, boundingRadius * 0.004), boundingRadius * 20);
      } else {
        eye = [c[0]+radius*Math.sin(phi)*Math.sin(theta), c[1]+radius*Math.cos(phi), c[2]+radius*Math.sin(phi)*Math.cos(theta)];
        view = lookAt(eye, c, [0,1,0]);
        proj = perspective(Math.PI/4.2, canvas.width/Math.max(1,canvas.height), Math.max(0.01,boundingRadius*0.02), boundingRadius*20);
      }
      const clip = clipUniformValues();
      drawAxisGizmo(view);
      updateMeasureOverlay(view, proj);

      if (viewMode === "fly" && flyPath) {
        drawFlyInterior(view, proj);
      } else if (viewMode === "mpr") {
        drawMprGhostMesh(view, proj);
        drawMprPlanes(view, proj);
        if (showGradientField) drawGradientField(view, proj);
      } else if (viewMode === "wire") {
        gl.useProgram(wireProgram);
        gl.uniformMatrix4fv(uModelViewW, false, view);
        gl.uniformMatrix4fv(uProjectionW, false, proj);
        gl.uniform3fv(uColorW, currentColor);
        gl.uniform1f(uAlphaW, 1.0);
        gl.uniform3fv(uClipNormalW, clip.normal);
        gl.uniform1f(uClipValueW, clip.value);
        gl.uniform1f(uClipEnabledW, clipEnabled ? 1.0 : 0.0);
        gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
        gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPositionW); gl.vertexAttribPointer(aPositionW, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, edgeBuf);
        gl.drawElements(gl.LINES, edgeCount, gl.UNSIGNED_INT, 0);
      } else {
        // Solid cap: when the clip plane slices a closed mesh open, the
        // interior would otherwise render as an empty hole (you'd see
        // straight through to the background). Draw the back-facing
        // triangles exposed by the cut — the mesh's own interior surface —
        // flat-shaded in a darker "cut tissue" tone first, so the cross
        // section reads as solid material, not a hollow shell.
        if (clipEnabled && viewMode === "solid") {
          gl.useProgram(wireProgram);
          gl.uniformMatrix4fv(uModelViewW, false, view);
          gl.uniformMatrix4fv(uProjectionW, false, proj);
          gl.uniform3fv(uColorW, [currentColor[0]*0.42, currentColor[1]*0.42, currentColor[2]*0.42]);
          gl.uniform1f(uAlphaW, 1.0);
          gl.uniform3fv(uClipNormalW, clip.normal);
          gl.uniform1f(uClipValueW, clip.value);
          gl.uniform1f(uClipEnabledW, 1.0);
          gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
          gl.enable(gl.CULL_FACE); gl.cullFace(gl.FRONT);
          gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPositionW); gl.vertexAttribPointer(aPositionW, 3, gl.FLOAT, false, 0, 0);
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
          gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);
          gl.cullFace(gl.BACK);
        }
        gl.useProgram(program);
        gl.uniformMatrix4fv(uModelView, false, view);
        gl.uniformMatrix4fv(uProjection, false, proj);
        gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
        gl.uniform3fv(uColor, currentColor);
        gl.uniform3fv(uOffset, [0, 0, 0]);
        gl.uniform3fv(uClipNormal, clip.normal);
        gl.uniform1f(uClipValue, clip.value);
        gl.uniform1f(uClipEnabled, clipEnabled ? 1.0 : 0.0);
        gl.uniform1f(uAlpha, alphaValue);
        if (viewMode === "xray") {
          gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
          gl.depthMask(false); gl.disable(gl.CULL_FACE);
        } else if (alphaValue < 0.999) {
          gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
          gl.depthMask(false); gl.enable(gl.CULL_FACE);
        } else {
          gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.CULL_FACE);
        }
        gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
        gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);
        gl.depthMask(true); gl.enable(gl.CULL_FACE); gl.disable(gl.BLEND);
      }

      if (labelsVisible && viewMode !== "mpr" && viewMode !== "fly") {
        for (let i = 0; i < currentLandmarks.length; i++) {
          const el = labelEls[i];
          if (!el) continue;
          const pos = currentLandmarks[i].pos;
          if (clipEnabled && (pos[0]*clip.normal[0]+pos[1]*clip.normal[1]+pos[2]*clip.normal[2]) > clip.value) {
            el.style.display = "none"; continue;
          }
          const screen = projectToScreen(pos, view, proj);
          if (!screen) { el.style.display = "none"; continue; }
          el.style.display = "";
          el.style.left = screen[0] + "px";
          el.style.top = screen[1] + "px";
        }
      }
    }
    requestAnimationFrame(render3d);
  }

  // ---------- shared panels ----------
  const metricsPanelEl = document.getElementById("metrics-panel");
  const validationPanelEl = document.getElementById("validation-panel");
  const sourceNoteEl = document.getElementById("source-note");
  const caveatNoteEl = document.getElementById("caveat-note");
  const detailsToggleBtn = document.getElementById("details-toggle-btn");
  const technicalDetailsPanelEl = document.getElementById("technical-details-panel");
  detailsToggleBtn.addEventListener("click", () => {
    const expanded = detailsToggleBtn.getAttribute("aria-expanded") === "true";
    detailsToggleBtn.setAttribute("aria-expanded", String(!expanded));
    technicalDetailsPanelEl.classList.toggle("hidden", expanded);
  });
  const topbarStudyNameEl = document.getElementById("topbar-study-name");
  const topbarStudyTypeEl = document.getElementById("topbar-study-type");
  const topbarStatusEl = document.getElementById("topbar-status");
  const topbarStatusTextEl = document.getElementById("topbar-status-text");

  function renderTopbar(key, meta, validation) {
    topbarStudyNameEl.textContent = meta.label;
    topbarStudyTypeEl.textContent = meta.study_type;
    const dot = topbarStatusEl.querySelector(".badge-dot");
    if (validation.passed) {
      dot.className = "badge-dot ok";
      topbarStatusTextEl.textContent = "Reconstrucción lista";
    } else {
      dot.className = "badge-dot warn";
      topbarStatusTextEl.textContent = "Marcado — ver advertencias";
    }
  }

  function renderMetrics(metrics) {
    const dims = [0,1,2].map((i) => metrics.bounding_box_max_mm[i] - metrics.bounding_box_min_mm[i]);
    const rows = [
      ["Tipo", "Órgano"],
      ["Vértices", fmt(metrics.num_vertices, 0)],
      ["Triángulos", fmt(metrics.num_triangles, 0)],
      ["Dimensiones (mm)", dims.map((v) => fmt(v, 0)).join(" × ")],
      ["Volumen", fmt(metrics.volume_ml, 1) + " mL"],
      ["Área de superficie", fmt(metrics.surface_area_mm2, 0) + " mm²"],
      ["Centroide (mm)", metrics.centroid_mm.map((v) => fmt(v, 0)).join(", ")],
    ];
    metricsPanelEl.innerHTML = rows.map(([k, v]) => `<div class="inspector-row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("")
      + `<p class="note" style="margin-top:0.5rem">Esta malla puede exportarse desde la sección "Exportar" más abajo. La vista 3D usa esta misma geometría, decimada para una interacción fluida.</p>`;
  }
  function renderValidation(validation) {
    const cls = validation.passed ? "pass" : "fail";
    const label = validation.passed ? "Listo — malla estanca, volumen plausible" : "Marcado — ver advertencias";
    validationPanelEl.innerHTML = `<div class="validation-line"><span class="validation-dot ${cls}"></span><span>${label}</span></div>`;
  }

  function organListHtml(activeKey) {
    return ORGAN_ORDER.map((key) => {
      const meta = ORGAN_META[key];
      const active = key === activeKey;
      return `
        <button class="organ-btn" data-organ="${key}" role="tab" aria-pressed="${active}">
          <span class="organ-swatch" style="background:${meta.color_hex}"></span>
          <span class="label-group"><span class="name">${meta.label}</span><span class="algo">${meta.algo}</span></span>
          <span class="structure-status"><span class="dot"></span>${active ? "Activo" : "En reposo"}</span>
        </button>`;
    }).join("");
  }

  let currentOrganKey = ORGAN_ORDER[0];

  // ---------- synthesized heartbeat (Web Audio API, no audio file) ----------
  let audioCtx = null;
  let heartbeatEnabled = false;
  let heartbeatTimer = null;
  function ensureAudioCtx() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    return audioCtx;
  }
  function playThump(ctx, time, freq, duration, gainPeak) {
    const osc = ctx.createOscillator();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, time);
    osc.frequency.exponentialRampToValueAtTime(Math.max(30, freq * 0.6), time + duration);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, time);
    gain.gain.exponentialRampToValueAtTime(gainPeak, time + duration * 0.15);
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);
    osc.connect(gain); gain.connect(ctx.destination);
    osc.start(time); osc.stop(time + duration + 0.02);
  }
  function scheduleHeartbeat() {
    if (!heartbeatEnabled || currentOrganKey !== "heart") return;
    const ctx = ensureAudioCtx();
    const bpmPeriodMs = 60 / 70 * 1000; // ~70 bpm, adult resting rate
    const now = ctx.currentTime + 0.05;
    playThump(ctx, now, 90, 0.14, 0.5);        // "lub" — AV valves closing
    playThump(ctx, now + 0.18, 70, 0.16, 0.32); // "dub" — semilunar valves closing
    heartbeatTimer = setTimeout(scheduleHeartbeat, bpmPeriodMs);
  }
  function stopHeartbeat() {
    if (heartbeatTimer) { clearTimeout(heartbeatTimer); heartbeatTimer = null; }
  }
  const heartbeatToggleEl = document.getElementById("heartbeat-toggle");
  heartbeatToggleEl.addEventListener("change", () => {
    heartbeatEnabled = heartbeatToggleEl.checked;
    stopHeartbeat();
    if (heartbeatEnabled) scheduleHeartbeat();
  });

  function selectOrgan(key) {
    currentOrganKey = key;
    stopHeartbeat();
    if (heartbeatEnabled && key === "heart") scheduleHeartbeat();
    const data = VIEWER_DATA[key];
    const meta = ORGAN_META[key];
    renderTopbar(key, meta, data.validation);
    document.getElementById("orientation-note").textContent = meta.orientation_note;
    measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = "";

    const mesh = decodeMesh(data.mesh, key);
    currentMesh = mesh;
    currentColor = hexToRgb01(meta.color_hex);
    theta = meta.initial_theta; phi = meta.initial_phi;
    frameCamera(mesh);
    uploadMesh(mesh);
    currentLandmarks = computeLandmarksFor(key, mesh);
    rebuildLabelEls();
    autoRotate = !reduceMotion;

    renderMetrics(data.metrics);
    renderValidation(data.validation);
    sourceNoteEl.textContent = meta.source_note;
    caveatNoteEl.textContent = meta.caveat;

    document.getElementById("anatomy-title").textContent = meta.label;
    document.getElementById("anatomy-algo").textContent = meta.algo;
    document.getElementById("anatomy-text").innerHTML = meta.anatomy;
    document.getElementById("anatomy-source").textContent = meta.source_note;
    document.getElementById("anatomy-caveat").textContent = meta.caveat;
    document.getElementById("anatomy-diagram").innerHTML = meta.diagram_svg;
    document.getElementById("anatomy-facts").innerHTML = meta.fun_facts.map((f) => `<li>${f}</li>`).join("");

    document.getElementById("slice-source-note").textContent =
      "Cortes del volumen preprocesado real que este pipeline realmente segmentó para " + meta.label.toLowerCase() +
      " (mismos datos de origen que la reconstrucción 3D), submuestreado para un archivo más ligero.";

    for (const list of [document.getElementById("organ-list"), document.getElementById("organ-list-slices"), document.getElementById("organ-list-anatomy"), document.getElementById("organ-list-lab")]) {
      for (const btn of list.querySelectorAll(".organ-btn")) {
        btn.setAttribute("aria-pressed", String(btn.dataset.organ === key));
      }
    }

    loadSliceVolume(data.slices);
    if (!panelSlices.classList.contains("hidden")) { resizeSliceCanvasDisplay(); drawSlice(); }
    labSelectOrgan(key);
    if (!panelLab.classList.contains("hidden")) labRender();

    mprAxialFrac = 0.5; mprCoronalFrac = 0.5; mprSagittalFrac = 0.5;
    mprAxialSlider.value = "50"; mprCoronalSlider.value = "50"; mprSagittalSlider.value = "50";
    if (viewMode === "mpr") { rebuildMprPlanes(); if (showGradientField) computeGradientField(); }

    flyPath = null; // recomputed lazily next time "Vuelo interior" is entered, or right now if already active
    if (viewMode === "fly") computeFlyPath();
  }

  for (const listId of ["organ-list", "organ-list-slices", "organ-list-anatomy", "organ-list-lab"]) {
    document.getElementById(listId).innerHTML = organListHtml(ORGAN_ORDER[0]);
  }
  for (const listId of ["organ-list", "organ-list-slices", "organ-list-anatomy", "organ-list-lab"]) {
    for (const btn of document.getElementById(listId).querySelectorAll(".organ-btn")) {
      btn.addEventListener("click", () => selectOrgan(btn.dataset.organ));
    }
  }

  /* =========================================================
     CT / slice viewer (per organ)
     ========================================================= */
  let sv = null; // active slice volume
  const sliceSlider = document.getElementById("slice-slider");
  const sliceReadout = document.getElementById("slice-readout");
  const levelSlider = document.getElementById("level-slider");
  const widthSlider = document.getElementById("width-slider");
  const levelValueEl = document.getElementById("level-value");
  const widthValueEl = document.getElementById("width-value");
  const presetRowEl = document.getElementById("preset-row");
  const sliceCanvas = document.getElementById("slice-canvas");
  const sliceCtx = sliceCanvas.getContext("2d");
  const huReadoutEl = document.getElementById("hu-readout");

  let windowLevel = 128, windowWidth = 255;
  const PRESETS = [
    {label: "Bajo", level: 64, width: 128},
    {label: "Medio", level: 128, width: 255},
    {label: "Alto contraste", level: 128, width: 60},
    {label: "Rango completo", level: 128, width: 510},
  ];
  presetRowEl.innerHTML = PRESETS.map((p, i) => `<button class="preset-btn" data-i="${i}" aria-pressed="${i===1}">${p.label}</button>`).join("");
  for (const btn of presetRowEl.querySelectorAll(".preset-btn")) {
    btn.addEventListener("click", () => {
      const p = PRESETS[Number(btn.dataset.i)];
      windowLevel = p.level; windowWidth = p.width;
      levelSlider.value = windowLevel; widthSlider.value = windowWidth;
      levelValueEl.textContent = windowLevel; widthValueEl.textContent = windowWidth;
      for (const b of presetRowEl.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", String(b === btn));
      drawSlice();
    });
  }
  levelSlider.value = windowLevel; widthSlider.value = windowWidth;
  levelValueEl.textContent = windowLevel; widthValueEl.textContent = windowWidth;
  function clearPresets() { for (const b of presetRowEl.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", "false"); }
  levelSlider.addEventListener("input", () => { windowLevel = Number(levelSlider.value); levelValueEl.textContent = windowLevel; clearPresets(); drawSlice(); });
  widthSlider.addEventListener("input", () => { windowWidth = Math.max(1, Number(widthSlider.value)); widthValueEl.textContent = windowWidth; clearPresets(); drawSlice(); });
  sliceSlider.addEventListener("input", drawSlice);

  let imgData = null;

  function loadSliceVolume(slicesData) {
    sv = {
      voxels: new Uint8Array(decodeB64(slicesData.voxels_b64)),
      shape: slicesData.shape_zyx,
      spacing: slicesData.spacing_xyz,
      origin: slicesData.origin_xyz,
      valueMin: slicesData.value_min,
      valueMax: slicesData.value_max,
    };
    const [snz, sny, snx] = sv.shape;
    sliceSlider.max = String(snz - 1);
    sliceSlider.value = String(Math.floor(snz / 2));
    sliceCanvas.width = snx; sliceCanvas.height = sny;
    imgData = sliceCtx.createImageData(snx, sny);
    renderTechnicalDetails();
  }

  const technicalDetailsRowsEl = document.getElementById("technical-details-rows");
  function renderTechnicalDetails() {
    if (!sv) return;
    const [snz, sny, snx] = sv.shape;
    const rows = [
      ["Dimensiones del cubo de vista", `${snx} × ${sny} × ${snz}`],
      ["Espaciado de vóxel (mm)", sv.spacing.map((v) => v.toFixed(2)).join(" × ")],
      ["Tipo de estudio", ORGAN_META[currentOrganKey].study_type],
    ];
    technicalDetailsRowsEl.innerHTML = rows.map(([k, v]) => `<div class="inspector-row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("")
      + `<p class="note" style="margin-top:0.4rem">El cubo de vista es un submuestreo del volumen real, reducido para que el archivo del visor sea liviano — no es la resolución original completa del escaneo.</p>`;
  }

  function drawSlice() {
    if (!sv) return;
    const [snz, sny, snx] = sv.shape;
    const z = Math.min(Number(sliceSlider.value), snz - 1);
    const zMm = (sv.origin[2] + z * sv.spacing[2]).toFixed(1);
    sliceReadout.textContent = `${z+1} / ${snz} · z=${zMm}mm`;
    const off = z * sny * snx;
    const lo = windowLevel - windowWidth/2, scale = 255/windowWidth;
    const data = imgData.data;
    for (let i = 0; i < sny*snx; i++) {
      let val = (sv.voxels[off+i] - lo) * scale;
      val = val < 0 ? 0 : val > 255 ? 255 : val;
      const o = i*4; data[o]=val; data[o+1]=val; data[o+2]=val; data[o+3]=255;
    }
    sliceCtx.putImageData(imgData, 0, 0);
  }
  function resizeSliceCanvasDisplay() {
    if (!sv) return;
    const [, sny, snx] = sv.shape;
    const stage = sliceCanvas.parentElement;
    const availW = stage.clientWidth * 0.92, availH = stage.clientHeight * 0.92;
    const aspect = snx / sny;
    let w = availW, h = w / aspect;
    if (h > availH) { h = availH; w = h * aspect; }
    sliceCanvas.style.width = Math.round(w) + "px";
    sliceCanvas.style.height = Math.round(h) + "px";
  }
  window.addEventListener("resize", () => { if (!panelSlices.classList.contains("hidden")) resizeSliceCanvasDisplay(); });
  sliceCanvas.addEventListener("mousemove", (e) => {
    if (!sv) return;
    const [, sny, snx] = sv.shape;
    const rect = sliceCanvas.getBoundingClientRect();
    const px = Math.floor((e.clientX-rect.left)/rect.width*snx), py = Math.floor((e.clientY-rect.top)/rect.height*sny);
    if (px<0||py<0||px>=snx||py>=sny) return;
    const z = Math.min(Number(sliceSlider.value), sv.shape[0]-1);
    const raw = sv.voxels[z*sny*snx+py*snx+px];
    const orig = sv.valueMin + (raw/255)*(sv.valueMax - sv.valueMin);
    huReadoutEl.textContent = `(${px}, ${py})  ${raw}/255  ≈${orig.toFixed(0)}`;
  });
  sliceCanvas.addEventListener("mouseleave", () => { huReadoutEl.textContent = "—"; });

  /* =========================================================
     Laboratorio: motor de morfología 2D + línea de tiempo + modo libre
     ========================================================= */
  function labThreshold(gray, w, h, t, below) {
    const mask = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) mask[i] = (below ? gray[i] < t : gray[i] > t) ? 1 : 0;
    return mask;
  }
  function labErode(mask, w, h) {
    const out = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let all = 1;
      for (let dy = -1; dy <= 1 && all; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= w || yy >= h || !mask[yy * w + xx]) { all = 0; break; }
      }
      out[y * w + x] = all;
    }
    return out;
  }
  function labDilate(mask, w, h) {
    const out = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let any = 0;
      for (let dy = -1; dy <= 1 && !any; dy++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx >= 0 && yy >= 0 && xx < w && yy < h && mask[yy * w + xx]) { any = 1; break; }
      }
      out[y * w + x] = any;
    }
    return out;
  }
  function labOpen(mask, w, h) { return labDilate(labErode(mask, w, h), w, h); }
  function labClose(mask, w, h) { return labErode(labDilate(mask, w, h), w, h); }
  function labLargestComponent(mask, w, h) {
    const labels = new Int32Array(w * h).fill(-1);
    let bestLabel = -1, bestSize = 0, label = 0;
    const stack = [];
    for (let start = 0; start < w * h; start++) {
      if (!mask[start] || labels[start] !== -1) continue;
      let size = 0;
      stack.push(start); labels[start] = label;
      while (stack.length) {
        const idx = stack.pop();
        size++;
        const x = idx % w, y = (idx / w) | 0;
        const nbrs = [[x-1,y],[x+1,y],[x,y-1],[x,y+1]];
        for (const [nx, ny] of nbrs) {
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          const nidx = ny * w + nx;
          if (mask[nidx] && labels[nidx] === -1) { labels[nidx] = label; stack.push(nidx); }
        }
      }
      if (size > bestSize) { bestSize = size; bestLabel = label; }
      label++;
    }
    const out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) out[i] = labels[i] === bestLabel ? 1 : 0;
    return out;
  }
  function labFillHoles(mask, w, h) {
    const bg = new Uint8Array(w * h);
    const stack = [];
    function seed(idx) { if (!mask[idx] && !bg[idx]) { bg[idx] = 1; stack.push(idx); } }
    for (let x = 0; x < w; x++) { seed(x); seed((h-1)*w + x); }
    for (let y = 0; y < h; y++) { seed(y*w); seed(y*w + w - 1); }
    while (stack.length) {
      const idx = stack.pop();
      const x = idx % w, y = (idx / w) | 0;
      const nbrs = [[x-1,y],[x+1,y],[x,y-1],[x,y+1]];
      for (const [nx, ny] of nbrs) {
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        seed(ny * w + nx);
      }
    }
    const out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) out[i] = (mask[i] || !bg[i]) ? 1 : 0;
    return out;
  }
  function labMaskBoundary(mask, w, h) {
    const eroded = labErode(mask, w, h);
    const out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) out[i] = mask[i] && !eroded[i] ? 1 : 0;
    return out;
  }

  // Render helpers: paint a grayscale array, optionally with a binary mask
  // washed in the accent color and/or a bright contour outline.
  function labPaintImageData(imgData, gray, w, h, mask, contourOnly) {
    const data = imgData.data;
    for (let i = 0; i < w * h; i++) {
      const g = gray[i];
      const o = i * 4;
      if (mask) {
        if (contourOnly) {
          if (mask[i]) { data[o]=70; data[o+1]=201; data[o+2]=194; data[o+3]=255; }
          else { data[o]=g; data[o+1]=g; data[o+2]=g; data[o+3]=255; }
        } else {
          // translucent wash over the grayscale background for pure mask stages
          const inside = mask[i];
          data[o] = inside ? Math.round(g*0.35 + 70*0.65) : g;
          data[o+1] = inside ? Math.round(g*0.35 + 201*0.65) : g;
          data[o+2] = inside ? Math.round(g*0.35 + 194*0.65) : g;
          data[o+3] = 255;
        }
      } else {
        data[o]=g; data[o+1]=g; data[o+2]=g; data[o+3]=255;
      }
    }
  }

  const labSubtabButtons = document.querySelectorAll(".lab-subtabs button");
  const labTimelineViewEl = document.getElementById("lab-timeline-view");
  const labFreeViewEl = document.getElementById("lab-free-view");
  const labCanvas = document.getElementById("lab-canvas");
  const labCtx = labCanvas.getContext("2d");
  const labFreeCanvas = document.getElementById("lab-free-canvas");
  const labFreeCtx = labFreeCanvas.getContext("2d");
  const labStageTitleEl = document.getElementById("lab-stage-title");
  const labStageTextEl = document.getElementById("lab-stage-text");
  const labDotsEl = document.getElementById("lab-dots");
  const labPrevBtn = document.getElementById("lab-prev");
  const labNextBtn = document.getElementById("lab-next");
  const labThresholdSlider = document.getElementById("lab-threshold-slider");
  const labThresholdValueEl = document.getElementById("lab-threshold-value");
  const labThresholdRealEl = document.getElementById("lab-threshold-real");
  const labOpeningToggle = document.getElementById("lab-opening-toggle");
  const labCleanupToggle = document.getElementById("lab-cleanup-toggle");
  const labFreeMatchEl = document.getElementById("lab-free-match");
  const labHistogramCanvas = document.getElementById("lab-histogram-canvas");
  const labHistogramCtx = labHistogramCanvas.getContext("2d");
  const labHistogramNoteEl = document.getElementById("lab-histogram-note");

  let labMode = "timeline";
  let labStage = 0;
  let labGray = null, labW = 0, labH = 0;
  let labThresholdNative = 0, labThresholdBelow = false, labQuantThreshold = 128;
  let labHistogram = null;

  function labSelectOrgan(key) {
    const slices = VIEWER_DATA[key].slices;
    const meta = ORGAN_META[key];
    const [nz, ny, nx] = slices.shape_zyx;
    const midZ = Math.floor(nz / 2);
    // sv.voxels was just decoded by loadSliceVolume() for the "Cortes CT"
    // tab (called right before this in selectOrgan) — reuse it instead of
    // decoding the same base64 payload a second time.
    labGray = sv.voxels.subarray(midZ * ny * nx, (midZ + 1) * ny * nx);
    labW = nx; labH = ny;
    labThresholdNative = meta.threshold_native;
    labThresholdBelow = meta.threshold_below;
    const frac = (labThresholdNative - slices.value_min) / (slices.value_max - slices.value_min);
    labQuantThreshold = Math.max(0, Math.min(255, Math.round(frac * 255)));
    labStage = 0;
    labThresholdSlider.value = String(labQuantThreshold);
    labThresholdValueEl.textContent = String(labQuantThreshold);
    labThresholdRealEl.textContent = "Valor real usado por el pipeline: " + meta.threshold_label;
    labOpeningToggle.checked = true;
    labCleanupToggle.checked = true;

    // Real histogram over the whole 3D volume (every voxel this pipeline
    // actually looked at), not just the one slice shown above — computed
    // once per organ since it never changes as the threshold slider moves.
    const hist = new Uint32Array(256);
    for (let i = 0; i < sv.voxels.length; i++) hist[sv.voxels[i]]++;
    labHistogram = hist;
  }

  function drawLabHistogram() {
    if (!labHistogram) return;
    const w = labHistogramCanvas.width, h = labHistogramCanvas.height;
    labHistogramCtx.clearRect(0, 0, w, h);
    const logs = new Float32Array(256);
    let maxLog = 0;
    for (let i = 0; i < 256; i++) { logs[i] = Math.log1p(labHistogram[i]); if (logs[i] > maxLog) maxLog = logs[i]; }
    const barW = w / 256;
    const rootStyle = getComputedStyle(document.documentElement);
    const dimColor = rootStyle.getPropertyValue("--text-faint").trim() || "#888";
    const accentColor = rootStyle.getPropertyValue("--accent").trim() || "#a5434b";
    let tissueCount = 0, total = 0;
    for (let i = 0; i < 256; i++) {
      const isTissueSide = labThresholdBelow ? i < labQuantThreshold : i > labQuantThreshold;
      const bh = maxLog > 0 ? (logs[i] / maxLog) * (h - 3) : 0;
      labHistogramCtx.fillStyle = isTissueSide ? accentColor : dimColor;
      labHistogramCtx.globalAlpha = isTissueSide ? 0.85 : 0.5;
      labHistogramCtx.fillRect(i * barW, h - bh, Math.max(1, barW), bh);
      total += labHistogram[i];
      if (isTissueSide) tissueCount += labHistogram[i];
    }
    labHistogramCtx.globalAlpha = 1;
    const x = labQuantThreshold * barW;
    labHistogramCtx.strokeStyle = accentColor;
    labHistogramCtx.lineWidth = 2;
    labHistogramCtx.beginPath(); labHistogramCtx.moveTo(x, 0); labHistogramCtx.lineTo(x, h); labHistogramCtx.stroke();
    const pct = total > 0 ? (100 * tissueCount / total).toFixed(1) : "0";
    labHistogramNoteEl.textContent = `${pct}% de los vóxeles del volumen caen del lado "tejido" con este umbral (escala vertical logarítmica).`;
  }

  function labComputeStageMask(stageIdx) {
    const t = labThreshold(labGray, labW, labH, labQuantThreshold, labThresholdBelow);
    if (stageIdx <= 0) return null;
    const opened = labOpen(t, labW, labH);
    if (stageIdx === 1) return t;
    if (stageIdx === 2) return opened;
    const largest = labLargestComponent(opened, labW, labH);
    if (stageIdx === 3) return largest;
    return labFillHoles(labClose(largest, labW, labH), labW, labH);
  }

  const LAB_STAGES = [
    {title: "0. Corte original", text: "El corte 2D real que este pipeline segmentó — sin ningún procesamiento todavía."},
    {title: "1. Umbral de intensidad", text: "Se marca como \"posible tejido\" cada píxel que cruza el umbral real de este órgano. Nota el ruido: puntos sueltos que no son tejido de verdad."},
    {title: "2. Apertura morfológica", text: "Erosiona y luego dilata la máscara — así desaparece el ruido de un solo píxel sin perder la forma principal."},
    {title: "3. Componente más grande", text: "De todas las regiones que sobrevivieron, se conserva solo la más grande — el resto era ruido residual o artefactos."},
    {title: "4. Cierre + relleno de huecos (resultado final)", text: "Se cierran pequeños huecos internos y se traza el contorno final — esta silueta es, en esencia, lo que se convierte en la malla 3D."},
  ];

  function labRenderTimeline() {
    if (!labGray) return;
    labCanvas.width = labW; labCanvas.height = labH;
    const imgData = labCtx.createImageData(labW, labH);
    const mask = labComputeStageMask(labStage);
    const isFinal = labStage === LAB_STAGES.length - 1;
    labPaintImageData(imgData, labGray, labW, labH, mask && isFinal ? labMaskBoundary(mask, labW, labH) : mask, isFinal);
    labCtx.putImageData(imgData, 0, 0);
    labStageTitleEl.textContent = LAB_STAGES[labStage].title;
    labStageTextEl.textContent = LAB_STAGES[labStage].text;
    labPrevBtn.disabled = labStage === 0;
    labNextBtn.disabled = labStage === LAB_STAGES.length - 1;
    labDotsEl.innerHTML = LAB_STAGES.map((_, i) => `<span data-active="${i === labStage}"></span>`).join("");
  }

  function labRenderFree() {
    if (!labGray) return;
    labFreeCanvas.width = labW; labFreeCanvas.height = labH;
    labQuantThreshold = Number(labThresholdSlider.value);
    labThresholdValueEl.textContent = String(labQuantThreshold);
    let mask = labThreshold(labGray, labW, labH, labQuantThreshold, labThresholdBelow);
    if (labOpeningToggle.checked) mask = labOpen(mask, labW, labH);
    if (labCleanupToggle.checked) mask = labFillHoles(labClose(labLargestComponent(mask, labW, labH), labW, labH), labW, labH);
    const imgData = labFreeCtx.createImageData(labW, labH);
    labPaintImageData(imgData, labGray, labW, labH, mask, false);
    labFreeCtx.putImageData(imgData, 0, 0);

    const officialQuant = Math.max(0, Math.min(255, Math.round(
      ((labThresholdNative - VIEWER_DATA[currentOrganKey].slices.value_min) /
       (VIEWER_DATA[currentOrganKey].slices.value_max - VIEWER_DATA[currentOrganKey].slices.value_min)) * 255
    )));
    labFreeMatchEl.textContent = Math.abs(labQuantThreshold - officialQuant) <= 8
      ? "¡Muy cerca del umbral real que usa el pipeline!" : "";
    drawLabHistogram();
  }

  function labRender() {
    if (labMode === "timeline") labRenderTimeline(); else labRenderFree();
  }

  for (const btn of labSubtabButtons) {
    btn.addEventListener("click", () => {
      labMode = btn.dataset.labMode;
      for (const b of labSubtabButtons) b.setAttribute("aria-pressed", String(b === btn));
      labTimelineViewEl.classList.toggle("hidden", labMode !== "timeline");
      labFreeViewEl.classList.toggle("hidden", labMode !== "free");
      labRender();
    });
  }
  labPrevBtn.addEventListener("click", () => { labStage = Math.max(0, labStage - 1); labRenderTimeline(); });
  labNextBtn.addEventListener("click", () => { labStage = Math.min(LAB_STAGES.length - 1, labStage + 1); labRenderTimeline(); });
  labThresholdSlider.addEventListener("input", labRenderFree);
  labOpeningToggle.addEventListener("change", labRenderFree);
  labCleanupToggle.addEventListener("change", labRenderFree);

  /* =========================================================
     Sala de órganos: all 5 organs in one scene, in the real
     physical-space (mm) coordinates their own pipeline produced —
     no per-organ rescaling, so relative size is genuinely to scale.
     Runs on its own canvas/WebGL context so it never touches the
     main viewer's state.
     ========================================================= */
  function compileFor(glCtx, type, src) {
    const s = glCtx.createShader(type); glCtx.shaderSource(s, src); glCtx.compileShader(s);
    if (!glCtx.getShaderParameter(s, glCtx.COMPILE_STATUS)) throw new Error(glCtx.getShaderInfoLog(s));
    return s;
  }
  function linkProgramFor(glCtx, vsSrc, fsSrc) {
    const p = glCtx.createProgram();
    glCtx.attachShader(p, compileFor(glCtx, glCtx.VERTEX_SHADER, vsSrc));
    glCtx.attachShader(p, compileFor(glCtx, glCtx.FRAGMENT_SHADER, fsSrc));
    glCtx.linkProgram(p);
    return p;
  }
  function projectToScreenGeneric(cnv, pos, view, proj) {
    const vx = view[0]*pos[0]+view[4]*pos[1]+view[8]*pos[2]+view[12];
    const vy = view[1]*pos[0]+view[5]*pos[1]+view[9]*pos[2]+view[13];
    const vz = view[2]*pos[0]+view[6]*pos[1]+view[10]*pos[2]+view[14];
    const vw = view[3]*pos[0]+view[7]*pos[1]+view[11]*pos[2]+view[15];
    const cx = proj[0]*vx+proj[4]*vy+proj[8]*vz+proj[12]*vw;
    const cy = proj[1]*vx+proj[5]*vy+proj[9]*vz+proj[13]*vw;
    const cw = proj[3]*vx+proj[7]*vy+proj[11]*vz+proj[15]*vw;
    if (cw <= 0.001) return null;
    const ndcX = cx / cw, ndcY = cy / cw;
    if (ndcX < -1.3 || ndcX > 1.3 || ndcY < -1.3 || ndcY > 1.3) return null;
    return [(ndcX*0.5+0.5) * cnv.clientWidth, (1-(ndcY*0.5+0.5)) * cnv.clientHeight];
  }

  const roomCanvas = document.getElementById("room-canvas");
  const roomGl = roomCanvas.getContext("webgl", {antialias: true, alpha: false});
  const roomProgram = linkProgramFor(roomGl, VS, FS);
  const room_aPosition = roomGl.getAttribLocation(roomProgram, "aPosition");
  const room_aNormal = roomGl.getAttribLocation(roomProgram, "aNormal");
  const room_uModelView = roomGl.getUniformLocation(roomProgram, "uModelView");
  const room_uProjection = roomGl.getUniformLocation(roomProgram, "uProjection");
  const room_uNormalMatrix = roomGl.getUniformLocation(roomProgram, "uNormalMatrix");
  const room_uColor = roomGl.getUniformLocation(roomProgram, "uColor");
  const room_uAlpha = roomGl.getUniformLocation(roomProgram, "uAlpha");
  const room_uOffset = roomGl.getUniformLocation(roomProgram, "uOffset");
  const room_uClipNormal = roomGl.getUniformLocation(roomProgram, "uClipNormal");
  const room_uClipValue = roomGl.getUniformLocation(roomProgram, "uClipValue");
  const room_uClipEnabled = roomGl.getUniformLocation(roomProgram, "uClipEnabled");
  roomGl.enable(roomGl.DEPTH_TEST); roomGl.enable(roomGl.CULL_FACE); roomGl.cullFace(roomGl.BACK);
  roomGl.getExtension("OES_element_index_uint");

  const roomLabelLayerEl = document.getElementById("room-label-layer");
  let roomBuilt = false;
  let roomEntries = [];
  let roomLabelEls = [];
  let roomBoundingRadius = 300;
  let roomTheta = 0.5, roomPhi = 1.2, roomRadius = 600, roomTargetRadius = 600;
  let roomAutoRotate = !reduceMotion;
  let roomDragging = false, roomLastX = 0, roomLastY = 0;

  function buildRoom() {
    if (roomBuilt) return;
    roomBuilt = true;
    const gapMm = 20;
    let cursorX = 0;
    const placed = [];
    for (const key of ORGAN_ORDER) {
      const mesh = decodeMesh(VIEWER_DATA[key].mesh, key);
      let r = 1;
      for (let i = 0; i < mesh.positions.length; i += 3) {
        const dx = mesh.positions[i]-mesh.center[0], dy = mesh.positions[i+1]-mesh.center[1], dz = mesh.positions[i+2]-mesh.center[2];
        const d = Math.sqrt(dx*dx + dy*dy + dz*dz);
        if (d > r) r = d;
      }
      cursorX += r;
      placed.push({key, mesh, r, offset: [cursorX - mesh.center[0], -mesh.center[1], -mesh.center[2]]});
      cursorX += r + gapMm;
    }
    const shiftX = (cursorX - gapMm) / 2;
    for (const p of placed) p.offset[0] -= shiftX;

    roomEntries = placed.map((p) => {
      const posBuf = roomGl.createBuffer();
      roomGl.bindBuffer(roomGl.ARRAY_BUFFER, posBuf); roomGl.bufferData(roomGl.ARRAY_BUFFER, p.mesh.positions, roomGl.STATIC_DRAW);
      const normBuf = roomGl.createBuffer();
      roomGl.bindBuffer(roomGl.ARRAY_BUFFER, normBuf); roomGl.bufferData(roomGl.ARRAY_BUFFER, p.mesh.normals, roomGl.STATIC_DRAW);
      const idxBuf = roomGl.createBuffer();
      roomGl.bindBuffer(roomGl.ELEMENT_ARRAY_BUFFER, idxBuf); roomGl.bufferData(roomGl.ELEMENT_ARRAY_BUFFER, p.mesh.indices, roomGl.STATIC_DRAW);
      const worldCenter = [p.mesh.center[0]+p.offset[0], p.mesh.center[1]+p.offset[1], p.mesh.center[2]+p.offset[2]];
      return {
        posBuf, normBuf, idxBuf,
        indexCount: p.mesh.indices.length,
        color: hexToRgb01(ORGAN_META[p.key].color_hex),
        offset: p.offset,
        label: ORGAN_META[p.key].label,
        worldCenter, radius: p.r,
      };
    });

    let maxDist = 1;
    for (const e of roomEntries) {
      const d = Math.hypot(e.worldCenter[0], e.worldCenter[1], e.worldCenter[2]) + e.radius;
      if (d > maxDist) maxDist = d;
    }
    roomBoundingRadius = maxDist;
    roomRadius = roomBoundingRadius * 2.3; roomTargetRadius = roomRadius;

    roomLabelLayerEl.innerHTML = "";
    roomLabelEls = roomEntries.map((e) => {
      const el = document.createElement("div");
      el.className = "landmark-label";
      el.textContent = e.label;
      roomLabelLayerEl.appendChild(el);
      return el;
    });
  }

  roomCanvas.addEventListener("pointerdown", (e) => { roomDragging = true; roomAutoRotate = false; roomLastX = e.clientX; roomLastY = e.clientY; roomCanvas.setPointerCapture(e.pointerId); });
  roomCanvas.addEventListener("pointerup", () => roomDragging = false);
  roomCanvas.addEventListener("pointermove", (e) => {
    if (!roomDragging) return;
    roomTheta -= (e.clientX - roomLastX) * 0.008; roomPhi -= (e.clientY - roomLastY) * 0.008;
    roomPhi = Math.max(0.15, Math.min(Math.PI - 0.15, roomPhi));
    roomLastX = e.clientX; roomLastY = e.clientY;
  });
  roomCanvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    roomTargetRadius = Math.max(roomBoundingRadius*0.3, Math.min(roomBoundingRadius*6, roomTargetRadius * Math.pow(1.0012, e.deltaY)));
  }, {passive: false});
  document.getElementById("room-reset-btn").addEventListener("click", () => {
    roomTheta = 0.5; roomPhi = 1.2; roomTargetRadius = roomBoundingRadius * 2.3; roomAutoRotate = !reduceMotion;
  });

  function resizeRoomGl() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(roomCanvas.clientWidth * dpr), h = Math.round(roomCanvas.clientHeight * dpr);
    if (roomCanvas.width !== w || roomCanvas.height !== h) { roomCanvas.width = w; roomCanvas.height = h; }
  }

  function renderRoom() {
    if (roomBuilt && !panelRoom.classList.contains("hidden")) {
      resizeRoomGl();
      roomGl.viewport(0, 0, roomCanvas.width, roomCanvas.height);
      roomGl.clearColor(0.039, 0.055, 0.075, 1.0);
      roomGl.clear(roomGl.COLOR_BUFFER_BIT | roomGl.DEPTH_BUFFER_BIT);
      roomRadius += (roomTargetRadius - roomRadius) * 0.12;
      if (roomAutoRotate) roomTheta += 0.0012;
      const eye = [roomRadius*Math.sin(roomPhi)*Math.sin(roomTheta), roomRadius*Math.cos(roomPhi), roomRadius*Math.sin(roomPhi)*Math.cos(roomTheta)];
      const view = lookAt(eye, [0, 0, 0], [0, 1, 0]);
      const proj = perspective(Math.PI/4.2, roomCanvas.width/Math.max(1, roomCanvas.height), Math.max(0.01, roomBoundingRadius*0.02), roomBoundingRadius*20);
      roomGl.useProgram(roomProgram);
      roomGl.uniformMatrix4fv(room_uModelView, false, view);
      roomGl.uniformMatrix4fv(room_uProjection, false, proj);
      roomGl.uniformMatrix3fv(room_uNormalMatrix, false, normalMat3(view));
      roomGl.uniform1f(room_uAlpha, 1.0);
      roomGl.uniform1f(room_uClipEnabled, 0.0);
      roomGl.uniform3fv(room_uClipNormal, [1, 0, 0]);
      roomGl.uniform1f(room_uClipValue, 0.0);
      for (const e of roomEntries) {
        roomGl.uniform3fv(room_uColor, e.color);
        roomGl.uniform3fv(room_uOffset, e.offset);
        roomGl.bindBuffer(roomGl.ARRAY_BUFFER, e.posBuf); roomGl.enableVertexAttribArray(room_aPosition); roomGl.vertexAttribPointer(room_aPosition, 3, roomGl.FLOAT, false, 0, 0);
        roomGl.bindBuffer(roomGl.ARRAY_BUFFER, e.normBuf); roomGl.enableVertexAttribArray(room_aNormal); roomGl.vertexAttribPointer(room_aNormal, 3, roomGl.FLOAT, false, 0, 0);
        roomGl.bindBuffer(roomGl.ELEMENT_ARRAY_BUFFER, e.idxBuf);
        roomGl.drawElements(roomGl.TRIANGLES, e.indexCount, roomGl.UNSIGNED_INT, 0);
      }
      for (let i = 0; i < roomEntries.length; i++) {
        const e = roomEntries[i];
        const labelPos = [e.worldCenter[0], e.worldCenter[1] + e.radius * 0.95, e.worldCenter[2]];
        const screen = projectToScreenGeneric(roomCanvas, labelPos, view, proj);
        const el = roomLabelEls[i];
        if (!screen) { el.style.display = "none"; continue; }
        el.style.display = ""; el.style.left = screen[0] + "px"; el.style.top = screen[1] + "px";
      }
    }
    requestAnimationFrame(renderRoom);
  }
  requestAnimationFrame(renderRoom);

  /* =========================================================
     Trivia: multiple-choice questions drawn straight from the
     same real fun_facts already shown in Anatomía — no new data,
     just a different, playful way to check what stuck.
     ========================================================= */
  const triviaOrganListEl = document.getElementById("organ-list-trivia");
  const triviaProgressEl = document.getElementById("trivia-progress");
  const triviaQuestionCardEl = document.getElementById("trivia-question-card");
  const triviaQuestionTextEl = document.getElementById("trivia-question-text");
  const triviaOptionsEl = document.getElementById("trivia-options");
  const triviaExplainEl = document.getElementById("trivia-explain");
  const triviaNextBtn = document.getElementById("trivia-next-btn");
  const triviaResultEl = document.getElementById("trivia-result");
  const triviaResultTitleEl = document.getElementById("trivia-result-title");
  const triviaResultTextEl = document.getElementById("trivia-result-text");
  const triviaRestartBtn = document.getElementById("trivia-restart-btn");

  let triviaInitDone = false;
  let triviaCurrentKey = ORGAN_ORDER[0];
  let triviaQuestions = [];
  let triviaIndex = 0;
  let triviaScore = 0;
  let triviaAnswered = false;

  function shuffleArray(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function triviaStart(key) {
    triviaCurrentKey = key;
    for (const btn of triviaOrganListEl.querySelectorAll(".organ-btn")) {
      btn.setAttribute("aria-pressed", String(btn.dataset.organ === key));
    }
    triviaQuestions = shuffleArray(ORGAN_META[key].quiz);
    triviaIndex = 0;
    triviaScore = 0;
    triviaResultEl.classList.add("hidden");
    triviaQuestionCardEl.classList.remove("hidden");
    triviaRenderQuestion();
  }

  function triviaRenderQuestion() {
    triviaAnswered = false;
    const q = triviaQuestions[triviaIndex];
    triviaProgressEl.textContent = `Pregunta ${triviaIndex + 1} de ${triviaQuestions.length} · Puntaje: ${triviaScore}`;
    triviaQuestionTextEl.textContent = q.q;
    triviaOptionsEl.innerHTML = "";
    for (const opt of shuffleArray(q.options)) {
      const btn = document.createElement("button");
      btn.className = "trivia-option-btn";
      btn.textContent = opt;
      btn.addEventListener("click", () => triviaSelectOption(opt, btn));
      triviaOptionsEl.appendChild(btn);
    }
    triviaExplainEl.classList.add("hidden");
    triviaNextBtn.classList.add("hidden");
  }

  function triviaSelectOption(opt, btn) {
    if (triviaAnswered) return;
    triviaAnswered = true;
    const q = triviaQuestions[triviaIndex];
    if (opt === q.correct) triviaScore++;
    for (const b of triviaOptionsEl.querySelectorAll(".trivia-option-btn")) {
      b.disabled = true;
      if (b.textContent === q.correct) b.dataset.state = "correct";
      else if (b === btn) b.dataset.state = "wrong";
    }
    triviaExplainEl.textContent = q.explain;
    triviaExplainEl.classList.remove("hidden");
    triviaNextBtn.textContent = triviaIndex < triviaQuestions.length - 1 ? "Siguiente →" : "Ver resultado";
    triviaNextBtn.classList.remove("hidden");
    triviaProgressEl.textContent = `Pregunta ${triviaIndex + 1} de ${triviaQuestions.length} · Puntaje: ${triviaScore}`;
  }

  function triviaShowResult() {
    triviaQuestionCardEl.classList.add("hidden");
    triviaResultEl.classList.remove("hidden");
    const total = triviaQuestions.length;
    const pct = triviaScore / total;
    triviaResultTitleEl.textContent = `¡Terminaste! ${triviaScore} / ${total}`;
    triviaResultTextEl.textContent =
      pct === 1 ? "Perfecto — dominas estos datos." :
      pct >= 0.75 ? "Muy bien, te sabes casi todo." :
      pct >= 0.5 ? "Nada mal, pero vale la pena repasar la pestaña Anatomía." :
      "Dale una vuelta a la pestaña Anatomía y vuelve a intentarlo.";
  }

  triviaNextBtn.addEventListener("click", () => {
    triviaIndex++;
    if (triviaIndex >= triviaQuestions.length) triviaShowResult();
    else triviaRenderQuestion();
  });
  triviaRestartBtn.addEventListener("click", () => triviaStart(triviaCurrentKey));

  function initTriviaTabIfNeeded() {
    if (triviaInitDone) return;
    triviaInitDone = true;
    triviaOrganListEl.innerHTML = organListHtml(triviaCurrentKey);
    for (const btn of triviaOrganListEl.querySelectorAll(".organ-btn")) {
      btn.addEventListener("click", () => triviaStart(btn.dataset.organ));
    }
    triviaStart(triviaCurrentKey);
  }

  // ---------- boot ----------
  selectOrgan(ORGAN_ORDER[0]);
  requestAnimationFrame(render3d);
</script>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, help="Path to the JSON payload from build_demo_payload.py")
    parser.add_argument("--output", required=True, help="Path to write the final HTML artifact to")
    args = parser.parse_args()

    with open(args.payload) as f:
        payload = json.load(f)

    html = build(payload)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"Wrote {args.output} ({size_mb:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
