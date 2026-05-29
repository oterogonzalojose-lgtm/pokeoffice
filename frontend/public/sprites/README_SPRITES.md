# Sprites de Pokeoffice

Coloca los archivos PNG en esta carpeta. El canvas los carga automáticamente.

---

## Archivos necesarios

| Archivo | Descripción | Dimensiones |
|---------|-------------|-------------|
| `room_bg.png` | Fondo completo de la oficina (sin personajes) | 800×760 px |
| `vp.png` | VP de frente, parado | 52×80 px (o múltiplo) |
| `agent_green.png` | Agente sentado, gorro verde (Recepcionista) | 52×68 px |
| `agent_dark.png` | Agente sentado, gorro negro (Programador) | 52×68 px |
| `agent_cyan.png` | Agente sentado, gorro cyan (Marketing) | 52×68 px |
| `agent_orange.png` | Agente sentado, gorro naranja (Contador) | 52×68 px |
| `agent_purple.png` | Agente sentado, gorro púrpura (Proveedores) | 52×68 px |

---

## Prompts para Midjourney

### room_bg.png — Fondo de oficina

```
top-down 2D pixel art office interior, retro RPG game style 32-bit, high quality,
dark mahogany wood paneled back wall with raised wainscot panels and crown molding,
three windows with white frames showing trees and light blue sky outside,
left section has a BOSS door in dark wood with a gold engraved "BOSS" plaque,
center section is a gray tiled print room with large industrial photocopier and paper shredder,
right section is a warm oak kitchen with upper cabinets, microwave, sink, coffee maker and water dispenser with blue bottle,
a horizontal divider wall separates back section from main floor with an open doorway in the center,
main floor has beautiful blue slate herringbone chevron pattern tiles,
two groups of dark brown wood office cubicles: three on the left and two on the right, each with CRT monitor on desk,
four palm trees in terracotta pots at the corners of the main floor,
diagonal golden light shafts from windows on the floor,
NO characters or people in the scene,
dark vignette border, pixel perfect, high detail
--ar 800:760 --v 6.1 --style raw
```

### vp.png — VP (Jefe de Gabinete)

```
pixel art character sprite sheet, single frame, front-facing standing office manager,
light blue button-up shirt, tan khaki slacks, short dark brown hair, medium skin tone,
friendly expression, arms at sides, pixel perfect, transparent background,
32-bit retro RPG game style, top-down perspective character
--ar 1:2 --v 6.1 --style raw
```

### agent_green.png — Recepcionista (gorro verde)

```
pixel art character sprite, back-facing seated office worker, solid green baseball cap,
dark navy work shirt, sitting in dark navy office chair, visible from behind and slightly above,
transparent background, 32-bit retro RPG game style
--ar 3:4 --v 6.1 --style raw
```

### agent_dark.png — Programador (gorro negro)

Mismo prompt que arriba, reemplazar "solid green" por "solid black/charcoal"

### agent_cyan.png — Marketing (gorro cyan)

Mismo prompt, reemplazar "solid green" por "solid cyan/turquoise"

### agent_orange.png — Contador (gorro naranja)

Mismo prompt, reemplazar "solid green" por "solid orange"

### agent_purple.png — Proveedores (gorro púrpura)

Mismo prompt, reemplazar "solid green" por "solid purple/violet"

---

## Alternativa: usar la imagen de referencia directamente

Si tenés la imagen de referencia (la que se usó como objetivo),
podés usarla directamente como `room_bg.png` y solo generar los personajes.
La imagen debe estar en 800×760 px (o será escalada por el canvas).

---

## Calibrar posiciones de personajes

Una vez que tengas `room_bg.png`, editá las coordenadas en `OfficeCanvas.jsx`:

```js
const AGENT_POS = {
  atencion_cliente: { x: 190, y: 432 },  // ← ajustar según imagen
  programador:      { x: 282, y: 432 },
  marketing:        { x: 374, y: 432 },
  contador:         { x: 528, y: 432 },
  proveedores:      { x: 620, y: 432 },
}
const VP_HOME = { x: 400, y: 590 }
```

Usá el inspector del browser (F12 → Canvas) para encontrar las coordenadas exactas.
