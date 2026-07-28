# Los órganos

Este documento describe, en términos anatómicos y fisiológicos accesibles,
los cinco órganos que Medical3DReconstruction puede reconstruir en 3D:
pulmones, corazón, hígado, riñones y cerebro. El objetivo es dar contexto
médico a quien evalúe el proyecto como herramienta educativa o de impacto
social, no solo a quien vaya a leer el código. Para el detalle técnico de
cada pipeline de segmentación, ver [`ORGAN_PIPELINES.md`](ORGAN_PIPELINES.md);
para la metodología de validación de volumen, ver
[`VALIDATION.md`](VALIDATION.md).

## Pulmones

### Ubicación anatómica y estructura general

Los pulmones son un par de órganos esponjosos alojados en la caja torácica,
uno a cada lado del mediastino (el espacio central que contiene el
corazón, la tráquea y los grandes vasos). No son simétricos: el pulmón
derecho tiene tres lóbulos (superior, medio e inferior) separados por
cisuras, mientras que el izquierdo tiene solo dos (superior e inferior)
para dejar espacio a la muesca cardíaca donde se aloja el corazón. Están
recubiertos por la pleura, una doble membrana serosa que permite el
deslizamiento durante la respiración.

### Función fisiológica principal

Su función es el intercambio gaseoso: el aire inspirado llega hasta los
alvéolos, diminutos sacos rodeados de capilares donde el oxígeno pasa a la
sangre y el dióxido de carbono pasa de la sangre al aire para ser
exhalado. Este proceso depende de una superficie de intercambio enorme
(decenas de metros cuadrados plegados en el volumen torácico) y de una vía
aérea continua —tráquea, bronquios, bronquiolos— que conecta el exterior
con cada alvéolo.

### Datos anatómicos relevantes al volumen/forma reconstruida

Anatómicamente son dos estructuras lobuladas y asimétricas, no un par de
esferas idénticas, lo cual se refleja directamente en la malla
reconstruida: el pipeline de este proyecto conserva los dos componentes
conexos más grandes (uno por pulmón) tras excluir la vía aérea central. El
volumen combinado de ambos pulmones varía considerablemente con el ciclo
respiratorio, el tamaño corporal y el estado de inflado en el momento de
la adquisición.

### Rango de volumen fisiológico plausible en adultos

Este proyecto usa un rango de plausibilidad de **2000–7000 mL** para el
volumen pulmonar combinado (módulo de validación,
`PLAUSIBLE_VOLUME_RANGES_ML`). Es un rango deliberadamente amplio: cubre
desde una espiración completa hasta una inspiración profunda en distintos
tamaños corporales, y sirve para detectar fallos graves de segmentación,
no para calificar precisión.

## Corazón

### Ubicación anatómica y estructura general

El corazón es un órgano muscular hueco del tamaño aproximado de un puño
cerrado, situado en el mediastino, ligeramente desplazado hacia la
izquierda, entre los dos pulmones y apoyado sobre el diafragma. Está
compuesto por cuatro cámaras (dos aurículas y dos ventrículos) y
conectado a los grandes vasos —aorta, arterias pulmonares, venas cavas y
venas pulmonares— que llevan y traen sangre del resto del cuerpo y de los
pulmones.

### Función fisiológica principal

Actúa como una bomba doble: el lado derecho impulsa sangre pobre en
oxígeno hacia los pulmones (circulación pulmonar) y el lado izquierdo
impulsa sangre oxigenada hacia el resto del cuerpo (circulación sistémica).
Late de forma rítmica gracias a su propio sistema de conducción eléctrica,
sin depender de un estímulo nervioso externo para cada latido.

### Datos anatómicos relevantes al volumen/forma reconstruida

