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

# Habilita anotaciones de tipo "perezosas" (evaluadas como texto, no en
# tiempo de definición) para poder usar `dict`/`str` etc. en type hints
# sin preocuparse por el orden de declaración.
from __future__ import annotations

import argparse  # Lee los argumentos de línea de comandos (--payload, --output).
import json      # Serializa/deserializa el payload y los datos que se incrustan en el HTML.
import os        # Crea la carpeta de salida y mide el tamaño del archivo final.

# Orden fijo en el que aparecen los organos en el selector de la barra
# lateral y en el que se procesan al construir el HTML. Es una lista (no
# un set) porque el orden importa para la interfaz.
ORGAN_ORDER = ["lungs", "heart", "liver", "kidneys", "brain"]

# Diccionario con toda la metadata "de texto" de cada organo: nombre a
# mostrar, algoritmo de segmentacion usado, tipo de estudio de origen,
# notas de orientacion, color del material 3D, informacion de cada pin
# anatomico (landmark_info), texto de la pestaña Anatomia, umbral de
# segmentacion, datos curiosos, preguntas del cuestionario y el SVG de
# los diagramas 2D. Esta metadata se combina en build() con los datos
# numericos reales (malla 3D, cortes, metricas) que vienen del payload.
ORGAN_META = {
    "lungs": {
        "label": "Pulmones",
        "algo": "Umbral + componentes conectados",
        "study_type": "CT clínica",
        "orientation_note": (
            "Orientación real verificada: coordenadas físicas DICOM (paciente "
            "left-posterior-superior) tomadas directamente de la TC de tórax. El "
            "modelo se muestra con esas mismas direcciones alineadas al eje vertical "
            "del visor (tráquea hacia arriba) en cualquier vista, no solo con los "
            "botones — Ant/Post/Izq/Der/Sup/Inf indican la dirección anatómica real."
        ),
        "color_hex": "#e8b4b8",
        "landmark_info": {
            "Pulmón derecho": (
                "El pulmón derecho es más corto y ancho que el izquierdo, y tiene tres "
                "lóbulos —superior, medio e inferior— separados por dos fisuras. Al ser "
                "más grande, recibe proporcionalmente algo más de la ventilación total."
            ),
            "Pulmón izquierdo": (
                "El pulmón izquierdo tiene solo dos lóbulos —superior e inferior— porque "
                "cede espacio al corazón: en su borde anterior hay una muesca llamada "
                "escotadura cardíaca, junto a una lengüeta de tejido, la língula."
            ),
        },
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
            "<h3>Zona de conducción vs. zona respiratoria</h3>"
            "<p>El árbol bronquial se divide funcionalmente en dos zonas. La "
            "<b>zona de conducción</b> —nariz, faringe, laringe, tráquea, bronquios y "
            "bronquiolos hasta los terminales— solo transporta, calienta, humedece y "
            "filtra el aire, sin intercambio de gases; por eso se le llama \"espacio "
            "muerto\". La <b>zona respiratoria</b> —bronquiolos respiratorios, "
            "conductos alveolares, sacos alveolares y alvéolos— es donde sí ocurre el "
            "intercambio real de O₂ y CO₂. El bronquio principal derecho es más ancho, "
            "más corto y más vertical que el izquierdo, lo que lo hace el camino más "
            "probable si algo se aspira accidentalmente hacia la vía aérea. Cada "
            "pulmón se subdivide en segmentos broncopulmonares independientes —10 en "
            "el derecho, 8 a 10 en el izquierdo—, cada uno con su propio bronquio "
            "segmentario, lo que en cirugía permite retirar un segmento sin tocar el "
            "resto del pulmón.</p>"
            "<h3>Qué hay exactamente en la pared de un alvéolo</h3>"
            "<p>La pared alveolar tiene tres tipos de células con trabajos distintos. "
            "Los <b>neumocitos tipo I</b> son un epitelio extremadamente delgado que "
            "cubre cerca del 90% de la superficie alveolar — son los que realmente "
            "dejan pasar el gas. Los <b>neumocitos tipo II</b>, más escasos, producen "
            "el surfactante, una sustancia que reduce la tensión superficial dentro "
            "del alvéolo y evita que se colapse entre respiración y respiración. Los "
            "<b>macrófagos alveolares</b> patrullan esa misma superficie eliminando "
            "partículas y microbios inhalados. La <b>membrana respiratoria</b> — pared "
            "alveolar + membrana basal + endotelio del capilar— es la distancia total "
            "que el oxígeno y el CO₂ tienen que cruzar por difusión.</p>"
        ),
        "threshold_native": -320,
        "threshold_below": True,
        "threshold_label": "-320 HU (aire = menor que el umbral)",
        "fun_facts": [
            "Frecuencia respiratoria en reposo: 12–20 respiraciones por minuto en un adulto.",
            "Capacidad pulmonar total: alrededor de 6 litros de aire.",
            "Si se desdoblara toda la superficie de intercambio alveolar, cubriría un área similar a una cancha de tenis (~70 m²).",
            "El pulmón derecho es más grande que el izquierdo porque el corazón ocupa parte del espacio del lado izquierdo del tórax.",
            "El bronquio principal derecho es más ancho, corto y vertical que el izquierdo — la vía más probable si algo se aspira.",
            "Cada pulmón se divide en segmentos broncopulmonares independientes: 10 en el derecho, de 8 a 10 en el izquierdo.",
            "El volumen corriente (aire de una respiración normal) es de apenas ~500 mL — una fracción de los ~6 litros de capacidad pulmonar total.",
            "Casi todo el CO₂ de la sangre viaja como bicarbonato, no disuelto directamente ni unido a la hemoglobina.",
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
            {"q": "¿Por qué el bronquio principal derecho es la vía más probable en una aspiración accidental?",
             "options": ["Es más ancho, corto y vertical que el izquierdo", "Es más largo y angosto", "Está más lejos de la tráquea", "Tiene más lóbulos"],
             "correct": "Es más ancho, corto y vertical que el izquierdo",
             "explain": "Su trayecto más recto y ancho hace que un objeto aspirado tienda a caer ahí en vez de al izquierdo."},
            {"q": "¿Qué célula alveolar produce el surfactante que evita el colapso del alvéolo?",
             "options": ["Neumocito tipo II", "Neumocito tipo I", "Macrófago alveolar", "Célula de Schwann"],
             "correct": "Neumocito tipo II",
             "explain": "Los neumocitos tipo II producen surfactante; los tipo I son el epitelio delgado donde ocurre el intercambio de gases."},
            {"q": "¿En cuántos segmentos broncopulmonares independientes se divide el pulmón derecho?",
             "options": ["10", "3", "23", "2"], "correct": "10",
             "explain": "El derecho tiene 10 segmentos broncopulmonares (el izquierdo, de 8 a 10), cada uno con su propio bronquio segmentario."},
            {"q": "¿Cómo viaja la mayor parte del CO₂ en la sangre?",
             "options": ["Como bicarbonato", "Disuelto directamente en el plasma", "Unido a la hemoglobina", "Como gas libre"],
             "correct": "Como bicarbonato",
             "explain": "La mayoría del CO₂ se transporta como bicarbonato; una fracción menor va unida a la hemoglobina y otra disuelta."},
            {"q": "¿Por qué a la zona de conducción (nariz, faringe, tráquea, bronquios) se le llama \"espacio muerto\"?",
             "options": ["Porque no hay intercambio de gases ahí", "Porque no le llega sangre", "Porque solo funciona al dormir", "Porque se colapsa al espirar"],
             "correct": "Porque no hay intercambio de gases ahí",
             "explain": "La zona de conducción solo transporta, calienta, humedece y filtra el aire; el intercambio real de O₂/CO₂ ocurre en la zona respiratoria."},
            {"q": "¿Qué es la língula?",
             "options": ["Una lengüeta de tejido del pulmón izquierdo, junto a la escotadura cardíaca", "Un tercer lóbulo del pulmón izquierdo", "Otro nombre para la tráquea", "Un tipo de alvéolo"],
             "correct": "Una lengüeta de tejido del pulmón izquierdo, junto a la escotadura cardíaca",
             "explain": "El pulmón izquierdo cede espacio al corazón: en su borde anterior hay una escotadura cardíaca junto a la língula."},
            {"q": "¿Qué porcentaje de la superficie alveolar cubren los neumocitos tipo I?",
             "options": ["Cerca del 90%", "Cerca del 10%", "El 50%", "El 100%, no hay otro tipo"],
             "correct": "Cerca del 90%",
             "explain": "Los neumocitos tipo I son un epitelio muy delgado que cubre ~90% de la superficie alveolar; ahí ocurre el intercambio de gases."},
            {"q": "¿Qué mide principalmente el tronco encefálico para regular el ritmo respiratorio?",
             "options": ["El nivel de CO₂ en la sangre", "El nivel de O₂ en la sangre", "La frecuencia cardiaca", "La temperatura corporal"],
             "correct": "El nivel de CO₂ en la sangre",
             "explain": "El tronco encefálico ajusta el ritmo respiratorio sobre todo según el CO₂ en sangre, mucho más que según el oxígeno."},
            {"q": "¿Qué músculo en forma de cúpula es el principal motor de la respiración?",
             "options": ["El diafragma", "El músculo cardíaco", "Los músculos abdominales", "El esternocleidomastoideo"],
             "correct": "El diafragma",
             "explain": "El diafragma se contrae y baja, y junto con los músculos intercostales genera la presión negativa que \"succiona\" el aire."},
            {"q": "¿Cuál es la capacidad pulmonar total aproximada de un adulto?",
             "options": ["Alrededor de 6 litros", "Alrededor de 1 litro", "Alrededor de 20 litros", "Alrededor de 0.5 litros"],
             "correct": "Alrededor de 6 litros",
             "explain": "La capacidad pulmonar total es de unos 6 litros, aunque una respiración normal (volumen corriente) mueve solo ~500 mL."},
            {"q": "¿Qué función cumplen los macrófagos alveolares?",
             "options": ["Eliminar partículas y microbios inhalados", "Producir surfactante", "Formar la pleura", "Transportar oxígeno en la sangre"],
             "correct": "Eliminar partículas y microbios inhalados",
             "explain": "Los macrófagos alveolares patrullan la superficie del alvéolo eliminando partículas y microorganismos inhalados."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 220 210" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
        "landmark_info": {
            "Ápex (punta)": (
                "El ápex cardíaco es la punta redondeada y móvil del corazón, formada "
                "casi por completo por el ventrículo izquierdo. En una persona viva, in "
                "situ, apunta hacia abajo, adelante y a la izquierda — es donde "
                "normalmente se palpa el latido en la pared torácica."
            ),
            "Base": (
                "La base es el extremo ancho y fijo del corazón, opuesto al ápex, "
                "formado principalmente por la aurícula izquierda. Aquí entran y salen "
                "los grandes vasos: las venas cavas, las venas pulmonares, la aorta y el "
                "tronco pulmonar."
            ),
        },
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
            "<h3>Las capas de la pared, de adentro hacia afuera</h3>"
            "<p>La pared del corazón tiene tres capas. El <b>endocardio</b> es la capa "
            "interna que recubre las cámaras y las válvulas. El <b>miocardio</b>, la "
            "capa media y muscular, es la que realmente genera la fuerza de bombeo — "
            "es mucho más grueso en el ventrículo izquierdo, que debe empujar sangre a "
            "todo el cuerpo. El <b>epicardio</b> es la capa externa, y por fuera de "
            "todo el corazón está envuelto en un saco llamado <b>pericardio</b>, cuyo "
            "líquido reduce la fricción con cada latido. Un <b>esqueleto fibroso</b> de "
            "anillos de tejido conectivo sostiene las cuatro válvulas y aísla "
            "eléctricamente las aurículas de los ventrículos, obligando al impulso "
            "eléctrico a pasar únicamente por el nodo AV y el haz de His.</p>"
            "<h3>Las arterias que alimentan al propio corazón</h3>"
            "<p>El músculo cardíaco tiene su propio riego, independiente de la sangre "
            "que bombea: las <b>arterias coronarias</b>, que nacen justo a la salida de "
            "la aorta. La <b>coronaria derecha</b> irriga la aurícula y el ventrículo "
            "derechos y la cara inferior del corazón, y en la mayoría de las personas "
            "nutre tanto el nodo sinusal como el nodo AV. La <b>coronaria izquierda</b> "
            "se divide en dos ramas: la <b>descendente anterior</b>, que irriga el "
            "tabique y la cara anterior del ventrículo izquierdo —apodada informalmente "
            "\"la arteria de la muerte súbita\" por lo crítico de un bloqueo ahí— y la "
            "<b>circunfleja</b>, que cubre la cara lateral y posterior del ventrículo "
            "izquierdo. Esto es justo lo que se tapa en un infarto: una placa de grasa "
            "bloqueando alguna de estas arterias.</p>"
            "<h3>Del impulso eléctrico al latido que se escucha</h3>"
            "<p>El recorrido eléctrico completo es: nodo sinusal → aurículas → nodo "
            "auriculoventricular (que retrasa la señal para dar tiempo a que los "
            "ventrículos terminen de llenarse) → haz de His → sus dos ramas por el "
            "tabique interventricular → fibras de Purkinje, que reparten el impulso "
            "por todo el miocardio ventricular para lograr una contracción coordinada. "
            "En un electrocardiograma, la onda P es la despolarización de las "
            "aurículas, el complejo QRS es la de los ventrículos y la onda T es su "
            "repolarización. Los dos sonidos del latido tienen origen mecánico "
            "preciso: <b>S1</b> (\"lub\") es el cierre de las válvulas "
            "auriculoventriculares al inicio de la sístole, y <b>S2</b> (\"dub\") es "
            "el cierre de las válvulas semilunares al inicio de la diástole.</p>"
        ),
        "threshold_native": 27000,
        "threshold_below": False,
        "threshold_label": "27000 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Frecuencia cardiaca en reposo: 60–100 latidos por minuto en un adulto (deportistas de resistencia pueden bajar de 40–50).",
            "Late en promedio unas 100,000 veces al día — más de 2,500 millones de veces en una vida.",
            "Bombea alrededor de 5 litros de sangre por minuto en reposo.",
            "Todos los vasos sanguíneos del cuerpo, estirados en línea, medirían más de 100,000 km.",
            "La arteria coronaria descendente anterior se apoda informalmente \"la arteria de la muerte súbita\" por lo crítico de un bloqueo en ella.",
            "El nodo sinusal genera entre 60 y 100 impulsos eléctricos por minuto sin necesitar ninguna señal externa del cerebro.",
            "El ventrículo izquierdo tiene una pared muscular mucho más gruesa que el derecho, porque bombea sangre a todo el cuerpo y no solo a los pulmones.",
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
            {"q": "¿Qué capa del corazón genera la fuerza real de bombeo?",
             "options": ["El miocardio", "El endocardio", "El epicardio", "El pericardio"], "correct": "El miocardio",
             "explain": "El miocardio es la capa media, muscular, y es mucho más grueso en el ventrículo izquierdo."},
            {"q": "¿Qué arteria coronaria se apoda informalmente \"la arteria de la muerte súbita\"?",
             "options": ["La descendente anterior", "La circunfleja", "La coronaria derecha", "La aorta"],
             "correct": "La descendente anterior",
             "explain": "La descendente anterior irriga el tabique y la cara anterior del ventrículo izquierdo — un bloqueo ahí es especialmente crítico."},
            {"q": "En el ECG, ¿qué representa el complejo QRS?",
             "options": ["La despolarización de los ventrículos", "La despolarización de las aurículas", "La repolarización ventricular", "El cierre de las válvulas AV"],
             "correct": "La despolarización de los ventrículos",
             "explain": "La onda P es la despolarización auricular, el QRS la ventricular, y la onda T la repolarización ventricular."},
            {"q": "¿Qué provoca el sonido S1 (\"lub\") del latido?",
             "options": ["El cierre de las válvulas auriculoventriculares", "El cierre de las válvulas semilunares", "La contracción del nodo sinusal", "El llenado de las aurículas"],
             "correct": "El cierre de las válvulas auriculoventriculares",
             "explain": "S1 es el cierre de tricúspide y mitral al inicio de la sístole; S2 es el cierre de las semilunares al inicio de la diástole."},
            {"q": "¿Cuántas veces late el corazón en promedio a lo largo de un día?",
             "options": ["Unas 100,000 veces", "Unas 1,000 veces", "Unas 10,000,000 de veces", "Unas 500 veces"],
             "correct": "Unas 100,000 veces",
             "explain": "Late en promedio unas 100,000 veces al día — más de 2,500 millones de veces a lo largo de una vida."},
            {"q": "¿Cómo se llama el saco que envuelve al corazón por fuera y cuyo líquido reduce la fricción de cada latido?",
             "options": ["El pericardio", "El endocardio", "El miocardio", "El esqueleto fibroso"],
             "correct": "El pericardio",
             "explain": "El epicardio es la capa externa del propio corazón; por fuera de todo está envuelto en el pericardio, un saco con líquido lubricante."},
            {"q": "¿Qué arteria coronaria irriga, en la mayoría de las personas, tanto el nodo sinusal como el nodo AV?",
             "options": ["La coronaria derecha", "La descendente anterior", "La circunfleja", "La aorta"],
             "correct": "La coronaria derecha",
             "explain": "La coronaria derecha irriga la aurícula y el ventrículo derechos, la cara inferior del corazón, y en la mayoría de las personas también los nodos sinusal y AV."},
            {"q": "¿Para qué sirve el esqueleto fibroso del corazón?",
             "options": ["Aísla eléctricamente las aurículas de los ventrículos", "Bombea la sangre por sí mismo", "Produce el surfactante cardíaco", "Genera el impulso eléctrico"],
             "correct": "Aísla eléctricamente las aurículas de los ventrículos",
             "explain": "El esqueleto fibroso sostiene las cuatro válvulas y obliga al impulso eléctrico a pasar únicamente por el nodo AV y el haz de His."},
            {"q": "¿Qué rama de la coronaria izquierda irriga la cara lateral y posterior del ventrículo izquierdo?",
             "options": ["La circunfleja", "La descendente anterior", "La coronaria derecha", "La arteria pulmonar"],
             "correct": "La circunfleja",
             "explain": "La coronaria izquierda se divide en descendente anterior (tabique y cara anterior) y circunfleja (cara lateral y posterior)."},
            {"q": "¿Qué representa la onda P en un electrocardiograma?",
             "options": ["La despolarización de las aurículas", "La despolarización de los ventrículos", "La repolarización ventricular", "El cierre de las válvulas semilunares"],
             "correct": "La despolarización de las aurículas",
             "explain": "La onda P es la despolarización auricular; el QRS es la ventricular y la onda T es la repolarización de los ventrículos."},
            {"q": "¿Qué provoca el sonido S2 (\"dub\") del latido?",
             "options": ["El cierre de las válvulas semilunares", "El cierre de las válvulas auriculoventriculares", "La contracción del nodo sinusal", "El llenado de los ventrículos"],
             "correct": "El cierre de las válvulas semilunares",
             "explain": "S2 es el cierre de las válvulas semilunares (aórtica y pulmonar) al inicio de la diástole."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 240 260" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
            "exhibición fija, no direcciones anatómicas verificadas. El modelo sí se "
            "rotó (180°, sobre su propio centro) para que la superficie más voluminosa "
            "quede arriba, en vez de abajo, según el análisis de asimetría de masa real "
            "de la malla — igual que la corrección del cerebro, es una elección de "
            "exhibición, no la orientación real del espécimen. Las etiquetas de "
            "\"lóbulo mayor/menor\" sobre el modelo sí están calculadas de forma real, "
            "a partir de la partición de volumen de la malla — no de la orientación."
        ),
        "color_hex": "#b9793f",
        "landmark_info": {
            "Lóbulo derecho (mayor)": (
                "El lóbulo derecho es, por mucho, la porción más grande del hígado — se "
                "estima que puede pesar de cinco a seis veces más que el izquierdo. "
                "Ocupa la mayor parte del cuadrante superior derecho del abdomen, justo "
                "bajo el diafragma."
            ),
            "Lóbulo izquierdo (menor)": (
                "El lóbulo izquierdo es notablemente más pequeño y se extiende hacia la "
                "línea media del abdomen, por delante del estómago. Aunque es menor en "
                "tamaño, contiene varios de los ocho segmentos de Couinaud, cada uno con "
                "su propio riego sanguíneo independiente."
            ),
        },
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
            {"q": "¿Qué arteria aporta el 25% restante de la sangre que recibe el hígado (el otro 75% viene de la vena porta)?",
             "options": ["La arteria hepática", "La arteria renal", "La arteria pulmonar", "La aorta directamente"],
             "correct": "La arteria hepática",
             "explain": "El hígado tiene doble entrada de sangre: ~75% por la vena porta y ~25% por la arteria hepática."},
            {"q": "¿En qué parte del abdomen se ubica el hígado?",
             "options": ["Cuadrante superior derecho, bajo el diafragma", "Cuadrante inferior izquierdo", "Justo detrás del ombligo", "En la pelvis"],
             "correct": "Cuadrante superior derecho, bajo el diafragma",
             "explain": "El hígado, el órgano sólido interno más grande, se ubica en el cuadrante superior derecho del abdomen."},
            {"q": "¿Cuál de los dos lóbulos hepáticos principales es mucho más grande?",
             "options": ["El lóbulo derecho", "El lóbulo izquierdo", "Son del mismo tamaño", "Depende de cada persona"],
             "correct": "El lóbulo derecho",
             "explain": "El lóbulo derecho puede pesar de cinco a seis veces más que el izquierdo."},
            {"q": "¿Cómo se llaman las unidades microscópicas donde se mezclan la sangre de la vena porta y la arteria hepática?",
             "options": ["Lobulillos hepáticos", "Nefronas", "Alvéolos", "Segmentos de Couinaud"],
             "correct": "Lobulillos hepáticos",
             "explain": "Dentro de los lobulillos hepáticos, los hepatocitos procesan la sangre mezclada antes de que salga por las venas hepáticas."},
            {"q": "¿Cómo se llaman las células del hígado que procesan la sangre?",
             "options": ["Hepatocitos", "Nefronas", "Neumocitos", "Cardiomiocitos"],
             "correct": "Hepatocitos",
             "explain": "Los hepatocitos son las células funcionales del hígado, responsables de la mayoría de sus funciones metabólicas."},
            {"q": "¿En qué forma almacena el hígado la glucosa sobrante para liberarla cuando hace falta energía?",
             "options": ["Como glucógeno", "Como grasa únicamente", "Como bilis", "No la almacena"],
             "correct": "Como glucógeno",
             "explain": "El hígado convierte el exceso de glucosa en glucógeno, una reserva que libera de vuelta cuando el cuerpo necesita energía."},
            {"q": "¿Qué proteína de la sangre, clave para mantener la presión oncótica, sintetiza el hígado?",
             "options": ["La albúmina", "La hemoglobina", "La insulina", "La renina"],
             "correct": "La albúmina",
             "explain": "El hígado sintetiza la albúmina y los factores de coagulación, entre muchas otras proteínas plasmáticas."},
            {"q": "¿Dónde se almacena la bilis que produce el hígado?",
             "options": ["En la vesícula biliar", "En el riñón", "En el estómago", "En el bazo"],
             "correct": "En la vesícula biliar",
             "explain": "La bilis producida por el hígado se almacena en la vesícula biliar y ayuda a digerir las grasas en el intestino."},
            {"q": "¿Cada cuánto tiempo se estima que toda la sangre del cuerpo pasa por el hígado para ser filtrada?",
             "options": ["Cada 2–3 minutos", "Cada 24 horas", "Una vez por semana", "Cada segundo"],
             "correct": "Cada 2–3 minutos",
             "explain": "Toda la sangre del cuerpo circula a través del hígado aproximadamente cada 2–3 minutos."},
            {"q": "¿Qué enfermedad hepática consiste en el reemplazo progresivo del tejido sano por cicatrices?",
             "options": ["Cirrosis", "Hepatitis", "Hígado graso", "Ictericia"],
             "correct": "Cirrosis",
             "explain": "Si el daño hepático se repite durante años, el tejido sano se reemplaza por cicatrices: cirrosis."},
            {"q": "¿Qué capacidad del hígado hace posible el trasplante de donante vivo?",
             "options": ["Su capacidad de regenerarse", "Su gran tamaño fijo", "Que no necesita riego sanguíneo", "Que no tiene funciones vitales"],
             "correct": "Su capacidad de regenerarse",
             "explain": "Tanto la porción donada como la que queda en el donante vuelven a crecer, porque el hígado puede regenerar su tamaño funcional."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="-40 0 360 280" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            '<path d="M40,85 C40,62 85,50 145,54 C220,58 280,80 280,132 C280,182 218,212 148,206 C88,201 40,168 40,122 Z" fill="#b9793f" fill-opacity="0.88" stroke="var(--border)" stroke-width="2"/>'
            '<line x1="172" y1="58" x2="150" y2="204" stroke="var(--bg)" stroke-width="4"/>'
            '<text x="220" y="128" font-size="12" text-anchor="middle" fill="#fff">Lóbulo derecho</text>'
            '<text x="100" y="98" font-size="11" text-anchor="middle" fill="#fff">Lóbulo<tspan x="100" dy="13">izquierdo</tspan></text>'
            '<ellipse cx="192" cy="192" rx="13" ry="9" fill="#6b8e4e"/>'
            '<text x="192" y="222" font-size="9" text-anchor="middle" fill="var(--text-dim)">Vesícula biliar</text>'
            '<line x1="60" y1="150" x2="16" y2="150" stroke="var(--text-dim)" stroke-width="2"/>'
            '<text x="14" y="145" font-size="9" text-anchor="end" fill="var(--text-dim)">Vena porta</text>'
            '</svg><div class="diagram-card-label">Los dos lóbulos principales y la vesícula biliar</div></div>'
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 220 210" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
        "landmark_info": {
            "Hilio renal (aprox.)": (
                "El hilio renal es el punto en el borde medial y cóncavo del riñón por "
                "donde entran y salen la arteria renal, la vena renal, los nervios y el "
                "uréter. En un riñón intacto es la referencia clave para saber qué lado "
                "es medial y cuál lateral."
            ),
            "Polo A": (
                "Los riñones tienen un polo superior y un polo inferior en los extremos "
                "de su eje más largo. Externamente son similares en forma, así que sin "
                "más contexto no es posible distinguir cuál es cuál solo por la "
                "geometría de la superficie — por eso este pin no se etiqueta como "
                "\"superior\" ni \"inferior\"."
            ),
            "Polo B": (
                "El otro extremo del eje más largo del riñón. Igual que el Polo A, no "
                "hay una forma honesta de saber si es el polo superior o el inferior "
                "sin metadatos de orientación del paciente."
            ),
        },
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
            "<h3>El camino de la sangre dentro del riñón</h3>"
            "<p>La sangre entra por la arteria renal y se ramifica en un orden muy "
            "preciso: arterias segmentarias → interlobares → arcuatas → "
            "interlobulillares → arteriola aferente → glomérulo → arteriola eferente → "
            "capilares peritubulares (que envuelven el resto de la nefrona) → venas → "
            "vena renal. El detalle clave es que el glomérulo queda atrapado entre dos "
            "arteriolas, no entre una arteria y una vena como el resto del cuerpo — así, "
            "el riñón puede regular la presión de filtración simplemente contrayendo o "
            "relajando el calibre de esas dos arteriolas.</p>"
            "<h3>Tres pasos, no solo uno</h3>"
            "<p>Formar orina no es solo \"filtrar\": son tres procesos independientes. La "
            "<b>filtración glomerular</b> empuja plasma del glomérulo hacia la cápsula "
            "de Bowman a un ritmo de unos 125 mL por minuto (la TFG, el mejor indicador "
            "global de qué tan bien funcionan los riñones). La <b>reabsorción "
            "tubular</b> devuelve a la sangre lo que todavía sirve —el túbulo "
            "contorneado proximal por sí solo reabsorbe cerca del 65% del sodio y el "
            "agua, y prácticamente toda la glucosa—. La <b>secreción tubular</b> hace "
            "el proceso inverso: pasa sustancias extra (H⁺, K⁺, ciertos fármacos) desde "
            "la sangre hacia el filtrado. Lo que queda al final, orina = filtrado − "
            "reabsorbido + secretado, sale por el conducto colector.</p>"
            "<h3>Un sensor de presión dentro del propio riñón</h3>"
            "<p>Donde el túbulo distal vuelve a pasar junto a su propio glomérulo de "
            "origen hay una estructura especializada, el <b>aparato "
            "yuxtaglomerular</b>: la mácula densa detecta la concentración de sodio y "
            "la presión del filtrado, y si detecta que la presión arterial bajó, las "
            "células yuxtaglomerulares liberan renina. Esa renina dispara el sistema "
            "renina-angiotensina-aldosterona (SRAA): angiotensina II contrae los vasos "
            "sanguíneos, y la aldosterona hace que el túbulo distal reabsorba más sodio "
            "y agua — dos formas distintas de subir la presión arterial de vuelta. La "
            "hormona antidiurética (ADH) actúa en el conducto colector concentrando la "
            "orina cuando el cuerpo necesita retener agua, y el péptido natriurético "
            "hace justo lo contrario cuando sobra volumen.</p>"
        ),
        "threshold_native": 44300,
        "threshold_below": False,
        "threshold_label": "44300 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Filtran alrededor de 180 litros de sangre al día, aunque solo producen 1–2 litros de orina.",
            "Cada riñón contiene cerca de un millón de nefronas, sus unidades de filtrado.",
            "Es posible llevar una vida normal con un solo riñón funcional.",
            "El glomérulo es el único lugar del cuerpo donde un lecho capilar queda entre dos arteriolas, no entre una arteria y una vena.",
            "La tasa de filtración glomerular (TFG) normal es de unos 125 mL por minuto — el mejor indicador global de la función renal.",
            "El túbulo contorneado proximal reabsorbe por sí solo cerca del 65% del sodio y el agua filtrados, y casi toda la glucosa.",
            "Los riñones reciben entre el 20% y el 25% de todo el gasto cardíaco, un porcentaje enorme para su tamaño.",
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
            {"q": "¿Qué tiene de especial el glomérulo comparado con otros lechos capilares del cuerpo?",
             "options": ["Queda entre dos arteriolas, no entre arteria y vena", "No recibe sangre arterial", "Es el único capilar sin membrana basal", "Está fuera del riñón"],
             "correct": "Queda entre dos arteriolas, no entre arteria y vena",
             "explain": "Esa disposición entre arteriola aferente y eferente permite regular la presión de filtración ajustando su calibre."},
            {"q": "¿Qué segmento de la nefrona reabsorbe cerca del 65% del sodio y el agua filtrados?",
             "options": ["El túbulo contorneado proximal", "El asa de Henle", "El túbulo contorneado distal", "El conducto colector"],
             "correct": "El túbulo contorneado proximal",
             "explain": "El TCP es el gran reabsorbedor de la nefrona: recupera ~65% del sodio y el agua, y casi toda la glucosa."},
            {"q": "¿Qué estructura detecta la presión y el sodio para liberar renina?",
             "options": ["El aparato yuxtaglomerular", "La cápsula de Bowman", "El conducto colector", "La pelvis renal"],
             "correct": "El aparato yuxtaglomerular",
             "explain": "Su mácula densa detecta presión/sodio y sus células yuxtaglomerulares liberan renina, activando el SRAA."},
            {"q": "¿Aproximadamente qué porcentaje del gasto cardíaco reciben los riñones?",
             "options": ["20–25%", "1–2%", "50–60%", "90%"], "correct": "20–25%",
             "explain": "Reciben entre el 20% y el 25% de todo el gasto cardíaco, un porcentaje muy alto para su tamaño relativo."},
            {"q": "¿Cuál es la tasa de filtración glomerular (TFG) normal aproximada?",
             "options": ["Unos 125 mL por minuto", "Unos 5 mL por minuto", "Unos 1000 mL por minuto", "Unos 25 mL por hora"],
             "correct": "Unos 125 mL por minuto",
             "explain": "La TFG normal es de unos 125 mL/min — el mejor indicador global de qué tan bien funcionan los riñones."},
            {"q": "¿Qué proceso tubular hace lo contrario de la reabsorción, pasando sustancias de la sangre hacia el filtrado?",
             "options": ["La secreción tubular", "La filtración glomerular", "La reabsorción tubular", "La micción"],
             "correct": "La secreción tubular",
             "explain": "La secreción tubular pasa sustancias extra (H⁺, K⁺, ciertos fármacos) desde la sangre hacia el filtrado, al revés de la reabsorción."},
            {"q": "¿Qué hormona producen los riñones para estimular la fabricación de glóbulos rojos en la médula ósea?",
             "options": ["Eritropoyetina", "Insulina", "Renina", "Aldosterona"],
             "correct": "Eritropoyetina",
             "explain": "Los riñones producen eritropoyetina, que estimula a la médula ósea a fabricar glóbulos rojos."},
            {"q": "¿Qué hormona actúa en el conducto colector para concentrar la orina cuando el cuerpo necesita retener agua?",
             "options": ["La hormona antidiurética (ADH)", "La eritropoyetina", "La insulina", "El péptido natriurético"],
             "correct": "La hormona antidiurética (ADH)",
             "explain": "La ADH concentra la orina reteniendo agua en el conducto colector; el péptido natriurético hace lo contrario cuando sobra volumen."},
            {"q": "¿Cuáles son las dos grandes zonas del tejido renal, de fuera hacia adentro?",
             "options": ["Corteza y médula renal", "Pelvis y uréter", "Cápsula y glomérulo", "Hilio y cáliz"],
             "correct": "Corteza y médula renal",
             "explain": "La corteza renal es la capa externa y la médula (dividida en pirámides) la interna; de ahí la orina gotea hacia la pelvis renal."},
            {"q": "¿Qué hace la angiotensina II una vez activado el sistema renina-angiotensina-aldosterona (SRAA)?",
             "options": ["Contrae los vasos sanguíneos, subiendo la presión arterial", "Dilata los vasos sanguíneos", "Elimina sodio del cuerpo", "Detiene la producción de orina"],
             "correct": "Contrae los vasos sanguíneos, subiendo la presión arterial",
             "explain": "La angiotensina II contrae los vasos, y la aldosterona hace que el túbulo distal retenga más sodio y agua: dos formas de subir la presión."},
            {"q": "¿A qué órgano llega la orina desde la pelvis renal a través del uréter?",
             "options": ["La vejiga", "El estómago", "El hígado", "El intestino"],
             "correct": "La vejiga",
             "explain": "El uréter conecta la pelvis renal, el embudo colector del riñón, con la vejiga."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 320 280" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
        "landmark_info": {
            "Hemisferio 1": (
                "Los dos hemisferios cerebrales están conectados por el cuerpo calloso y "
                "son, en su forma externa, casi simétricos entre sí — aunque no "
                "funcionalmente idénticos: el lenguaje, por ejemplo, suele dominar en "
                "uno solo. Sin marcas externas ni metadatos de orientación, no hay forma "
                "honesta de etiquetar cuál es el izquierdo y cuál el derecho solo a "
                "partir de la geometría de esta malla."
            ),
            "Hemisferio 2": (
                "El otro hemisferio cerebral. Igual que su par, es casi simétrico "
                "externamente, así que este pin tampoco se etiqueta como izquierdo o "
                "derecho — sería una afirmación que esta malla no puede respaldar."
            ),
        },
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
            "<h3>Un mapa del cuerpo dibujado en la corteza</h3>"
            "<p>La corteza motora primaria (en el lóbulo frontal) y la corteza "
            "somatosensitiva primaria (justo detrás, en el parietal) representan cada "
            "parte del cuerpo en un mapa ordenado pero muy desproporcionado — el "
            "llamado <b>homúnculo</b>: la cara y las manos, que necesitan un control "
            "finísimo, ocupan un área de corteza mucho mayor que el tronco o las "
            "piernas. El lenguaje también tiene sus propias zonas dedicadas, "
            "normalmente en el hemisferio dominante: el <b>área de Broca</b>, en el "
            "frontal, produce el habla —si se lesiona, la persona entiende todo pero "
            "habla de forma entrecortada—, y el <b>área de Wernicke</b>, en el "
            "temporal, la comprende —si se lesiona, el habla sigue siendo fluida pero "
            "deja de tener sentido—.</p>"
            "<h3>Estructuras profundas: movimiento, memoria y estado de alerta</h3>"
            "<p>Debajo de la corteza hay núcleos que no se ven desde la superficie del "
            "cerebro pero son igual de importantes. Los <b>ganglios basales</b> "
            "(núcleo caudado, putamen y globo pálido) inician y regulan el movimiento "
            "y el tono muscular — cuando fallan aparecen el Parkinson o la Huntington. "
            "El <b>sistema límbico</b> incluye al hipocampo, encargado de formar "
            "nuevos recuerdos, y a la amígdala, el centro del miedo y las emociones; "
            "el daño al hipocampo produce amnesia. La <b>formación reticular</b>, "
            "repartida por el tronco encefálico, regula el nivel de conciencia, la "
            "vigilia y el sueño.</p>"
            "<h3>Cómo llega la sangre al cerebro</h3>"
            "<p>Tres grandes arterias, todas ramas del sistema que forma el "
            "<b>círculo de Willis</b> en la base del cráneo, cubren todo el cerebro: "
            "la <b>cerebral anterior</b> irriga la cara medial de los hemisferios "
            "(donde está representada la pierna en el homúnculo), la <b>cerebral "
            "media</b> cubre toda la cara lateral —cara, brazo y las áreas del "
            "lenguaje— y es la arteria más afectada en un ACV, y la <b>cerebral "
            "posterior</b> irriga el lóbulo occipital, la zona de la visión.</p>"
        ),
        "threshold_native": 5000,
        "threshold_below": False,
        "threshold_label": "5000 unidades nativas (tejido = mayor que el umbral)",
        "fun_facts": [
            "Consume cerca del 20% de la energía total del cuerpo, aunque representa solo ~2% del peso corporal.",
            "Contiene aproximadamente 86 mil millones de neuronas.",
            "Las señales nerviosas pueden viajar hasta 120 metros por segundo.",
            "El propio tejido cerebral no tiene receptores de dolor — por eso algunas cirugías cerebrales se hacen con el paciente consciente.",
            "En el homúnculo motor y sensitivo, la cara y las manos ocupan mucha más corteza que el tronco o las piernas, por lo fino de su control.",
            "El área de Broca (producción del habla) y el área de Wernicke (comprensión) son zonas distintas del cerebro — dañar una u otra produce problemas de lenguaje muy diferentes.",
            "La arteria cerebral media es la más afectada en un accidente cerebrovascular (ACV).",
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
            {"q": "¿Qué le pasa al habla si se lesiona el área de Broca?",
             "options": ["Se vuelve entrecortada, pero se entiende todo", "El paciente pierde por completo la memoria", "El habla es fluida pero sin sentido", "No hay ningún efecto"],
             "correct": "Se vuelve entrecortada, pero se entiende todo",
             "explain": "Broca produce el habla; su lesión da un habla entrecortada con comprensión intacta. Wernicke es al revés: habla fluida sin sentido."},
            {"q": "¿Qué grupo de núcleos, al fallar, se asocia con Parkinson o Huntington?",
             "options": ["Los ganglios basales", "El sistema límbico", "El cerebelo", "El tálamo"],
             "correct": "Los ganglios basales",
             "explain": "Los ganglios basales (caudado, putamen, globo pálido) inician y regulan el movimiento y el tono muscular."},
            {"q": "¿Cuál arteria cerebral es la más afectada en un accidente cerebrovascular (ACV)?",
             "options": ["La cerebral media", "La cerebral anterior", "La cerebral posterior", "La basilar"],
             "correct": "La cerebral media",
             "explain": "La cerebral media cubre toda la cara lateral del cerebro (cara, brazo, lenguaje) y es la más afectada por un ACV."},
            {"q": "¿Qué estructura del sistema límbico es clave para formar nuevos recuerdos?",
             "options": ["El hipocampo", "La amígdala", "El tálamo", "El cerebelo"], "correct": "El hipocampo",
             "explain": "El hipocampo forma nuevos recuerdos; su daño produce amnesia. La amígdala procesa miedo y emociones."},
            {"q": "¿Qué lóbulo cerebral procesa principalmente la información visual?",
             "options": ["El lóbulo occipital", "El lóbulo frontal", "El lóbulo parietal", "El lóbulo temporal"],
             "correct": "El lóbulo occipital",
             "explain": "El lóbulo occipital procesa la visión; el frontal razona y planifica, el parietal procesa tacto y orientación, el temporal oye y recuerda."},
            {"q": "¿Qué estructura conecta y comunica el hemisferio cerebral izquierdo con el derecho?",
             "options": ["El cuerpo calloso", "El cerebelo", "El tronco encefálico", "La amígdala"],
             "correct": "El cuerpo calloso",
             "explain": "El cuerpo calloso es el haz de fibras (sustancia blanca) que comunica ambos hemisferios."},
            {"q": "¿Cuál es la función principal del cerebelo?",
             "options": ["Afinar la coordinación motora y el equilibrio", "Generar el habla", "Formar nuevos recuerdos", "Regular la presión arterial"],
             "correct": "Afinar la coordinación motora y el equilibrio",
             "explain": "El cerebelo afina la coordinación, el equilibrio y la precisión de los movimientos, aunque no los origina."},
            {"q": "¿Qué líquido amortigua al cerebro dentro del cráneo, circulando entre las meninges?",
             "options": ["El líquido cefalorraquídeo", "El plasma sanguíneo", "La linfa", "El humor vítreo"],
             "correct": "El líquido cefalorraquídeo",
             "explain": "Tres membranas (meninges) envuelven el cerebro, y entre ellas circula el líquido cefalorraquídeo, que lo amortigua como un cojín líquido."},
            {"q": "¿Qué pasa con el habla si se lesiona el área de Wernicke?",
             "options": ["Sigue siendo fluida pero deja de tener sentido", "Se vuelve entrecortada pero se entiende todo", "Se pierde por completo la memoria", "No hay ningún efecto"],
             "correct": "Sigue siendo fluida pero deja de tener sentido",
             "explain": "Wernicke comprende el lenguaje; su lesión da habla fluida sin sentido. Es lo opuesto a una lesión de Broca."},
            {"q": "¿Qué estructura del sistema límbico es el centro del miedo y las emociones?",
             "options": ["La amígdala", "El hipocampo", "El tálamo", "La formación reticular"],
             "correct": "La amígdala",
             "explain": "La amígdala procesa el miedo y las emociones; el hipocampo, en cambio, forma nuevos recuerdos."},
            {"q": "¿Qué arteria cerebral irriga el lóbulo occipital, la zona de la visión?",
             "options": ["La cerebral posterior", "La cerebral anterior", "La cerebral media", "La carótida externa"],
             "correct": "La cerebral posterior",
             "explain": "Las tres arterias cerebrales (anterior, media y posterior) nacen del círculo de Willis; la posterior irriga el occipital."},
        ],
        "diagram_svg": (
            '<div class="diagram-card diagram-main"><svg viewBox="0 0 380 280" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
            '<div class="diagram-card diagram-inset"><svg viewBox="0 0 240 170" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
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
    # payload es el JSON producido por build_demo_payload.py: trae, para
    # cada organo disponible, la malla 3D codificada, los cortes 2D y las
    # metricas/validacion reales de la reconstruccion. Aqui solo se
    # seleccionan esos 4 campos por organo (se descarta cualquier otro
    # campo de payload que no use el visor).
    viewer_data = {}
    for organ in ORGAN_ORDER:
        if organ not in payload:
            # Si el payload no trae este organo (p. ej. una corrida parcial),
            # simplemente se omite: el visor solo mostrara los que sí llegaron.
            continue
        entry = payload[organ]
        viewer_data[organ] = {
            "mesh": entry["mesh"],              # posiciones/normales/indices de la malla 3D, en base64.
            "slices": entry["slices"],          # cubo de voxeles submuestreado para los cortes MPR.
            "metrics": entry["metrics"],        # volumen, num. de vertices/caras, etc.
            "validation": entry["validation"],  # resultado del pipeline de validacion (real, no inventado).
        }

    # Lista final de organos que realmente van a aparecer en el visor,
    # respetando el orden de ORGAN_ORDER.
    available_organs = [o for o in ORGAN_ORDER if o in viewer_data]

    # _TEMPLATE es el HTML/CSS/JS completo del visor como un solo string,
    # con tres marcadores de texto (__..._JSON__) que se sustituyen aqui
    # por datos reales serializados a JSON. Se usa .replace() de texto
    # plano (no .format()) precisamente para no chocar con las llaves
    # { } que abundan en el CSS y el JavaScript de la plantilla.
    html = _TEMPLATE
    html = html.replace("__ORGAN_ORDER_JSON__", json.dumps(available_organs))
    html = html.replace("__ORGAN_META_JSON__", json.dumps({k: ORGAN_META[k] for k in available_organs}))
    html = html.replace("__VIEWER_DATA_JSON__", json.dumps(viewer_data))
    return html


_TEMPLATE = r"""<!doctype html>
<html lang="es">
<title>Medical3DReconstruction — Visor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  /* ---- tema: variables de color/tipografía en modo oscuro (por defecto) ----
     "Design tokens": todo color/tipografía/radio de la interfaz sale de esta
     lista única — nunca un valor suelto en otra parte del CSS (los colores
     de los diagramas SVG educativos son la única excepción intencional:
     representan estructuras anatómicas reales — O₂, CO₂, vasos — no son
     parte del sistema de interfaz y deben verse igual sin importar el tema). */
  :root {
    --bg: #17181a; --surface: #1d1f22; --surface-raised: #26282c; --border: #35373b;
    /* --text-faint se usa como texto real (eyebrows, pies de nota, hints),
       así que su valor está calibrado para pasar el contraste mínimo 4.5:1
       de WCAG AA contra --bg Y contra --surface-raised, no solo "verse bien". */
    --text: #e8e9eb; --text-dim: #9a9da2; --text-faint: #8d8f95;
    --accent: #a5434b; --accent-soft: rgba(165,67,75,0.16); --accent-strong: #c0525b;
    --accent-ink: #f3e4e2;
    --warn: #c9974a; --ok: #5da868;
    --focus-ring: #7ab8e8; /* anillo de foco de teclado: debe contrastar contra fondo Y contra --accent, así que usa un tono distinto (azul) en vez de reutilizar --accent */
    --font-ui: "Inter", ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif;
    --font-serif: ui-serif, Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
    --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", "Consolas", monospace;
    --radius-sm: 3px; --radius-md: 4px; --radius-lg: 6px;
  }
  /* Sobrescribe las mismas variables para el tema claro, activado a mano
     con el atributo data-theme="light" en <html>/<body> (ver toggleTheme). */
  :root[data-theme="light"] {
    --bg: #f4f3f1; --surface: #ffffff; --surface-raised: #eceae6; --border: #d7d3cc;
    --text: #1c1b19; --text-dim: #5c574f; --text-faint: #6d685f;
    --accent: #8c2f39; --accent-soft: rgba(140,47,57,0.09); --accent-strong: #6b232b;
    --accent-ink: #fbeeee;
    --focus-ring: #1a5fa8;
  }
  /* Y también según la preferencia del sistema operativo, si el usuario
     no forzó un tema explícito con data-theme. */
  @media (prefers-color-scheme: light) {
    :root:not([data-theme="dark"]) {
      --bg: #f4f3f1; --surface: #ffffff; --surface-raised: #eceae6; --border: #d7d3cc;
      --text: #1c1b19; --text-dim: #5c574f; --text-faint: #6d685f;
      --accent: #8c2f39; --accent-soft: rgba(140,47,57,0.09); --accent-strong: #6b232b;
      --accent-ink: #fbeeee;
      --focus-ring: #1a5fa8;
    }
  }

  /* ---- reseteo base y layout general de la página (header + main a pantalla completa) ---- */
  * { box-sizing: border-box; }
  .hidden { display: none; }
  /* Anillo de foco de teclado, global: sin esto, navegar con Tab por la
     interfaz es invisible — un usuario que no usa mouse no puede saber
     dónde está parado. :focus-visible (no :focus a secas) evita mostrarlo
     en clics de mouse, solo en navegación real de teclado. */
  :focus-visible { outline: 2.5px solid var(--focus-ring); outline-offset: 2px; border-radius: var(--radius-sm); }
  /* Los controles ya redondeados (botones, sliders) se ven mejor con un
     anillo pegado a su propia forma en vez del reseteo genérico de arriba. */
  button:focus-visible, .organ-btn:focus-visible, .tab-btn:focus-visible { outline-offset: 1px; }
  /* Clase utilitaria "sr-only": mantiene el elemento accesible para lectores
     de pantalla sin mostrarlo visualmente — para labels de campos cuyo
     propósito ya es obvio para un usuario vidente por el contexto visual. */
  .visually-hidden { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
  html, body { height: 100%; margin: 0; background: var(--bg); color: var(--text); font-family: var(--font-ui); overflow: hidden; }
  body { display: flex; flex-direction: column; }
  /* Barra superior: logo, título, nombre del estudio y badges de estado. */
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

  /* ---- layout de dos columnas: barra lateral (aside) + área principal ---- */
  main { flex: 1; display: grid; grid-template-columns: 280px 1fr; min-height: 0; }
  main.hidden { display: none; }
  aside { border-right: 1px solid var(--border); background: var(--surface); overflow-y: auto; padding: 0.9rem; display: flex; flex-direction: column; gap: 0; }
  .panel-group { padding: 0.85rem 0; border-bottom: 1px solid var(--border); }
  .panel-group:first-child { padding-top: 0; }
  .panel-group:last-child { border-bottom: none; padding-bottom: 0; }
  .eyebrow { font-size: 0.64rem; font-weight: 650; letter-spacing: 0.07em; text-transform: uppercase; color: var(--text-faint); margin: 0 0 0.55rem; }
  /* ---- secciones secundarias colapsables (ley de Hick): "Medición" y
     "Exportar" no son lo primero que la mayoría de la gente toca, así que
     viven cerradas por defecto detrás de <details>/<summary> — nativo del
     navegador, con foco/teclado/lector de pantalla ya resueltos por el
     propio HTML, sin JavaScript. Reduce cuántas opciones compiten por
     atención al abrir la pestaña, sin quitarle ni un botón a nadie. ---- */
  details.panel-group summary { list-style: none; cursor: pointer; display: flex; align-items: center; justify-content: space-between; margin: 0 0 0.55rem; }
  details.panel-group summary::-webkit-details-marker { display: none; }
  details.panel-group summary .eyebrow { margin: 0; }
  details.panel-group summary .chevron { width: 12px; height: 12px; color: var(--text-faint); transition: transform 0.12s ease; flex-shrink: 0; }
  details.panel-group[open] summary .chevron { transform: rotate(180deg); }
  details.panel-group .details-body { padding-top: 0.15rem; }
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

  /* ---- lienzo 3D (stage) donde vive el canvas WebGL y sus overlays ---- */
  .stage { position: relative; background: var(--bg); }
  #gl-canvas, #room-canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
  .stage-hud { position: absolute; left: 0.85rem; bottom: 0.75rem; font-size: 0.68rem; color: var(--text-faint); font-family: var(--font-mono); }
  .icon-btn { position: absolute; top: 0.85rem; right: 0.85rem; padding: 0.32rem 0.58rem; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--surface); color: var(--text-dim); font-size: 0.7rem; cursor: pointer; font-family: inherit; }

  /* ---- esqueleto de carga: silueta gris animada en vez de una pantalla
     vacía, solo donde hay una espera sincrónica real que cubrir (ver
     buildRoom() en el <script>) — no se usa de adorno en todas partes. ---- */
  .stage-skeleton { position: absolute; inset: 0; z-index: 4; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.7rem; background: var(--bg); }
  .stage-skeleton.hidden { display: none; }
  .stage-skeleton .skel-shape { background: linear-gradient(100deg, var(--surface-raised) 30%, var(--border) 50%, var(--surface-raised) 70%); background-size: 300% 100%; animation: skel-shimmer 1.3s ease-in-out infinite; }
  .stage-skeleton .skel-blob { width: 38%; max-width: 220px; height: 34%; max-height: 150px; border-radius: 20% 20% 24% 24% / 30% 30% 20% 20%; }
  .stage-skeleton .skel-text { margin: 0; font-size: 0.78rem; color: var(--text-dim); }
  @keyframes skel-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -100% 0; } }
  @media (prefers-reduced-motion: reduce) { .stage-skeleton .skel-shape { animation: none; } }

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
  /* ---- pestaña Anatomía: texto descriptivo + diagramas SVG por órgano ---- */
  .anatomy-panel { padding: 1.4rem 1.8rem; overflow-y: auto; max-width: 62rem; }
  .anatomy-panel h2 { font-family: var(--font-serif); font-weight: 600; font-size: 1.5rem; margin: 0 0 0.3rem; text-transform: capitalize; }
  .anatomy-panel .algo-line { font-size: 0.78rem; color: var(--text-dim); margin: 0 0 1.1rem; }
  .anatomy-panel p { font-size: 0.88rem; line-height: 1.65; color: var(--text); }
  /* Los <h3> del HTML de anatomía (ORGAN_META["anatomy"] en Python) ya no se
     muestran directamente: wrapAnatomySections() en el <script> los
     convierte en <details>/<summary> justo después de insertar el HTML, así
     el usuario ve solo los títulos de sección de entrada (jerarquía real,
     ley de Hick) y abre cada una si le interesa, en vez de un bloque de
     texto largo de golpe. El contenido en sí no cambia ni se recorta. */
  .anatomy-panel .anatomy-detail details.anatomy-section { border-bottom: 1px solid var(--border); }
  .anatomy-panel .anatomy-detail details.anatomy-section:last-child { border-bottom: none; }
  .anatomy-panel .anatomy-detail summary { list-style: none; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; padding: 0.85rem 0; font-family: var(--font-serif); font-weight: 600; font-size: 1.05rem; color: var(--accent-strong); }
  .anatomy-panel .anatomy-detail summary::-webkit-details-marker { display: none; }
  .anatomy-panel .anatomy-detail summary .chevron { width: 14px; height: 14px; flex-shrink: 0; color: var(--text-faint); transition: transform 0.12s ease; }
  .anatomy-panel .anatomy-detail details[open] summary .chevron { transform: rotate(180deg); }
  .anatomy-panel .anatomy-detail .details-body { padding: 0 0 1rem; }
  .anatomy-panel .anatomy-detail .details-body p { margin: 0 0 0.6rem; }
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
    pointer-events: auto; cursor: pointer; font-family: inherit;
  }
  .landmark-label:hover { background: var(--accent-soft); }
  .landmark-label::after {
    content: ""; position: absolute; left: 50%; bottom: -5px; width: 6px; height: 6px;
    background: var(--accent); border-radius: 50%; transform: translateX(-50%);
  }
  .landmark-popover {
    position: absolute; max-width: 17rem; padding: 0.7rem 0.85rem;
    border-radius: var(--radius-md); background: var(--surface-raised);
    border: 1px solid var(--accent-strong); box-shadow: 0 8px 24px rgba(0,0,0,0.28);
    pointer-events: auto; z-index: 5;
  }
  .landmark-popover h4 { margin: 0 0 0.35rem; padding-right: 1.2rem; font-size: 0.8rem; font-weight: 650; color: var(--text); }
  .landmark-popover p { margin: 0; font-size: 0.76rem; line-height: 1.5; color: var(--text-dim); }
  .landmark-popover .close-btn {
    position: absolute; top: 0.4rem; right: 0.4rem; background: none; border: none;
    color: var(--text-faint); cursor: pointer; padding: 0.2rem;
    display: flex; align-items: center; justify-content: center;
  }
  .landmark-popover .close-btn:hover { color: var(--text); }

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
  .welcome-card input[type="text"]:focus { border-color: var(--accent-strong); }
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
<!-- Pantalla de bienvenida a pantalla completa: pide el nombre y luego
     muestra un saludo antes de dejar ver la interfaz principal (ver
     los listeners de #welcome-name-btn / #welcome-enter-btn en el <script>). -->
<div id="welcome-overlay">
  <div class="welcome-card">
    <svg class="mark" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="13" r="8.4" stroke="currentColor" stroke-width="1.3"/><circle cx="12" cy="13" r="5" stroke="currentColor" stroke-width="1.3" opacity="0.6"/><circle cx="12" cy="13" r="1.6" fill="currentColor"/><path d="M4.2 6 L19.8 6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
    <div class="welcome-step" id="welcome-step-name" data-active="true">
      <h2>Bienvenido al reconstructor de órganos en 3D</h2>
      <p class="sub" id="welcome-name-prompt">Reconstrucciones reales de pulmones, corazón, hígado, riñones y cerebro a partir de tomografías reales. ¿Cómo te llamas?</p>
      <label for="welcome-name-input" class="visually-hidden">Tu nombre</label>
      <input type="text" id="welcome-name-input" placeholder="Tu nombre" autocomplete="off" maxlength="40" aria-describedby="welcome-name-prompt"/>
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
<!-- Barra superior: logo, nombre del estudio y badges de estado (izquierda),
     selector de pestañas (centro/derecha) y botón de tema (extremo derecho).
     Cada botón .tab-btn corresponde a un <main id="panel-..."> de más abajo;
     activateTab() alterna cuál se muestra. -->
<header>
  <svg class="mark" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="13" r="8.4" stroke="currentColor" stroke-width="1.3"/><circle cx="12" cy="13" r="5" stroke="currentColor" stroke-width="1.3" opacity="0.6"/><circle cx="12" cy="13" r="1.6" fill="currentColor"/><path d="M4.2 6 L19.8 6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
  <h1>Medical3DReconstruction</h1>
  <div class="topbar-divider"></div>
  <div class="topbar-study">
    <span class="study-name" id="topbar-study-name"></span>
    <span class="badge" id="topbar-study-type"></span>
    <span class="badge" id="topbar-status"><span class="badge-dot ok" aria-hidden="true"></span><span id="topbar-status-text" aria-live="polite">Listo</span></span>
  </div>
  <span class="spacer"></span>
  <!-- role="tablist"/"tab"/"tabpanel" es el patrón ARIA correcto para pestañas:
       aria-selected solo es válido en elementos con estos roles (en un
       <button> plano, como estaba antes, los lectores de pantalla lo ignoran).
       aria-label en cada botón asegura que siga siendo anunciado aunque el
       CSS oculte el texto visible ".tab-label" en pantallas angostas. -->
  <div class="tab-switch" role="tablist" aria-label="Secciones del visor">
    <button class="tab-btn" id="tab-btn-3d" role="tab" aria-selected="true" aria-controls="panel-3d" aria-label="Reconstrucción 3D"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 2 4 6.5v11L12 22l8-4.5v-11L12 2Z"/><path d="M4 6.5 12 11l8-4.5"/><path d="M12 11v11"/></svg><span class="tab-label">Reconstrucción 3D</span></button>
    <button class="tab-btn" id="tab-btn-slices" role="tab" aria-selected="false" aria-controls="panel-slices" aria-label="Cortes CT"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="1.5"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg><span class="tab-label">Cortes CT</span></button>
    <button class="tab-btn" id="tab-btn-lab" role="tab" aria-selected="false" aria-controls="panel-lab" aria-label="Laboratorio"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 2v6.5L4.5 17a2 2 0 0 0 1.8 3h11.4a2 2 0 0 0 1.8-3L15 8.5V2"/><path d="M9 2h6"/><path d="M7.5 14h9"/></svg><span class="tab-label">Laboratorio</span></button>
    <button class="tab-btn" id="tab-btn-anatomy" role="tab" aria-selected="false" aria-controls="panel-anatomy" aria-label="Anatomía"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 19.5V5.5A2.5 2.5 0 0 1 6.5 3H20v15.5"/><path d="M6.5 21A2.5 2.5 0 0 1 4 18.5H20V21H6.5Z"/></svg><span class="tab-label">Anatomía</span></button>
    <button class="tab-btn" id="tab-btn-room" role="tab" aria-selected="false" aria-controls="panel-room" aria-label="Sala de órganos"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg><span class="tab-label">Sala de órganos</span></button>
    <button class="tab-btn" id="tab-btn-trivia" role="tab" aria-selected="false" aria-controls="panel-trivia" aria-label="Trivia"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.2 9.3a2.8 2.8 0 1 1 3.9 2.6c-.9.4-1.6 1-1.6 2.1"/><path d="M12 17.5h.01"/></svg><span class="tab-label">Trivia</span></button>
  </div>
  <span class="spacer"></span>
  <button class="icon-btn-flat" id="theme-btn">Tema</button>
</header>

<!-- ==================== Pestaña "Reconstrucción 3D" ====================
     La vista principal: barra lateral con todos los controles (selector de
     órgano, modo de visualización, opacidad/clipping, medición, panel de
     métricas/validación, exportar) + el canvas WebGL con la malla 3D. -->
<main id="panel-3d" role="tabpanel" aria-labelledby="tab-btn-3d">
  <aside>
    <div class="panel-group">
      <p class="eyebrow">Estructuras</p>
      <div class="organ-list" id="organ-list" role="group" aria-label="Selecciona un órgano"></div>
      <label class="toggle-row" style="margin-top:0.6rem"><input type="checkbox" id="heartbeat-toggle"> <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style="vertical-align:-2px" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M4 9v6h4l5 5V4L8 9H4z" fill="currentColor"/><path d="M17 8a5 5 0 0 1 0 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M19.5 5.5a9 9 0 0 1 0 13" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.55"/></svg> Sonido del latido (solo corazón)</label>
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
          <div class="label-row"><label for="mpr-axial-slider"><span class="mpr-dot" style="background:#5c8fbd" aria-hidden="true"></span>Axial (Z)</label><span id="mpr-axial-value"></span></div>
          <input type="range" id="mpr-axial-slider" min="0" max="100" value="50">
        </div>
        <div class="lab-field">
          <div class="label-row"><label for="mpr-coronal-slider"><span class="mpr-dot" style="background:#789e61" aria-hidden="true"></span>Coronal (Y)</label><span id="mpr-coronal-value"></span></div>
          <input type="range" id="mpr-coronal-slider" min="0" max="100" value="50">
        </div>
        <div class="lab-field">
          <div class="label-row"><label for="mpr-sagittal-slider"><span class="mpr-dot" style="background:#c76b5c" aria-hidden="true"></span>Sagital (X)</label><span id="mpr-sagittal-value"></span></div>
          <input type="range" id="mpr-sagittal-slider" min="0" max="100" value="50">
        </div>
        <label class="toggle-row" style="margin-top:0.3rem"><input type="checkbox" id="mpr-gradient-toggle"> Campo de orientación (aproximado)</label>
        <p class="diagram-caveat" style="margin:0.3rem 0 0;text-align:left">No es tractografía DTI real — este proyecto no tiene datos de difusión. Son líneas cortas siguiendo el gradiente de intensidad real de este escaneo (dirección de mayor cambio de densidad), coloreadas por eje solo como referencia visual.</p>
      </div>
      <div id="fly-section" class="hidden" style="margin-top:0.7rem">
        <p class="note">Una cámara en primera persona recorre el interior real del órgano, siguiendo el eje central de la máscara segmentada — no una animación decorativa, es la geometría de este espécimen.</p>
        <div class="toggle-row" style="gap:0.5rem">
          <button class="preset-btn" id="fly-play-btn" aria-pressed="true">Pausar</button>
          <span id="fly-progress-note" class="lab-tick-note" aria-live="polite"></span>
        </div>
        <div class="lab-field" style="margin-top:0.5rem">
          <div class="label-row"><label for="fly-speed-slider">Velocidad</label></div>
          <input type="range" id="fly-speed-slider" min="20" max="200" value="70">
        </div>
      </div>
    </div>
    <div class="panel-group">
      <p class="eyebrow">Reconstrucción</p>
      <div id="opacity-row">
        <div class="label-row"><label for="opacity-slider" style="font-size:0.76rem;color:var(--text-dim)">Opacidad</label><span id="opacity-value" style="font-size:0.72rem;color:var(--text-dim)">100%</span></div>
        <input type="range" id="opacity-slider" min="5" max="100" value="100">
      </div>
      <div id="clip-section" style="margin-top:0.7rem">
        <label class="toggle-row"><input type="checkbox" id="clip-enabled"> Clipping (corte virtual)</label>
        <div class="clip-controls" id="clip-controls" data-enabled="false">
          <div class="label-row" style="margin-top:0.3rem"><span id="clip-axis-label">Plano</span></div>
          <div class="segmented-row" id="clip-axis-row" role="group" aria-labelledby="clip-axis-label">
            <button data-axis="0" aria-pressed="true">X</button>
            <button data-axis="1" aria-pressed="false">Y</button>
            <button data-axis="2" aria-pressed="false">Z</button>
          </div>
          <div class="label-row" style="margin-top:0.3rem"><label for="clip-slider">Posición</label></div>
          <input type="range" id="clip-slider" min="0" max="100" value="50">
        </div>
      </div>
    </div>
    <details class="panel-group" id="measure-group">
      <summary><span class="eyebrow">Medición</span><svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></summary>
      <div class="details-body">
        <label class="toggle-row"><input type="checkbox" id="measure-enabled"> Activar herramienta de medición</label>
        <p class="note" style="margin-top:0.4rem">Con la herramienta activa, haz clic en dos puntos de la superficie del modelo. La distancia se calcula en milímetros reales, sobre las mismas coordenadas de la malla exportada.</p>
        <div class="inspector-row" id="measure-readout-row" style="display:none">
          <span class="k">Distancia</span><span class="v" id="measure-readout-value" aria-live="polite"></span>
        </div>
        <button class="preset-btn" id="measure-clear-btn" style="margin-top:0.4rem;display:none">Borrar medición</button>
      </div>
    </details>
    <div class="panel-group">
      <p class="eyebrow">Anatomy Inspector</p>
      <p class="inspector-subhead">Malla</p>
      <div id="metrics-panel"></div>
      <p class="inspector-subhead">Validación</p>
      <div id="validation-panel"></div>
      <button class="details-toggle" id="details-toggle-btn" aria-expanded="false" aria-controls="technical-details-panel">Technical details<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></button>
      <div id="technical-details-panel" class="hidden">
        <div id="technical-details-rows"></div>
      </div>
      <p class="inspector-subhead">Fuente de datos</p>
      <p class="note" id="source-note"></p>
      <p class="note" id="caveat-note" style="margin-top:0.5rem"></p>
    </div>
    <details class="panel-group">
      <summary><span class="eyebrow">Exportar</span><svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></summary>
      <div class="details-body">
        <p class="note">Descarga la malla tal como está cargada ahora mismo en el visor (misma geometría que ves, ya decimada para la web).</p>
        <div class="segmented-row" style="margin-top:0.5rem">
          <button class="export-btn" id="export-stl-btn">STL</button>
          <button class="export-btn" id="export-obj-btn">OBJ</button>
        </div>
        <button class="preset-btn" id="capture-view-btn" style="margin-top:0.5rem;width:100%">Capturar vista (PNG)</button>
        <p class="lab-tick-note" id="export-status" style="margin-top:0.4rem" aria-live="polite"></p>
      </div>
    </details>
  </aside>
  <!-- El canvas WebGL real, más las capas HTML superpuestas: etiquetas de
       landmarks anatómicos, puntos de medición, el popover de un landmark
       al hacer clic, la brújula de ejes y la barra de vistas de cámara. -->
  <div class="stage">
    <canvas id="gl-canvas" aria-label="Vista 3D interactiva del órgano seleccionado" role="img"></canvas>
    <div class="label-layer" id="label-layer"></div>
    <div class="label-layer" id="measure-layer"></div>
    <div id="landmark-popover" class="landmark-popover hidden">
      <button class="close-btn" id="landmark-popover-close" title="Cerrar" aria-label="Cerrar"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
      <h4 id="landmark-popover-title"></h4>
      <p id="landmark-popover-text"></p>
    </div>
    <div class="axis-gizmo-wrap"><canvas id="axis-gizmo-canvas" width="64" height="64" aria-hidden="true"></canvas></div>
    <div class="viewport-toolbar" id="viewport-toolbar">
      <button data-view="front" title="Vista frontal (Anterior)">Ant</button>
      <button data-view="back" title="Vista posterior">Post</button>
      <button data-view="left" title="Vista izquierda">Izq</button>
      <button data-view="right" title="Vista derecha">Der</button>
      <button data-view="top" title="Vista superior">Sup</button>
      <button data-view="bottom" title="Vista inferior">Inf</button>
      <button data-view="iso" title="Vista isométrica">Iso</button>
      <span class="vt-divider"></span>
      <button id="fit-btn" title="Encuadrar modelo (Fit)" aria-label="Encuadrar modelo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
      </button>
      <button id="labels-toggle-btn" aria-pressed="true" title="Mostrar/ocultar etiquetas anatómicas" aria-label="Mostrar/ocultar etiquetas anatómicas">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 3H4a1 1 0 0 0-1 1v7a1 1 0 0 0 .3.7l9 9a1 1 0 0 0 1.4 0l7-7a1 1 0 0 0 0-1.4l-9-9A1 1 0 0 0 11 3Z"/><circle cx="7.5" cy="7.5" r="1"/></svg>
      </button>
    </div>
    <div class="stage-hud">arrastra para rotar &middot; desplaza para hacer zoom</div>
  </div>
</main>

<!-- ==================== Pestaña "Cortes CT" ====================
     Muestra un corte 2D real del volumen (axial/coronal/sagital según el
     órgano), con presets de ventana HU y sliders de nivel/ancho manuales. -->
<main id="panel-slices" class="hidden" role="tabpanel" aria-labelledby="tab-btn-slices">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-slices" role="group" aria-label="Selecciona un órgano"></div>
    </div>
    <div>
      <p class="eyebrow" id="slice-slider-label">Corte</p>
      <div class="slider-row">
        <input type="range" id="slice-slider" min="0" max="0" value="0" aria-labelledby="slice-slider-label">
        <span id="slice-readout" style="font-family:var(--font-mono);font-size:0.74rem;min-width:7rem;text-align:right"></span>
      </div>
    </div>
    <div>
      <p class="eyebrow">Preajuste de ventana</p>
      <div class="preset-row" id="preset-row"></div>
    </div>
    <div>
      <p class="eyebrow" id="level-width-label">Nivel / ancho de ventana</p>
      <div class="slider-row"><input type="range" id="level-slider" min="0" max="255" value="128" aria-label="Nivel de ventana"><span id="level-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
      <div class="slider-row"><input type="range" id="width-slider" min="1" max="510" value="255" aria-label="Ancho de ventana"><span id="width-value" style="min-width:3rem;text-align:right;font-size:0.72rem"></span></div>
    </div>
    <p class="note" id="slice-source-note"></p>
  </aside>
  <div class="slice-stage">
    <canvas id="slice-canvas" role="img" aria-label="Corte 2D del volumen tomográfico en el índice y ventana actuales"></canvas>
    <div class="hu-readout" id="hu-readout" aria-live="polite">&mdash;</div>
  </div>
</main>

<!-- ==================== Pestaña "Anatomía" ====================
     Texto educativo (de ORGAN_META["anatomy"]/["fun_facts"]) más un
     diagrama SVG esquemático por órgano y la ficha de fuente/advertencia. -->
<main id="panel-anatomy" class="hidden" style="grid-template-columns: 300px 1fr;" role="tabpanel" aria-labelledby="tab-btn-anatomy">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-anatomy" role="group" aria-label="Selecciona un órgano"></div>
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

<!-- ==================== Pestaña "Laboratorio" ====================
     Reproduce en 2D, sobre el corte real, los pasos que el pipeline de
     segmentación aplicó de verdad en 3D: umbral, morfología (erosión/
     dilatación), componente más grande y relleno de huecos. Dos modos:
     "Línea de tiempo" (pasos fijos) y "Modo libre" (el usuario ajusta
     el umbral y los toggles con su propia mano). -->
<main id="panel-lab" class="hidden" role="tabpanel" aria-labelledby="tab-btn-lab">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-lab" role="group" aria-label="Selecciona un órgano"></div>
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
        <canvas id="lab-canvas" role="img" aria-labelledby="lab-stage-title"></canvas>
        <div class="lab-stage-caption">
          <h4 id="lab-stage-title"></h4>
          <p id="lab-stage-text"></p>
        </div>
      </div>
      <div class="lab-stepper">
        <button id="lab-prev">&larr; Anterior</button>
        <div class="lab-dots" id="lab-dots" role="group" aria-label="Progreso de la línea de tiempo"></div>
        <button id="lab-next">Siguiente &rarr;</button>
      </div>
    </div>
    <div id="lab-free-view" class="hidden">
      <div class="lab-canvas-row">
        <canvas id="lab-free-canvas" role="img" aria-label="Resultado del pipeline de segmentación con tus propios ajustes"></canvas>
        <div class="lab-stage-caption">
          <h4>Arma tu propio pipeline</h4>
          <p>Ajusta el umbral y activa o desactiva los pasos de limpieza — el mismo corte real, tus propias decisiones.</p>
          <p class="lab-match" id="lab-free-match" aria-live="polite"></p>
        </div>
      </div>
      <div class="lab-field">
        <div class="label-row"><label for="lab-threshold-slider">Umbral</label><span id="lab-threshold-value"></span></div>
        <input type="range" id="lab-threshold-slider" min="0" max="255" value="128">
        <span class="lab-tick-note" id="lab-threshold-real"></span>
      </div>
      <div class="lab-histogram-wrap">
        <p class="eyebrow" style="margin-bottom:0.3rem" id="lab-histogram-label">Histograma real de densidades (todo el volumen)</p>
        <canvas id="lab-histogram-canvas" width="460" height="100" role="img" aria-labelledby="lab-histogram-label" aria-describedby="lab-histogram-note"></canvas>
        <p class="lab-tick-note" id="lab-histogram-note"></p>
      </div>
      <label class="toggle-row"><input type="checkbox" id="lab-opening-toggle" checked> Apertura morfológica (quita ruido de la segmentación)</label>
      <label class="toggle-row"><input type="checkbox" id="lab-cleanup-toggle" checked> Quedarse con la forma más grande y rellenar huecos</label>
    </div>
  </div>
</main>

<!-- ==================== Pestaña "Sala de órganos" ====================
     Los 5 órganos reconstruidos juntos, cada uno en sus coordenadas físicas
     reales (mm) tal como las produjo su propio pipeline, sin reescalar —
     así el tamaño relativo entre ellos también es información real. -->
<main id="panel-room" class="hidden" style="grid-template-columns: 300px 1fr;" role="tabpanel" aria-labelledby="tab-btn-room">
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
    <canvas id="room-canvas" role="img" aria-label="Vista 3D de los cinco órganos reconstruidos juntos, a escala real"></canvas>
    <div class="label-layer" id="room-label-layer"></div>
    <button class="icon-btn" id="room-reset-btn">Restablecer vista</button>
    <div class="stage-hud">arrastra para rotar &middot; desplaza para hacer zoom</div>
    <!-- Esqueleto: la única operación de este visor con una espera sincrónica
         real y perceptible es decodificar + subir a GPU los 5 órganos la
         primera vez que se abre esta pestaña (buildRoom en el <script>).
         Se muestra aquí, no en cada pestaña, porque en el resto de la
         interfaz no hay ningún retraso real que ocultar. -->
    <div class="stage-skeleton hidden" id="room-skeleton" role="status" aria-live="polite">
      <div class="skel-shape skel-blob"></div>
      <p class="skel-text">Cargando los cinco órganos…</p>
    </div>
  </div>
</main>

<!-- ==================== Pestaña "Trivia" ====================
     Cuestionario de opción múltiple (ORGAN_META["quiz"]) con 15 preguntas
     por órgano, cada una con retroalimentación inmediata y explicación. -->
<main id="panel-trivia" class="hidden" style="grid-template-columns: 300px 1fr;" role="tabpanel" aria-labelledby="tab-btn-trivia">
  <aside>
    <div>
      <p class="eyebrow">Órgano</p>
      <div class="organ-list" id="organ-list-trivia" role="group" aria-label="Selecciona un órgano"></div>
    </div>
    <p class="note">
      Preguntas de opción múltiple con los mismos datos reales de la
      pestaña "Anatomía" — para poner a prueba lo que aprendiste.
    </p>
  </aside>
  <div class="trivia-panel">
    <p class="eyebrow" id="trivia-progress" aria-live="polite"></p>
    <div id="trivia-question-card">
      <h3 id="trivia-question-text"></h3>
      <div id="trivia-options" class="trivia-options"></div>
      <p id="trivia-explain" class="trivia-explain hidden" aria-live="polite"></p>
      <button id="trivia-next-btn" class="welcome-btn trivia-action-btn hidden">Siguiente &rarr;</button>
    </div>
    <div id="trivia-result" class="hidden" aria-live="polite">
      <h3 id="trivia-result-title"></h3>
      <p id="trivia-result-text"></p>
      <button id="trivia-restart-btn" class="welcome-btn trivia-action-btn">Reintentar</button>
    </div>
  </div>
</main>

<script>
  // Estas tres constantes son el puente entre Python y JavaScript: build()
  // sustituye estos tres marcadores de texto por JSON real antes de
  // escribir el archivo, así que en el HTML final esto ya no dice
  // "__ORGAN_ORDER_JSON__" sino un array/objeto JavaScript literal.
  const ORGAN_ORDER = __ORGAN_ORDER_JSON__;   // ["lungs", "heart", "liver", "kidneys", "brain"]
  const ORGAN_META = __ORGAN_META_JSON__;     // metadata de texto por órgano (ORGAN_META de Python)
  const VIEWER_DATA = __VIEWER_DATA_JSON__;   // malla 3D + cortes + métricas reales por órgano

  // Decodifica un string base64 (como llegan la malla y los cortes) a un
  // ArrayBuffer binario crudo, para poder leerlo como Float32Array/Uint32Array.
  function decodeB64(b64) {
    const bin = atob(b64);                          // atob: base64 -> string binario (1 char = 1 byte)
    const bytes = new Uint8Array(bin.length);        // reserva un array de bytes del mismo largo que el string binario
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);  // copia byte a byte (charCodeAt da el valor 0-255 de cada char)
    return bytes.buffer;                             // .buffer expone el ArrayBuffer crudo detrás del Uint8Array
  }
  // Convierte un color hexadecimal ("#rrggbb") a un array [r,g,b] con
  // componentes en el rango 0..1, el formato que espera WebGL.
  function hexToRgb01(hex) {
    const v = parseInt(hex.replace("#", ""), 16);            // quita el "#" y lo interpreta como entero en base 16
    return [((v >> 16) & 255) / 255,                          // byte alto (rojo): desplaza 16 bits y se queda con los 8 bits bajos
            ((v >> 8) & 255) / 255,                           // byte medio (verde): desplaza 8 bits y aísla 8 bits
            (v & 255) / 255];                                 // byte bajo (azul): los 8 bits menos significativos, sin desplazar
  }
  // Formatea un número con exactamente `d` decimales, usando el separador
  // de miles/decimales del navegador (p. ej. para mostrar volúmenes o mm).
  function fmt(n, d) { return Number(n).toLocaleString(undefined, {maximumFractionDigits: d, minimumFractionDigits: d}); }

  // ---------- tabs ----------
  // Referencias a los 6 botones de pestaña y sus paneles <main> asociados.
  const tabBtn3d = document.getElementById("tab-btn-3d");            // botón "Reconstrucción 3D"
  const tabBtnSlices = document.getElementById("tab-btn-slices");    // botón "Cortes CT"
  const tabBtnLab = document.getElementById("tab-btn-lab");          // botón "Laboratorio"
  const tabBtnAnatomy = document.getElementById("tab-btn-anatomy");  // botón "Anatomía"
  const panel3d = document.getElementById("panel-3d");               // <main> de la pestaña 3D
  const panelSlices = document.getElementById("panel-slices");       // <main> de la pestaña de cortes
  const panelLab = document.getElementById("panel-lab");             // <main> del laboratorio
  const panelAnatomy = document.getElementById("panel-anatomy");     // <main> de anatomía

  const tabBtnRoom = document.getElementById("tab-btn-room");        // botón "Sala de órganos"
  const panelRoom = document.getElementById("panel-room");           // <main> de la sala de órganos
  const tabBtnTrivia = document.getElementById("tab-btn-trivia");    // botón "Trivia"
  const panelTrivia = document.getElementById("panel-trivia");       // <main> de la trivia

  // Muestra el panel `which` y oculta los otros cinco, marcando también
  // aria-selected en el botón correspondiente (para estilo y accesibilidad).
  // Algunas pestañas necesitan "despertar" su contenido justo al mostrarse
  // (redibujar un canvas que estaba oculto, o inicializar datos la primera vez).
  function activateTab(which) {
    tabBtn3d.setAttribute("aria-selected", String(which === "3d"));            // true solo si `which` es "3d"
    tabBtnSlices.setAttribute("aria-selected", String(which === "slices"));    // true solo si `which` es "slices"
    tabBtnLab.setAttribute("aria-selected", String(which === "lab"));          // true solo si `which` es "lab"
    tabBtnAnatomy.setAttribute("aria-selected", String(which === "anatomy"));  // true solo si `which` es "anatomy"
    tabBtnRoom.setAttribute("aria-selected", String(which === "room"));       // true solo si `which` es "room"
    tabBtnTrivia.setAttribute("aria-selected", String(which === "trivia"));   // true solo si `which` es "trivia"
    panel3d.classList.toggle("hidden", which !== "3d");            // oculta este panel si NO es el activo
    panelSlices.classList.toggle("hidden", which !== "slices");    // ídem para cortes
    panelLab.classList.toggle("hidden", which !== "lab");          // ídem para laboratorio
    panelAnatomy.classList.toggle("hidden", which !== "anatomy");  // ídem para anatomía
    panelRoom.classList.toggle("hidden", which !== "room");        // ídem para la sala de órganos
    panelTrivia.classList.toggle("hidden", which !== "trivia");    // ídem para trivia
    // Un canvas oculto con display:none no puede medirse ni dibujarse bien,
    // así que estas pestañas recalculan tamaño/contenido justo al activarse.
    if (which === "slices") { resizeSliceCanvasDisplay(); drawSlice(); }  // reajusta tamaño y repinta el corte
    if (which === "lab") { labRender(); }        // repinta la etapa/modo actual del laboratorio
    if (which === "room") { enterRoomTab(); }    // construye la sala de órganos (si no existía ya), mostrando el esqueleto mientras dura
    if (which === "trivia") { initTriviaTabIfNeeded(); }  // arranca el cuestionario la primera vez
  }
  // Cada botón de pestaña simplemente llama a activateTab con su propio nombre.
  tabBtn3d.addEventListener("click", () => activateTab("3d"));           // clic en "Reconstrucción 3D"
  tabBtnSlices.addEventListener("click", () => activateTab("slices"));   // clic en "Cortes CT"
  tabBtnLab.addEventListener("click", () => activateTab("lab"));         // clic en "Laboratorio"
  tabBtnAnatomy.addEventListener("click", () => activateTab("anatomy")); // clic en "Anatomía"
  tabBtnRoom.addEventListener("click", () => activateTab("room"));       // clic en "Sala de órganos"
  tabBtnTrivia.addEventListener("click", () => activateTab("trivia"));   // clic en "Trivia"

  // ---------- theme ----------
  // Alterna entre tema oscuro y claro. Si el usuario nunca lo tocó, el
  // tema sigue la preferencia del sistema operativo (ver el <style> arriba);
  // en cuanto hace clic aquí, se fija un data-theme explícito que gana
  // siempre sobre esa preferencia.
  document.getElementById("theme-btn").addEventListener("click", () => {
    const root = document.documentElement;  // el elemento <html>, donde vive el atributo data-theme
    // Si ya hay un tema fijado a mano se usa ese; si no, se consulta la preferencia del sistema operativo.
    const current = root.getAttribute("data-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    root.setAttribute("data-theme", current === "dark" ? "light" : "dark");  // invierte el tema actual
  });

  // ---------- welcome screen ----------
  // Función auto-ejecutada (IIFE) que controla la pantalla de bienvenida:
  // pide el nombre, guarda un saludo personalizado, y recuerda el nombre
  // en localStorage para la próxima visita del mismo navegador.
  (function initWelcome() {
    const overlay = document.getElementById("welcome-overlay");        // el overlay de pantalla completa
    const stepName = document.getElementById("welcome-step-name");     // paso 1: pedir nombre
    const stepGreet = document.getElementById("welcome-step-greet");   // paso 2: saludo
    const nameInput = document.getElementById("welcome-name-input");   // <input> de texto del nombre
    const nameBtn = document.getElementById("welcome-name-btn");       // botón "Entrar"
    const greetNameEl = document.getElementById("welcome-greet-name"); // <span> donde se imprime el nombre
    const specialEl = document.getElementById("welcome-special");      // caja del mensaje especial
    const enterBtn = document.getElementById("welcome-enter-btn");     // botón "Comenzar"

    // Pasa del paso "pedir nombre" al paso "saludo", usando el nombre
    // escrito (o "amigo/a" si vino vacío). Incluye un mensaje especial
    // fijo para un nombre concreto, y persiste el nombre para la próxima vez.
    function showGreeting(rawName) {
      const name = rawName.trim();                       // quita espacios sobrantes al inicio/final
      greetNameEl.textContent = name || "amigo/a";        // si quedó vacío, usa un nombre genérico
      if (name.toLowerCase() === "hillary") {             // comparación sin distinguir mayúsculas/minúsculas
        specialEl.textContent = "Sé que serás una gran doctora algún día. Estoy orgulloso de ti, Laly <3";
        specialEl.style.display = "block";                // muestra la caja de mensaje especial
      } else {
        specialEl.style.display = "none";                 // para cualquier otro nombre, la caja permanece oculta
      }
      stepName.setAttribute("data-active", "false");   // el CSS oculta el paso que no tiene data-active="true"
      stepGreet.setAttribute("data-active", "true");   // muestra el paso de saludo
      try { localStorage.setItem("medical3d_visitor_name", name); } catch (e) {}  // guarda el nombre; ignora el error si localStorage está bloqueado
    }

    // Confirmar el nombre por clic o con Enter; "Comenzar" cierra el overlay.
    nameBtn.addEventListener("click", () => showGreeting(nameInput.value));  // botón "Entrar"
    nameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") showGreeting(nameInput.value); });  // tecla Enter en el input
    enterBtn.addEventListener("click", () => overlay.classList.add("hidden"));  // botón "Comenzar": oculta el overlay (CSS: opacity 0 + pointer-events none)

    // Si ya había un nombre guardado de una visita anterior, se precarga
    // en el campo de texto (dentro de try/catch por si localStorage está
    // bloqueado, p. ej. en navegación privada).
    let savedName = "";  // valor por defecto si no hay nada guardado o localStorage falla
    try { savedName = localStorage.getItem("medical3d_visitor_name") || ""; } catch (e) {}  // lee el nombre guardado, si existe
    if (savedName) nameInput.value = savedName;  // precarga el input solo si había algo guardado
    nameInput.focus();                           // pone el cursor listo para escribir de inmediato
  })();  // se ejecuta inmediatamente al cargar la página (IIFE)

  /* =========================================================
     3D reconstruction viewer
     ========================================================= */
  // Ex-vivo specimens were scanned/mounted in whatever orientation was
  // physically convenient, not a standardized "patient up" pose (see
  // load_volume()'s own docstring: slice-image archives carry no direction/
  // origin metadata at all). Most organs don't have an obvious visual "up",
  // so this goes unnoticed — but some do, and this is purely a DISPLAY
  // correction based on this specimen's own real shape (or, for lungs, its
  // real verified metadata), not a fabricated pose. All named fixes below
  // are proper 90°/180° rotations (det=+1, not a mirror), so winding/
  // normals stay valid.
  //   flipY    — brain: this specimen renders smooth vault down / irregular
  //              base up; 180° about the mesh's own vertical (Z) axis fixes
  //              it. Also reused for liver: without any fix, its bulkier
  //              diaphragmatic surface (see the mass-asymmetry analysis in
  //              computeLiverLandmarks) renders at the bottom instead of
  //              the top — the same 180° correction fixes that too.
  //   rotXdown — heart: apex (the tapered extremity, farthest mesh point
  //              from centroid — see computeHeartLandmarks below) sits at
  //              +Z in the raw mesh, base at -Z (verified: the apex→base
  //              vector is >99.8% aligned with the Z axis for this
  //              specimen). A 90° rotation about X sends apex to -Y so it
  //              renders pointing down, base up — the conventional heart-
  //              illustration pose, exactly the same "purely for display"
  //              idea as flipY.
  //   rotZup   — lungs: real DICOM metadata (see CAMERA_VIEWS below) puts
  //              verified Superior along raw +Z, but the renderer's camera
  //              always treats +Y as "up" — so without a fix, the trachea
  //              renders sideways instead of pointing up. A 90° rotation
  //              about X sends raw +Z (Superior) to +Y (render-up) and raw
  //              -Y (Anterior) to +Z, so the real verified anatomical axes
  //              line up with the viewer's natural vertical, in any view —
  //              not just via the camera-preset buttons.
  const ORGAN_DISPLAY_FIX = { brain: "flipY", liver: "flipY", heart: "rotXdown", lungs: "rotZup" };
  // Decodifica la malla base64 de un órgano a arrays tipados de WebGL y,
  // si ese órgano necesita una rotación "de exhibición" (ver el comentario
  // largo de arriba), aplica esa misma rotación a CADA vértice y CADA
  // normal — así la malla en memoria ya queda orientada, y el resto del
  // código (cámara, MPR, landmarks) no necesita saber que hubo una rotación.
  function decodeMesh(meshData, organKey) {
    const positions = new Float32Array(decodeB64(meshData.positions_b64));  // decodifica y reinterpreta los bytes como floats de 32 bits (x,y,z por vértice)
    const normals = new Float32Array(decodeB64(meshData.normals_b64));      // igual, pero para las normales (nx,ny,nz por vértice)
    const fix = ORGAN_DISPLAY_FIX[organKey];  // "flipY" | "rotXdown" | "rotZup" | undefined (según el órgano)
    if (fix === "flipY") {
      // Giro de 180° alrededor del eje Z, centrado en el centroide de la
      // malla: refleja X e Y respecto al centro (2*centro - coordenada),
      // sin tocar Z. Las normales solo invierten dirección en X/Y también.
      const cx = meshData.center[0], cy = meshData.center[1];  // coordenadas X,Y del centro real de la malla
      for (let i = 0; i < positions.length; i += 3) {  // recorre cada vértice (3 floats: x,y,z)
        positions[i] = 2 * cx - positions[i];         // refleja la coordenada X respecto al centro
        positions[i + 1] = 2 * cy - positions[i + 1]; // refleja la coordenada Y respecto al centro
        normals[i] = -normals[i];                     // invierte la componente X de la normal
        normals[i + 1] = -normals[i + 1];             // invierte la componente Y de la normal
      }
    } else if (fix === "rotXdown") {
      // Giro de 90° alrededor del eje X: intercambia Y y Z (con un signo)
      // para que el ápice del corazón, que en la malla original apunta en
      // +Z, termine apuntando hacia -Y (abajo) en el espacio ya rotado.
      const [cx, cy, cz] = meshData.center;      // desestructura las 3 coordenadas del centro real
      for (let i = 0; i < positions.length; i += 3) {  // recorre cada vértice
        const y = positions[i + 1], z = positions[i + 2];  // guarda Y,Z originales antes de sobreescribirlas
        positions[i + 1] = cy - (z - cz);   // la nueva Y depende de la distancia de Z al centro (invertida)
        positions[i + 2] = cz + (y - cy);   // la nueva Z depende de la distancia de Y al centro
        const ny = normals[i + 1], nz = normals[i + 2];  // guarda componentes originales de la normal
        normals[i + 1] = -nz;   // misma rotación aplicada a la normal (sin desplazamiento, solo direcciones)
        normals[i + 2] = ny;
      }
    } else if (fix === "rotZup") {
      // Giro de 90° alrededor del eje X en el sentido opuesto al anterior:
      // manda el eje Superior real (+Z en los datos DICOM) hacia +Y, que es
      // "arriba" para la cámara del visor, en vez de dejarlo en el plano
      // horizontal (que es lo que hacía que la tráquea se viera de lado).
      const [cx, cy, cz] = meshData.center;      // centro real de la malla
      for (let i = 0; i < positions.length; i += 3) {  // recorre cada vértice
        const y = positions[i + 1], z = positions[i + 2];  // guarda Y,Z originales
        positions[i + 1] = cy + (z - cz);   // la nueva Y crece con la distancia de Z al centro
        positions[i + 2] = cz - (y - cy);   // la nueva Z depende de la distancia de Y al centro (invertida)
        const ny = normals[i + 1], nz = normals[i + 2];  // guarda componentes originales de la normal
        normals[i + 1] = nz;    // misma rotación aplicada a la normal
        normals[i + 2] = -ny;
      }
    }
    return {
      positions,                                              // posiciones ya rotadas (o iguales, si no había fix)
      normals,                                                 // normales ya rotadas
      indices: new Uint32Array(decodeB64(meshData.indices_b64)),  // qué 3 vértices forman cada triángulo
      numVertices: meshData.num_vertices,                      // total de vértices, para mostrar en el inspector
      numTriangles: meshData.num_triangles,                    // total de triángulos, ídem
      center: meshData.center,  // centro original (sin rotar) — se sigue usando para encuadrar la cámara.
    };
  }

  // El único canvas WebGL de la pestaña 3D principal. preserveDrawingBuffer
  // permite leer los píxeles ya dibujados con canvas.toBlob() para el botón
  // "Capturar vista (PNG)" — sin esa opción el buffer se borraría antes de
  // poder leerlo.
  const canvas = document.getElementById("gl-canvas");  // el <canvas> de la pestaña 3D principal
  const gl = canvas.getContext("webgl", {
    antialias: true,               // suaviza los bordes dentados de los triángulos
    alpha: false,                  // el canvas no necesita transparencia hacia la página (fondo siempre opaco)
    preserveDrawingBuffer: true,   // permite leer los píxeles ya dibujados (necesario para "Capturar vista")
  });

  // Fragmento de código GLSL compartido por varios fragment shaders: define
  // el plano de clipping (corte virtual) y una función que decide si un
  // fragmento debe descartarse por estar del lado "cortado" del plano.
  // Se inserta con ${...} dentro de los otros shaders para no repetirlo.
  const CLIP_UNIFORMS_FS = `
    uniform vec3 uClipNormal; uniform float uClipValue; uniform float uClipEnabled;  // normal del plano, su posición, y si el corte está activo
    bool clipDiscard(vec3 worldPos) {
      // Si el clipping está activo (>0.5, o sea "true") Y el punto queda del
      // lado positivo del plano (producto punto mayor que uClipValue),
      // se descarta ese fragmento — así se ve el "corte virtual".
      return uClipEnabled > 0.5 && dot(worldPos, uClipNormal) > uClipValue;
    }`;
  // Vertex shader principal (malla sólida/rayos-X). Recibe la posición y
  // normal de cada vértice; les suma un desplazamiento uOffset (usado en
  // la "Sala de órganos" para separar los 5 órganos) y un empuje a lo largo
  // de la normal (uPulse) que infla ligeramente la malla al ritmo del
  // latido cuando el órgano activo es el corazón (ver heartPulseAmount).
  const VS = `attribute vec3 aPosition; attribute vec3 aNormal;
    // aPosition/aNormal llegan de los buffers de la malla, un valor por vértice.
    uniform mat4 uModelView; uniform mat4 uProjection; uniform mat3 uNormalMatrix;
    uniform vec3 uOffset; uniform float uPulse;
    // Las variables "varying" se calculan por vértice aquí y WebGL las
    // interpola automáticamente para cada píxel dentro del triángulo,
    // así el fragment shader las recibe ya suavizadas.
    varying vec3 vNormal; varying vec3 vViewPos; varying vec3 vWorldPos;
    void main() {
      vec3 worldPos = aPosition + uOffset + aNormal * uPulse;  // posición real: vértice + desplazamiento + pulso del latido
      vec4 vp = uModelView * vec4(worldPos, 1.0);              // pasa la posición al espacio de la cámara
      vViewPos = vp.xyz;                              // posición en espacio de cámara, para el fragment shader
      vWorldPos = worldPos;                            // posición en espacio del mundo, para el clipping
      vNormal = normalize(uNormalMatrix * aNormal);   // normal transformada al espacio de cámara
      gl_Position = uProjection * vp;                 // posición final en clip space
    }`;
  // Fragment shader principal: ilumina cada píxel de la malla con dos
  // luces direccionales fijas (key + fill), un brillo especular tipo
  // Blinn-Phong, y el término de Fresnel que resalta el contorno visto
  // "de canto" — la única adición puramente cosmética de esta ronda, y
  // está basada en un efecto óptico real (ver el comentario sobre Fresnel).
  const FS = `precision highp float; varying vec3 vNormal; varying vec3 vViewPos; varying vec3 vWorldPos;
    uniform vec3 uColor; uniform float uAlpha;
    ${CLIP_UNIFORMS_FS}
    void main() {
      if (clipDiscard(vWorldPos)) discard;  // descarta el fragmento si cae del lado cortado (no dibuja nada ahí)
      vec3 N = normalize(vNormal); if (!gl_FrontFacing) N = -N;  // ilumina igual ambas caras (útil en modo rayos-X)
      vec3 V = normalize(-vViewPos);                              // vector hacia la cámara
      vec3 keyDir = normalize(vec3(0.55, 0.65, 0.85));            // dirección de la luz principal
      vec3 fillDir = normalize(vec3(-0.6, -0.2, 0.5));            // luz de relleno, más tenue, desde el lado opuesto
      float key = max(dot(N, keyDir), 0.0);   // cuánta luz principal recibe este píxel (0 si mira para otro lado)
      float fill = max(dot(N, fillDir), 0.0); // cuánta luz de relleno recibe
      vec3 halfV = normalize(keyDir + V);     // vector "a medio camino" entre luz y cámara, para el especular
      float spec = pow(max(dot(N, halfV), 0.0), 28.0) * 0.22;     // brillo especular (Blinn-Phong)
      // Fresnel rim: real grazing-angle brightening (Schlick-style), not a
      // fabricated glow — a physically motivated cue that reads the
      // silhouette more clearly, the same reason real optical materials
      // look brighter at their edges.
      float fresnel = pow(1.0 - max(dot(N, V), 0.0), 2.5) * 0.35;  // más fuerte cuanto más "de canto" se ve la superficie
      vec3 color = uColor * (0.32 + key * 0.72 + fill * 0.22) + vec3(spec) + uColor * fresnel;  // combina color base + ambas luces + brillo + fresnel
      gl_FragColor = vec4(color, uAlpha);  // color final del píxel, con la opacidad global
    }`;
  // Par de shaders más simple, sin iluminación, usado para dibujar la malla
  // en modo "Alambre" (wireframe): solo posiciona los segmentos de línea y
  // los pinta de un color plano con transparencia.
  const VS_WIRE = `attribute vec3 aPosition;
    uniform mat4 uModelView; uniform mat4 uProjection;
    varying vec3 vWorldPos;
    void main() {
      vWorldPos = aPosition;                                       // posición en espacio del mundo, para el clipping
      gl_Position = uProjection * uModelView * vec4(aPosition, 1.0);  // transforma directo a clip space, sin iluminación
    }`;
  const FS_WIRE = `precision highp float; varying vec3 vWorldPos;
    uniform vec3 uColor; uniform float uAlpha;
    ${CLIP_UNIFORMS_FS}
    void main() {
      if (clipDiscard(vWorldPos)) discard;  // respeta el mismo plano de corte que el shader principal
      gl_FragColor = vec4(uColor, uAlpha);  // color plano, sin ningún cálculo de luz
    }`;
  // Compila un shader (vertex o fragment) a partir de su código fuente GLSL
  // y lanza un error legible si el compilador de la GPU lo rechaza.
  function compile(type, src) {
    const s = gl.createShader(type);   // reserva un objeto shader vacío del tipo pedido
    gl.shaderSource(s, src);           // le asigna el código fuente GLSL
    gl.compileShader(s);               // pide a la GPU que lo compile
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));  // si falló, revienta con el log real del compilador
    return s;
  }
  // Compila un par vertex+fragment y los enlaza en un "programa" de WebGL
  // listo para usarse con gl.useProgram().
  function linkProgram(vsSrc, fsSrc) {
    const p = gl.createProgram();                              // crea el objeto "programa" vacío
    gl.attachShader(p, compile(gl.VERTEX_SHADER, vsSrc));       // compila y adjunta el vertex shader
    gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fsSrc));     // compila y adjunta el fragment shader
    gl.linkProgram(p);                                          // enlaza ambos en un programa ejecutable
    return p;
  }
  // Programa "sólido/rayos-X" (el que usa VS/FS de arriba) y las ubicaciones
  // de sus atributos/uniforms, obtenidas una sola vez y reutilizadas en
  // cada frame para no volver a consultarlas todo el tiempo.
  const program = linkProgram(VS, FS);
  gl.useProgram(program);  // activa este programa como el que se usará en las próximas llamadas de dibujo
  const aPosition = gl.getAttribLocation(program, "aPosition");        // índice del atributo aPosition en este programa
  const aNormal = gl.getAttribLocation(program, "aNormal");            // índice del atributo aNormal
  const uModelView = gl.getUniformLocation(program, "uModelView");     // ubicación del uniform de la matriz de vista
  const uProjection = gl.getUniformLocation(program, "uProjection");   // ubicación del uniform de la matriz de proyección
  const uNormalMatrix = gl.getUniformLocation(program, "uNormalMatrix"); // ubicación de la matriz normal 3x3
  const uColor = gl.getUniformLocation(program, "uColor");             // color base del material
  const uAlpha = gl.getUniformLocation(program, "uAlpha");             // opacidad global
  const uClipNormal = gl.getUniformLocation(program, "uClipNormal");   // normal del plano de corte
  const uClipValue = gl.getUniformLocation(program, "uClipValue");     // posición del plano de corte
  const uClipEnabled = gl.getUniformLocation(program, "uClipEnabled"); // si el clipping está activo
  const uOffset = gl.getUniformLocation(program, "uOffset");           // desplazamiento (usado en la Sala de órganos)
  const uPulse = gl.getUniformLocation(program, "uPulse");             // magnitud del pulso del latido

  // Programa "alambre" (VS_WIRE/FS_WIRE), con su propio juego de ubicaciones.
  const wireProgram = linkProgram(VS_WIRE, FS_WIRE);
  const aPositionW = gl.getAttribLocation(wireProgram, "aPosition");         // atributo de posición en el programa alambre
  const uModelViewW = gl.getUniformLocation(wireProgram, "uModelView");     // matriz de vista
  const uProjectionW = gl.getUniformLocation(wireProgram, "uProjection");   // matriz de proyección
  const uColorW = gl.getUniformLocation(wireProgram, "uColor");             // color de las líneas
  const uAlphaW = gl.getUniformLocation(wireProgram, "uAlpha");             // opacidad de las líneas
  const uClipNormalW = gl.getUniformLocation(wireProgram, "uClipNormal");   // normal del plano de corte (copia propia)
  const uClipValueW = gl.getUniformLocation(wireProgram, "uClipValue");     // posición del plano de corte (copia propia)
  const uClipEnabledW = gl.getUniformLocation(wireProgram, "uClipEnabled"); // si el clipping está activo (copia propia)

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
  const aPositionP = gl.getAttribLocation(planeProgram, "aPosition");     // esquinas del plano MPR
  const aTexCoordP = gl.getAttribLocation(planeProgram, "aTexCoord");     // coordenadas UV para muestrear la textura
  const uModelViewP = gl.getUniformLocation(planeProgram, "uModelView");  // matriz de vista
  const uProjectionP = gl.getUniformLocation(planeProgram, "uProjection"); // matriz de proyección
  const uTextureP = gl.getUniformLocation(planeProgram, "uTexture");      // unidad de textura a muestrear

  // ---------- colored line shader (gradient-orientation field) ----------
  const VS_LINEC = `attribute vec3 aPosition; attribute vec3 aColor;
    uniform mat4 uModelView; uniform mat4 uProjection;
    varying vec3 vColor;
    void main() {
      vColor = aColor;    // pasa el color del vértice tal cual al fragment shader
      gl_Position = uProjection * uModelView * vec4(aPosition, 1.0);  // transforma a clip space
    }`;
  const FS_LINEC = `precision highp float; varying vec3 vColor; uniform float uAlpha;
    void main() { gl_FragColor = vec4(vColor, uAlpha); }`;  // pinta el color interpolado con la opacidad dada
  const lineColorProgram = linkProgram(VS_LINEC, FS_LINEC);
  const aPositionLC = gl.getAttribLocation(lineColorProgram, "aPosition");    // posición de cada punto de línea
  const aColorLC = gl.getAttribLocation(lineColorProgram, "aColor");          // color por vértice
  const uModelViewLC = gl.getUniformLocation(lineColorProgram, "uModelView"); // matriz de vista
  const uProjectionLC = gl.getUniformLocation(lineColorProgram, "uProjection"); // matriz de proyección
  const uAlphaLC = gl.getUniformLocation(lineColorProgram, "uAlpha");         // opacidad de las líneas

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
      vec4 vp0 = uModelView * vec4(aPosition, 1.0);   // extremo A del segmento, en espacio de cámara
      vec4 vp1 = uModelView * vec4(aOther, 1.0);       // extremo B del segmento, en espacio de cámara
      vec3 dir = vp1.xyz - vp0.xyz;                    // vector que va de A a B
      float dl = length(dir);                          // largo de ese vector
      vec3 dirN = dl > 0.0001 ? dir / dl : vec3(1.0, 0.0, 0.0);  // dirección normalizada (evita dividir entre casi cero)
      vec3 perp = normalize(cross(dirN, vec3(0.0, 0.0, 1.0)));   // perpendicular al segmento Y a la cámara (billboard)
      vec3 offsetPos = vp0.xyz + perp * aSide * uWidth;  // desplaza a un lado u otro según aSide (-1/+1) y el ancho
      vColor = aColor;                                  // pasa el color al fragment shader
      gl_Position = uProjection * vec4(offsetPos, 1.0);  // proyecta el punto ya desplazado
    }`;
  const FS_RIBBON = `precision highp float; varying vec3 vColor; uniform float uAlpha;
    void main() { gl_FragColor = vec4(vColor, uAlpha); }`;  // color plano con la opacidad de la franja
  const ribbonProgram = linkProgram(VS_RIBBON, FS_RIBBON);
  const aPositionR = gl.getAttribLocation(ribbonProgram, "aPosition");     // extremo A de cada segmento
  const aOtherR = gl.getAttribLocation(ribbonProgram, "aOther");           // extremo B (el opuesto) de cada segmento
  const aSideR = gl.getAttribLocation(ribbonProgram, "aSide");             // -1 o +1: a qué lado se infla la franja
  const aColorR = gl.getAttribLocation(ribbonProgram, "aColor");           // color por vértice
  const uModelViewR = gl.getUniformLocation(ribbonProgram, "uModelView");  // matriz de vista
  const uProjectionR = gl.getUniformLocation(ribbonProgram, "uProjection"); // matriz de proyección
  const uWidthR = gl.getUniformLocation(ribbonProgram, "uWidth");          // ancho de la franja en mm
  const uAlphaR = gl.getUniformLocation(ribbonProgram, "uAlpha");          // opacidad de la franja

  // Buffers de GPU reutilizados para la malla actual: posiciones, normales,
  // índices de triángulos, e índices de aristas (para el modo "Alambre").
  // Se vuelven a llenar con uploadMesh() cada vez que cambia el órgano activo.
  const posBuf = gl.createBuffer(), normBuf = gl.createBuffer(), idxBuf = gl.createBuffer(), edgeBuf = gl.createBuffer();
  let edgeCount = 0;  // cuántos índices de arista hay actualmente cargados (para drawElements en modo alambre)
  gl.enable(gl.DEPTH_TEST);   // los triángulos más cercanos a la cámara tapan a los más lejanos
  gl.enable(gl.CULL_FACE);    // no dibuja las caras que miran "para adentro" de la malla
  gl.cullFace(gl.BACK);       // específicamente, descarta las caras traseras (back-facing)
  // WebGL1 solo soporta índices de 16 bits por defecto; esta extensión
  // habilita índices de 32 bits (Uint32Array), necesarios porque algunas
  // mallas tienen más de 65535 vértices.
  gl.getExtension("OES_element_index_uint");

  // ---------- view mode + clipping plane state ----------
  let viewMode = "solid"; // "solid" | "xray" | "wire"
  let clipEnabled = false, clipAxis = 0, clipFraction = 0.5;
  let measureEnabled = false, measurePoints = [];
  let meshBoundsMin = [0,0,0], meshBoundsMax = [0,0,0];

  // A partir de los índices de triángulos, calcula la lista única de
  // aristas (pares de vértices) para dibujar el modo "Alambre" como
  // GL_LINES en vez de triángulos rellenos. Usa un Set con una clave
  // "menor_mayor" para no repetir una arista compartida por dos triángulos.
  function buildEdgeIndices(indices) {
    const seen = new Set();           // claves "menor_mayor" de aristas ya agregadas, para no duplicar
    const edges = [];                 // lista plana de pares [v0,v1, v0,v1, ...]
    function addEdge(a, b) {
      const lo = Math.min(a, b), hi = Math.max(a, b);  // normaliza el orden para que (a,b) y (b,a) den la misma clave
      const key = lo + "_" + hi;
      if (seen.has(key)) return;      // ya se agregó esta arista desde el triángulo vecino, no repetir
      seen.add(key);
      edges.push(lo, hi);
    }
    for (let i = 0; i < indices.length; i += 3) {  // recorre cada triángulo (3 índices)
      addEdge(indices[i], indices[i+1]);    // arista entre el vértice 0 y 1 del triángulo
      addEdge(indices[i+1], indices[i+2]);  // arista entre el vértice 1 y 2
      addEdge(indices[i+2], indices[i]);    // arista entre el vértice 2 y 0 (cierra el triángulo)
    }
    return new Uint32Array(edges);
  }

  // Calcula, para el eje de clipping activo (X/Y/Z), el vector normal del
  // plano de corte y su posición real en mm: interpola linealmente entre
  // el mínimo y el máximo de la malla en ese eje según clipFraction (0..1,
  // controlado por el slider "Posición").
  function clipUniformValues() {
    const normal = clipAxis === 0 ? [1,0,0] : clipAxis === 1 ? [0,1,0] : [0,0,1];  // vector unitario del eje elegido
    const lo = meshBoundsMin[clipAxis], hi = meshBoundsMax[clipAxis];  // límites reales de la malla en ese eje
    return {normal, value: lo + (hi - lo) * clipFraction};  // interpola la posición del plano entre lo y hi
  }

  let alphaValue = 1.0;
  const opacitySlider = document.getElementById("opacity-slider");
  const opacityValueEl = document.getElementById("opacity-value");
  // Actualiza la opacidad global de la malla (0-100%) y refleja el valor
  // tanto en el propio slider como en la etiqueta numérica junto a él.
  function setOpacity(pct) {
    alphaValue = pct / 100;
    opacitySlider.value = String(pct);
    opacityValueEl.textContent = pct + "%";
  }
  opacitySlider.addEventListener("input", () => setOpacity(Number(opacitySlider.value)));

  const opacityRowEl = document.getElementById("opacity-row");   // fila del slider de opacidad
  const clipSectionEl = document.getElementById("clip-section"); // sección completa de clipping
  const mprSectionEl = document.getElementById("mpr-section");   // controles exclusivos del modo MPR
  const flySectionEl = document.getElementById("fly-section");   // controles exclusivos del modo vuelo
  const viewModeRow = document.getElementById("view-mode-row");  // fila de botones Sólido/Rayos-X/Alambre/MPR/Vuelo
  // Botones "Sólido / Rayos-X / Alambre / Cortes MPR / Vuelo interior":
  // cambia viewMode y muestra/oculta los paneles de opciones que solo
  // aplican a un modo concreto (clipping no tiene sentido en MPR, etc.).
  viewModeRow.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-mode]");  // sube desde el elemento clicado hasta el <button> con data-mode
    if (!btn) return;                                     // el clic no fue sobre un botón de modo (p. ej. el borde de la fila)
    hideLandmarkPopover();                                 // cierra cualquier popover de landmark abierto
    viewMode = btn.dataset.mode;                           // "solid" | "xray" | "wire" | "mpr" | "fly"
    for (const b of viewModeRow.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === btn));  // marca solo el botón elegido como activo
    // Rayos-X es, en esencia, "sólido" pero translúcido: ajusta la opacidad
    // automáticamente al entrar/salir de ese modo.
    if (viewMode === "xray") setOpacity(35);
    else if (viewMode === "solid") setOpacity(100);
    const isMpr = viewMode === "mpr";
    const isFly = viewMode === "fly";
    mprSectionEl.classList.toggle("hidden", !isMpr);   // muestra los sliders MPR solo en ese modo
    flySectionEl.classList.toggle("hidden", !isFly);   // muestra los controles de vuelo solo en ese modo
    opacityRowEl.classList.toggle("hidden", isMpr || isFly);  // la opacidad no aplica a MPR ni vuelo
    clipSectionEl.classList.toggle("hidden", isMpr || isFly); // el clipping tampoco aplica ahí
    labelLayerEl.classList.toggle("hidden", isMpr || isFly || !labelsVisible);  // oculta landmarks en esos modos (o si el usuario ya los ocultó)
    // En MPR/vuelo no tiene sentido dejar puntos de medición sobre la malla
    // sólida (no se está mostrando), así que se limpian al entrar a esos modos.
    if (isMpr || isFly) { measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = ""; }
    if (isMpr) {
      rebuildMprPlanes();                                          // recalcula los 3 planos con la posición actual de los sliders
      if (showGradientField) computeGradientField();               // si el overlay de gradiente estaba activo, lo recalcula también
      targetRadius = boundingRadius * 2.1; // a bit closer: more of the scene now, worth framing tighter
    }
    if (isFly) {
      if (!flyPath) computeFlyPath();  // calcula la ruta de vuelo una sola vez y la reutiliza
      flyPlaying = true;                              // arranca el vuelo automáticamente al entrar al modo
      flyPlayBtn.textContent = "Pausar";               // el botón ahora ofrece pausar, ya que está reproduciendo
      flyPlayBtn.setAttribute("aria-pressed", "true"); // refleja visualmente que está "presionado" (reproduciendo)
    }
  });

  // ---------- controles de clipping (corte virtual) ----------
  const clipEnabledEl = document.getElementById("clip-enabled");   // casilla que activa/desactiva el clipping
  const clipControlsEl = document.getElementById("clip-controls"); // contenedor de los controles de eje/posición
  const clipAxisRow = document.getElementById("clip-axis-row");    // fila de botones X/Y/Z
  const clipSliderEl = document.getElementById("clip-slider");     // slider de posición del plano
  // Casilla que activa/desactiva el clipping (y atenúa visualmente sus
  // controles cuando está apagado, vía el atributo data-enabled + CSS).
  clipEnabledEl.addEventListener("change", () => {
    clipEnabled = clipEnabledEl.checked;                        // guarda el nuevo estado (true/false)
    clipControlsEl.dataset.enabled = String(clipEnabled);       // el CSS atenúa/reactiva los controles según este atributo
  });
  // Elige sobre qué eje (X/Y/Z) se aplica el plano de corte.
  clipAxisRow.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-axis]");  // botón X, Y o Z que se clicó
    if (!btn) return;                                     // clic fuera de un botón válido
    clipAxis = Number(btn.dataset.axis);                  // 0=X, 1=Y, 2=Z
    for (const b of clipAxisRow.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b === btn));  // resalta solo el eje elegido
  });
  // Posición del plano de corte a lo largo de ese eje, como fracción 0..1
  // del rango real de la malla (ver clipUniformValues).
  clipSliderEl.addEventListener("input", () => {
    clipFraction = Number(clipSliderEl.value) / 100;  // el slider va de 0 a 100; se normaliza a 0..1
  });

  // =========================================================
  // Cortes MPR: the same real slice volume shown as 3 rotatable
  // orthogonal planes (axial/coronal/sagittal), like a clinical
  // multiplanar-reconstruction viewer. Optional gradient-orientation
  // overlay: NOT diffusion tractography (this project has no DTI data)
  // — short line segments following the real intensity gradient of
  // the scan, colored by axis only as a visual reference.
  // =========================================================
  // Aplica exactamente la misma rotación "de exhibición" que decodeMesh()
  // usó sobre los vértices de la malla, pero a un punto suelto (x, y, z).
  // Se necesita porque los cortes MPR, el campo de gradiente y el vuelo
  // interior trabajan con coordenadas del volumen de voxeles original (sin
  // rotar), y hay que llevarlas al mismo espacio "ya rotado" en el que vive
  // la malla en pantalla para que todo se vea alineado.
  function applyDisplayFixPoint(key, x, y, z) {
    const fix = ORGAN_DISPLAY_FIX[key];              // qué rotación (si alguna) usa este órgano
    if (!currentMesh) return [x, y, z];               // sin malla cargada todavía, no hay centro con qué rotar
    if (fix === "flipY") {
      const cx = currentMesh.center[0], cy = currentMesh.center[1];  // centro real en X,Y
      return [2 * cx - x, 2 * cy - y, z];              // mismo reflejo 180° que decodeMesh(), aplicado a este punto suelto
    }
    if (fix === "rotXdown") {
      const [cx, cy, cz] = currentMesh.center;
      return [x, cy - (z - cz), cz + (y - cy)];        // misma fórmula de rotación que decodeMesh() para "rotXdown"
    }
    if (fix === "rotZup") {
      const [cx, cy, cz] = currentMesh.center;
      return [x, cy + (z - cz), cz - (y - cy)];        // misma fórmula de rotación que decodeMesh() para "rotZup"
    }
    return [x, y, z];  // este órgano no tiene rotación de exhibición: el punto se devuelve sin cambios
  }

  let mprAxialFrac = 0.5, mprCoronalFrac = 0.5, mprSagittalFrac = 0.5;  // posición (0..1) de cada uno de los 3 sliders MPR
  let showGradientField = false;  // si el overlay de campo de gradiente está activo
  // Una textura 2D por plano (axial/coronal/sagital); se repintan cada vez
  // que cambia el slider correspondiente o se cambia de órgano.
  const mprTexAxial = gl.createTexture(), mprTexCoronal = gl.createTexture(), mprTexSagittal = gl.createTexture();
  for (const tex of [mprTexAxial, mprTexCoronal, mprTexSagittal]) {
    gl.bindTexture(gl.TEXTURE_2D, tex);                                    // activa esta textura para configurarla
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);     // suaviza al reducir la textura
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);     // suaviza al ampliarla
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);  // no repite la textura en el eje U
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);  // no repite la textura en el eje V
  }
  const mprPosBuf = gl.createBuffer(), mprUvBuf = gl.createBuffer();  // buffers compartidos: posiciones y UV de "el plano que toque" dibujar
  let mprPlaneGeo = { axial: null, coronal: null, sagittal: null };  // geometría + textura calculada de cada plano (llenado por rebuildMprPlanes)

  // Aplica "ventaneo" (windowing) tipo radiológico a un valor crudo de
  // intensidad: todo lo que cae por debajo de (nivel - ancho/2) se ve
  // negro, por encima de (nivel + ancho/2) se ve blanco, y en medio se
  // interpola linealmente a 0-255 — el mismo control que "Nivel/Ancho de
  // ventana" en la pestaña Cortes CT.
  function windowedTexel(raw) {
    const lo = windowLevel - windowWidth / 2, scale = 255 / windowWidth;  // límite inferior de la ventana, y el factor de escala
    let val = (raw - lo) * scale;                 // reescala el valor crudo al rango 0..255 según la ventana
    return val < 0 ? 0 : val > 255 ? 255 : val;   // recorta (clamp) para que no se salga de 0..255
  }
  // Extrae el corte axial (plano XY, perpendicular a Z) en zIndex del cubo
  // de voxeles `sv` y lo convierte en una textura RGBA en escala de grises
  // lista para subir a la GPU. Las tres funciones build*Texture leen el
  // mismo array plano `sv.voxels` (orden z,y,x) con una fórmula de índice
  // distinta según qué eje se mantiene fijo.
  function buildAxialTexture(zIndex) {
    const [nz, ny, nx] = sv.shape;              // dimensiones del cubo de voxeles (profundidad, alto, ancho)
    const off = zIndex * ny * nx;               // desplazamiento al inicio del corte zIndex dentro del array plano
    const data = new Uint8Array(nx * ny * 4);   // buffer RGBA de salida (4 bytes por píxel)
    for (let i = 0; i < nx * ny; i++) {         // recorre cada píxel del corte
      const val = windowedTexel(sv.voxels[off + i]);            // aplica el ventaneo nivel/ancho
      const o = i * 4; data[o] = val; data[o + 1] = val; data[o + 2] = val; data[o + 3] = 255;  // gris (R=G=B) totalmente opaco
    }
    return { data, w: nx, h: ny };
  }
  // Corte coronal (plano XZ, perpendicular a Y) en yIndex.
  function buildCoronalTexture(yIndex) {
    const [nz, ny, nx] = sv.shape;
    const data = new Uint8Array(nx * nz * 4);      // este corte mide nx de ancho por nz de alto
    for (let z = 0; z < nz; z++) {                 // recorre cada fila (profundidad)
      for (let x = 0; x < nx; x++) {                // recorre cada columna (ancho)
        const val = windowedTexel(sv.voxels[z * ny * nx + yIndex * nx + x]);  // índice 3D con Y fija en yIndex
        const o = (z * nx + x) * 4; data[o] = val; data[o + 1] = val; data[o + 2] = val; data[o + 3] = 255;
      }
    }
    return { data, w: nx, h: nz };
  }
  // Corte sagital (plano YZ, perpendicular a X) en xIndex.
  function buildSagittalTexture(xIndex) {
    const [nz, ny, nx] = sv.shape;
    const data = new Uint8Array(ny * nz * 4);      // este corte mide ny de ancho por nz de alto
    for (let z = 0; z < nz; z++) {                 // recorre cada fila (profundidad)
      for (let y = 0; y < ny; y++) {                // recorre cada columna (alto del cubo)
        const val = windowedTexel(sv.voxels[z * ny * nx + y * nx + xIndex]);  // índice 3D con X fija en xIndex
        const o = (z * ny + y) * 4; data[o] = val; data[o + 1] = val; data[o + 2] = val; data[o + 3] = 255;
      }
    }
    return { data, w: ny, h: nz };
  }

  // Reconstruye los tres planos MPR (posiciones 3D + textura) según la
  // posición actual de los tres sliders (mprAxialFrac/CoronalFrac/
  // SagittalFrac, cada uno 0..1). Convierte cada índice de voxel a
  // milímetros reales usando el origen y espaciado (spacing) reales del
  // volumen, y aplica applyDisplayFixPoint para que los planos queden en
  // el mismo espacio "ya rotado" que la malla 3D.
  function rebuildMprPlanes() {
    if (!sv) return;                      // sin volumen de cortes cargado todavía, no hay nada que construir
    const [nz, ny, nx] = sv.shape;        // dimensiones del cubo en voxeles
    const [ox, oy, oz] = sv.origin;       // coordenada real (mm) del voxel (0,0,0)
    const [sx, sy, sz] = sv.spacing;      // tamaño real (mm) de un voxel en cada eje
    const x0 = ox, x1 = ox + sx * (nx - 1);  // extremos reales del volumen en X
    const y0 = oy, y1 = oy + sy * (ny - 1);  // extremos reales del volumen en Y
    const z0 = oz, z1 = oz + sz * (nz - 1);  // extremos reales del volumen en Z

    const zIndex = Math.max(0, Math.min(nz - 1, Math.round(mprAxialFrac * (nz - 1))));     // índice de voxel Z según el slider (acotado al rango válido)
    const yIndex = Math.max(0, Math.min(ny - 1, Math.round(mprCoronalFrac * (ny - 1))));   // ídem para Y
    const xIndex = Math.max(0, Math.min(nx - 1, Math.round(mprSagittalFrac * (nx - 1))));  // ídem para X
    const zMm = oz + zIndex * sz, yMm = oy + yIndex * sy, xMm = ox + xIndex * sx;  // esos mismos índices, convertidos a milímetros reales

    const key = currentOrganKey;
    const fix = (p) => applyDisplayFixPoint(key, p[0], p[1], p[2]);  // atajo: aplica la rotación de exhibición a un punto [x,y,z]

    mprPlaneGeo.axial = {
      // Las 4 esquinas del plano axial (a la altura zMm fija), ya rotadas
      // para coincidir con el espacio en el que vive la malla 3D.
      positions: new Float32Array([...fix([x0, y0, zMm]), ...fix([x1, y0, zMm]), ...fix([x0, y1, zMm]), ...fix([x1, y1, zMm])]),
      uv: new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]),  // coordenadas de textura de cada esquina (orden TL,TR,BL,BR)
      tex: buildAxialTexture(zIndex),                   // los píxeles reales de ese corte
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

    // Muestra al usuario, en milímetros reales, en qué posición quedó cada plano.
    document.getElementById("mpr-axial-value").textContent = zMm.toFixed(0) + " mm";
    document.getElementById("mpr-coronal-value").textContent = yMm.toFixed(0) + " mm";
    document.getElementById("mpr-sagittal-value").textContent = xMm.toFixed(0) + " mm";

    // Sube los 3 nuevos bitmaps a sus texturas de GPU correspondientes.
    for (const [tex, geo] of [[mprTexAxial, mprPlaneGeo.axial], [mprTexCoronal, mprPlaneGeo.coronal], [mprTexSagittal, mprPlaneGeo.sagittal]]) {
      gl.bindTexture(gl.TEXTURE_2D, tex);        // selecciona esta textura como destino
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, geo.tex.w, geo.tex.h, 0, gl.RGBA, gl.UNSIGNED_BYTE, geo.tex.data);  // sube los píxeles calculados
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

  // Dibuja los tres planos MPR como quads texturizados (dos triángulos en
  // TRIANGLE_STRIP), uno por uno, aplicando un polygonOffset distinto a
  // cada uno para evitar el "z-fighting" donde se cruzan (ver el comentario
  // largo de arriba). Al final dibuja también sus bordes de colores.
  function drawMprPlanes(view, proj) {
    if (!mprPlaneGeo.axial) return;             // todavía no se calculó ningún plano (sin volumen cargado)
    gl.useProgram(planeProgram);                 // activa el shader de plano texturizado
    gl.uniformMatrix4fv(uModelViewP, false, view);   // sube la matriz de vista actual
    gl.uniformMatrix4fv(uProjectionP, false, proj);  // sube la matriz de proyección actual
    gl.disable(gl.CULL_FACE);                    // los planos deben verse desde ambos lados
    gl.enable(gl.DEPTH_TEST); gl.depthMask(true); gl.disable(gl.BLEND);  // opacos, con test de profundidad normal
    gl.enable(gl.POLYGON_OFFSET_FILL);           // activa el desplazamiento de profundidad anti z-fighting
    gl.activeTexture(gl.TEXTURE0);               // selecciona la unidad de textura 0
    gl.uniform1i(uTextureP, 0);                  // le dice al shader que use la unidad de textura 0
    for (const [name, tex, offsetUnits] of MPR_PLANE_ORDER) {  // dibuja axial, luego coronal, luego sagital
      const geo = mprPlaneGeo[name];             // geometría + textura ya calculadas de este plano
      gl.polygonOffset(0, offsetUnits);          // desplazamiento distinto por plano (evita el parpadeo en los cruces)
      gl.bindTexture(gl.TEXTURE_2D, tex);        // activa la textura de este plano específico
      gl.bindBuffer(gl.ARRAY_BUFFER, mprPosBuf); // selecciona el buffer de posiciones compartido
      gl.bufferData(gl.ARRAY_BUFFER, geo.positions, gl.DYNAMIC_DRAW);  // sube las 4 esquinas de este plano
      gl.enableVertexAttribArray(aPositionP);
      gl.vertexAttribPointer(aPositionP, 3, gl.FLOAT, false, 0, 0);    // 3 floats por vértice (x,y,z)
      gl.bindBuffer(gl.ARRAY_BUFFER, mprUvBuf);  // selecciona el buffer de coordenadas de textura
      gl.bufferData(gl.ARRAY_BUFFER, geo.uv, gl.DYNAMIC_DRAW);         // sube las UV de este plano
      gl.enableVertexAttribArray(aTexCoordP);
      gl.vertexAttribPointer(aTexCoordP, 2, gl.FLOAT, false, 0, 0);    // 2 floats por vértice (u,v)
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);    // dibuja el quad (2 triángulos) con las 4 esquinas
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);          // ya no hace falta para lo que sigue
    gl.enable(gl.CULL_FACE);                     // restaura el culling normal para el resto del render
    drawMprPlaneBorders(view, proj);             // dibuja encima los contornos de colores
  }

  // Dibuja el contorno de cada plano MPR como una línea cerrada de color
  // (azul=axial, verde=coronal, rojo=sagital) para que se distingan entre
  // sí incluso cuando se cruzan o se ven de canto.
  function drawMprPlaneBorders(view, proj) {
    gl.useProgram(lineColorProgram);              // activa el shader de líneas de color
    gl.uniformMatrix4fv(uModelViewLC, false, view);
    gl.uniformMatrix4fv(uProjectionLC, false, proj);
    gl.uniform1f(uAlphaLC, 0.95);                 // casi opaco
    gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(0, -1);  // acerca ligeramente las líneas a la cámara para que no se las coman los planos
    for (const name of ["axial", "coronal", "sagittal"]) {
      const geo = mprPlaneGeo[name];
      const p = geo.positions;                    // las 4 esquinas ya calculadas [x,y,z]*4
      // TRIANGLE_STRIP order is TL,TR,BL,BR; walk the perimeter TL->TR->BR->BL.
      const loop = new Float32Array([              // reordena las 4 esquinas para formar un contorno cerrado
        p[0], p[1], p[2], p[3], p[4], p[5], p[9], p[10], p[11], p[6], p[7], p[8],
      ]);
      const c = MPR_PLANE_COLORS[name];            // color fijo de este plano (azul/verde/rojo)
      const colors = new Float32Array([c[0], c[1], c[2], c[0], c[1], c[2], c[0], c[1], c[2], c[0], c[1], c[2]]);  // el mismo color repetido para las 4 esquinas
      gl.bindBuffer(gl.ARRAY_BUFFER, mprBorderPosBuf);
      gl.bufferData(gl.ARRAY_BUFFER, loop, gl.DYNAMIC_DRAW);      // sube las posiciones del contorno
      gl.enableVertexAttribArray(aPositionLC);
      gl.vertexAttribPointer(aPositionLC, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, mprBorderColorBuf);
      gl.bufferData(gl.ARRAY_BUFFER, colors, gl.DYNAMIC_DRAW);    // sube los colores del contorno
      gl.enableVertexAttribArray(aColorLC);
      gl.vertexAttribPointer(aColorLC, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.LINE_LOOP, 0, 4);           // dibuja las 4 aristas cerrando el ciclo automáticamente
    }
    gl.disable(gl.POLYGON_OFFSET_FILL);
  }

  // Ghostly translucent mesh drawn around the MPR box for context — the
  // same layered look as the reference video (the organ's silhouette
  // visible around the slice planes and fiber-like lines inside it).
  function drawMprGhostMesh(view, proj) {
    if (!currentMesh) return;                     // sin malla cargada, nada que dibujar como "fantasma"
    gl.useProgram(program);                        // reutiliza el shader sólido principal
    gl.uniformMatrix4fv(uModelView, false, view);
    gl.uniformMatrix4fv(uProjection, false, proj);
    gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
    gl.uniform3fv(uColor, currentColor);           // color real del órgano activo
    gl.uniform3fv(uOffset, [0, 0, 0]);              // sin desplazamiento (no es la Sala de órganos)
    gl.uniform1f(uPulse, 0.0);                      // sin pulso de latido en esta vista fantasma
    gl.uniform3fv(uClipNormal, [1, 0, 0]);          // valores neutros de clipping (no se usa aquí)
    gl.uniform1f(uClipValue, 1e9);                  // un valor enorme para que el plano nunca corte nada
    gl.uniform1f(uClipEnabled, 0.0);                // clipping desactivado explícitamente
    gl.uniform1f(uAlpha, 0.15);                     // muy translúcido: solo sugiere la silueta
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);  // mezcla normal de transparencia
    gl.depthMask(false); gl.disable(gl.CULL_FACE); gl.enable(gl.DEPTH_TEST);  // no escribe profundidad, ve ambas caras
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);  // dibuja todos los triángulos de la malla
    gl.depthMask(true); gl.enable(gl.CULL_FACE); gl.disable(gl.BLEND);  // restaura el estado normal para lo que se dibuje después
  }

  // ---- gradient-orientation field (approximate, NOT tractography) ----
  let gradientLineData = null;
  const gradRibbonBuf = gl.createBuffer();
  const RIBBON_STRIDE = 10; // px,py,pz, ox,oy,oz, side, r,g,b
  let gradRibbonWidthMm = 0.5;
  // Añade un segmento p0->p1 al array plano `arr`, ya como 2 triángulos
  // (6 vértices) del shader "ribbon": cada vértice lleva su propio extremo,
  // el extremo OPUESTO del segmento (aOther) y un signo de lado (aSide);
  // el vertex shader usa esos 3 datos para inflar la línea en una franja
  // (billboard) que siempre mira a la cámara, con el color r,g,b dado.
  function pushRibbonSegment(arr, p0, p1, r, g, b) {
    // 6 vértices = 2 triángulos que forman el rectángulo (franja) de este
    // segmento: 3 en el lado -1 y 3 en el lado +1, compartiendo p0/p1.
    const verts = [[p0, -1], [p0, 1], [p1, -1], [p0, 1], [p1, 1], [p1, -1]];
    for (const [p, side] of verts) {
      const other = p === p0 ? p1 : p0;  // el extremo contrario a este vértice (lo necesita el shader para calcular la dirección)
      arr.push(p[0], p[1], p[2], other[0], other[1], other[2], side, r, g, b);  // 10 números por vértice (ver RIBBON_STRIDE)
    }
  }

  // Genera el "campo de orientación" aproximado: siembra puntos en una
  // rejilla dentro del volumen, y desde cada punto de tejido real (según
  // el mismo umbral que usa la segmentación 3D) traza un par de líneas
  // cortas siguiendo el gradiente de intensidad local, unos pasos hacia
  // cada lado. El color de cada línea codifica hacia qué eje apunta el
  // gradiente en ese punto (rojo=X, verde=Y, azul=Z), solo como referencia
  // visual — de nuevo, no es tractografía real.
  function computeGradientField() {
    if (!sv) { gradientLineData = null; return; }         // sin volumen cargado, no hay nada que trazar
    const meta = ORGAN_META[currentOrganKey];              // metadata del órgano activo (trae su umbral real)
    const [nz, ny, nx] = sv.shape;                         // dimensiones del cubo de voxeles
    const [ox, oy, oz] = sv.origin;                        // origen real (mm) del volumen
    const [sx, sy, sz] = sv.spacing;                       // tamaño real (mm) de un voxel por eje
    const frac = (meta.threshold_native - sv.valueMin) / (sv.valueMax - sv.valueMin);  // el umbral real, como fracción 0..1 del rango del volumen
    const quantThreshold = Math.max(0, Math.min(255, Math.round(frac * 255)));          // esa fracción, en la escala 0-255 del cubo submuestreado
    const below = meta.threshold_below;                    // true si "tejido" es lo que está POR DEBAJO del umbral (p. ej. aire en pulmones)
    const key = currentOrganKey;

    const strideX = Math.max(1, Math.round(nx / 28));  // separa las semillas ~28 veces a lo largo de X (rejilla, no cada voxel)
    const strideY = Math.max(1, Math.round(ny / 28));  // ídem en Y
    const strideZ = Math.max(1, Math.round(nz / 28));  // ídem en Z
    const stepMm = Math.max(sx, sy, sz) * 0.75;        // largo de cada paso del trazado, en milímetros reales
    const STEPS = 6; // per direction from the seed, so up to 12 short segments form one flowing streamline
    gradRibbonWidthMm = stepMm * 0.16; // thin relative to segment length, or it reads as confetti instead of a strand

    // ¿Este voxel cuenta como "tejido" según el mismo umbral que usa la segmentación 3D real?
    function isTissueAt(xi, yi, zi) {
      const v = sv.voxels[zi * ny * nx + yi * nx + xi];  // valor de intensidad de ese voxel
      return below ? v < quantThreshold : v > quantThreshold;
    }
    // Gradiente de intensidad en un voxel: diferencia central (voxel siguiente
    // menos voxel anterior) en cada eje por separado, más su magnitud total.
    function gradAt(xi, yi, zi) {
      const idx = zi * ny * nx + yi * nx + xi;               // índice plano de este voxel
      const drx = sv.voxels[idx + 1] - sv.voxels[idx - 1];        // cambio de intensidad a lo largo de X
      const dry = sv.voxels[idx + nx] - sv.voxels[idx - nx];      // cambio de intensidad a lo largo de Y
      const drz = sv.voxels[idx + ny * nx] - sv.voxels[idx - ny * nx];  // cambio de intensidad a lo largo de Z
      return [drx, dry, drz, Math.hypot(drx, dry, drz)];     // magnitud total del cambio (qué tan "filoso" es el borde ahí)
    }

    // Short traced streamlets, not single straight spikes: from each seed,
    // step a few times each way following the *local* gradient at every
    // step (recomputed per step, so the path curves with the real data)
    // instead of one straight segment along the seed's own gradient.
    const ribbon = [];  // acumula todos los vértices de todas las franjas, listo para subir a GPU
    for (let z = strideZ; z < nz - strideZ; z += strideZ) {      // recorre la rejilla de semillas en Z
      for (let y = strideY; y < ny - strideY; y += strideY) {    // en Y
        for (let x = strideX; x < nx - strideX; x += strideX) {  // en X
          if (!isTissueAt(x, y, z)) continue;                     // salta semillas fuera del tejido real
          const [drx0, dry0, drz0, rawMag0] = gradAt(x, y, z);    // gradiente en el punto semilla
          if (rawMag0 < 14) continue;                             // zona demasiado uniforme, sin borde claro que seguir
          const gx0 = drx0 / (2 * sx), gy0 = dry0 / (2 * sy), gz0 = drz0 / (2 * sz);  // convierte a gradiente por milímetro real
          const mag0 = Math.hypot(gx0, gy0, gz0) || 1;            // magnitud (o 1, para no dividir entre cero)
          const r = Math.abs(gx0 / mag0), g = Math.abs(gy0 / mag0), b = Math.abs(gz0 / mag0);  // color: qué tanto del gradiente es de cada eje

          for (const sign of [1, -1]) {  // traza hacia "adelante" (+1) y hacia "atrás" (-1) desde la misma semilla
            let fx = x, fy = y, fz = z;                            // posición actual del trazado, en índices de voxel (con decimales)
            let prev = [ox + fx * sx, oy + fy * sy, oz + fz * sz]; // esa misma posición, convertida a milímetros reales
            for (let step = 0; step < STEPS; step++) {             // hasta 6 pasos cortos por dirección
              const xi = Math.max(1, Math.min(nx - 2, Math.round(fx)));  // índice de voxel más cercano, acotado a un borde interior seguro
              const yi = Math.max(1, Math.min(ny - 2, Math.round(fy)));
              const zi = Math.max(1, Math.min(nz - 2, Math.round(fz)));
              if (!isTissueAt(xi, yi, zi)) break;                  // salió del tejido: termina esta rama del trazado
              const [drx, dry, drz, rawMag] = gradAt(xi, yi, zi);  // recalcula el gradiente LOCAL en cada paso (no el de la semilla)
              if (rawMag < 8) break;                               // el borde se desvaneció, ya no hay dirección clara que seguir
              const gx = drx / (2 * sx), gy = dry / (2 * sy), gz = drz / (2 * sz);
              const mag = Math.hypot(gx, gy, gz) || 1;
              const dx = sign * gx / mag, dy = sign * gy / mag, dz = sign * gz / mag;  // dirección unitaria del paso, con el signo de esta rama
              const next = [prev[0] + dx * stepMm, prev[1] + dy * stepMm, prev[2] + dz * stepMm];  // avanza un paso de stepMm milímetros
              const p0 = applyDisplayFixPoint(key, prev[0], prev[1], prev[2]);  // rota el punto anterior al espacio de exhibición
              const p1 = applyDisplayFixPoint(key, next[0], next[1], next[2]);  // rota el punto nuevo también
              pushRibbonSegment(ribbon, p0, p1, r, g, b);           // agrega este tramo del "hilo" a la lista de franjas
              prev = next;                                          // el nuevo punto pasa a ser el "anterior" del próximo paso
              fx += dx * stepMm / sx; fy += dy * stepMm / sy; fz += dz * stepMm / sz;  // avanza también la posición en índices de voxel
              if (fx < 1 || fy < 1 || fz < 1 || fx > nx - 2 || fy > ny - 2 || fz > nz - 2) break;  // se acercó demasiado al borde del volumen
            }
          }
        }
      }
    }
    const data = new Float32Array(ribbon);                              // convierte la lista acumulada a un array tipado
    gradientLineData = { data, count: data.length / RIBBON_STRIDE };    // cuenta cuántos vértices resultaron en total
    gl.bindBuffer(gl.ARRAY_BUFFER, gradRibbonBuf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);              // sube todos los vértices de una sola vez a la GPU
  }

  // Dibuja todas las franjas del campo de gradiente con mezcla ADITIVA
  // (SRC_ALPHA, ONE): donde varias líneas se cruzan, se suman y brillan
  // más en vez de taparse entre sí, dando un efecto de "haz de fibras".
  function drawGradientField(view, proj) {
    if (!gradientLineData || gradientLineData.count === 0) return;  // nada calculado todavía, o el volumen no tenía tejido suficiente
    gl.useProgram(ribbonProgram);
    gl.uniformMatrix4fv(uModelViewR, false, view);
    gl.uniformMatrix4fv(uProjectionR, false, proj);
    gl.uniform1f(uAlphaR, 0.62);                    // semi-transparente
    gl.uniform1f(uWidthR, gradRibbonWidthMm);        // ancho de franja calculado en computeGradientField
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE); // additive: crossing strands glow instead of just occluding
    gl.depthMask(false); gl.enable(gl.DEPTH_TEST);
    const stride = RIBBON_STRIDE * 4;  // 10 floats * 4 bytes = bytes que ocupa un vértice completo en el buffer
    gl.bindBuffer(gl.ARRAY_BUFFER, gradRibbonBuf);
    // Los 4 atributos leen del MISMO buffer intercalado, cada uno con su
    // propio desplazamiento (offset) en bytes dentro de cada vértice.
    gl.enableVertexAttribArray(aPositionR); gl.vertexAttribPointer(aPositionR, 3, gl.FLOAT, false, stride, 0);   // posición: primeros 3 floats
    gl.enableVertexAttribArray(aOtherR); gl.vertexAttribPointer(aOtherR, 3, gl.FLOAT, false, stride, 12);        // extremo opuesto: siguientes 3 floats (12 = 3*4 bytes)
    gl.enableVertexAttribArray(aSideR); gl.vertexAttribPointer(aSideR, 1, gl.FLOAT, false, stride, 24);          // lado: 1 float (24 = 6*4 bytes)
    gl.enableVertexAttribArray(aColorR); gl.vertexAttribPointer(aColorR, 3, gl.FLOAT, false, stride, 28);        // color: últimos 3 floats (28 = 7*4 bytes)
    gl.drawArrays(gl.TRIANGLES, 0, gradientLineData.count);  // dibuja todos los triángulos de todas las franjas de una vez
    gl.depthMask(true); gl.disable(gl.BLEND);
  }

  const mprAxialSlider = document.getElementById("mpr-axial-slider");        // slider del plano axial
  const mprCoronalSlider = document.getElementById("mpr-coronal-slider");    // slider del plano coronal
  const mprSagittalSlider = document.getElementById("mpr-sagittal-slider");  // slider del plano sagital
  const mprGradientToggle = document.getElementById("mpr-gradient-toggle");  // casilla del campo de gradiente
  mprAxialSlider.addEventListener("input", () => { mprAxialFrac = Number(mprAxialSlider.value) / 100; rebuildMprPlanes(); });        // mueve el plano axial y lo recalcula
  mprCoronalSlider.addEventListener("input", () => { mprCoronalFrac = Number(mprCoronalSlider.value) / 100; rebuildMprPlanes(); });  // ídem coronal
  mprSagittalSlider.addEventListener("input", () => { mprSagittalFrac = Number(mprSagittalSlider.value) / 100; rebuildMprPlanes(); }); // ídem sagital
  mprGradientToggle.addEventListener("change", () => {
    showGradientField = mprGradientToggle.checked;         // guarda si el overlay debe mostrarse
    if (showGradientField) computeGradientField();          // solo se calcula cuando hace falta (es costoso)
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
    flyPath = null;                          // se reconstruye desde cero cada vez que se llama
    if (!sv) return;                          // sin volumen de voxeles, no hay eje central que calcular
    const meta = ORGAN_META[currentOrganKey];
    const [nz, ny, nx] = sv.shape;
    const [ox, oy, oz] = sv.origin;
    const [sx, sy, sz] = sv.spacing;
    const frac = (meta.threshold_native - sv.valueMin) / (sv.valueMax - sv.valueMin);   // umbral real como fracción 0..1
    const quantThreshold = Math.max(0, Math.min(255, Math.round(frac * 255)));           // ese umbral en la escala 0-255
    const below = meta.threshold_below;
    const key = currentOrganKey;

    const rawPts = [];                        // un punto (centroide) por cada corte Z que tenga suficiente tejido
    for (let z = 0; z < nz; z++) {             // recorre cada corte axial del volumen
      let sumX = 0, sumY = 0, count = 0;       // acumuladores para promediar las posiciones de tejido en este corte
      const zOff = z * ny * nx;                // desplazamiento al inicio de este corte en el array plano
      for (let y = 0; y < ny; y++) {
        const rowOff = zOff + y * nx;          // desplazamiento al inicio de esta fila
        for (let x = 0; x < nx; x++) {
          const v = sv.voxels[rowOff + x];
          if (below ? v < quantThreshold : v > quantThreshold) { sumX += x; sumY += y; count++; }  // suma esta posición si es tejido real
        }
      }
      if (count < 12) continue; // too little real tissue on this slice to trust a centroid
      const cx = ox + (sumX / count) * sx, cy = oy + (sumY / count) * sy, cz = oz + z * sz;  // promedio de posiciones, convertido a milímetros reales
      rawPts.push(applyDisplayFixPoint(key, cx, cy, cz));  // rota el centroide al espacio de exhibición antes de guardarlo
    }
    if (rawPts.length < 3) return;  // muy pocos cortes válidos como para trazar una ruta con sentido
    // light 3-point smoothing so the camera doesn't jitter slice-to-slice
    flyPath = rawPts.map((p, i) => {
      const a = rawPts[Math.max(0, i - 1)], b = rawPts[Math.min(rawPts.length - 1, i + 1)];  // vecino anterior y siguiente (repite el extremo en los bordes)
      return [(a[0] + p[0] + b[0]) / 3, (a[1] + p[1] + b[1]) / 3, (a[2] + p[2] + b[2]) / 3];  // promedio simple de los 3 puntos consecutivos
    });
    flyT = 0; flyDir = 1;  // reinicia el progreso del vuelo al principio, avanzando hacia adelante
  }

  // Dada la posición actual en la ruta (flyT, 0..1), interpola linealmente
  // entre los dos puntos de flyPath más cercanos para obtener la posición
  // exacta del "ojo" de la cámara, y usa un punto un poco más adelante en
  // la ruta como el punto hacia el que mira (look), para que la vista
  // apunte siempre "hacia adelante" en el recorrido.
  function flyEyeLook() {
    const path = flyPath, n = path.length;
    const f = flyT * (n - 1);                              // posición continua a lo largo de la ruta (0 .. n-1)
    const i0 = Math.max(0, Math.min(n - 2, Math.floor(f))); // índice del punto justo antes de esa posición
    const frac = f - i0;                                    // qué tan avanzado está entre i0 e i0+1 (0..1)
    const p0 = path[i0], p1 = path[i0 + 1];
    const eye = [p0[0] + (p1[0]-p0[0])*frac, p0[1] + (p1[1]-p0[1])*frac, p0[2] + (p1[2]-p0[2])*frac];  // interpolación lineal entre p0 y p1
    const look = path[Math.min(n - 1, i0 + 2)];             // apunta 2 puntos más adelante en la ruta (acotado al final)
    return { eye, look };
  }

  // Avanza flyT cada frame según la velocidad del slider, y rebota (invierte
  // flyDir) al llegar a cualquiera de los dos extremos de la ruta, para que
  // el vuelo vaya y vuelva en bucle en vez de detenerse.
  function updateFlyProgress() {
    if (!flyPlaying || !flyPath) return;                    // en pausa, o sin ruta calculada todavía
    const fracPerFrame = (Number(flySpeedSlider.value) / 100) * 0.00167;  // cuánto avanza flyT en este frame, según el slider de velocidad
    flyT += flyDir * fracPerFrame;                           // avanza (o retrocede) la posición en la ruta
    if (flyT >= 1) { flyT = 1; flyDir = -1; } else if (flyT <= 0) { flyT = 0; flyDir = 1; }  // rebota en cualquiera de los dos extremos
    flyProgressNoteEl.textContent = flyDir > 0 ? "recorriendo →" : "← de regreso";  // indica visualmente el sentido actual
  }

  // Dibuja la malla igual que el modo sólido normal, pero con las caras
  // frontales descartadas (cullFace(FRONT) en vez de BACK): como la cámara
  // está literalmente dentro de la malla, lo que normalmente se vería "por
  // detrás" y se descarta es ahora la pared interior que sí queremos ver.
  function drawFlyInterior(view, proj) {
    gl.useProgram(program);
    gl.uniformMatrix4fv(uModelView, false, view);
    gl.uniformMatrix4fv(uProjection, false, proj);
    gl.uniformMatrix3fv(uNormalMatrix, false, normalMat3(view));
    gl.uniform3fv(uColor, currentColor);       // color real del órgano
    gl.uniform3fv(uOffset, [0, 0, 0]);          // sin desplazamiento
    gl.uniform1f(uPulse, 0.0);                  // sin pulso de latido dentro del vuelo
    gl.uniform3fv(uClipNormal, [1, 0, 0]);      // clipping neutro (no se usa aquí)
    gl.uniform1f(uClipValue, 1e9);
    gl.uniform1f(uClipEnabled, 0.0);
    gl.uniform1f(uAlpha, 1.0);                  // totalmente opaco
    gl.disable(gl.BLEND); gl.depthMask(true); gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE); gl.cullFace(gl.FRONT); // camera sits inside a closed mesh: show its interior wall
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.enableVertexAttribArray(aPosition); gl.vertexAttribPointer(aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.enableVertexAttribArray(aNormal); gl.vertexAttribPointer(aNormal, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
    gl.drawElements(gl.TRIANGLES, currentMesh.indices.length, gl.UNSIGNED_INT, 0);  // dibuja la malla completa (ahora vista desde adentro)
    gl.cullFace(gl.BACK);
  }

  flyPlayBtn.addEventListener("click", () => {
    flyPlaying = !flyPlaying;                                             // invierte pausado/reproduciendo
    flyPlayBtn.textContent = flyPlaying ? "Pausar" : "Reanudar";           // el texto del botón ofrece la acción opuesta al estado actual
    flyPlayBtn.setAttribute("aria-pressed", String(flyPlaying));
  });

  // Matriz de proyección en perspectiva estándar (4x4, en formato column-
  // major que espera WebGL) a partir del campo de visión vertical (fovy,
  // en radianes), la relación de aspecto del canvas, y los planos de
  // recorte cercano/lejano.
  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);  // f: factor de escala vertical; nf: normaliza el rango de profundidad
    return new Float32Array([f/aspect,0,0,0, 0,f,0,0, 0,0,(far+near)*nf,-1, 0,0,2*far*near*nf,0]);  // matriz 4x4 en orden column-major
  }
  // Matriz de vista (view matrix) que ubica una cámara en `eye`, mirando
  // hacia `target`, con `up` como referencia de "arriba". Construye una
  // base ortonormal (x,y,z de la cámara) a partir de esos tres vectores
  // usando productos cruz, y arma la matriz que transforma coordenadas del
  // mundo a coordenadas relativas a esa cámara.
  function lookAt(eye, target, up) {
    let zx=eye[0]-target[0], zy=eye[1]-target[1], zz=eye[2]-target[2];     // eje Z de la cámara: de target hacia eye
    let zl=Math.hypot(zx,zy,zz)||1; zx/=zl; zy/=zl; zz/=zl;                // normaliza el eje Z
    let xx=up[1]*zz-up[2]*zy, xy=up[2]*zx-up[0]*zz, xz=up[0]*zy-up[1]*zx;  // eje X de la cámara: up × Z
    let xl=Math.hypot(xx,xy,xz)||1; xx/=xl; xy/=xl; xz/=xl;                // normaliza el eje X
    const yx=zy*xz-zz*xy, yy=zz*xx-zx*xz, yz=zx*xy-zy*xx;                  // eje Y de la cámara: Z × X (ya normalizado, no hace falta reescalar)
    return new Float32Array([xx,yx,zx,0, xy,yy,zy,0, xz,yz,zz,0,
      -(xx*eye[0]+xy*eye[1]+xz*eye[2]), -(yx*eye[0]+yy*eye[1]+yz*eye[2]), -(zx*eye[0]+zy*eye[1]+zz*eye[2]), 1]);  // rotación + traslación que lleva el mundo al espacio de la cámara
  }
  // Extrae la submatriz 3x3 superior izquierda de una matriz de vista 4x4
  // (descarta la traslación) para transformar normales correctamente al
  // espacio de cámara — así la iluminación no se distorsiona al rotar.
  function normalMat3(m) { return new Float32Array([m[0],m[1],m[2], m[4],m[5],m[6], m[8],m[9],m[10]]); }

  // Estado global de la escena 3D principal: la malla activa, su color,
  // el radio de su caja envolvente, los ángulos/distancia de la cámara
  // orbital (theta = ángulo horizontal, phi = ángulo vertical, radius =
  // distancia al centro), si la rotación automática está activa, y el
  // estado del arrastre con el mouse/touch.
  let currentMesh = null, currentColor = [0.7,0.7,0.7], boundingRadius = 1;
  let theta = 0.6, phi = 1.15, radius = 1, targetRadius = 1;
  let reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let autoRotate = !reduceMotion;
  let dragging = false, lastX = 0, lastY = 0;

  // Recalcula, para la malla recién cargada, el radio de su caja
  // envolvente (la distancia máxima de cualquier vértice al centro) y sus
  // límites reales por eje (usados por el clipping). También fija una
  // distancia de cámara inicial proporcional a ese radio, para que
  // cualquier órgano —grande o pequeño— quede encuadrado igual de bien.
  function frameCamera(mesh) {
    boundingRadius = 1;                                        // valor de partida antes de medir la malla real
    const c = mesh.center;
    meshBoundsMin = [Infinity, Infinity, Infinity];             // arranca en +infinito para que cualquier valor real sea "menor"
    meshBoundsMax = [-Infinity, -Infinity, -Infinity];          // arranca en -infinito para que cualquier valor real sea "mayor"
    for (let i = 0; i < mesh.positions.length; i += 3) {        // recorre cada vértice
      const x = mesh.positions[i], y = mesh.positions[i+1], z = mesh.positions[i+2];
      const d = Math.hypot(x-c[0], y-c[1], z-c[2]);             // distancia de este vértice al centro
      if (d > boundingRadius) boundingRadius = d;               // se queda con la distancia máxima encontrada
      if (x < meshBoundsMin[0]) meshBoundsMin[0] = x; if (x > meshBoundsMax[0]) meshBoundsMax[0] = x;  // actualiza mínimo/máximo en X
      if (y < meshBoundsMin[1]) meshBoundsMin[1] = y; if (y > meshBoundsMax[1]) meshBoundsMax[1] = y;  // ídem en Y
      if (z < meshBoundsMin[2]) meshBoundsMin[2] = z; if (z > meshBoundsMax[2]) meshBoundsMax[2] = z;  // ídem en Z
    }
    radius = boundingRadius * 2.6; targetRadius = radius;  // distancia inicial de cámara, proporcional al tamaño real de la malla
  }
  // Sube la malla activa (posiciones, normales, índices de triángulos y sus
  // aristas derivadas) a los buffers de GPU creados antes. STATIC_DRAW le
  // dice a WebGL que estos datos se escriben una vez y se dibujan muchas
  // veces, sin cambiar — la optimización correcta aquí porque solo se
  // vuelve a llamar cuando el usuario cambia de órgano.
  function uploadMesh(mesh) {
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.bufferData(gl.ARRAY_BUFFER, mesh.positions, gl.STATIC_DRAW);   // sube posiciones
    gl.bindBuffer(gl.ARRAY_BUFFER, normBuf); gl.bufferData(gl.ARRAY_BUFFER, mesh.normals, gl.STATIC_DRAW);    // sube normales
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, mesh.indices, gl.STATIC_DRAW);  // sube índices de triángulos
    const edges = buildEdgeIndices(mesh.indices);   // calcula las aristas únicas para el modo alambre
    edgeCount = edges.length;                        // guarda cuántos índices de arista hay, para drawElements
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, edgeBuf); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, edges, gl.STATIC_DRAW);  // sube esos índices de arista
  }

  /* =========================================================
     3D anatomical landmarks — computed from the mesh's own
     geometry (connected components, extremities, local surface
     concavity), never from a fixed/guessed coordinate. Where no
     reliable geometric signal exists (liver), no landmark is shown
     rather than a fabricated one — see the chat discussion this
     scope came out of.
     ========================================================= */
  // Lee las 3 coordenadas (x,y,z) del vértice `i` desde el array plano
  // `positions` (donde cada vértice ocupa 3 posiciones consecutivas).
  function vertexPos(positions, i) { return [positions[i*3], positions[i*3+1], positions[i*3+2]]; }

  // Construye una lista de adyacencia (qué vértices están conectados por
  // una arista a cuál) a partir de la lista plana de aristas — se usa para
  // detectar concavidades locales (ver computeKidneyLandmarks).
  function adjacencyFromEdges(edges, numVertices) {
    const adj = new Array(numVertices);                  // un array vacío de vecinos por cada vértice
    for (let i = 0; i < numVertices; i++) adj[i] = [];    // inicializa cada entrada como lista vacía
    for (let i = 0; i < edges.length; i += 2) {           // recorre cada par (arista)
      const a = edges[i], b = edges[i+1];
      adj[a].push(b); adj[b].push(a);                     // la relación es bidireccional: a es vecino de b y viceversa
    }
    return adj;
  }

  // Promedio simple de las coordenadas de un subconjunto de vértices —
  // el centro geométrico de esa porción de la malla.
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
    const numVerts = mesh.positions.length / 3;                          // cuántos vértices tiene la malla
    const midX = (meshBoundsMin[0] + meshBoundsMax[0]) / 2;               // punto medio real del rango en X
    const vertsLeft = [], vertsRight = [];                                // índices de vértice de cada mitad
    for (let i = 0; i < numVerts; i++) {                                  // clasifica cada vértice según su lado de X
      (mesh.positions[i*3] > midX ? vertsLeft : vertsRight).push(i);      // X mayor = izquierda del paciente (convención DICOM)
    }
    if (!vertsLeft.length || !vertsRight.length) return [];  // si por algún motivo un lado quedó vacío, no hay landmarks fiables
    return [
      {label: "Pulmón izquierdo", pos: centroidOf(mesh.positions, vertsLeft)},   // centro geométrico de la mitad izquierda
      {label: "Pulmón derecho", pos: centroidOf(mesh.positions, vertsRight)},    // centro geométrico de la mitad derecha
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
    let apexIdx = 0, apexDist = -1;                    // mejor candidato a ápex encontrado hasta ahora
    for (let i = 0; i < numVerts; i++) {                // busca el vértice más lejano del centroide
      const dx = mesh.positions[i*3]-c[0], dy = mesh.positions[i*3+1]-c[1], dz = mesh.positions[i*3+2]-c[2];
      const d = dx*dx + dy*dy + dz*dz;                  // distancia al cuadrado (evita la raíz cuadrada, no hace falta para comparar)
      if (d > apexDist) { apexDist = d; apexIdx = i; }  // se queda con el vértice más lejano visto hasta ahora
    }
    const apex = vertexPos(mesh.positions, apexIdx);    // coordenadas reales del ápex encontrado
    let baseIdx = 0, baseDist = -1;                     // mejor candidato a base encontrado hasta ahora
    for (let i = 0; i < numVerts; i++) {                // busca el vértice más lejano DEL ÁPEX (no del centro)
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
    const adj = adjacencyFromEdges(buildEdgeIndices(mesh.indices), numVerts);  // vecinos directos de cada vértice
    const c = mesh.center;
    const dist = new Float32Array(numVerts);            // distancia de cada vértice al centroide, precalculada
    for (let i = 0; i < numVerts; i++) {
      const dx = mesh.positions[i*3]-c[0], dy = mesh.positions[i*3+1]-c[1], dz = mesh.positions[i*3+2]-c[2];
      dist[i] = Math.sqrt(dx*dx + dy*dy + dz*dz);
    }
    let bestIdx = -1, bestScore = -Infinity;             // el vértice con mayor "concavidad" encontrado hasta ahora
    for (let i = 0; i < numVerts; i++) {
      const nbrs = adj[i];                                // vecinos directos de este vértice
      if (nbrs.length < 4) continue;                      // muy pocos vecinos: la malla ahí es rara, se ignora
      let sum = 0;
      for (const nb of nbrs) sum += dist[nb];              // suma las distancias al centro de todos los vecinos
      const concavity = (sum / nbrs.length) - dist[i];    // si el promedio de los vecinos es MAYOR que la propia distancia, es un hueco (hendidura)
      if (concavity > bestScore) { bestScore = concavity; bestIdx = i; }  // se queda con la hendidura más marcada
    }
    const landmarks = [];
    if (bestIdx !== -1) landmarks.push({label: "Hilio renal (aprox.)", pos: vertexPos(mesh.positions, bestIdx)});  // solo si se encontró alguna concavidad real

    // Poles: the two extremities along the mesh's longest axis — a kidney
    // is reliably elongated pole-to-pole, so this is shape-intrinsic, same
    // idea as the heart's apex/base. Not labeled superior/inferior: unlike
    // the heart's apex (a single unambiguous point), both kidney poles look
    // similar, so there's no honest way to tell which is which from shape
    // alone on an isolated ex-vivo specimen.
    const extent = [meshBoundsMax[0]-meshBoundsMin[0], meshBoundsMax[1]-meshBoundsMin[1], meshBoundsMax[2]-meshBoundsMin[2]];  // largo real de la malla en cada eje
    let axis = 0;                          // arranca suponiendo que X es el eje más largo
    if (extent[1] > extent[axis]) axis = 1;  // Y es más largo que el candidato actual
    if (extent[2] > extent[axis]) axis = 2;  // Z es más largo que el candidato actual
    let loIdx = 0, loVal = Infinity, hiIdx = 0, hiVal = -Infinity;  // vértices extremos en el eje más largo
    for (let i = 0; i < numVerts; i++) {
      const v = mesh.positions[i*3 + axis];   // coordenada de este vértice, solo en el eje elegido
      if (v < loVal) { loVal = v; loIdx = i; }  // nuevo extremo mínimo
      if (v > hiVal) { hiVal = v; hiIdx = i; }  // nuevo extremo máximo
    }
    landmarks.push({label: "Polo A", pos: vertexPos(mesh.positions, loIdx)});  // extremo mínimo del eje largo
    landmarks.push({label: "Polo B", pos: vertexPos(mesh.positions, hiIdx)});  // extremo máximo del eje largo
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
    const extent = [meshBoundsMax[0]-meshBoundsMin[0], meshBoundsMax[1]-meshBoundsMin[1], meshBoundsMax[2]-meshBoundsMin[2]];  // largo real por eje
    let axis = 0;                            // eje más largo de la caja envolvente (verificado real: es el eje izq-der en este espécimen)
    if (extent[1] > extent[axis]) axis = 1;
    if (extent[2] > extent[axis]) axis = 2;
    const mid = (meshBoundsMin[axis] + meshBoundsMax[axis]) / 2;  // punto medio real de ese eje
    const vertsA = [], vertsB = [];           // vértices de cada mitad
    for (let i = 0; i < numVerts; i++) {
      (mesh.positions[i*3 + axis] < mid ? vertsA : vertsB).push(i);  // clasifica según de qué lado del punto medio cae
    }
    if (!vertsA.length || !vertsB.length) return [];  // una mitad quedó vacía, no hay partición fiable
    const [bigger, smaller] = vertsA.length >= vertsB.length ? [vertsA, vertsB] : [vertsB, vertsA];  // ordena por cantidad de vértices (proxy de volumen)
    return [
      {label: "Lóbulo derecho (mayor)", pos: centroidOf(mesh.positions, bigger)},   // el lóbulo hepático derecho es siempre el más grande
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
    const extent = [meshBoundsMax[0]-meshBoundsMin[0], meshBoundsMax[1]-meshBoundsMin[1], meshBoundsMax[2]-meshBoundsMin[2]];  // largo real por eje
    let axis = 0;                            // arranca suponiendo X como el eje más ESTRECHO
    if (extent[1] < extent[axis]) axis = 1;  // Y es más estrecho que el candidato actual
    if (extent[2] < extent[axis]) axis = 2;  // Z es más estrecho que el candidato actual
    const mid = (meshBoundsMin[axis] + meshBoundsMax[axis]) / 2;  // punto medio real de ese eje (el eje izq-der, por ser el más angosto)
    const vertsA = [], vertsB = [];
    for (let i = 0; i < numVerts; i++) {
      (mesh.positions[i*3 + axis] < mid ? vertsA : vertsB).push(i);  // clasifica cada vértice según de qué lado cae
    }
    return [
      {label: "Hemisferio 1", pos: centroidOf(mesh.positions, vertsA)},  // sin etiqueta izq/der: no hay forma honesta de saber cuál es cuál
      {label: "Hemisferio 2", pos: centroidOf(mesh.positions, vertsB)},
    ];
  }

  // Enruta al cálculo de landmarks específico de cada órgano — cada uno
  // usa la señal geométrica que realmente tiene sentido para esa forma
  // (ver los comentarios de cada función computeXLandmarks arriba).
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
  // Botón de la brújula que muestra/oculta todas las etiquetas de landmarks
  // a la vez, sin recalcularlas (solo alterna la visibilidad de la capa).
  labelsToggleBtn.addEventListener("click", () => {
    labelsVisible = !labelsVisible;
    labelsToggleBtn.setAttribute("aria-pressed", String(labelsVisible));
    labelsToggleBtn.title = "Etiquetas anatómicas: " + (labelsVisible ? "visibles" : "ocultas");
    labelLayerEl.classList.toggle("hidden", !labelsVisible);
  });

  // Crea (o recrea) un <div> de etiqueta HTML por cada landmark actual,
  // cada uno con su propio listener de clic que abre el popover con la
  // información anatómica de ORGAN_META. Su posición en pantalla se
  // actualiza cada frame en render3d() vía projectToScreen().
  function rebuildLabelEls() {
    labelLayerEl.innerHTML = "";                          // borra las etiquetas del órgano anterior
    labelEls = currentLandmarks.map((lm) => {              // crea un <div> nuevo por cada landmark actual
      const el = document.createElement("div");
      el.className = "landmark-label";
      el.textContent = lm.label;                            // el texto visible (p. ej. "Ápex (punta)")
      el.addEventListener("click", (e) => { e.stopPropagation(); showLandmarkPopover(lm.label, el); });  // evita que el clic también dispare el arrastre de cámara
      labelLayerEl.appendChild(el);
      return el;
    });
    hideLandmarkPopover();  // cierra cualquier popover que hubiera quedado abierto del órgano anterior
  }

  // Clicking a landmark pin shows real anatomical background on that
  // structure (ORGAN_META[key].landmark_info) — general, well-established
  // anatomy of the labeled part, not a fabricated claim about this exact
  // specimen beyond what's already established elsewhere in the UI.
  const landmarkPopoverEl = document.getElementById("landmark-popover");
  const landmarkPopoverTitleEl = document.getElementById("landmark-popover-title");
  const landmarkPopoverTextEl = document.getElementById("landmark-popover-text");
  function showLandmarkPopover(label, labelEl) {
    const info = (ORGAN_META[currentOrganKey].landmark_info || {})[label];  // texto real para esta etiqueta concreta
    if (!info) return;                          // este landmark no tiene información asociada, no hace nada
    landmarkPopoverTitleEl.textContent = label;  // título del popover: el mismo texto de la etiqueta
    landmarkPopoverTextEl.textContent = info;    // cuerpo del popover: la explicación anatómica
    // Posiciona el popover justo al lado de la etiqueta que se clicó,
    // recortando contra el ancho del canvas para que no se salga por la
    // derecha ni por arriba de la pantalla.
    const left = parseFloat(labelEl.style.left) || 0;
    const top = parseFloat(labelEl.style.top) || 0;
    const stageWidth = canvas.clientWidth;
    landmarkPopoverEl.style.left = Math.min(left + 14, stageWidth - 280) + "px";
    landmarkPopoverEl.style.top = Math.max(top - 90, 8) + "px";
    landmarkPopoverEl.classList.remove("hidden");
  }
  function hideLandmarkPopover() {
    landmarkPopoverEl.classList.add("hidden");
  }
  document.getElementById("landmark-popover-close").addEventListener("click", hideLandmarkPopover);

  // Convierte un punto 3D del mundo a coordenadas de píxel en el canvas:
  // lo pasa por la matriz de vista y luego de proyección (a mano, en vez
  // de con una librería de matrices) para obtener "clip space", divide por
  // w para llegar a NDC (-1..1), y por último remapea NDC a píxeles reales.
  // Devuelve null si el punto queda detrás de la cámara o muy fuera de
  // pantalla, para que el llamador pueda ocultar esa etiqueta.
  function projectToScreen(pos, view, proj) {
    const vx = view[0]*pos[0]+view[4]*pos[1]+view[8]*pos[2]+view[12];   // multiplicación manual matriz(4x4) × vector, componente X
    const vy = view[1]*pos[0]+view[5]*pos[1]+view[9]*pos[2]+view[13];   // componente Y en espacio de cámara
    const vz = view[2]*pos[0]+view[6]*pos[1]+view[10]*pos[2]+view[14];  // componente Z en espacio de cámara
    const vw = view[3]*pos[0]+view[7]*pos[1]+view[11]*pos[2]+view[15];  // componente W (siempre 1 para una matriz de vista normal)
    const cx = proj[0]*vx+proj[4]*vy+proj[8]*vz+proj[12]*vw;   // aplica la proyección: X en clip space
    const cy = proj[1]*vx+proj[5]*vy+proj[9]*vz+proj[13]*vw;   // Y en clip space
    const cw = proj[3]*vx+proj[7]*vy+proj[11]*vz+proj[15]*vw;  // W en clip space (usado para la división de perspectiva)
    if (cw <= 0.001) return null;               // el punto está detrás (o casi en) el plano de la cámara
    const ndcX = cx / cw, ndcY = cy / cw;        // división de perspectiva: pasa de clip space a NDC (-1..1)
    if (ndcX < -1.3 || ndcX > 1.3 || ndcY < -1.3 || ndcY > 1.3) return null;  // muy fuera de pantalla (con un margen de 0.3)
    return [(ndcX*0.5+0.5) * canvas.clientWidth, (1-(ndcY*0.5+0.5)) * canvas.clientHeight];  // NDC -> píxeles (Y se invierte: NDC crece hacia arriba, CSS hacia abajo)
  }

  // ---------- controles de cámara orbital con mouse/touch ----------
  // Empieza a arrastrar (o, si la herramienta de medición está activa,
  // delega el clic a handleMeasureClick en vez de rotar la cámara).
  canvas.addEventListener("pointerdown", e => {
    if (measureEnabled) { handleMeasureClick(e); return; }
    hideLandmarkPopover();
    dragging = true; autoRotate = false; lastX = e.clientX; lastY = e.clientY; canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointerup", () => dragging = false);
  // Mientras se arrastra, el movimiento horizontal del mouse gira theta
  // (ángulo alrededor del eje vertical) y el vertical gira phi (ángulo
  // polar), con phi acotado para no pasar de un polo al otro de golpe.
  canvas.addEventListener("pointermove", e => {
    if (!dragging) return;                                     // solo gira la cámara mientras el botón sigue presionado
    theta -= (e.clientX - lastX) * 0.008; phi -= (e.clientY - lastY) * 0.008;  // movimiento del mouse en X gira theta; en Y gira phi
    phi = Math.max(0.15, Math.min(Math.PI - 0.15, phi));         // evita llegar exactamente al polo (ahí la cámara "voltea" bruscamente)
    lastX = e.clientX; lastY = e.clientY;                        // guarda la posición actual para calcular el delta del siguiente movimiento
  });
  // La rueda del mouse acerca/aleja la cámara (zoom), acotado entre 1.15x
  // y 6x el radio de la malla para no poder alejarse o acercarse demasiado.
  canvas.addEventListener("wheel", e => {
    e.preventDefault();  // evita que la página completa haga scroll al usar la rueda sobre el canvas
    targetRadius = Math.max(boundingRadius*1.15, Math.min(boundingRadius*6, targetRadius * Math.pow(1.0012, e.deltaY)));  // escala exponencial: mismo "sentimiento" de zoom sin importar la distancia actual
  }, {passive: false});  // passive:false es necesario para que preventDefault() realmente funcione en wheel

  // ---- camera view presets (Anterior/Posterior/Left/Right/Superior/Inferior/Isometric) ----
  // theta/phi are spherical angles of the orbit camera around the mesh
  // center (see the eye computation in render3d): phi is polar angle from
  // +Y (the renderer always treats +Y as "up"), theta is azimuth around Y.
  // So "Superior"/"Inferior" target the poles (phi near 0/PI) and the
  // other four sit on the equator (phi=PI/2).
  //
  // For LUNGS these are real, verified patient-anatomical directions: the
  // source CTChest.nrrd carries a real DICOM-style direction/origin
  // (confirmed from its NRRD header: "space: left-posterior-superior",
  // identity direction matrix), which the pipeline's index_to_world
  // carries straight through to mesh vertex coordinates (see
  // core/mesh.py) — real Left/Posterior/Superior axes, then the "rotZup"
  // ORGAN_DISPLAY_FIX above re-expresses them so Superior lines up with
  // the renderer's vertical, which is exactly what these targets assume.
  //
  // For the ex-vivo synchrotron organs (heart/liver/kidneys/brain) no such
  // metadata exists — those specimens were physically mounted in the
  // scanner's sample tube however was convenient, not in a documented
  // patient pose (see docs/ORGAN_PIPELINES.md and the load_volume()
  // docstring). For those, the same buttons are a fixed *display*
  // convention (some, like the heart, aligned to a real shape-intrinsic
  // feature via ORGAN_DISPLAY_FIX — others not), not a verified direction
  // — the UI caveats this explicitly per organ (see orientation-note).
  const CAMERA_VIEWS = {
    front:  {theta: 0,            phi: Math.PI / 2},   // ecuador (phi=90°), mirando de frente
    back:   {theta: Math.PI,      phi: Math.PI / 2},    // ecuador, girado 180°
    left:   {theta: Math.PI / 2,  phi: Math.PI / 2},    // ecuador, girado 90°
    right:  {theta: -Math.PI / 2, phi: Math.PI / 2},    // ecuador, girado -90°
    top:    {theta: 0.001,        phi: 0.08},           // casi el polo superior (phi≈0)
    bottom: {theta: 0.001,        phi: Math.PI - 0.08}, // casi el polo inferior (phi≈π)
    iso:    {theta: -Math.PI / 4, phi: 1.15},           // ángulo isométrico intermedio, ni polo ni ecuador
  };
  // Salta directamente a los ángulos de un botón de vista (Ant/Post/etc.),
  // deteniendo la auto-rotación para que la vista elegida no se pierda.
  function setCameraView(name) {
    const v = CAMERA_VIEWS[name];                                       // busca los ángulos de este nombre de vista
    if (!v) return;                                                      // nombre desconocido, no hace nada
    theta = v.theta; phi = v.phi; targetRadius = boundingRadius * 2.6;   // salta directo a esos ángulos y una distancia estándar
    autoRotate = false;                                                  // deja de girar solo, para que la vista elegida se quede fija
  }
  // Botón "Encuadrar" (fit): vuelve al ángulo inicial curado para este
  // órgano (ORGAN_META[...].initial_theta/phi) y reactiva la auto-rotación
  // si el usuario no pidió reducir el movimiento (prefers-reduced-motion).
  function fitAndReset() {
    const meta = ORGAN_META[currentOrganKey];
    theta = meta.initial_theta; phi = meta.initial_phi; targetRadius = boundingRadius * 2.6;  // ángulo/distancia curados por órgano
    autoRotate = !reduceMotion;   // reanuda el giro automático, salvo que el usuario pida menos movimiento
  }
  document.getElementById("fit-btn").addEventListener("click", fitAndReset);  // botón de la brújula "Encuadrar"
  document.getElementById("viewport-toolbar").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-view]");  // cualquiera de los botones Ant/Post/Izq/Der/Sup/Inf/Iso
    if (!btn) return;
    setCameraView(btn.dataset.view);
  });

  // ---- axis gizmo: small always-on corner indicator of X/Y/Z orientation ----
  const gizmoCanvas = document.getElementById("axis-gizmo-canvas");
  const gizmoCtx = gizmoCanvas.getContext("2d");
  // Dibuja la pequeña brújula 2D de la esquina superior izquierda: proyecta
  // los tres ejes unitarios (X/Y/Z) con la misma matriz de vista que usa la
  // escena 3D, y los ordena por profundidad (z) para que el eje más cercano
  // a la cámara se dibuje al final, encima de los demás.
  function drawAxisGizmo(view) {
    const cx = 32, cy = 32, len = 20;         // centro del mini-canvas (64x64) y largo de cada flecha en píxeles
    gizmoCtx.clearRect(0, 0, 64, 64);         // limpia el frame anterior
    const axes = [                             // los 3 ejes unitarios del mundo, con su color y letra
      {v: [1,0,0], color: "#c76b5c", label: "X"},
      {v: [0,1,0], color: "#789e61", label: "Y"},
      {v: [0,0,1], color: "#5c8fbd", label: "Z"},
    ];
    const projected = axes.map(a => {
      // Solo rota el vector (sin traslación, ignora la 4ta fila/columna):
      // basta con la orientación de la cámara, no su posición.
      const vx = view[0]*a.v[0]+view[4]*a.v[1]+view[8]*a.v[2];
      const vy = view[1]*a.v[0]+view[5]*a.v[1]+view[9]*a.v[2];
      const vz = view[2]*a.v[0]+view[6]*a.v[1]+view[10]*a.v[2];
      return {...a, sx: cx + vx*len, sy: cy - vy*len, z: vz};  // posición 2D en el canvas (Y invertida: pantalla crece hacia abajo) + profundidad
    }).sort((a,b) => a.z - b.z);  // ordena de más lejano a más cercano, para dibujar el cercano al final (por encima)
    for (const a of projected) {
      gizmoCtx.strokeStyle = a.color; gizmoCtx.lineWidth = 2;
      gizmoCtx.beginPath(); gizmoCtx.moveTo(cx, cy); gizmoCtx.lineTo(a.sx, a.sy); gizmoCtx.stroke();  // línea desde el centro hasta la punta del eje
      gizmoCtx.fillStyle = a.color;
      gizmoCtx.beginPath(); gizmoCtx.arc(a.sx, a.sy, 4.5, 0, Math.PI*2); gizmoCtx.fill();  // círculo relleno en la punta
      gizmoCtx.fillStyle = "#fff"; gizmoCtx.font = "9px sans-serif"; gizmoCtx.textAlign = "center"; gizmoCtx.textBaseline = "middle";
      gizmoCtx.fillText(a.label, a.sx, a.sy);  // la letra (X/Y/Z) centrada dentro del círculo
    }
  }

  // ---- export: serialize the mesh already loaded in the browser to STL/OBJ ----
  // Truco estándar del navegador para "descargar" un Blob sin servidor:
  // crea una URL temporal apuntando a los bytes en memoria, la asigna a un
  // <a download> invisible, simula el clic, y libera la URL poco después.
  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;                          // el atributo download fuerza a "guardar" en vez de navegar
    document.body.appendChild(a); a.click(); document.body.removeChild(a);  // el <a> debe estar en el DOM para que .click() funcione en todos los navegadores
    setTimeout(() => URL.revokeObjectURL(url), 2000);              // libera la memoria de la URL temporal, dando tiempo a que la descarga arranque
  }
  // Serializa la malla activa al formato STL binario: un header de 80
  // bytes, un contador de triángulos de 4 bytes, y luego 50 bytes por
  // triángulo (normal + 3 vértices, todo en float32, más 2 bytes sin usar
  // que exige el formato). La normal de cada triángulo se recalcula aquí
  // con un producto cruz (no se reutiliza la normal por vértice de la
  // malla), que es lo que espera un lector de STL estándar.
  function meshToStlBlob(mesh) {
    const triCount = mesh.indices.length / 3;                 // cada triángulo usa 3 índices
    const buf = new ArrayBuffer(84 + triCount * 50);           // 84 bytes de header + 50 bytes por triángulo
    const view = new DataView(buf);                            // permite escribir números en posiciones exactas de bytes
    const header = "Medical3DReconstruction export";
    for (let i = 0; i < header.length; i++) view.setUint8(i, header.charCodeAt(i));  // escribe el texto del header byte a byte
    view.setUint32(80, triCount, true);   // bytes 80-83: cantidad de triángulos (little-endian, por el "true")
    let off = 84;                          // los datos de los triángulos empiezan justo después del header
    const p = mesh.positions;
    for (let t = 0; t < triCount; t++) {
      const i0 = mesh.indices[t*3] * 3, i1 = mesh.indices[t*3+1] * 3, i2 = mesh.indices[t*3+2] * 3;  // índices (×3) de los 3 vértices de este triángulo
      const ax = p[i0], ay = p[i0+1], az = p[i0+2];   // vértice A
      const bx = p[i1], by = p[i1+1], bz = p[i1+2];   // vértice B
      const cx = p[i2], cy = p[i2+1], cz = p[i2+2];   // vértice C
      const ux = bx-ax, uy = by-ay, uz = bz-az;       // vector A->B
      const vx = cx-ax, vy = cy-ay, vz = cz-az;       // vector A->C
      let nx = uy*vz - uz*vy, ny = uz*vx - ux*vz, nz = ux*vy - uy*vx;  // producto cruz (A->B) × (A->C) = normal del triángulo
      const nl = Math.hypot(nx, ny, nz) || 1;         // magnitud de esa normal (o 1, para no dividir entre cero)
      nx /= nl; ny /= nl; nz /= nl;                    // normaliza a longitud 1
      view.setFloat32(off, nx, true); view.setFloat32(off+4, ny, true); view.setFloat32(off+8, nz, true);       // escribe la normal (12 bytes)
      view.setFloat32(off+12, ax, true); view.setFloat32(off+16, ay, true); view.setFloat32(off+20, az, true);  // escribe el vértice A (12 bytes)
      view.setFloat32(off+24, bx, true); view.setFloat32(off+28, by, true); view.setFloat32(off+32, bz, true);  // escribe el vértice B (12 bytes)
      view.setFloat32(off+36, cx, true); view.setFloat32(off+40, cy, true); view.setFloat32(off+44, cz, true);  // escribe el vértice C (12 bytes)
      view.setUint16(off+48, 0, true);   // 2 bytes de "atributo" que exige el formato STL, sin uso aquí
      off += 50;                          // avanza al siguiente bloque de triángulo
    }
    return new Blob([buf], {type: "model/stl"});
  }
  // Serializa la malla activa al formato de texto OBJ: una línea "v x y z"
  // por vértice, una "vn x y z" por normal, y una "f" por triángulo con
  // índices 1-based (OBJ no empieza en 0, a diferencia de los arrays de JS).
  function meshToObjString(mesh) {
    const lines = ["# Medical3DReconstruction export", `# ${ORGAN_META[currentOrganKey].label} — ${mesh.numVertices} vértices, ${mesh.numTriangles} triángulos`];  // encabezado informativo como comentarios OBJ
    const p = mesh.positions, n = mesh.normals;
    for (let i = 0; i < p.length; i += 3) lines.push(`v ${p[i]} ${p[i+1]} ${p[i+2]}`);    // una línea "v" por cada vértice
    for (let i = 0; i < n.length; i += 3) lines.push(`vn ${n[i]} ${n[i+1]} ${n[i+2]}`);   // una línea "vn" por cada normal
    for (let t = 0; t < mesh.indices.length; t += 3) {
      const a = mesh.indices[t]+1, b = mesh.indices[t+1]+1, c = mesh.indices[t+2]+1;  // +1 porque OBJ numera desde 1, no desde 0
      lines.push(`f ${a}//${a} ${b}//${b} ${c}//${c}`);  // "vértice//normal" para cada esquina del triángulo (mismo índice para ambos)
    }
    return lines.join("\n");
  }
  const exportStatusEl = document.getElementById("export-status");
  // Formatea un tamaño en bytes como "X.X MB" o "X KB" para el mensaje de
  // confirmación de exportación.
  function fmtBytes(n) { return n > 1e6 ? (n/1e6).toFixed(1)+" MB" : (n/1e3).toFixed(0)+" KB"; }
  document.getElementById("export-stl-btn").addEventListener("click", () => {
    if (!currentMesh) return;                             // nada cargado todavía
    const blob = meshToStlBlob(currentMesh);               // serializa la malla actual a bytes STL
    downloadBlob(blob, `${currentOrganKey}.stl`);          // dispara la descarga en el navegador
    exportStatusEl.textContent = `Exportado: ${currentOrganKey}.stl (${fmtBytes(blob.size)})`;  // mensaje de confirmación con el tamaño real
  });
  document.getElementById("export-obj-btn").addEventListener("click", () => {
    if (!currentMesh) return;
    const text = meshToObjString(currentMesh);              // texto OBJ completo
    const blob = new Blob([text], {type: "text/plain"});    // lo empaqueta como archivo de texto
    downloadBlob(blob, `${currentOrganKey}.obj`);
    exportStatusEl.textContent = `Exportado: ${currentOrganKey}.obj (${fmtBytes(blob.size)})`;
  });
  document.getElementById("capture-view-btn").addEventListener("click", () => {
    canvas.toBlob((blob) => {                    // captura de forma asíncrona el contenido actual del canvas como imagen
      if (!blob) return;                          // el navegador no pudo generar la imagen (caso raro)
      downloadBlob(blob, `${currentOrganKey}_vista.png`);
      exportStatusEl.textContent = `Capturado: ${currentOrganKey}_vista.png (${fmtBytes(blob.size)})`;
    }, "image/png");                              // formato de salida: PNG
  });

  // ---- measurement: point-to-point distance via CPU ray/triangle picking ----
  // The mesh's own vertex coordinates are already real millimeters (same
  // space as the "Centroide (mm)"/bounding box readouts), so a distance
  // between two picked surface points is a real physical measurement, not
  // an approximation from screen pixels.
  // Algoritmo de Möller–Trumbore: calcula si el rayo (origen ox,oy,oz,
  // dirección dx,dy,dz) atraviesa el triángulo v0-v1-v2, y a qué distancia
  // `t` a lo largo del rayo ocurre el impacto (o null si no hay impacto,
  // incluyendo el caso de rayo paralelo al triángulo).
  function rayTriangleHit(ox, oy, oz, dx, dy, dz, v0, v1, v2) {
    const EPS = 1e-7;                                    // margen para evitar división por (casi) cero
    const e1x = v1[0]-v0[0], e1y = v1[1]-v0[1], e1z = v1[2]-v0[2];  // arista v0->v1
    const e2x = v2[0]-v0[0], e2y = v2[1]-v0[1], e2z = v2[2]-v0[2];  // arista v0->v2
    const hx = dy*e2z - dz*e2y, hy = dz*e2x - dx*e2z, hz = dx*e2y - dy*e2x;  // producto cruz dirección × e2
    const a = e1x*hx + e1y*hy + e1z*hz;                  // producto punto e1 · h
    if (Math.abs(a) < EPS) return null;                  // el rayo es casi paralelo al triángulo: no hay impacto bien definido
    const f = 1 / a;
    const sx = ox-v0[0], sy = oy-v0[1], sz = oz-v0[2];   // vector desde v0 hasta el origen del rayo
    const u = f * (sx*hx + sy*hy + sz*hz);                // primera coordenada baricéntrica
    if (u < 0 || u > 1) return null;                      // fuera del triángulo en esta coordenada
    const qx = sy*e1z - sz*e1y, qy = sz*e1x - sx*e1z, qz = sx*e1y - sy*e1x;  // producto cruz s × e1
    const v = f * (dx*qx + dy*qy + dz*qz);                // segunda coordenada baricéntrica
    if (v < 0 || u+v > 1) return null;                    // fuera del triángulo (v negativo o u+v pasa de 1)
    const t = f * (e2x*qx + e2y*qy + e2z*qz);  // distancia a lo largo del rayo donde ocurre el impacto
    return t > EPS ? t : null;                  // solo cuenta si el impacto está adelante del origen (t positivo)
  }
  // Prueba el rayo contra CADA triángulo de la malla activa (fuerza bruta:
  // suficiente aquí porque la malla ya está muy decimada para la web) y se
  // queda con el impacto más cercano al origen del rayo — el punto de la
  // superficie que el usuario realmente "vería" primero desde ese ángulo.
  function pickMeshPoint(originArr, dirArr) {
    if (!currentMesh) return null;                              // sin malla cargada, no hay superficie que tocar
    const [ox, oy, oz] = originArr, [dx, dy, dz] = dirArr;
    const p = currentMesh.positions, idx = currentMesh.indices;
    let bestT = Infinity;                                        // distancia del impacto más cercano encontrado hasta ahora
    const v0 = [0,0,0], v1 = [0,0,0], v2 = [0,0,0];              // arrays reutilizados en cada iteración (evita crear basura para el recolector)
    for (let t = 0; t < idx.length; t += 3) {                   // recorre cada triángulo de la malla
      const i0 = idx[t]*3, i1 = idx[t+1]*3, i2 = idx[t+2]*3;    // índices (×3) de sus 3 vértices
      v0[0]=p[i0]; v0[1]=p[i0+1]; v0[2]=p[i0+2];                 // copia el vértice 0 a v0
      v1[0]=p[i1]; v1[1]=p[i1+1]; v1[2]=p[i1+2];                 // copia el vértice 1 a v1
      v2[0]=p[i2]; v2[1]=p[i2+1]; v2[2]=p[i2+2];                 // copia el vértice 2 a v2
      const hit = rayTriangleHit(ox,oy,oz, dx,dy,dz, v0,v1,v2); // prueba el rayo contra este triángulo
      if (hit !== null && hit < bestT) bestT = hit;              // se queda con el impacto más cercano al origen
    }
    if (!isFinite(bestT)) return null;                           // el rayo no tocó ningún triángulo
    return [ox+dx*bestT, oy+dy*bestT, oz+dz*bestT];              // punto real de impacto: origen + dirección × distancia
  }
  // Con la herramienta de medición activa, convierte el clic en pantalla
  // (mx,my en coordenadas -1..1) en un rayo 3D desde la cámara actual —
  // reconstruyendo a mano la misma base de cámara y el mismo campo de
  // visión que usa el render principal (ver render3d/lookAt) — y usa
  // pickMeshPoint para encontrar dónde ese rayo toca la superficie real
  // de la malla. Guarda hasta 2 puntos; al llegar a un tercer clic,
  // reinicia la medición desde cero.
  function handleMeasureClick(e) {
    if (!currentMesh || (viewMode !== "solid" && viewMode !== "xray" && viewMode !== "wire")) return;  // solo tiene sentido sobre la malla sólida
    const rect = canvas.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * 2 - 1;    // posición X del clic, normalizada a -1..1
    const my = -(((e.clientY - rect.top) / rect.height) * 2 - 1); // posición Y del clic, normalizada e invertida (pantalla crece hacia abajo, NDC hacia arriba)
    const c = currentMesh.center;
    const eye = [c[0]+radius*Math.sin(phi)*Math.sin(theta), c[1]+radius*Math.cos(phi), c[2]+radius*Math.sin(phi)*Math.cos(theta)];  // misma fórmula de cámara orbital que usa render3d()
    // camera basis, matching lookAt(eye, c, [0,1,0])
    let zx=eye[0]-c[0], zy=eye[1]-c[1], zz=eye[2]-c[2];             // eje Z de la cámara
    let zl=Math.hypot(zx,zy,zz)||1; zx/=zl; zy/=zl; zz/=zl;         // normalizado
    let xx=1*zz-0*zy, xy=0*zx-0*zz, xz=0*zy-1*zx;                   // eje X de la cámara (up=[0,1,0] × Z, simplificado a mano)
    let xl=Math.hypot(xx,xy,xz)||1; xx/=xl; xy/=xl; xz/=xl;         // normalizado
    const yx=zy*xz-zz*xy, yy=zz*xx-zx*xz, yz=zx*xy-zy*xx;           // eje Y de la cámara (Z × X)
    const aspect = canvas.width / Math.max(1, canvas.height);       // relación de aspecto real del canvas
    const tanHalf = Math.tan((Math.PI/4.2) / 2);                    // mismo campo de visión que usa la proyección principal
    const dvx = mx*aspect*tanHalf, dvy = my*tanHalf, dvz = -1;      // dirección del rayo en espacio de cámara (mirando hacia -Z)
    let dirx = dvx*xx + dvy*yx + dvz*zx;                            // convierte esa dirección a espacio del mundo, componente X
    let diry = dvx*xy + dvy*yy + dvz*zy;                            // componente Y
    let dirz = dvx*xz + dvy*yz + dvz*zz;                            // componente Z
    const dl = Math.hypot(dirx,diry,dirz)||1; dirx/=dl; diry/=dl; dirz/=dl;  // normaliza la dirección final del rayo
    const hitPoint = pickMeshPoint(eye, [dirx, diry, dirz]);        // busca dónde ese rayo toca la malla
    if (!hitPoint) return;                                           // el clic no tocó la superficie (p. ej. cayó en el fondo)
    if (measurePoints.length >= 2) measurePoints = [];               // un tercer clic reinicia la medición
    measurePoints.push(hitPoint);
    updateMeasureReadout();
  }
  const measureLayerEl = document.getElementById("measure-layer");
  // Distancia euclidiana simple entre dos puntos 3D — como las mallas ya
  // están en milímetros reales, el resultado es una medida física real.
  function dist3(a, b) { return Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]); }
  // Redibuja, sobre la capa HTML de medición, la línea punteada y los dos
  // puntos entre las posiciones 3D ya proyectadas a pantalla, más la
  // etiqueta con la distancia en mm a la mitad del segmento.
  function updateMeasureOverlay(view, proj) {
    if (measurePoints.length === 0) { measureLayerEl.innerHTML = ""; return; }  // nada que dibujar
    const screenPts = measurePoints.map((p) => projectToScreen(p, view, proj));  // proyecta los puntos 3D a coordenadas de pantalla
    let html = "";
    if (screenPts[0] && screenPts[1]) {  // solo si ambos puntos son visibles en pantalla ahora mismo
      html += `<svg style="position:absolute;inset:0;width:100%;height:100%;overflow:visible" aria-hidden="true"><line x1="${screenPts[0][0]}" y1="${screenPts[0][1]}" x2="${screenPts[1][0]}" y2="${screenPts[1][1]}" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="4 3"/></svg>`;  // línea punteada entre ambos (decorativa: el valor real ya se anuncia por aria-live en el panel lateral)
    }
    for (const sp of screenPts) if (sp) html += `<div class="measure-dot" style="left:${sp[0]}px;top:${sp[1]}px"></div>`;  // un punto visual por cada punto medido y visible
    if (screenPts[0] && screenPts[1]) {
      const mx = (screenPts[0][0]+screenPts[1][0])/2, my = (screenPts[0][1]+screenPts[1][1])/2;  // punto medio en pantalla, para colocar la etiqueta
      html += `<div class="measure-label" style="left:${mx}px;top:${my}px">${dist3(measurePoints[0], measurePoints[1]).toFixed(1)} mm</div>`;  // distancia real en milímetros
    }
    measureLayerEl.innerHTML = html;  // reemplaza todo el contenido de la capa de un solo golpe
  }
  const measureReadoutRowEl = document.getElementById("measure-readout-row");
  const measureReadoutValueEl = document.getElementById("measure-readout-value");
  const measureClearBtn = document.getElementById("measure-clear-btn");
  // Muestra u oculta la fila de "Distancia" del panel lateral según cuántos
  // puntos de medición hay (0, 1 o 2), y el botón para borrar la medición.
  function updateMeasureReadout() {
    if (measurePoints.length === 2) {                                     // medición completa: hay 2 puntos
      measureReadoutRowEl.style.display = "";                             // muestra la fila de distancia
      measureReadoutValueEl.textContent = dist3(measurePoints[0], measurePoints[1]).toFixed(1) + " mm";  // calcula y muestra la distancia real
      measureClearBtn.style.display = "";                                 // ofrece el botón de borrar
    } else {
      measureReadoutRowEl.style.display = "none";                         // sin 2 puntos, no hay distancia que mostrar
      measureClearBtn.style.display = measurePoints.length > 0 ? "" : "none";  // el botón de borrar solo aparece si hay al menos 1 punto puesto
    }
  }
  document.getElementById("measure-enabled").addEventListener("change", (e) => {
    measureEnabled = e.target.checked;                                     // activa/desactiva la herramienta
    if (!measureEnabled) { measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = ""; }  // al apagarla, borra cualquier medición en curso
  });
  measureClearBtn.addEventListener("click", () => { measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = ""; });  // borra los puntos y su dibujo

  // Ajusta el tamaño real (en píxeles) del buffer del canvas al tamaño
  // que ocupa en pantalla, respetando devicePixelRatio (para verse nítido
  // en pantallas de alta densidad) pero acotado a 2x para no gastar de más
  // en GPUs modestas. Solo reasigna canvas.width/height si de verdad
  // cambió — reasignarlos siempre borraría el framebuffer sin necesidad.
  function resizeGl() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
  }
  // El bucle de render principal: se vuelve a llamar a sí mismo con
  // requestAnimationFrame al final, así que corre una vez por frame
  // mientras la pestaña esté visible. En cada frame: ajusta el tamaño,
  // limpia el canvas, calcula la cámara según el modo activo (órbita
  // normal, o la cámara en primera persona del vuelo interior), y dibuja
  // la malla con el shader/blending que corresponda al modo de vista.
  function render3d() {
    resizeGl();                                                    // ajusta el tamaño del buffer si cambió el tamaño en pantalla
    gl.viewport(0, 0, canvas.width, canvas.height);                 // el área de dibujo cubre todo el canvas
    gl.clearColor(0.039, 0.055, 0.075, 1.0);                        // color de fondo (azul-gris muy oscuro)
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);            // borra tanto el color como la profundidad del frame anterior
    if (currentMesh) {
      // Suaviza el zoom acercándose gradualmente a targetRadius en vez de
      // saltar de golpe (evita que la rueda del mouse se sienta brusca).
      radius += (targetRadius - radius) * 0.12;
      if (autoRotate) theta += 0.0022;
      const c = currentMesh.center;
      let eye, view, proj;
      if (viewMode === "fly" && flyPath) {
        // Cámara en primera persona siguiendo la ruta de vuelo interior.
        updateFlyProgress();
        const fl = flyEyeLook();
        eye = fl.eye;
        view = lookAt(eye, fl.look, [0, 1, 0]);
        proj = perspective(Math.PI / 2.3, canvas.width / Math.max(1, canvas.height), Math.max(0.05, boundingRadius * 0.004), boundingRadius * 20);
      } else {
        // Cámara orbital normal: posición esférica alrededor del centro de
        // la malla, según los ángulos theta/phi que controla el arrastre
        // del mouse (o los botones de vista/auto-rotación).
        eye = [c[0]+radius*Math.sin(phi)*Math.sin(theta), c[1]+radius*Math.cos(phi), c[2]+radius*Math.sin(phi)*Math.cos(theta)];
        view = lookAt(eye, c, [0,1,0]);
        proj = perspective(Math.PI/4.2, canvas.width/Math.max(1,canvas.height), Math.max(0.01,boundingRadius*0.02), boundingRadius*20);
      }
      const clip = clipUniformValues();
      drawAxisGizmo(view);
      updateMeasureOverlay(view, proj);

      // Cada modo de vista dibuja la escena de forma distinta: vuelo
      // interior (cara interna de la malla), MPR (planos + malla fantasma),
      // alambre (solo aristas), o sólido/rayos-X (relleno con iluminación).
      if (viewMode === "fly" && flyPath) {
        drawFlyInterior(view, proj);
      } else if (viewMode === "mpr") {
        drawMprGhostMesh(view, proj);
        drawMprPlanes(view, proj);
        if (showGradientField) drawGradientField(view, proj);
      } else if (viewMode === "wire") {
        // Modo "Alambre": dibuja solo las aristas (GL_LINES) precalculadas
        // por buildEdgeIndices/uploadMesh, sin iluminación.
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
        // heartPulseAmount() devuelve 0 para cualquier órgano que no sea el
        // corazón, así que este uniform solo tiene efecto real ahí.
        gl.uniform1f(uPulse, heartPulseAmount());
        gl.uniform3fv(uClipNormal, clip.normal);
        gl.uniform1f(uClipValue, clip.value);
        gl.uniform1f(uClipEnabled, clipEnabled ? 1.0 : 0.0);
        gl.uniform1f(uAlpha, alphaValue);
        // Con transparencia (rayos-X, o opacidad manual < 100%) hay que
        // mezclar (BLEND) y no escribir al depth buffer (depthMask false),
        // si no los triángulos traseros no se verían nunca a través de los
        // delanteros. Totalmente opaco es más barato y evita artefactos de
        // orden de dibujado, así que usa el camino normal sin blending.
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

      // Reposiciona cada etiqueta HTML de landmark según dónde cae su
      // punto 3D en la pantalla ESTE frame (la cámara pudo haber girado).
      // Se oculta si quedó del lado cortado por el plano de clipping, o si
      // projectToScreen determina que está fuera de vista/detrás de cámara.
      if (labelsVisible && viewMode !== "mpr" && viewMode !== "fly") {
        for (let i = 0; i < currentLandmarks.length; i++) {   // recorre cada landmark del órgano activo
          const el = labelEls[i];                              // su <div> HTML correspondiente
          if (!el) continue;
          const pos = currentLandmarks[i].pos;                 // posición 3D real del landmark
          if (clipEnabled && (pos[0]*clip.normal[0]+pos[1]*clip.normal[1]+pos[2]*clip.normal[2]) > clip.value) {  // mismo producto punto que usa el shader para decidir el corte
            el.style.display = "none"; continue;                // el landmark quedó del lado cortado, se oculta
          }
          const screen = projectToScreen(pos, view, proj);
          if (!screen) { el.style.display = "none"; continue; }
          el.style.display = "";
          el.style.left = screen[0] + "px";
          el.style.top = screen[1] + "px";
        }
      }
    }
    // Encadena el siguiente frame — así el visor se sigue redibujando
    // indefinidamente mientras la página esté abierta.
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
    const expanded = detailsToggleBtn.getAttribute("aria-expanded") === "true";  // estado actual antes de este clic
    detailsToggleBtn.setAttribute("aria-expanded", String(!expanded));           // lo invierte
    technicalDetailsPanelEl.classList.toggle("hidden", expanded);                // muestra el panel si ANTES estaba colapsado
  });
  const topbarStudyNameEl = document.getElementById("topbar-study-name");
  const topbarStudyTypeEl = document.getElementById("topbar-study-type");
  const topbarStatusEl = document.getElementById("topbar-status");
  const topbarStatusTextEl = document.getElementById("topbar-status-text");

  // Actualiza el nombre del estudio, su tipo (CT clínica / micro-CT
  // sincrotrón) y el badge de estado en la barra superior según si la
  // validación real del pipeline pasó o quedó marcada con advertencias.
  function renderTopbar(key, meta, validation) {
    topbarStudyNameEl.textContent = meta.label;       // nombre del órgano en la barra superior
    topbarStudyTypeEl.textContent = meta.study_type;  // "CT clínica" o "Micro-CT sincrotrón (ex-vivo)"
    const dot = topbarStatusEl.querySelector(".badge-dot");  // el puntito de color dentro del badge de estado
    if (validation.passed) {
      dot.className = "badge-dot ok";                        // verde
      topbarStatusTextEl.textContent = "Reconstrucción lista";
    } else {
      dot.className = "badge-dot warn";                      // ámbar
      topbarStatusTextEl.textContent = "Marcado — ver advertencias";
    }
  }

  // Rellena la lista "Anatomy Inspector > Malla" con las métricas reales
  // calculadas por el pipeline de Python (vértices, triángulos, dimensiones,
  // volumen, área de superficie, centroide) — nada de esto se inventa en
  // el navegador, solo se formatea para mostrarlo.
  function renderMetrics(metrics) {
    const dims = [0,1,2].map((i) => metrics.bounding_box_max_mm[i] - metrics.bounding_box_min_mm[i]);  // ancho/alto/profundo real, restando min de max en cada eje
    const rows = [                              // pares [etiqueta, valor ya formateado] a mostrar
      ["Tipo", "Órgano"],
      ["Vértices", fmt(metrics.num_vertices, 0)],
      ["Triángulos", fmt(metrics.num_triangles, 0)],
      ["Dimensiones (mm)", dims.map((v) => fmt(v, 0)).join(" × ")],
      ["Volumen", fmt(metrics.volume_ml, 1) + " mL"],
      ["Área de superficie", fmt(metrics.surface_area_mm2, 0) + " mm²"],
      ["Centroide (mm)", metrics.centroid_mm.map((v) => fmt(v, 0)).join(", ")],
    ];
    metricsPanelEl.innerHTML = rows.map(([k, v]) => `<div class="inspector-row"><span class="k">${k}</span><span class="v">${v}</span></div>`).join("")  // una fila HTML por cada par
      + `<p class="note" style="margin-top:0.5rem">Esta malla puede exportarse desde la sección "Exportar" más abajo. La vista 3D usa esta misma geometría, decimada para una interacción fluida.</p>`;
  }
  // Muestra el resultado real de la validación del pipeline (malla
  // estanca/manifold, volumen dentro de un rango plausible, etc.) como una
  // línea con un punto verde o ámbar.
  function renderValidation(validation) {
    const cls = validation.passed ? "pass" : "fail";
    const label = validation.passed ? "Listo — malla estanca, volumen plausible" : "Marcado — ver advertencias";
    validationPanelEl.innerHTML = `<div class="validation-line"><span class="validation-dot ${cls}" aria-hidden="true"></span><span>${label}</span></div>`;
  }

  // Genera el HTML de la lista de botones de órgano, reutilizado por las 6
  // pestañas que tienen su propia copia de esa lista (3D, cortes, lab,
  // anatomía, sala, trivia) — cada una la regenera con su propia clave
  // "activa" para resaltar el botón correcto en esa pestaña en particular.
  function organListHtml(activeKey) {
    return ORGAN_ORDER.map((key) => {           // un botón por cada uno de los 5 órganos
      const meta = ORGAN_META[key];
      const active = key === activeKey;          // si este es el que debe verse marcado como activo
      return `
        <button class="organ-btn" data-organ="${key}" aria-pressed="${active}">
          <span class="organ-swatch" style="background:${meta.color_hex}" aria-hidden="true"></span>
          <span class="label-group"><span class="name">${meta.label}</span><span class="algo">${meta.algo}</span></span>
          <span class="structure-status"><span class="dot" aria-hidden="true"></span>${active ? "Activo" : "En reposo"}</span>
        </button>`;
    }).join("");  // concatena los 5 botones en un solo string HTML
  }

  let currentOrganKey = ORGAN_ORDER[0];

  // ---------- synthesized heartbeat (Web Audio API, no audio file) ----------
  let audioCtx = null;
  let heartbeatEnabled = false;
  let heartbeatTimer = null;
  let heartbeatCycleStartMs = 0;
  // A small vertex-normal displacement, timed to the exact "lub"/"dub"
  // onsets already scheduled below — this is a visual echo of a sound the
  // organ is already making, not a new claim about real cardiac motion.
  function heartPulseAmount() {
    if (!heartbeatEnabled || currentOrganKey !== "heart") return 0;  // sin sonido activo, o no es el corazón: sin pulso visual
    const t = (performance.now() - heartbeatCycleStartMs) / 1000;    // segundos transcurridos desde que empezó este ciclo de latido
    const bump = (center, width, amp) => amp * Math.exp(-Math.pow((t - center) / width, 2));  // curva de campana (gaussiana) centrada en `center`
    const envelope = bump(0.05, 0.05, 1.0) + bump(0.23, 0.06, 0.6);   // dos golpes: uno fuerte (lub) y uno más suave (dub), como el sonido real
    return envelope * boundingRadius * 0.01;                          // escala el desplazamiento según el tamaño real del órgano
  }
  // Crea el AudioContext solo la primera vez que hace falta (los
  // navegadores no dejan crear audio antes de una interacción del
  // usuario), y lo reanuda si el navegador lo había suspendido.
  function ensureAudioCtx() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();  // crea el contexto una sola vez (usa el prefijo webkit en Safari viejo)
    if (audioCtx.state === "suspended") audioCtx.resume();                                // algunos navegadores lo suspenden hasta la primera interacción
    return audioCtx;
  }
  // Sintetiza un "thump" de latido con un oscilador simple: una onda seno
  // que baja de frecuencia (simulando el golpe grave de un latido real) con
  // una envolvente de volumen que sube y baja rápido (ataque/decaimiento
  // exponencial) — no es un archivo de audio grabado, se genera en vivo.
  function playThump(ctx, time, freq, duration, gainPeak) {
    const osc = ctx.createOscillator();                            // generador de onda
    osc.type = "sine";                                              // onda seno, la más "suave"/grave de todas
    osc.frequency.setValueAtTime(freq, time);                       // frecuencia inicial, en el instante `time`
    osc.frequency.exponentialRampToValueAtTime(Math.max(30, freq * 0.6), time + duration);  // baja de frecuencia hacia el final (efecto "golpe grave")
    const gain = ctx.createGain();                                  // control de volumen
    gain.gain.setValueAtTime(0.0001, time);                         // arranca casi en silencio (0 exacto no funciona con rampas exponenciales)
    gain.gain.exponentialRampToValueAtTime(gainPeak, time + duration * 0.15);  // sube rápido al volumen máximo (ataque)
    gain.gain.exponentialRampToValueAtTime(0.0001, time + duration);          // y vuelve a bajar a silencio (decaimiento)
    osc.connect(gain); gain.connect(ctx.destination);               // cadena de audio: oscilador -> control de volumen -> altavoces
    osc.start(time); osc.stop(time + duration + 0.02);              // programa cuándo empieza y termina exactamente este sonido
  }
  // Programa un ciclo completo de latido ("lub" + "dub", separados 0.18s,
  // imitando el cierre de las válvulas AV y luego las semilunares) y se
  // vuelve a reprogramar a sí mismo con setTimeout al ritmo de ~70 lpm,
  // formando un bucle continuo mientras heartbeatEnabled siga activo.
  function scheduleHeartbeat() {
    if (!heartbeatEnabled || currentOrganKey !== "heart") return;  // no aplica si el sonido está apagado o el órgano no es el corazón
    const ctx = ensureAudioCtx();
    const bpmPeriodMs = 60 / 70 * 1000; // ~70 bpm, adult resting rate
    const now = ctx.currentTime + 0.05;                // pequeño margen para que el audio arranque de forma limpia
    playThump(ctx, now, 90, 0.14, 0.5);        // "lub" — AV valves closing
    playThump(ctx, now + 0.18, 70, 0.16, 0.32); // "dub" — semilunar valves closing
    heartbeatCycleStartMs = performance.now() + 50; // matches the ctx.currentTime+0.05 offset above
    heartbeatTimer = setTimeout(scheduleHeartbeat, bpmPeriodMs);  // se reprograma a sí mismo para el siguiente latido
  }
  function stopHeartbeat() {
    if (heartbeatTimer) { clearTimeout(heartbeatTimer); heartbeatTimer = null; }  // cancela el próximo latido programado, si había uno
  }
  const heartbeatToggleEl = document.getElementById("heartbeat-toggle");  // casilla "Sonido del latido"
  heartbeatToggleEl.addEventListener("change", () => {
    heartbeatEnabled = heartbeatToggleEl.checked;
    stopHeartbeat();                                    // limpia cualquier ciclo pendiente antes de decidir qué hacer
    if (heartbeatEnabled) scheduleHeartbeat();           // solo arranca el bucle si se acaba de activar
  });

  // Jerarquía visual / ley de Hick para la pestaña Anatomía: el HTML de
  // ORGAN_META["anatomy"] es una secuencia plana de <h3>título</h3> seguido
  // de sus <p> (ver build_interactive_artifact.py, construcción de
  // ORGAN_META). En vez de mostrar los 6-9 títulos y todos sus párrafos de
  // golpe (una pared de texto), esta función recorre esos nodos ya
  // insertados y agrupa cada <h3> con los nodos que le siguen, hasta el
  // próximo <h3>, dentro de un <details>/<summary> — así el usuario ve
  // primero la lista de títulos (el resumen real del contenido) y abre
  // solo la sección que le interesa. No se quita ni se resume ningún
  // dato real: todo el texto sigue ahí, solo se reorganiza la exhibición.
  function wrapAnatomySections(container) {
    const nodes = Array.from(container.childNodes);  // copia estática: container se va a vaciar/reconstruir durante el recorrido
    const frag = document.createDocumentFragment();
    let body = null;      // <div class="details-body"> de la sección <details> actual
    let sectionIndex = -1;
    for (const node of nodes) {
      if (node.nodeType === 1 && node.tagName === "H3") {
        const details = document.createElement("details");
        details.className = "anatomy-section";
        sectionIndex++;
        if (sectionIndex === 0) details.open = true;  // la primera sección empieza abierta: da el resumen inmediato sin ocultar todo
        const summary = document.createElement("summary");
        summary.innerHTML = node.innerHTML;  // el título real de la sección (viene de datos reales, no se inventa)
        const chevron = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        chevron.setAttribute("class", "chevron");
        chevron.setAttribute("viewBox", "0 0 24 24");
        chevron.setAttribute("fill", "none");
        chevron.setAttribute("stroke", "currentColor");
        chevron.setAttribute("stroke-width", "2");
        chevron.setAttribute("stroke-linecap", "round");
        chevron.setAttribute("stroke-linejoin", "round");
        chevron.setAttribute("aria-hidden", "true");
        chevron.innerHTML = '<path d="M6 9l6 6 6-6"/>';
        summary.appendChild(chevron);
        body = document.createElement("div");
        body.className = "details-body";
        details.appendChild(summary);
        details.appendChild(body);
        frag.appendChild(details);
      } else if (body) {
        body.appendChild(node);  // appendChild sobre un nodo que aún cuelga de `container` lo mueve, no lo copia
      } else {
        frag.appendChild(node);  // caso defensivo: contenido antes del primer <h3> (no ocurre con los datos actuales)
      }
    }
    container.innerHTML = "";
    container.appendChild(frag);
  }

  // La función "cambiar de órgano": se llama al hacer clic en cualquier
  // botón de órgano en cualquier pestaña. Actualiza TODO lo que depende
  // del órgano activo — la malla 3D, la cámara, los landmarks, los
  // paneles de métricas/validación, el texto de anatomía, el volumen de
  // cortes, el laboratorio de segmentación y los MPR/vuelo si ya estaban
  // activos — para que las 6 pestañas queden sincronizadas con el mismo
  // órgano sin importar desde cuál se hizo el cambio.
  function selectOrgan(key) {
    currentOrganKey = key;                              // desde ahora, "el órgano activo" es este
    stopHeartbeat();                                     // cancela cualquier latido programado del órgano anterior
    if (heartbeatEnabled && key === "heart") scheduleHeartbeat();  // si el sonido estaba activo y el nuevo órgano ES el corazón, lo reinicia
    const data = VIEWER_DATA[key];                       // datos numéricos reales (malla/cortes/métricas) de este órgano
    const meta = ORGAN_META[key];                        // metadata de texto de este órgano
    renderTopbar(key, meta, data.validation);
    document.getElementById("orientation-note").textContent = meta.orientation_note;  // texto de advertencia de orientación específico de este órgano
    measurePoints = []; updateMeasureReadout(); measureLayerEl.innerHTML = "";  // una medición del órgano anterior no tiene sentido en el nuevo

    const mesh = decodeMesh(data.mesh, key);            // decodifica y rota (si aplica) la malla de este órgano
    currentMesh = mesh;
    currentColor = hexToRgb01(meta.color_hex);           // color del material 3D
    theta = meta.initial_theta; phi = meta.initial_phi;  // ángulo de cámara curado para este órgano en particular
    frameCamera(mesh);                                    // recalcula radio/límites de la nueva malla
    uploadMesh(mesh);                                     // sube la nueva malla a los buffers de GPU
    currentLandmarks = computeLandmarksFor(key, mesh);    // recalcula los landmarks anatómicos de este órgano
    rebuildLabelEls();                                     // reconstruye los <div> de etiqueta correspondientes
    autoRotate = !reduceMotion;                            // reanuda el giro automático al cambiar de órgano

    renderMetrics(data.metrics);
    renderValidation(data.validation);
    sourceNoteEl.textContent = meta.source_note;
    caveatNoteEl.textContent = meta.caveat;

    // Pestaña Anatomía: título, texto, diagrama SVG y datos curiosos, todo
    // reemplazado de una vez con el contenido de este órgano.
    document.getElementById("anatomy-title").textContent = meta.label;
    document.getElementById("anatomy-algo").textContent = meta.algo;
    const anatomyTextEl = document.getElementById("anatomy-text");
    anatomyTextEl.innerHTML = meta.anatomy;
    wrapAnatomySections(anatomyTextEl);  // convierte los <h3>/<p> planos en un acordeón escaneable (ver CSS .anatomy-detail summary)
    document.getElementById("anatomy-source").textContent = meta.source_note;
    document.getElementById("anatomy-caveat").textContent = meta.caveat;
    document.getElementById("anatomy-diagram").innerHTML = meta.diagram_svg;
    document.getElementById("anatomy-facts").innerHTML = meta.fun_facts.map((f) => `<li>${f}</li>`).join("");  // una viñeta <li> por cada dato curioso

    document.getElementById("slice-source-note").textContent =
      "Cortes del volumen preprocesado real que este pipeline realmente segmentó para " + meta.label.toLowerCase() +
      " (mismos datos de origen que la reconstrucción 3D), submuestreado para un archivo más ligero.";

    // Sincroniza el botón "activo" en las 4 listas de órgano que existen
    // fuera de la trivia (esa se maneja aparte, con su propio estado).
    for (const list of [document.getElementById("organ-list"), document.getElementById("organ-list-slices"), document.getElementById("organ-list-anatomy"), document.getElementById("organ-list-lab")]) {
      for (const btn of list.querySelectorAll(".organ-btn")) {
        btn.setAttribute("aria-pressed", String(btn.dataset.organ === key));  // solo el botón de este órgano queda marcado
      }
    }

    loadSliceVolume(data.slices);                          // decodifica el cubo de voxeles de este órgano
    if (!panelSlices.classList.contains("hidden")) { resizeSliceCanvasDisplay(); drawSlice(); }  // si la pestaña de cortes ya está visible, la repinta ya mismo
    labSelectOrgan(key);                                    // prepara el laboratorio de segmentación para este órgano
    if (!panelLab.classList.contains("hidden")) labRender();  // si el laboratorio ya está visible, lo repinta ya mismo

    // Reinicia los 3 planos MPR al centro del volumen (no tendría sentido
    // conservar la posición de los planos del órgano anterior).
    mprAxialFrac = 0.5; mprCoronalFrac = 0.5; mprSagittalFrac = 0.5;
    mprAxialSlider.value = "50"; mprCoronalSlider.value = "50"; mprSagittalSlider.value = "50";
    if (viewMode === "mpr") { rebuildMprPlanes(); if (showGradientField) computeGradientField(); }  // si ya se estaba en modo MPR, lo recalcula con el nuevo órgano

    flyPath = null; // recomputed lazily next time "Vuelo interior" is entered, or right now if already active
    if (viewMode === "fly") computeFlyPath();  // si ya se estaba en modo vuelo, calcula la nueva ruta de inmediato
  }

  // Rellena las 4 listas de órgano (fuera de trivia) con el primer órgano
  // marcado como activo, y les conecta el listener de clic a cada botón.
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

  let windowLevel = 128, windowWidth = 255;  // valores de ventana por defecto (rango completo de 0-255, centrado)
  const PRESETS = [                            // preajustes típicos de un visor radiológico
    {label: "Bajo", level: 64, width: 128},
    {label: "Medio", level: 128, width: 255},
    {label: "Alto contraste", level: 128, width: 60},
    {label: "Rango completo", level: 128, width: 510},
  ];
  presetRowEl.innerHTML = PRESETS.map((p, i) => `<button class="preset-btn" data-i="${i}" aria-pressed="${i===1}">${p.label}</button>`).join("");  // "Medio" (índice 1) empieza marcado como activo
  for (const btn of presetRowEl.querySelectorAll(".preset-btn")) {
    btn.addEventListener("click", () => {
      const p = PRESETS[Number(btn.dataset.i)];                              // preajuste correspondiente a este botón
      windowLevel = p.level; windowWidth = p.width;                          // aplica sus valores
      levelSlider.value = windowLevel; widthSlider.value = windowWidth;      // sincroniza los sliders manuales
      levelValueEl.textContent = windowLevel; widthValueEl.textContent = windowWidth;  // y sus etiquetas numéricas
      for (const b of presetRowEl.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", String(b === btn));  // marca solo este preset como activo
      drawSlice();  // repinta el corte con la nueva ventana
    });
  }
  levelSlider.value = windowLevel; widthSlider.value = windowWidth;                    // estado inicial de los sliders
  levelValueEl.textContent = windowLevel; widthValueEl.textContent = windowWidth;      // y de sus etiquetas
  // Cuando el usuario mueve un slider de nivel/ancho a mano, ningún preset
  // sigue aplicando exactamente — se les quita el estado "presionado".
  function clearPresets() { for (const b of presetRowEl.querySelectorAll(".preset-btn")) b.setAttribute("aria-pressed", "false"); }
  levelSlider.addEventListener("input", () => { windowLevel = Number(levelSlider.value); levelValueEl.textContent = windowLevel; clearPresets(); drawSlice(); });  // nivel manual
  widthSlider.addEventListener("input", () => { windowWidth = Math.max(1, Number(widthSlider.value)); widthValueEl.textContent = windowWidth; clearPresets(); drawSlice(); });  // ancho manual (mínimo 1, para no dividir entre 0)
  sliceSlider.addEventListener("input", drawSlice);  // cambia de corte (Z) y repinta

  let imgData = null;

  // Decodifica el cubo de voxeles submuestreado (mismos datos de origen
  // que la reconstrucción 3D, en menor resolución para pesar menos) y
  // guarda su forma, espaciado real (mm por voxel) y origen — todo lo
  // necesario para mapear índices de voxel a milímetros reales en MPR,
  // el campo de gradiente y el vuelo interior.
  function loadSliceVolume(slicesData) {
    sv = {
      voxels: new Uint8Array(decodeB64(slicesData.voxels_b64)),  // los valores de intensidad, ya en 0-255
      shape: slicesData.shape_zyx,       // [profundidad, alto, ancho] en voxeles
      spacing: slicesData.spacing_xyz,   // tamaño real (mm) de un voxel en cada eje
      origin: slicesData.origin_xyz,     // coordenada real (mm) del voxel (0,0,0)
      valueMin: slicesData.value_min,    // valor de intensidad original mínimo (antes de cuantizar a 0-255)
      valueMax: slicesData.value_max,    // valor de intensidad original máximo
    };
    const [snz, sny, snx] = sv.shape;
    sliceSlider.max = String(snz - 1);                    // el slider de corte va de 0 al último índice Z
    sliceSlider.value = String(Math.floor(snz / 2));        // arranca mostrando el corte de en medio
    sliceCanvas.width = snx; sliceCanvas.height = sny;      // el canvas coincide en tamaño real con el corte
    imgData = sliceCtx.createImageData(snx, sny);           // buffer de píxeles reutilizado por drawSlice()
    renderTechnicalDetails();                                // actualiza el panel de detalles técnicos con la nueva forma
  }

  const technicalDetailsRowsEl = document.getElementById("technical-details-rows");
  // Rellena el desplegable "Technical details" del inspector con datos del
  // cubo de voxeles cargado (dimensiones, espaciado real, tipo de estudio).
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

  // Dibuja en el canvas 2D de la pestaña "Cortes CT" el corte axial actual
  // (según el slider "Corte"), aplicando el ventaneo nivel/ancho vigente —
  // la misma lógica de windowedTexel pero escrita en línea para este canvas.
  function drawSlice() {
    if (!sv) return;
    const [snz, sny, snx] = sv.shape;
    const z = Math.min(Number(sliceSlider.value), snz - 1);
    const zMm = (sv.origin[2] + z * sv.spacing[2]).toFixed(1);   // posición real en mm de este corte
    sliceReadout.textContent = `${z+1} / ${snz} · z=${zMm}mm`;    // "3 / 120 · z=45.2mm" por ejemplo
    const off = z * sny * snx;                                    // desplazamiento al inicio de este corte
    const lo = windowLevel - windowWidth/2, scale = 255/windowWidth;  // mismos parámetros de ventaneo que windowedTexel
    const data = imgData.data;
    for (let i = 0; i < sny*snx; i++) {          // recorre cada píxel del corte
      let val = (sv.voxels[off+i] - lo) * scale;
      val = val < 0 ? 0 : val > 255 ? 255 : val;  // recorta al rango 0-255
      const o = i*4; data[o]=val; data[o+1]=val; data[o+2]=val; data[o+3]=255;  // gris opaco
    }
    sliceCtx.putImageData(imgData, 0, 0);  // vuelca todos los píxeles calculados al canvas de una sola vez
  }
  // Ajusta el tamaño CSS (no el número de píxeles reales) del canvas de
  // corte para que quepa en el espacio disponible del stage conservando su
  // relación de aspecto original (evita estirar/deformar la imagen).
  function resizeSliceCanvasDisplay() {
    if (!sv) return;
    const [, sny, snx] = sv.shape;                                     // solo interesan alto y ancho aquí
    const stage = sliceCanvas.parentElement;                            // el contenedor disponible en pantalla
    const availW = stage.clientWidth * 0.92, availH = stage.clientHeight * 0.92;  // deja un pequeño margen (8%)
    const aspect = snx / sny;                                            // relación de aspecto real del corte
    let w = availW, h = w / aspect;                                      // intenta usar todo el ancho disponible
    if (h > availH) { h = availH; w = h * aspect; }                      // si no entra en alto, ajusta por el alto en su lugar
    sliceCanvas.style.width = Math.round(w) + "px";
    sliceCanvas.style.height = Math.round(h) + "px";
  }
  window.addEventListener("resize", () => { if (!panelSlices.classList.contains("hidden")) resizeSliceCanvasDisplay(); });  // solo si la pestaña de cortes está visible
  // Al mover el mouse sobre el corte, calcula a qué voxel corresponde ese
  // píxel de pantalla y muestra su intensidad cruda y su valor real
  // aproximado (deshaciendo la cuantización a 0-255).
  sliceCanvas.addEventListener("mousemove", (e) => {
    if (!sv) return;
    const [, sny, snx] = sv.shape;
    const rect = sliceCanvas.getBoundingClientRect();     // posición y tamaño real del canvas en pantalla
    const px = Math.floor((e.clientX-rect.left)/rect.width*snx), py = Math.floor((e.clientY-rect.top)/rect.height*sny);  // convierte píxeles de pantalla a índice de voxel
    if (px<0||py<0||px>=snx||py>=sny) return;              // el mouse quedó fuera del área real del corte
    const z = Math.min(Number(sliceSlider.value), sv.shape[0]-1);  // corte Z actualmente mostrado
    const raw = sv.voxels[z*sny*snx+py*snx+px];             // intensidad cruda (0-255) en ese voxel exacto
    const orig = sv.valueMin + (raw/255)*(sv.valueMax - sv.valueMin);  // valor real aproximado, deshaciendo la cuantización
    huReadoutEl.textContent = `(${px}, ${py})  ${raw}/255  ≈${orig.toFixed(0)}`;
  });
  sliceCanvas.addEventListener("mouseleave", () => { huReadoutEl.textContent = "—"; });  // limpia el lector al sacar el mouse

  /* =========================================================
     Laboratorio: motor de morfología 2D + línea de tiempo + modo libre
     ========================================================= */
  // Umbral binario simple sobre una imagen en escala de grises: 1 (tejido)
  // donde el valor cae por debajo (`below`=true) o por encima del umbral
  // `t`, 0 en el resto — la misma idea que el umbral de intensidad que usa
  // la segmentación 3D real, pero aplicada aquí a un solo corte 2D.
  function labThreshold(gray, w, h, t, below) {
    const mask = new Uint8Array(w * h);       // 1 = tejido, 0 = fondo, uno por píxel
    for (let i = 0; i < w * h; i++) mask[i] = (below ? gray[i] < t : gray[i] > t) ? 1 : 0;  // aplica el umbral según el sentido correcto para este órgano
    return mask;
  }
  // Erosión morfológica: un píxel sobrevive (queda en 1) solo si TODOS sus
  // 8 vecinos (incluido él mismo) también están en la máscara — "encoge"
  // la máscara y elimina ruido de un solo píxel.
  function labErode(mask, w, h) {
    const out = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {  // recorre cada píxel de salida
      let all = 1;                                              // asume que sobrevive, hasta que se demuestre lo contrario
      for (let dy = -1; dy <= 1 && all; dy++) for (let dx = -1; dx <= 1; dx++) {  // revisa los 9 píxeles del vecindario 3x3 (incluido el propio)
        const xx = x + dx, yy = y + dy;
        if (xx < 0 || yy < 0 || xx >= w || yy >= h || !mask[yy * w + xx]) { all = 0; break; }  // fuera de imagen o no es tejido: falla la erosión aquí
      }
      out[y * w + x] = all;
    }
    return out;
  }
  // Dilatación morfológica: la operación opuesta a la erosión — un píxel
  // pasa a 1 si ALGUNO de sus 8 vecinos está en la máscara. "Engorda" la
  // máscara y rellena pequeños huecos.
  function labDilate(mask, w, h) {
    const out = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {   // recorre cada píxel de salida
      let any = 0;                                               // asume que NO pasa a tejido, hasta encontrar un vecino que sí lo sea
      for (let dy = -1; dy <= 1 && !any; dy++) for (let dx = -1; dx <= 1; dx++) {  // revisa el vecindario 3x3
        const xx = x + dx, yy = y + dy;
        if (xx >= 0 && yy >= 0 && xx < w && yy < h && mask[yy * w + xx]) { any = 1; break; }  // encontró un vecino de tejido dentro de la imagen
      }
      out[y * w + x] = any;
    }
    return out;
  }
  // Apertura (erosionar y luego dilatar): quita ruido pequeño sin cambiar
  // mucho el tamaño general de la forma — el paso de "limpieza" del pipeline.
  function labOpen(mask, w, h) { return labDilate(labErode(mask, w, h), w, h); }
  // Cierre (dilatar y luego erosionar): rellena huecos pequeños sin
  // cambiar mucho el contorno exterior.
  function labClose(mask, w, h) { return labErode(labDilate(mask, w, h), w, h); }
  // Encuentra la componente conexa más grande de la máscara mediante una
  // búsqueda en profundidad (flood fill) con una pila explícita, y
  // descarta todo lo demás — el paso "quedarse con la forma más grande"
  // que el pipeline real aplica en 3D, aquí reproducido en 2D sobre un corte.
  function labLargestComponent(mask, w, h) {
    const labels = new Int32Array(w * h).fill(-1);  // -1 = todavía sin visitar; en otro caso, a qué componente pertenece
    let bestLabel = -1, bestSize = 0, label = 0;     // la componente más grande encontrada hasta ahora, y el próximo número a asignar
    const stack = [];                                 // pila explícita para el flood fill (evita recursión profunda)
    for (let start = 0; start < w * h; start++) {     // intenta arrancar un flood fill desde cada píxel
      if (!mask[start] || labels[start] !== -1) continue;  // no es tejido, o ya pertenece a una componente visitada
      let size = 0;                                    // tamaño de esta nueva componente
      stack.push(start); labels[start] = label;        // arranca el flood fill desde aquí
      while (stack.length) {
        const idx = stack.pop();
        size++;
        const x = idx % w, y = (idx / w) | 0;          // recupera coordenadas 2D del índice plano
        const nbrs = [[x-1,y],[x+1,y],[x,y-1],[x,y+1]]; // vecindario de 4 (arriba/abajo/izq/der), no diagonal
        for (const [nx, ny] of nbrs) {
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;  // fuera de la imagen
          const nidx = ny * w + nx;
          if (mask[nidx] && labels[nidx] === -1) { labels[nidx] = label; stack.push(nidx); }  // vecino de tejido sin visitar: se une a esta componente
        }
      }
      if (size > bestSize) { bestSize = size; bestLabel = label; }  // esta componente es la más grande vista hasta ahora
      label++;                                          // el siguiente flood fill usará un número de componente nuevo
    }
    const out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) out[i] = labels[i] === bestLabel ? 1 : 0;  // solo sobrevive la componente ganadora
    return out;
  }
  // Rellena huecos interiores de la máscara: primero identifica el "fondo"
  // real haciendo flood fill desde los bordes de la imagen (todo lo que se
  // puede alcanzar desde afuera sin cruzar la máscara sigue siendo fondo);
  // cualquier píxel de fondo que NO se alcanzó desde el borde es un hueco
  // interior rodeado de máscara, y se convierte en parte de la máscara.
  function labFillHoles(mask, w, h) {
    const bg = new Uint8Array(w * h);                   // 1 = confirmado como fondo real (alcanzable desde el borde)
    const stack = [];
    function seed(idx) { if (!mask[idx] && !bg[idx]) { bg[idx] = 1; stack.push(idx); } }  // marca un píxel de fondo y lo agrega a explorar, si no se había visto
    for (let x = 0; x < w; x++) { seed(x); seed((h-1)*w + x); }   // siembra toda la fila superior e inferior
    for (let y = 0; y < h; y++) { seed(y*w); seed(y*w + w - 1); } // siembra toda la columna izquierda y derecha
    while (stack.length) {                                // flood fill del fondo real, partiendo de los bordes
      const idx = stack.pop();
      const x = idx % w, y = (idx / w) | 0;
      const nbrs = [[x-1,y],[x+1,y],[x,y-1],[x,y+1]];
      for (const [nx, ny] of nbrs) {
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        seed(ny * w + nx);
      }
    }
    const out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) out[i] = (mask[i] || !bg[i]) ? 1 : 0;  // tejido real, O fondo que nunca se alcanzó desde afuera (=hueco interior)
    return out;
  }
  // El contorno de la máscara: los píxeles que están en la máscara pero
  // que la erosión eliminaría — es decir, la capa más externa de 1 píxel.
  function labMaskBoundary(mask, w, h) {
    const eroded = labErode(mask, w, h);          // la máscara "encogida" 1 píxel
    const out = new Uint8Array(w * h);
    for (let i = 0; i < w * h; i++) out[i] = mask[i] && !eroded[i] ? 1 : 0;  // estaba en la máscara original pero NO en la encogida
    return out;
  }

  // Render helpers: paint a grayscale array, optionally with a binary mask
  // washed in the accent color and/or a bright contour outline.
  function labPaintImageData(imgData, gray, w, h, mask, contourOnly) {
    const data = imgData.data;
    for (let i = 0; i < w * h; i++) {   // recorre cada píxel
      const g = gray[i];                 // valor de gris original de este píxel
      const o = i * 4;                   // desplazamiento en el buffer RGBA
      if (mask) {
        if (contourOnly) {               // etapa final: solo el contorno se pinta de color, el resto queda en gris
          if (mask[i]) { data[o]=70; data[o+1]=201; data[o+2]=194; data[o+3]=255; }  // color de acento (verde azulado) en el contorno
          else { data[o]=g; data[o+1]=g; data[o+2]=g; data[o+3]=255; }               // gris normal fuera del contorno
        } else {
          // translucent wash over the grayscale background for pure mask stages
          const inside = mask[i];         // si este píxel cayó dentro de la máscara en esta etapa
          data[o] = inside ? Math.round(g*0.35 + 70*0.65) : g;    // mezcla 35% del gris original con 65% del color de acento
          data[o+1] = inside ? Math.round(g*0.35 + 201*0.65) : g;
          data[o+2] = inside ? Math.round(g*0.35 + 194*0.65) : g;
          data[o+3] = 255;
        }
      } else {
        data[o]=g; data[o+1]=g; data[o+2]=g; data[o+3]=255;  // sin máscara (etapa 0): imagen en escala de grises pura
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
    const midZ = Math.floor(nz / 2);   // usa el corte de en medio como imagen de trabajo del laboratorio
    // sv.voxels was just decoded by loadSliceVolume() for the "Cortes CT"
    // tab (called right before this in selectOrgan) — reuse it instead of
    // decoding the same base64 payload a second time.
    labGray = sv.voxels.subarray(midZ * ny * nx, (midZ + 1) * ny * nx);  // vista (sin copiar) de solo ese corte dentro del array grande
    labW = nx; labH = ny;
    labThresholdNative = meta.threshold_native;    // umbral real (en unidades nativas) que usa el pipeline para este órgano
    labThresholdBelow = meta.threshold_below;      // si "tejido" es lo que está por debajo o por encima del umbral
    const frac = (labThresholdNative - slices.value_min) / (slices.value_max - slices.value_min);  // ese umbral, como fracción 0..1
    labQuantThreshold = Math.max(0, Math.min(255, Math.round(frac * 255)));  // esa fracción, en la escala 0-255 de la imagen
    labStage = 0;                                    // reinicia la línea de tiempo al primer paso
    labThresholdSlider.value = String(labQuantThreshold);       // el slider del modo libre arranca en el valor real
    labThresholdValueEl.textContent = String(labQuantThreshold);
    labThresholdRealEl.textContent = "Valor real usado por el pipeline: " + meta.threshold_label;
    labOpeningToggle.checked = true;                 // ambos pasos de limpieza empiezan activados por defecto
    labCleanupToggle.checked = true;

    // Real histogram over the whole 3D volume (every voxel this pipeline
    // actually looked at), not just the one slice shown above — computed
    // once per organ since it never changes as the threshold slider moves.
    const hist = new Uint32Array(256);               // un contador por cada posible valor de intensidad (0-255)
    for (let i = 0; i < sv.voxels.length; i++) hist[sv.voxels[i]]++;  // cuenta cuántos voxeles de TODO el volumen tienen cada valor
    labHistogram = hist;
  }

  // Dibuja el histograma real de intensidades de TODO el volumen (no solo
  // el corte visible) en escala logarítmica en Y (para que los valores
  // poco frecuentes no desaparezcan aplastados por los muy frecuentes),
  // coloreando en el color de acento la mitad que el umbral actual
  // clasifica como "tejido", y una línea vertical marcando ese umbral.
  function drawLabHistogram() {
    if (!labHistogram) return;                                        // sin datos todavía
    const w = labHistogramCanvas.width, h = labHistogramCanvas.height;
    labHistogramCtx.clearRect(0, 0, w, h);                             // limpia el frame anterior
    const logs = new Float32Array(256);                                // versión logarítmica de cada conteo, para la escala vertical
    let maxLog = 0;                                                     // el mayor valor logarítmico, para normalizar las alturas de barra
    for (let i = 0; i < 256; i++) { logs[i] = Math.log1p(labHistogram[i]); if (logs[i] > maxLog) maxLog = logs[i]; }  // log1p evita log(0)
    const barW = w / 256;                                               // ancho de cada barra (256 valores posibles)
    const rootStyle = getComputedStyle(document.documentElement);       // lee las variables CSS actuales (cambian con el tema claro/oscuro)
    const dimColor = rootStyle.getPropertyValue("--text-faint").trim() || "#888";
    const accentColor = rootStyle.getPropertyValue("--accent").trim() || "#a5434b";
    let tissueCount = 0, total = 0;                                     // para calcular el porcentaje mostrado al final
    for (let i = 0; i < 256; i++) {                                     // dibuja una barra por cada valor de intensidad
      const isTissueSide = labThresholdBelow ? i < labQuantThreshold : i > labQuantThreshold;  // ¿este valor cae del lado "tejido" del umbral actual?
      const bh = maxLog > 0 ? (logs[i] / maxLog) * (h - 3) : 0;         // altura de la barra, proporcional a su valor logarítmico
      labHistogramCtx.fillStyle = isTissueSide ? accentColor : dimColor; // color de acento si es tejido, gris apagado si no
      labHistogramCtx.globalAlpha = isTissueSide ? 0.85 : 0.5;
      labHistogramCtx.fillRect(i * barW, h - bh, Math.max(1, barW), bh); // dibuja la barra desde abajo hacia arriba
      total += labHistogram[i];
      if (isTissueSide) tissueCount += labHistogram[i];
    }
    labHistogramCtx.globalAlpha = 1;
    const x = labQuantThreshold * barW;               // posición horizontal exacta del umbral actual
    labHistogramCtx.strokeStyle = accentColor;
    labHistogramCtx.lineWidth = 2;
    labHistogramCtx.beginPath(); labHistogramCtx.moveTo(x, 0); labHistogramCtx.lineTo(x, h); labHistogramCtx.stroke();  // línea vertical marcando el umbral
    const pct = total > 0 ? (100 * tissueCount / total).toFixed(1) : "0";  // porcentaje real de voxeles clasificados como tejido
    labHistogramNoteEl.textContent = `${pct}% de los vóxeles del volumen caen del lado "tejido" con este umbral (escala vertical logarítmica).`;
  }

  // Recalcula la máscara para una de las 5 etapas de la línea de tiempo,
  // aplicando en cascada cada paso sobre el resultado del anterior: 0=nada,
  // 1=umbral, 2=+apertura, 3=+componente más grande, 4=+cierre y relleno
  // de huecos (el resultado final, lo que en 3D se convierte en la malla).
  function labComputeStageMask(stageIdx) {
    const t = labThreshold(labGray, labW, labH, labQuantThreshold, labThresholdBelow);  // etapa 1: umbral crudo
    if (stageIdx <= 0) return null;                          // etapa 0: sin máscara, solo la imagen original
    const opened = labOpen(t, labW, labH);                    // etapa 2: quita ruido pequeño
    if (stageIdx === 1) return t;
    if (stageIdx === 2) return opened;
    const largest = labLargestComponent(opened, labW, labH);  // etapa 3: se queda solo con la forma más grande
    if (stageIdx === 3) return largest;
    return labFillHoles(labClose(largest, labW, labH), labW, labH);  // etapa 4: cierra y rellena huecos internos (resultado final)
  }

  const LAB_STAGES = [
    {title: "0. Corte original", text: "El corte 2D real que este pipeline segmentó — sin ningún procesamiento todavía."},
    {title: "1. Umbral de intensidad", text: "Se marca como \"posible tejido\" cada píxel que cruza el umbral real de este órgano. Nota el ruido: puntos sueltos que no son tejido de verdad."},
    {title: "2. Apertura morfológica", text: "Erosiona y luego dilata la máscara — así desaparece el ruido de un solo píxel sin perder la forma principal."},
    {title: "3. Componente más grande", text: "De todas las regiones que sobrevivieron, se conserva solo la más grande — el resto era ruido residual o artefactos."},
    {title: "4. Cierre + relleno de huecos (resultado final)", text: "Se cierran pequeños huecos internos y se traza el contorno final — esta silueta es, en esencia, lo que se convierte en la malla 3D."},
  ];

  // Dibuja la etapa actual de la línea de tiempo: en la última etapa
  // pinta solo el contorno final (labMaskBoundary) sobre la imagen en
  // gris; en las etapas intermedias, un lavado de color translúcido sobre
  // toda el área de la máscara. También actualiza el texto explicativo y
  // los puntitos de progreso.
  function labRenderTimeline() {
    if (!labGray) return;                              // sin corte de trabajo cargado
    labCanvas.width = labW; labCanvas.height = labH;
    const imgData = labCtx.createImageData(labW, labH);
    const mask = labComputeStageMask(labStage);         // máscara correspondiente a la etapa actual
    const isFinal = labStage === LAB_STAGES.length - 1; // si es la última etapa (resultado final)
    labPaintImageData(imgData, labGray, labW, labH, mask && isFinal ? labMaskBoundary(mask, labW, labH) : mask, isFinal);  // en la última etapa pinta solo el contorno; antes, el lavado de color
    labCtx.putImageData(imgData, 0, 0);
    labStageTitleEl.textContent = LAB_STAGES[labStage].title;   // título explicativo de esta etapa
    labStageTextEl.textContent = LAB_STAGES[labStage].text;     // texto explicativo de esta etapa
    labPrevBtn.disabled = labStage === 0;                        // no se puede retroceder antes de la primera etapa
    labNextBtn.disabled = labStage === LAB_STAGES.length - 1;    // no se puede avanzar después de la última
    labDotsEl.innerHTML = LAB_STAGES.map((_, i) => `<span data-active="${i === labStage}"></span>`).join("");  // un punto de progreso por etapa
  }

  // Modo libre: aplica el pipeline completo (umbral -> apertura opcional
  // -> componente más grande + cierre + relleno opcional) con el umbral y
  // los toggles que el usuario elija en vivo, y le avisa si su umbral
  // quedó muy cerca (±8 en la escala 0-255) del que el pipeline real usó.
  function labRenderFree() {
    if (!labGray) return;
    labFreeCanvas.width = labW; labFreeCanvas.height = labH;
    labQuantThreshold = Number(labThresholdSlider.value);         // umbral elegido a mano por el usuario
    labThresholdValueEl.textContent = String(labQuantThreshold);
    let mask = labThreshold(labGray, labW, labH, labQuantThreshold, labThresholdBelow);  // paso 1 siempre se aplica
    if (labOpeningToggle.checked) mask = labOpen(mask, labW, labH);                       // paso 2 solo si el usuario lo activó
    if (labCleanupToggle.checked) mask = labFillHoles(labClose(labLargestComponent(mask, labW, labH), labW, labH), labW, labH);  // pasos 3+4 solo si el usuario los activó
    const imgData = labFreeCtx.createImageData(labW, labH);
    labPaintImageData(imgData, labGray, labW, labH, mask, false);  // siempre con lavado de color, nunca solo contorno (modo libre no tiene "etapa final" fija)
    labFreeCtx.putImageData(imgData, 0, 0);

    // Recalcula el umbral OFICIAL (el que de verdad usa el pipeline) en la
    // misma escala 0-255, para poder comparar contra lo que eligió el usuario.
    const officialQuant = Math.max(0, Math.min(255, Math.round(
      ((labThresholdNative - VIEWER_DATA[currentOrganKey].slices.value_min) /
       (VIEWER_DATA[currentOrganKey].slices.value_max - VIEWER_DATA[currentOrganKey].slices.value_min)) * 255
    )));
    labFreeMatchEl.textContent = Math.abs(labQuantThreshold - officialQuant) <= 8   // tolerancia de ±8 sobre 255
      ? "¡Muy cerca del umbral real que usa el pipeline!" : "";
    drawLabHistogram();  // repinta el histograma para reflejar el nuevo umbral
  }

  // Redirige al renderizado del subtab activo (línea de tiempo o libre).
  function labRender() {
    if (labMode === "timeline") labRenderTimeline(); else labRenderFree();
  }

  for (const btn of labSubtabButtons) {         // botones "Línea de tiempo" / "Modo libre"
    btn.addEventListener("click", () => {
      labMode = btn.dataset.labMode;
      for (const b of labSubtabButtons) b.setAttribute("aria-pressed", String(b === btn));  // marca solo el subtab elegido
      labTimelineViewEl.classList.toggle("hidden", labMode !== "timeline");   // muestra la vista de línea de tiempo solo si corresponde
      labFreeViewEl.classList.toggle("hidden", labMode !== "free");           // muestra la vista libre solo si corresponde
      labRender();
    });
  }
  labPrevBtn.addEventListener("click", () => { labStage = Math.max(0, labStage - 1); labRenderTimeline(); });  // retrocede una etapa (sin bajar de 0)
  labNextBtn.addEventListener("click", () => { labStage = Math.min(LAB_STAGES.length - 1, labStage + 1); labRenderTimeline(); });  // avanza una etapa (sin pasar de la última)
  labThresholdSlider.addEventListener("input", labRenderFree);   // mover el slider de umbral repinta el modo libre
  labOpeningToggle.addEventListener("change", labRenderFree);    // activar/desactivar apertura repinta el modo libre
  labCleanupToggle.addEventListener("change", labRenderFree);    // activar/desactivar limpieza repinta el modo libre

  /* =========================================================
     Sala de órganos: all 5 organs in one scene, in the real
     physical-space (mm) coordinates their own pipeline produced —
     no per-organ rescaling, so relative size is genuinely to scale.
     Runs on its own canvas/WebGL context so it never touches the
     main viewer's state.
     ========================================================= */
  // Versiones de compile()/linkProgram() que reciben el contexto WebGL
  // como parámetro en vez de usar la variable global `gl` — necesarias
  // porque la Sala de órganos usa su PROPIO canvas y contexto (roomGl),
  // completamente separado del de la pestaña 3D principal.
  function compileFor(glCtx, type, src) {
    const s = glCtx.createShader(type); glCtx.shaderSource(s, src); glCtx.compileShader(s);  // crea, asigna fuente y compila
    if (!glCtx.getShaderParameter(s, glCtx.COMPILE_STATUS)) throw new Error(glCtx.getShaderInfoLog(s));  // revienta con el log real si falló
    return s;
  }
  function linkProgramFor(glCtx, vsSrc, fsSrc) {
    const p = glCtx.createProgram();
    glCtx.attachShader(p, compileFor(glCtx, glCtx.VERTEX_SHADER, vsSrc));    // compila y adjunta el vertex shader
    glCtx.attachShader(p, compileFor(glCtx, glCtx.FRAGMENT_SHADER, fsSrc));  // compila y adjunta el fragment shader
    glCtx.linkProgram(p);
    return p;
  }
  // Igual que projectToScreen() de la pestaña 3D principal, pero
  // parametrizada por canvas (`cnv`) para poder usarse también en la Sala
  // de órganos con su propio canvas y sus propias etiquetas.
  function projectToScreenGeneric(cnv, pos, view, proj) {
    const vx = view[0]*pos[0]+view[4]*pos[1]+view[8]*pos[2]+view[12];   // igual que projectToScreen(), pero con `cnv` en vez de `canvas`
    const vy = view[1]*pos[0]+view[5]*pos[1]+view[9]*pos[2]+view[13];
    const vz = view[2]*pos[0]+view[6]*pos[1]+view[10]*pos[2]+view[14];
    const vw = view[3]*pos[0]+view[7]*pos[1]+view[11]*pos[2]+view[15];
    const cx = proj[0]*vx+proj[4]*vy+proj[8]*vz+proj[12]*vw;
    const cy = proj[1]*vx+proj[5]*vy+proj[9]*vz+proj[13]*vw;
    const cw = proj[3]*vx+proj[7]*vy+proj[11]*vz+proj[15]*vw;
    if (cw <= 0.001) return null;                        // detrás de la cámara
    const ndcX = cx / cw, ndcY = cy / cw;                 // división de perspectiva
    if (ndcX < -1.3 || ndcX > 1.3 || ndcY < -1.3 || ndcY > 1.3) return null;  // muy fuera de pantalla
    return [(ndcX*0.5+0.5) * cnv.clientWidth, (1-(ndcY*0.5+0.5)) * cnv.clientHeight];  // NDC -> píxeles del canvas dado
  }

  // Segundo canvas/contexto WebGL completamente independiente del
  // principal, reutilizando los MISMOS shaders VS/FS (así los 5 órganos
  // se ven con la misma iluminación/Fresnel que en la pestaña 3D).
  const roomCanvas = document.getElementById("room-canvas");
  const roomGl = roomCanvas.getContext("webgl", {antialias: true, alpha: false});
  const roomProgram = linkProgramFor(roomGl, VS, FS);   // mismos shaders VS/FS que la pestaña 3D, compilados para roomGl
  const room_aPosition = roomGl.getAttribLocation(roomProgram, "aPosition");
  const room_aNormal = roomGl.getAttribLocation(roomProgram, "aNormal");
  const room_uModelView = roomGl.getUniformLocation(roomProgram, "uModelView");
  const room_uProjection = roomGl.getUniformLocation(roomProgram, "uProjection");
  const room_uNormalMatrix = roomGl.getUniformLocation(roomProgram, "uNormalMatrix");
  const room_uColor = roomGl.getUniformLocation(roomProgram, "uColor");
  const room_uAlpha = roomGl.getUniformLocation(roomProgram, "uAlpha");
  const room_uOffset = roomGl.getUniformLocation(roomProgram, "uOffset");        // aquí sí se usa de verdad: separa los 5 órganos en la fila
  const room_uClipNormal = roomGl.getUniformLocation(roomProgram, "uClipNormal");
  const room_uClipValue = roomGl.getUniformLocation(roomProgram, "uClipValue");
  const room_uClipEnabled = roomGl.getUniformLocation(roomProgram, "uClipEnabled");  // siempre desactivado en esta escena
  roomGl.enable(roomGl.DEPTH_TEST); roomGl.enable(roomGl.CULL_FACE); roomGl.cullFace(roomGl.BACK);  // mismo estado base que el contexto principal
  roomGl.getExtension("OES_element_index_uint");

  const roomLabelLayerEl = document.getElementById("room-label-layer");
  let roomBuilt = false;
  let roomEntries = [];
  let roomLabelEls = [];
  let roomBoundingRadius = 300;
  let roomTheta = 0.5, roomPhi = 1.2, roomRadius = 600, roomTargetRadius = 600;
  let roomAutoRotate = !reduceMotion;
  let roomDragging = false, roomLastX = 0, roomLastY = 0;

  // Construye la escena de la Sala de órganos UNA SOLA VEZ (roomBuilt evita
  // reconstruirla cada vez que se abre la pestaña): decodifica los 5
  // órganos con sus rotaciones de exhibición normales, y los coloca en
  // fila a lo largo de X —cada uno separado por un espacio fijo (gapMm)
  // más el radio de los dos vecinos, para que no se encimen— sin cambiar
  // el tamaño real de ninguno, y centra el conjunto en el origen.
  function buildRoom() {
    if (roomBuilt) return;                  // ya se construyó antes, no repetir el trabajo
    roomBuilt = true;
    const gapMm = 20;                        // espacio fijo (mm) entre el borde de un órgano y el siguiente
    let cursorX = 0;                          // posición X donde se colocará el próximo órgano
    const placed = [];                        // acumula {key, mesh, r, offset} de cada órgano ya posicionado
    for (const key of ORGAN_ORDER) {
      const mesh = decodeMesh(VIEWER_DATA[key].mesh, key);  // decodifica cada órgano con su rotación de exhibición normal
      let r = 1;                               // radio de su caja envolvente (mínimo 1 para evitar división rara)
      for (let i = 0; i < mesh.positions.length; i += 3) {   // recorre cada vértice para encontrar el radio real
        const dx = mesh.positions[i]-mesh.center[0], dy = mesh.positions[i+1]-mesh.center[1], dz = mesh.positions[i+2]-mesh.center[2];
        const d = Math.sqrt(dx*dx + dy*dy + dz*dz);
        if (d > r) r = d;
      }
      cursorX += r;                            // avanza hasta el borde de este órgano
      placed.push({key, mesh, r, offset: [cursorX - mesh.center[0], -mesh.center[1], -mesh.center[2]]});  // desplazamiento para centrar Y/Z y ubicar X
      cursorX += r + gapMm;                    // avanza más allá de este órgano, dejando el espacio fijo
    }
    const shiftX = (cursorX - gapMm) / 2;       // mitad del ancho total ocupado por la fila
    for (const p of placed) p.offset[0] -= shiftX;  // recorre la fila y la centra en X=0

    roomEntries = placed.map((p) => {
      const posBuf = roomGl.createBuffer();
      roomGl.bindBuffer(roomGl.ARRAY_BUFFER, posBuf); roomGl.bufferData(roomGl.ARRAY_BUFFER, p.mesh.positions, roomGl.STATIC_DRAW);  // sube sus posiciones
      const normBuf = roomGl.createBuffer();
      roomGl.bindBuffer(roomGl.ARRAY_BUFFER, normBuf); roomGl.bufferData(roomGl.ARRAY_BUFFER, p.mesh.normals, roomGl.STATIC_DRAW);   // sube sus normales
      const idxBuf = roomGl.createBuffer();
      roomGl.bindBuffer(roomGl.ELEMENT_ARRAY_BUFFER, idxBuf); roomGl.bufferData(roomGl.ELEMENT_ARRAY_BUFFER, p.mesh.indices, roomGl.STATIC_DRAW);  // sube sus índices
      const worldCenter = [p.mesh.center[0]+p.offset[0], p.mesh.center[1]+p.offset[1], p.mesh.center[2]+p.offset[2]];  // dónde queda su centro real en la escena conjunta
      return {
        posBuf, normBuf, idxBuf,
        indexCount: p.mesh.indices.length,
        color: hexToRgb01(ORGAN_META[p.key].color_hex),
        offset: p.offset,
        label: ORGAN_META[p.key].label,
        worldCenter, radius: p.r,
      };
    });

    let maxDist = 1;                          // distancia máxima desde el origen a cualquier punto de cualquier órgano
    for (const e of roomEntries) {
      const d = Math.hypot(e.worldCenter[0], e.worldCenter[1], e.worldCenter[2]) + e.radius;  // distancia al centro de ese órgano + su propio radio
      if (d > maxDist) maxDist = d;
    }
    roomBoundingRadius = maxDist;              // usado para calibrar la distancia de cámara de toda la escena
    roomRadius = roomBoundingRadius * 2.3; roomTargetRadius = roomRadius;

    roomLabelLayerEl.innerHTML = "";           // limpia por si buildRoom se hubiera llamado dos veces
    roomLabelEls = roomEntries.map((e) => {    // un <div> de etiqueta por cada uno de los 5 órganos
      const el = document.createElement("div");
      el.className = "landmark-label";
      el.textContent = e.label;
      roomLabelLayerEl.appendChild(el);
      return el;
    });
  }

  // Punto de entrada real a la pestaña Sala de órganos: si buildRoom() ya
  // corrió antes, no hay nada costoso que esperar, así que no muestra el
  // esqueleto (evita un parpadeo inútil de <100ms). Si es la primera vez,
  // sí hay una espera sincrónica real (decodificar + subir 5 mallas a la
  // GPU), así que: muestra el esqueleto, cede el control al navegador con
  // un doble requestAnimationFrame para GARANTIZAR que ese frame realmente
  // se pinte en pantalla (un solo rAF no basta: el navegador puede agrupar
  // el cambio de estilo con el trabajo pesado que sigue en el mismo frame),
  // y solo entonces ejecuta el trabajo pesado y oculta el esqueleto.
  const roomSkeletonEl = document.getElementById("room-skeleton");
  function enterRoomTab() {
    if (roomBuilt) { buildRoom(); return; }  // no-op real (buildRoom sale de inmediato) — nada que anunciar
    roomSkeletonEl.classList.remove("hidden");
    requestAnimationFrame(() => requestAnimationFrame(() => {
      buildRoom();
      roomSkeletonEl.classList.add("hidden");
    }));
  }

  // Controles de cámara orbital para la Sala — idénticos en espíritu a los
  // del canvas principal, pero con su propio estado (roomTheta/roomPhi/...)
  // porque es una escena y una cámara totalmente aparte.
  roomCanvas.addEventListener("pointerdown", (e) => { roomDragging = true; roomAutoRotate = false; roomLastX = e.clientX; roomLastY = e.clientY; roomCanvas.setPointerCapture(e.pointerId); });  // empieza a arrastrar
  roomCanvas.addEventListener("pointerup", () => roomDragging = false);   // suelta el arrastre
  roomCanvas.addEventListener("pointermove", (e) => {
    if (!roomDragging) return;
    roomTheta -= (e.clientX - roomLastX) * 0.008; roomPhi -= (e.clientY - roomLastY) * 0.008;  // igual que la cámara principal
    roomPhi = Math.max(0.15, Math.min(Math.PI - 0.15, roomPhi));       // evita cruzar el polo
    roomLastX = e.clientX; roomLastY = e.clientY;
  });
  roomCanvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    roomTargetRadius = Math.max(roomBoundingRadius*0.3, Math.min(roomBoundingRadius*6, roomTargetRadius * Math.pow(1.0012, e.deltaY)));  // zoom acotado a la escala de la sala completa
  }, {passive: false});
  document.getElementById("room-reset-btn").addEventListener("click", () => {   // botón "Restablecer vista"
    roomTheta = 0.5; roomPhi = 1.2; roomTargetRadius = roomBoundingRadius * 2.3; roomAutoRotate = !reduceMotion;
  });

  // Igual que resizeGl() pero para el canvas de la Sala de órganos.
  function resizeRoomGl() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(roomCanvas.clientWidth * dpr), h = Math.round(roomCanvas.clientHeight * dpr);
    if (roomCanvas.width !== w || roomCanvas.height !== h) { roomCanvas.width = w; roomCanvas.height = h; }
  }

  // Bucle de render de la Sala de órganos: dibuja los 5 órganos ya
  // colocados por buildRoom(), cada uno con su propio uOffset (para
  // ubicarlo en su posición en la fila) pero compartiendo una sola cámara
  // orbital centrada en el origen de toda la escena. Solo hace trabajo si
  // la pestaña ya se construyó y está visible — si no, no tiene sentido
  // gastar tiempo de GPU dibujando algo que nadie ve.
  function renderRoom() {
    if (roomBuilt && !panelRoom.classList.contains("hidden")) {   // solo si ya se construyó Y la pestaña está visible
      resizeRoomGl();
      roomGl.viewport(0, 0, roomCanvas.width, roomCanvas.height);
      roomGl.clearColor(0.039, 0.055, 0.075, 1.0);                 // mismo color de fondo que la pestaña principal
      roomGl.clear(roomGl.COLOR_BUFFER_BIT | roomGl.DEPTH_BUFFER_BIT);
      roomRadius += (roomTargetRadius - roomRadius) * 0.12;        // suaviza el zoom, igual que en la cámara principal
      if (roomAutoRotate) roomTheta += 0.0012;                     // gira más despacio que la cámara principal (hay más que mirar)
      const eye = [roomRadius*Math.sin(roomPhi)*Math.sin(roomTheta), roomRadius*Math.cos(roomPhi), roomRadius*Math.sin(roomPhi)*Math.cos(roomTheta)];  // cámara orbital, centrada en el origen de la escena
      const view = lookAt(eye, [0, 0, 0], [0, 1, 0]);
      const proj = perspective(Math.PI/4.2, roomCanvas.width/Math.max(1, roomCanvas.height), Math.max(0.01, roomBoundingRadius*0.02), roomBoundingRadius*20);
      roomGl.useProgram(roomProgram);
      roomGl.uniformMatrix4fv(room_uModelView, false, view);
      roomGl.uniformMatrix4fv(room_uProjection, false, proj);
      roomGl.uniformMatrix3fv(room_uNormalMatrix, false, normalMat3(view));
      roomGl.uniform1f(room_uAlpha, 1.0);              // todo opaco en esta escena
      roomGl.uniform1f(room_uClipEnabled, 0.0);         // sin clipping aquí
      roomGl.uniform3fv(room_uClipNormal, [1, 0, 0]);   // valores neutros (no se usan)
      roomGl.uniform1f(room_uClipValue, 0.0);
      for (const e of roomEntries) {                    // dibuja cada uno de los 5 órganos, uno por uno
        roomGl.uniform3fv(room_uColor, e.color);         // color propio de este órgano
        roomGl.uniform3fv(room_uOffset, e.offset);       // lo desplaza a su posición en la fila
        roomGl.bindBuffer(roomGl.ARRAY_BUFFER, e.posBuf); roomGl.enableVertexAttribArray(room_aPosition); roomGl.vertexAttribPointer(room_aPosition, 3, roomGl.FLOAT, false, 0, 0);
        roomGl.bindBuffer(roomGl.ARRAY_BUFFER, e.normBuf); roomGl.enableVertexAttribArray(room_aNormal); roomGl.vertexAttribPointer(room_aNormal, 3, roomGl.FLOAT, false, 0, 0);
        roomGl.bindBuffer(roomGl.ELEMENT_ARRAY_BUFFER, e.idxBuf);
        roomGl.drawElements(roomGl.TRIANGLES, e.indexCount, roomGl.UNSIGNED_INT, 0);
      }
      // Reposiciona la etiqueta con el nombre de cada órgano justo encima
      // de su malla (a 0.95 veces su radio, para que quede cerca del borde
      // superior sin tocarlo), proyectando su posición 3D a píxeles.
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

  // Barajado de Fisher-Yates: recorre el array de atrás hacia adelante,
  // intercambiando cada posición con una posición aleatoria anterior o
  // igual a ella — el algoritmo estándar para mezclar sin sesgo. Se usa
  // tanto para el orden de las 15 preguntas como para el orden de las
  // opciones de cada pregunta, así no se memoriza un patrón fijo.
  function shuffleArray(arr) {
    const a = arr.slice();                              // copia el array: nunca modifica el original
    for (let i = a.length - 1; i > 0; i--) {             // recorre de atrás hacia adelante
      const j = Math.floor(Math.random() * (i + 1));     // elige una posición aleatoria entre 0 e i (inclusive)
      [a[i], a[j]] = [a[j], a[i]];                        // intercambia las posiciones i y j
    }
    return a;
  }

  // Empieza (o reinicia) el cuestionario del órgano `key`: baraja sus 15
  // preguntas, resetea el puntaje y muestra la primera pregunta.
  function triviaStart(key) {
    triviaCurrentKey = key;
    for (const btn of triviaOrganListEl.querySelectorAll(".organ-btn")) {
      btn.setAttribute("aria-pressed", String(btn.dataset.organ === key));  // marca el botón de este órgano como activo
    }
    triviaQuestions = shuffleArray(ORGAN_META[key].quiz);  // las 15 preguntas de este órgano, en orden aleatorio
    triviaIndex = 0;                    // empieza desde la primera pregunta
    triviaScore = 0;                    // reinicia el puntaje
    triviaResultEl.classList.add("hidden");           // oculta la pantalla de resultado (si venía de un intento anterior)
    triviaQuestionCardEl.classList.remove("hidden");  // muestra la tarjeta de pregunta
    triviaRenderQuestion();
  }

  // Muestra la pregunta actual (índice triviaIndex) con sus opciones en
  // orden aleatorio, y crea un botón por opción con su propio listener de
  // clic. Oculta la explicación y el botón "Siguiente" hasta que se responda.
  function triviaRenderQuestion() {
    triviaAnswered = false;                     // esta nueva pregunta todavía no tiene respuesta elegida
    const q = triviaQuestions[triviaIndex];      // la pregunta actual (objeto {q, options, correct, explain})
    triviaProgressEl.textContent = `Pregunta ${triviaIndex + 1} de ${triviaQuestions.length} · Puntaje: ${triviaScore}`;
    triviaQuestionTextEl.textContent = q.q;       // el enunciado de la pregunta
    triviaOptionsEl.innerHTML = "";                // borra los botones de la pregunta anterior
    for (const opt of shuffleArray(q.options)) {   // un botón por cada opción, en orden aleatorio
      const btn = document.createElement("button");
      btn.className = "trivia-option-btn";
      btn.textContent = opt;
      btn.addEventListener("click", () => triviaSelectOption(opt, btn));
      triviaOptionsEl.appendChild(btn);
    }
    triviaExplainEl.classList.add("hidden");   // la explicación aparece solo después de responder
    triviaNextBtn.classList.add("hidden");     // el botón "Siguiente" también
  }

  // Procesa la respuesta elegida: solo la primera vez por pregunta
  // (triviaAnswered evita cambiar la respuesta después), suma el puntaje
  // si acertó, marca visualmente cuál era la correcta y cuál se eligió
  // (si fue incorrecta), y muestra la explicación real de la pregunta.
  function triviaSelectOption(opt, btn) {
    if (triviaAnswered) return;               // ya se respondió esta pregunta, ignora más clics
    triviaAnswered = true;
    const q = triviaQuestions[triviaIndex];
    if (opt === q.correct) triviaScore++;      // suma punto solo si la opción elegida es la correcta
    for (const b of triviaOptionsEl.querySelectorAll(".trivia-option-btn")) {
      b.disabled = true;                        // bloquea todos los botones tras responder
      if (b.textContent === q.correct) b.dataset.state = "correct";  // resalta en verde cuál era la correcta
      else if (b === btn) b.dataset.state = "wrong";                  // resalta en ámbar la elegida, si fue incorrecta
    }
    triviaExplainEl.textContent = q.explain;
    triviaExplainEl.classList.remove("hidden");    // muestra la explicación real
    triviaNextBtn.textContent = triviaIndex < triviaQuestions.length - 1 ? "Siguiente →" : "Ver resultado";  // último texto cambia en la pregunta final
    triviaNextBtn.classList.remove("hidden");
    triviaProgressEl.textContent = `Pregunta ${triviaIndex + 1} de ${triviaQuestions.length} · Puntaje: ${triviaScore}`;  // refleja el puntaje ya actualizado
  }

  // Al terminar las 15 preguntas, cambia la tarjeta de pregunta por la de
  // resultado final, con un mensaje distinto según el porcentaje de aciertos.
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

  // "Siguiente" avanza a la próxima pregunta, o muestra el resultado si ya
  // no quedan más; "Reintentar" vuelve a empezar el mismo cuestionario
  // (con las preguntas y opciones barajadas de nuevo).
  triviaNextBtn.addEventListener("click", () => {
    triviaIndex++;
    if (triviaIndex >= triviaQuestions.length) triviaShowResult();
    else triviaRenderQuestion();
  });
  triviaRestartBtn.addEventListener("click", () => triviaStart(triviaCurrentKey));

  // Construye la lista de órganos de la pestaña Trivia solo la primera vez
  // que se entra a ella (igual que el resto de "lazy init" del resto del
  // visor), y arranca el cuestionario del órgano por defecto.
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
  // Carga el primer órgano (pulmones) para que la página no arranque
  // vacía, y arranca el bucle de render principal — de aquí en adelante,
  // todo lo demás ocurre en respuesta a eventos del usuario.
  selectOrgan(ORGAN_ORDER[0]);
  requestAnimationFrame(render3d);
</script>
"""


def main() -> int:
    # Define la interfaz de línea de comandos: dos rutas obligatorias,
    # el payload de entrada (generado por build_demo_payload.py) y la
    # ruta del HTML final a escribir.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", required=True, help="Path to the JSON payload from build_demo_payload.py")
    parser.add_argument("--output", required=True, help="Path to write the final HTML artifact to")
    args = parser.parse_args()

    # Carga el payload JSON completo en memoria.
    with open(args.payload) as f:
        payload = json.load(f)

    # Construye el HTML final combinando la plantilla con los datos reales.
    html = build(payload)
    # Se asegura de que la carpeta destino exista antes de escribir
    # (por ejemplo, si --output apunta a docs/index.html y docs/ no existe aún).
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    # Reporta el tamaño final en MB, útil para vigilar que no se pase
    # del límite de publicación del artifact (~16MB).
    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"Wrote {args.output} ({size_mb:.2f} MB)")
    return 0


# Solo ejecuta main() si el archivo se corre directamente (no si se
# importa como módulo desde otro script), y usa su valor de retorno
# como código de salida del proceso.
if __name__ == "__main__":
    raise SystemExit(main())
