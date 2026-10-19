import os
import asyncio
import sqlite3
import subprocess
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import edge_tts

class Escena(BaseModel):
    titulo_arriba: str = Field(description="Encabezado corto de máximo 4 palabras")
    texto_central: str = Field(description="Contenido visual principal: comparativa corta, código corto o dato clave con saltos de línea")
    locucion: str = Field(description="Lo que dirá el narrador en esta escena, máximo 25 palabras, directo al grano")
    color_acento: str = Field(description="Color hexadecimal brillante como #00FFCC, #FF3366 o #FFCC00")

class VideoScript(BaseModel):
    nicho: str
    titulo_video: str = Field(description="Título viral corto con #Shorts #Tech")
    descripcion_redes: str = Field(description="Descripción atractiva con llamado a la acción y 4 hashtags")
    escenas: list[Escena] = Field(description="Exactamente 5 escenas para un video de 35 a 45 segundos")

def inicializar_db():
    conn = sqlite3.connect("historial.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY, fecha TEXT, nicho TEXT, titulo TEXT)")
    conn.commit()
    return conn

def obtener_temas_previos(conn):
    c = conn.cursor()
    c.execute("SELECT titulo FROM videos ORDER BY id DESC LIMIT 30")
    return [row[0] for row in c.fetchall()]

def generar_guion(nicho_tipo: int, usados: list[str]) -> VideoScript:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    
    prompts_nichos = {
        1: "NICHO 1 (Comparativa Tech/Gadgets): Compara dos tecnologías, gadgets o herramientas populares (ej. SSD vs NVMe, Raspberry Pi vs Mini PC, Android vs iOS en algo técnico). Da datos concretos y un ganador.",
        2: "NICHO 2 (Desastres de Ingeniería / Bugs Millonarios): Cuenta la historia real de un fallo técnico, bug informático o error de cálculo que costó millones (ej. cohete Ariane 5, sonda de la NASA, caída mundial). Empieza con el impacto en el segundo 1.",
        3: "NICHO 3 (Reto / Trivia Rápida): Plantea un acertijo lógico o curioso de tecnología/programación en las primeras 2 escenas, da tiempo para pensar en la escena 3 y revela la respuesta en la 4 y 5."
    }

    prompt = f"""
    Eres un creador experto en videos virales para TikTok y YouTube Shorts.
    Crea un video para este formato: {prompts_nichos[nicho_tipo]}
    NO repitas estos temas ya usados: {usados}.
    Genera exactamente 5 escenas dinámicas en español.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VideoScript,
            temperature=0.8,
        ),
    )
    return VideoScript.model_validate_json(response.text)

def crear_imagen_escena(escena: Escena, output_path: str):
    img = Image.new("RGB", (1080, 1920), color="#0D1117")
    draw = ImageDraw.Draw(img)

    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_mono = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    
    f_titulo = ImageFont.truetype(font_bold, 54)
    f_central = ImageFont.truetype(font_mono, 40)
    f_sub = ImageFont.truetype(font_bold, 44)

    color = escena.color_acento if escena.color_acento.startswith("#") and len(escena.color_acento) == 7 else "#00FFCC"

    draw.rectangle([(80, 220), (1000, 235)], fill=color)
    draw.text((85, 270), escena.titulo_arriba.upper()[:28], font=f_titulo, fill=color)
    draw.rounded_rectangle([(70, 420), (1010, 1250)], radius=30, fill="#161B22", outline=color, width=4)
    
    lineas_centrales = []
    for linea in escena.texto_central.split("\n"):
        while len(linea) > 32:
            lineas_centrales.append(linea[:32])
            linea = linea[32:]
        lineas_centrales.append(linea)
    
    y_text = 480
    for linea in lineas_centrales[:11]:
        draw.text((110, y_text), linea, font=f_central, fill="#E6EDF3")
        y_text += 62

    palabras = escena.locucion.split()
    lineas_sub, actual = [], ""
    for p in palabras:
        if len(actual + " " + p) < 28:
            actual += " " + p
        else:
            lineas_sub.append(actual.strip())
            actual = p
    if actual:
        lineas_sub.append(actual.strip())

    y_sub = 1360
    for l in lineas_sub[:5]:
        draw.text((90, y_sub), l, font=f_sub, fill="#FFFFFF")
        y_sub += 65

    img.save(output_path)

async def producir_video(guion: VideoScript, output_final: str):
    os.makedirs("temp", exist_ok=True)
    clips_escenas = []
    voz = "es-MX-JorgeNeural"

    for i, escena in enumerate(guion.escenas):
        img_path = f"temp/escena_{i}.png"
        audio_path = f"temp/audio_{i}.mp3"
        clip_path = f"temp/clip_{i}.mp4"

        crear_imagen_escena(escena, img_path)

        communicate = edge_tts.Communicate(escena.locucion, voz, rate="+10%")
        await communicate.save(audio_path)

        cmd_clip = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path, "-i", audio_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest", clip_path
        ]
        subprocess.run(cmd_clip, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clips_escenas.append(clip_path)

    with open("temp/lista.txt", "w") as f:
        for clip in clips_escenas:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", "temp/lista.txt", "-c", "copy", output_final
    ]
    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