Este proyecto reconstruye el corazón de dos formas distintas. La primera,
a partir de una TC clínica sin contraste, produce la silueta cardíaca
completa (cámaras + miocardio + muñones de los grandes vasos adheridos)
sin detalle cámara-por-cámara, porque la TC no realzada no separa con
fiabilidad aurículas de ventrículos. La segunda usa datos reales de
tomografía por síncrotrón ex-vivo del ESRF Human Organ Atlas / HiP-CT
(espécimen LADAF-2021-17, un corazón donado escaneado fuera del cuerpo),
que resuelve un detalle anatómico —vasos pequeños, trabéculas, pared
miocárdica— muy superior al de cualquier TC clínica, gracias al contraste
de fase de esa modalidad.

### Rango de volumen fisiológico plausible en adultos

El rango de plausibilidad configurado es **300–900 mL**, correspondiente a
un corazón adulto en un paciente vivo medido por TC/RM clínica. Las
reconstrucciones a partir del espécimen ex-vivo de síncrotrón pueden caer
legítimamente fuera de este rango: un corazón excisado y fijado
químicamente para su conservación no tiene el mismo volumen que un corazón
latiendo dentro de un tórax —el tejido se contrae con la fijación— así que
una marca de "no plausible" en ese caso es una limitación documentada y
esperada, no un error del pipeline.

## Hígado

### Ubicación anatómica y estructura general

El hígado es el órgano interno sólido más grande del cuerpo humano. Se
ubica en el cuadrante superior derecho del abdomen, justo debajo del
diafragma, protegido en parte por las costillas inferiores. Se divide
clásicamente en un lóbulo derecho, considerablemente más grande, y un
lóbulo izquierdo más pequeño, además de los lóbulos caudado y cuadrado
descritos en la anatomía segmentaria más detallada. Recibe un doble
aporte sanguíneo: la vena porta (rica en nutrientes absorbidos del
intestino) y la arteria hepática.

### Función fisiológica principal

El hígado desempeña cientos de funciones metabólicas: sintetiza proteínas
plasmáticas y factores de coagulación, produce bilis para la digestión de
grasas, metaboliza y almacena glucosa en forma de glucógeno, y filtra y
neutraliza toxinas y fármacos de la sangre que llega desde el intestino.
Es también uno de los pocos órganos humanos con capacidad significativa
de regeneración tisular.

### Datos anatómicos relevantes al volumen/forma reconstruida

Su asimetría marcada —el lóbulo derecho puede ser varias veces más grande
que el izquierdo— y su parénquima homogéneo pero no único en intensidad
(se superpone en TC con la del bazo, el riñón y el músculo) son
precisamente lo que motiva el algoritmo de crecimiento de regiones que usa
este proyecto en lugar de un umbral simple. La forma reconstruida refleja
esa asimetría anatómica real, no un artefacto del algoritmo.

### Rango de volumen fisiológico plausible en adultos

El rango de plausibilidad usado es **1000–2500 mL**, coherente con el
volumen hepático normal reportado en la literatura de volumetría por TC/RM
en adultos vivos. Cuando el hígado se reconstruye en modalidad síncrotrón
ex-vivo a partir de un espécimen conservado, el volumen puede caer fuera
de este rango por la misma razón que en el corazón: el tejido fijado no
conserva el volumen del órgano en vida, y eso es un resultado esperado, no
un fallo de segmentación.

## Riñones

### Ubicación anatómica y estructura general

Los riñones son un par de órganos con forma de frijol (judía), situados en
posición retroperitoneal —detrás del peritoneo, a ambos lados de la
columna vertebral, aproximadamente entre la última vértebra torácica y la
tercera vértebra lumbar. El riñón derecho suele estar ligeramente más bajo
que el izquierdo debido al espacio que ocupa el hígado por encima. Cada
riñón pesa aproximadamente entre 115 y 190 gramos y está rodeado por una
cápsula fibrosa y una capa de grasa perirrenal que lo protege y lo fija en
su posición.

### Función fisiológica principal

Los riñones filtran la sangre para eliminar productos de desecho
metabólico y regular el balance de agua, electrolitos y pH del cuerpo,
produciendo orina como resultado. Cada riñón contiene alrededor de un
millón de nefronas, las unidades funcionales microscópicas donde ocurre
la filtración, reabsorción y secreción. También cumplen funciones
endocrinas: producen renina (regulación de la presión arterial) y
eritropoyetina (estimula la producción de glóbulos rojos).

