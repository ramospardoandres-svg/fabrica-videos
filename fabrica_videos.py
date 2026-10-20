import os
import time
import urllib.parse
import asyncio
import sqlite3
import subprocess
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import edge_tts

# ==========================================
# 1. ESTRUCTURA VIRAL DE ALTA RETENCIÓN
# ==========================================
class Escena(BaseModel):
    badge_superior: str = Field(description="Etiqueta impactante de 2 a 3 palabras en mayúsculas, ej: 'ERROR DE $500M', 'DATO OCULTO', 'GANADOR CLARO'")
    locucion: str = Field(description="Frase hablada ultra dinámica de 14 a 20 palabras. Sin relleno.")
    prompt_imagen_ia: str = Field(description="Detailed English prompt to generate a cinematic, dramatic, hyper-realistic vertical illustration of this exact scene. No text in image.")
    color_hex: str = Field(description="Color vibrante hexadecimal: '#00FFCC', '#FF2A85', '#FFE600', o '#00E5FF'")

class VideoScript(BaseModel):
    nicho: str
    titulo_video: str = Field(description="Título magnético con curiosidad extrema + #Shorts #Tech")
    descripcion_redes: str = Field(description="Descripción corta con pregunta para generar comentarios + 4 hashtags")
    escenas: list[Escena] = Field(description="Exactamente 6 escenas rápidas. La escena 1 debe atrapar en 2 segundos.")

# ==========================================
# 2. BASE DE DATOS Y FUENTES
# ==========================================
def cargar_fuente(size: int):
    rutas = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    for r in rutas:
        if os.path.exists(r):
            return ImageFont.truetype(r, size)
    return ImageFont.load_default()

def inicializar_db():
    conn = sqlite3.connect("historial.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, fecha TEXT, nicho TEXT, titulo TEXT)")
    conn.commit()
    return conn

def obtener_temas_previos(conn):
    c = conn.cursor()
    c.execute("SELECT titulo FROM videos ORDER BY id DESC LIMIT 40")
    return [row[0] for row in c.fetchall()]

# ==========================================
# 3. CEREBRO IA (FÓRMULA VIRAL + LOOP INFINITO)
# ==========================================
def generar_guion(nicho_tipo: int, usados: list[str]) -> VideoScript:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    client = genai.Client(api_key=api_key)
    
    prompts_nichos = {
        1: "NICHO 1 (Batalla de Tecnología/Hardware): Enfrenta dos tecnologías famosas con un giro sorprendente (ej. por qué algo barato supera a algo caro, o un secreto técnico de procesadores, discos, IA o gadgets).",
        2: "NICHO 2 (Desastres y Bugs Millonarios): Cómo un pequeño error humano, una línea de código o un fallo físico causó una catástrofe tecnológica real o pérdida millonaria.",
        3: "NICHO 3 (Paradojas y Retos Mentales Tech): Un misterio tecnológico, acertijo lógico o dato que parece mentira pero es 100% real. Revela el giro en la escena 5."
    }

    prompt = f"""
    Eres el guionista #1 de YouTube Shorts y TikTok con retención del 90%.
    Crea un guion hipnótico de 6 escenas sobre: {prompts_nichos[nicho_tipo]}
    PROHIBIDO repetir cualquiera de estos temas: {usados}.

    REGLAS DE ORO VIRALES:
    1. ESCENA 1 (GANCHO): Empieza con una afirmación chocante o pregunta imposible de ignorar. Prohibido saludar.
    2. RITMO: Cada escena tiene un cambio visual fuerte. Escribe el 'prompt_imagen_ia' en inglés describiendo una escena visualmente espectacular, estilo fotografía cinematográfica cyberpunk/tech iluminación neón 8k.
    3. COMENTARIOS: En la escena 5 o 6 incluye un detalle debatible para que la gente comente.
    4. LOOP PERFECTO: La última frase de la escena 6 debe conectar de forma natural con la primera frase de la escena 1.
    """

    # Intentar con el modelo más reciente requerido por tu cuenta de AI Studio
    modelos_a_probar = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    ultimo_error = None

    for mod in modelos_a_probar:
        try:
            print(f"Generando guion viral con {mod}...")
            response = client.models.generate_content(
                model=mod,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VideoScript,
                    temperature=0.85,
                ),
            )
            return VideoScript.model_validate_json(response.text)
        except Exception as e:
            ultimo_error = e
            continue

    raise RuntimeError(f"No se pudo conectar con ningún modelo: {ultimo_error}")