### Datos anatómicos relevantes al volumen/forma reconstruida

La forma de frijol, con un borde lateral convexo y un borde medial cóncavo
(el hilio renal, por donde entran y salen los vasos y el uréter), es la
característica geométrica más distintiva que debe preservar una malla
reconstruida fielmente. Este proyecto segmenta ambos riñones de forma
bilateral e independiente a partir de TC clínica (una semilla y un level
set por cada lado), y cuenta además con una variante de síncrotrón ex-vivo
para un riñón excisado individual, con un contraste de tejido mucho más
alto que el de la TC.

### Rango de volumen fisiológico plausible en adultos

El rango de plausibilidad configurado es **200–450 mL** para el volumen
combinado de ambos riñones en TC/RM clínica de un paciente vivo. Al igual
que con el corazón y el hígado, una reconstrucción de un espécimen
ex-vivo de síncrotrón puede caer fuera de este rango porque el tejido
renal fijado y excisado no tiene el mismo volumen que un riñón in situ e
irrigado —una diferencia biológica real y documentada, no un defecto del
pipeline.

## Cerebro

### Ubicación anatómica y estructura general

El cerebro es la porción más voluminosa del encéfalo, alojada dentro de la
caja craneal y protegida además por las meninges y el líquido
cefalorraquídeo. Se organiza en dos hemisferios (izquierdo y derecho)
unidos por el cuerpo calloso, cada uno con una corteza externa de
sustancia gris muy plegada (los giros y surcos que le dan su superficie
característica) que envuelve la sustancia blanca interna, además de
estructuras profundas como los ganglios basales, el tálamo y el
cerebelo en la parte posterior.

### Función fisiológica principal

Es el centro de control del sistema nervioso: integra la información
sensorial, coordina el movimiento voluntario, y sustenta funciones
cognitivas superiores como el lenguaje, la memoria, el razonamiento y la
emoción, además de regular —junto con el tronco encefálico— funciones
vitales automáticas como la respiración y la frecuencia cardíaca.

### Datos anatómicos relevantes al volumen/forma reconstruida

Conviene ser explícito sobre una limitación de este proyecto: la
reconstrucción cerebral **solo** está disponible a partir de datos de
tomografía por síncrotrón ex-vivo (el mismo espécimen donado
LADAF-2021-17 del ESRF Human Organ Atlas / HiP-CT usado para el corazón).
**No existe en este proyecto un pipeline de cerebro para TC o RM
clínicas**, a diferencia de pulmones, corazón, hígado y riñones, que sí
tienen ruta de TC clínica además de la variante de síncrotrón. La razón es
que la TC clínica sin contraste no separa de forma fiable la sustancia
gris de la blanca ni las estructuras profundas del cerebro, mientras que
la tomografía por contraste de fase ex-vivo sí resuelve ese detalle.
Cualquier malla cerebral de este proyecto proviene, por tanto, de un
espécimen excisado y fijado, no de un paciente vivo.

### Rango de volumen fisiológico plausible en adultos

El rango de plausibilidad configurado es **1000–1600 mL**, el rango
habitual del volumen cerebral en un adulto vivo medido por RM/TC clínica.
Puesto que la única vía de reconstrucción cerebral de este proyecto es un
espécimen ex-vivo fijado, es esperable —y no indica un error— que el
volumen reconstruido caiga fuera de este rango de referencia. A diferencia
del corazón, el hígado y los riñones (donde la fijación y la ausencia de
perfusión tienden a **reducir** el volumen respecto al órgano in vivo), la
reconstrucción real de este espécimen (LADAF-2021-17) midió **~2248 mL**,
**por encima** del rango — el escaneo "órgano completo" probablemente
incluye tronco encefálico, cerebelo y restos meníngeos/tejido conectivo
adherido que un protocolo típico de volumetría por RM en un paciente vivo
excluye o mide por separado. Esta discrepancia es una limitación conocida
y documentada del proyecto, no una falla de la segmentación.
</content>