# ==========================================
# 4. GENERADOR DE IMÁGENES IA GRATIS (POLLINATIONS FLUX)
# ==========================================
def descargar_imagen_ia(prompt_en: str, index: int, out_path: str):
    prompt_limpio = f"{prompt_en}, cinematic lighting, hyperrealistic, vertical wallpaper, 8k, dramatic composition, no text"
    encoded = urllib.parse.quote(prompt_limpio)
    seed = int(time.time()) + (index * 77)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={seed}&model=flux&nologo=true"
    
    try:
        r = requests.get(url, timeout=35)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(out_path, "wb") as f:
                f.write(r.content)
            return
    except Exception as e:
        print(f"Aviso descarga IA escena {index}: usando fondo respaldado ({e})")

    # Respaldo elegante si el servidor de imágenes demora
    img = Image.new("RGB", (1080, 1920), color="#101520")
    img.save(out_path)

# ==========================================
# 5. COMPOSICIÓN VISUAL Y SUBTÍTULOS DINÁMICOS
# ==========================================
def dividir_en_bloques_cortos(texto: str, max_palabras: int = 5) -> list[str]:
    palabras = texto.split()
    bloques = []
    for i in range(0, len(palabras), max_palabras):
        bloques.append(" ".join(palabras[i:i + max_palabras]))
    return bloques if bloques else [texto]

def estampar_interfaz_viral(bg_path: str, badge: str, subtitulo_corto: str, color_hex: str, paso_actual: int, total_pasos: int, out_path: str):
    img = Image.open(bg_path).convert("RGB").resize((1080, 1920))
    
    # Oscurecer ligeramente la imagen para que las letras resalten al 100%
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.55)
    draw = ImageDraw.Draw(img)

    color = color_hex.strip() if (color_hex.startswith("#") and len(color_hex.strip()) == 7) else "#00FFCC"

    f_badge = cargar_fuente(44)
    f_sub = cargar_fuente(68)

    # 1. Barra de progreso superior (retención psicológica)
    ancho_barra = int((paso_actual / total_pasos) * 920)
    draw.rounded_rectangle([(80, 110), (1000, 128)], radius=9, fill="#222831")
    draw.rounded_rectangle([(80, 110), (80 + max(40, ancho_barra), 128)], radius=9, fill=color)

    # 2. Etiqueta / Badge Superior con fondo oscuro
    draw.rounded_rectangle([(80, 160), (750, 245)], radius=18, fill="#0D1117", outline=color, width=4)
    draw.text((110, 178), badge.upper()[:22], font=f_badge, fill=color)

    # 3. Subtítulo Estilo Viral en el centro-bajo (máximo 2 líneas grandes con borde negro)
    palabras = subtitulo_corto.upper().split()
    mitad = (len(palabras) + 1) // 2
    lineas = [" ".join(palabras[:mitad]), " ".join(palabras[mitad:])] if len(palabras) > 3 else [" ".join(palabras)]

    # Caja semitransparente/oscura detrás del subtítulo para lectura instantánea
    draw.rounded_rectangle([(60, 1220), (1020, 1520)], radius=28, fill="#0D1117", outline=color, width=3)

    y_sub = 1265 if len(lineas) > 1 else 1320
    for linea in lineas:
        # Borde negro grueso + texto blanco/color
        for dx, dy in [(-3,-3), (3,-3), (-3,3), (3,3)]:
            draw.text((100 + dx, y_sub + dy), linea, font=f_sub, fill="#000000")
        draw.text((100, y_sub), linea, font=f_sub, fill="#FFFFFF")
        y_sub += 95

    img.save(out_path)

# ==========================================
# 6. ENSAMBLAJE CON MOVIMIENTO (KEN BURNS + AUDIO)
# ==========================================
def obtener_duracion_audio(audio_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return max(1.5, float(res.stdout.strip()))
    except Exception:
        return 4.0

async def producir_video(guion: VideoScript, output_final: str):
    os.makedirs("temp", exist_ok=True)
    clips_finales = []
    voz = "es-MX-JorgeNeural"
    total_escenas = len(guion.escenas)

    for i, escena in enumerate(guion.escenas):
        print(f"--> Generando arte IA y voz para Escena {i+1}/{total_escenas}...")
        raw_bg = f"temp/bg_{i}.jpg"
        audio_path = f"temp/audio_{i}.mp3"

        # 1. Descargar imagen IA única para la escena
        descargar_imagen_ia(escena.prompt_imagen_ia, i, raw_bg)

        # 2. Generar voz neuronal con ritmo dinámico (+12% velocidad)
        communicate = edge_tts.Communicate(escena.locucion, voz, rate="+12%")
        await communicate.save(audio_path)
        duracion_total = obtener_duracion_audio(audio_path)

        # 3. Dividir la escena en micro-bloques de subtítulos para que cambien rápido
        bloques = dividir_en_bloques_cortos(escena.locucion, max_palabras=5)
        dur_bloque = duracion_total / len(bloques)
        
        imgs_concat_txt = f"temp/imgs_{i}.txt"
        with open(imgs_concat_txt, "w") as f:
            for b_idx, texto_corto in enumerate(bloques):
                frame_path = f"temp/frame_{i}_{b_idx}.png"
                estampar_interfaz_viral(raw_bg, escena.badge_superior, texto_corto, escena.color_hex, i + 1, total_escenas, frame_path)
                f.write(f"file '{os.path.abspath(frame_path)}'\n")
                f.write(f"duration {dur_bloque:.3f}\n")
            # Repetir el último frame por requisito de FFmpeg concat demuxer
            f.write(f"file '{os.path.abspath(frame_path)}'\n")

        # 4. Crear clip con suave pulso visual y unir con la voz
        clip_escena = f"temp/clip_{i}.mp4"
        cmd_clip = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", imgs_concat_txt,
            "-i", audio_path,
            "-vf", "scale=1140:2026,crop=1080:1920:'30+20*sin(2*PI*t/5)':'50+30*cos(2*PI*t/5)',fps=30",
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-shortest",
            clip_escena
        ]
        subprocess.run(cmd_clip, check=True)
        clips_finales.append(clip_escena)

    # 5. Unir todas las escenas
    with open("temp/lista_final.txt", "w") as f:
        for c in clips_finales:
            f.write(f"file '{os.path.abspath(c)}'\n")

    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "temp/lista_final.txt", "-c", "copy", output_final
    ]
    subprocess.run(cmd_concat, check=True)
    print("¡VIDEO VIRAL PRODUCIDO CON ÉXITO!")

if __name__ == "__main__":
    conn = inicializar_db()
    usados = obtener_temas_previos(conn)
    nicho_actual = (len(usados) % 3) + 1
    
    guion = generar_guion(nicho_actual, usados)
    asyncio.run(producir_video(guion, "VIDEO_LISTO.mp4"))
    
    with open("COPIAR_TITULO_Y_DESCRIPCION.txt", "w", encoding="utf-8") as f:
        f.write(f"=== TÍTULO PARA YOUTUBE / TIKTOK ===\n{guion.titulo_video}\n\n")
        f.write(f"=== DESCRIPCIÓN Y HASHTAGS ===\n{guion.descripcion_redes}\n")
        
    fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.execute("INSERT INTO videos (fecha, nicho, titulo) VALUES (?, ?, ?)",
                 (fecha_str, guion.nicho, guion.titulo_video))
    conn.commit()
    conn.close()
