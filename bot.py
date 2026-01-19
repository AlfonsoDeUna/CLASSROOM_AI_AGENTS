"""
Bot para Google Classroom - Extracción de Entregas de Alumnos (v3)
Navega a las tareas y extrae los archivos adjuntos entregados por los alumnos
INCLUYE: Nombre del alumno + URLs de archivos + Descarga en PDF
"""

from playwright.sync_api import sync_playwright
import re
import time
import os
import json
import shutil
import tempfile

class ClassroomEntregasBot:
    def __init__(self, email, password, user_data_dir=None):
        self.email = email
        self.password = password
        # Usar carpeta en TEMP para evitar problemas con OneDrive
        if user_data_dir is None:
            self.user_data_dir = os.path.join(tempfile.gettempdir(), "classroom_chrome_profile")
        else:
            self.user_data_dir = user_data_dir
        self.browser = None
        self.page = None
        self.base_url = "https://classroom.google.com"
    
    def iniciar_navegador(self, headless=False):
        """Inicia el navegador con perfil persistente"""
        self.playwright = sync_playwright().start()
        
        print(f"📁 Usando perfil en: {self.user_data_dir}")
        
        # Si hay error con el perfil, intentar limpiarlo
        try:
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                slow_mo=100,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
        except Exception as e:
            print(f"⚠ Error con perfil existente: {e}")
            print("🔄 Limpiando perfil corrupto...")
            
            # Limpiar perfil corrupto
            if os.path.exists(self.user_data_dir):
                try:
                    shutil.rmtree(self.user_data_dir)
                    print("✓ Perfil limpiado")
                except:
                    pass
            
            # Reintentar
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,
                slow_mo=100,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
        
        # Usar página existente o crear nueva
        if self.browser.pages:
            self.page = self.browser.pages[0]
        else:
            self.page = self.browser.new_page()
        
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        print("✓ Navegador iniciado")
    
    def esperar(self, segundos=2):
        """Espera simple"""
        time.sleep(segundos)
    
    def login(self):
        """Login en Google"""
        print("Navegando a login...")
        self.page.goto("https://accounts.google.com/signin", wait_until="domcontentloaded")
        self.esperar(3)
        
        if "myaccount.google.com" in self.page.url or "classroom.google.com" in self.page.url:
            print("✓ Ya estás logueado")
            return True
        
        try:
            campo_email = self.page.wait_for_selector('input[type="email"]', timeout=5000)
            if campo_email:
                campo_email.fill(self.email)
                self.esperar(1)
                self.page.click('#identifierNext')
                self.esperar(3)
            
            campo_password = self.page.wait_for_selector('input[type="password"]:visible', timeout=5000)
            if campo_password:
                campo_password.fill(self.password)
                self.esperar(1)
                self.page.click('#passwordNext')
                self.esperar(5)
            
            print("✓ Login completado")
            return True
            
        except Exception as e:
            print(f"Error en login: {e}")
            return False
    
    def ir_a_classroom(self):
        """Navega a Classroom"""
        print("Navegando a Classroom...")
        self.page.goto(self.base_url, wait_until="domcontentloaded")
        self.esperar(3)
    
    def listar_clases(self):
        """Lista las clases disponibles"""
        clases = []
        html = self.page.content()
        
        # Buscar enlaces a clases /c/ID
        patron = r'href="(/c/([A-Za-z0-9]+))"[^>]*>.*?YVvGBb[^>]*>([^<]+)<'
        matches = re.findall(patron, html, re.DOTALL)
        
        vistas = set()
        for href, clase_id, nombre in matches:
            nombre = nombre.strip()
            if clase_id not in vistas and nombre not in ['Inicio', 'Calendar', 'Para revisar', 'Ajustes', 'Clases archivadas']:
                clases.append({
                    'id': clase_id,
                    'nombre': nombre,
                    'url': f"{self.base_url}/c/{clase_id}"
                })
                vistas.add(clase_id)
        
        # Método alternativo
        if not clases:
            enlaces = self.page.query_selector_all('a[href*="/c/"]')
            for enlace in enlaces:
                try:
                    href = enlace.get_attribute('href')
                    match = re.search(r'/c/([A-Za-z0-9]+)', href)
                    if match:
                        clase_id = match.group(1)
                        if clase_id not in vistas:
                            texto = enlace.inner_text().strip()
                            if texto and texto not in ['Inicio', 'Calendar']:
                                clases.append({
                                    'id': clase_id,
                                    'nombre': texto[:50],
                                    'url': f"{self.base_url}/c/{clase_id}"
                                })
                                vistas.add(clase_id)
                except:
                    continue
        
        return clases
    
    def ir_a_trabajo_de_clase(self, clase_id):
        """
        Navega a la sección de Trabajo de clase
        URL: /w/CLASE_ID/t/all
        """
        url = f"{self.base_url}/w/{clase_id}/t/all"
        print(f"Navegando a: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        self.esperar(3)
    
    def listar_tareas(self):
        """
        Lista las tareas disponibles en la página actual.
        Busca elementos con enlaces a tareas /a/ID
        """
        tareas = []
        self.esperar(2)
        html = self.page.content()
        
        # Buscar elementos que son tareas (tienen href con /a/ seguido de ID largo)
        # El patrón ACg8oc... es típico de tareas
        patron = r'href="[^"]*?/a/(ACg8oc[A-Za-z0-9_-]+)[^"]*"'
        ids_tareas = list(set(re.findall(patron, html)))
        
        # Buscar IDs numéricos también
        patron2 = r'href="[^"]*?/a/(\d{15,})[^"]*"'
        ids_tareas.extend(list(set(re.findall(patron2, html))))
        
        # Obtener nombres de las tareas buscando en el DOM
        elementos = self.page.query_selector_all('[data-item-id], [data-coursework-id]')
        
        for elem in elementos:
            try:
                item_id = elem.get_attribute('data-item-id') or elem.get_attribute('data-coursework-id')
                
                # Buscar texto del título
                titulo_elem = elem.query_selector('.asQXV, .YVvGBb, [role="heading"]')
                nombre = ""
                if titulo_elem:
                    nombre = titulo_elem.inner_text().strip()
                
                if not nombre:
                    nombre = elem.inner_text().split('\n')[0].strip()[:60]
                
                if item_id and nombre:
                    tareas.append({
                        'id': item_id,
                        'nombre': nombre
                    })
            except:
                continue
        
        # Si no encontramos con selectores, buscar por patrón en HTML
        if not tareas:
            # Buscar bloques de tarea
            bloques = self.page.query_selector_all('li[data-item-id]')
            for bloque in bloques:
                try:
                    item_id = bloque.get_attribute('data-item-id')
                    texto = bloque.inner_text().strip()
                    nombre = texto.split('\n')[0][:60]
                    if item_id and nombre:
                        tareas.append({'id': item_id, 'nombre': nombre})
                except:
                    continue
        
        # Eliminar duplicados
        vistos = set()
        tareas_unicas = []
        for t in tareas:
            if t['id'] not in vistos:
                vistos.add(t['id'])
                tareas_unicas.append(t)
        
        return tareas_unicas
    
    def ir_a_entregas_tarea(self, clase_id, tarea_id):
        """
        Navega a la página de entregas de una tarea específica.
        URL: /c/CLASE_ID/a/TAREA_ID/submissions/by-status/and-sort-name/all
        """
        url = f"{self.base_url}/c/{clase_id}/a/{tarea_id}/submissions/by-status/and-sort-name/all"
        print(f"Navegando a entregas: {url}")
        self.page.goto(url, wait_until="domcontentloaded")
        self.esperar(3)
    
    def obtener_lista_estudiantes(self, clase_id, tarea_id):
        """
        Obtiene la lista de estudiantes con sus IDs Y NOMBRES.
        Retorna lista de diccionarios: [{'id': '...', 'nombre': '...'}]
        """
        self.ir_a_entregas_tarea(clase_id, tarea_id)
        html = self.page.content()
        
        estudiantes = []
        vistos = set()
        
        # Método 1: Buscar patrón ID + nombre en span.YVvGBb
        # Formato: /student/ID" ... <span class="YVvGBb">Nombre</span>
        patron = r'/student/([A-Za-z0-9]{16,})"[^>]*>.*?<span[^>]*class="YVvGBb"[^>]*>([^<]+)</span>'
        matches = re.findall(patron, html, re.DOTALL)
        
        for est_id, nombre in matches:
            nombre = nombre.strip()
            if est_id not in vistos and nombre:
                estudiantes.append({'id': est_id, 'nombre': nombre})
                vistos.add(est_id)
        
        # Método 2: Si no encontramos con el patrón, usar data-student-id
        if not estudiantes:
            # Buscar en filas de la tabla
            patron2 = r'data-student-id="(\d+)".*?<span[^>]*class="YVvGBb"[^>]*>([^<]+)</span>'
            matches2 = re.findall(patron2, html, re.DOTALL)
            for est_id, nombre in matches2:
                nombre = nombre.strip()
                if est_id not in vistos and nombre:
                    # Convertir ID numérico a base64 si es necesario
                    estudiantes.append({'id': est_id, 'nombre': nombre})
                    vistos.add(est_id)
        
        # Método 3: Fallback - solo IDs
        if not estudiantes:
            patron_simple = r'/student/([A-Za-z0-9]{16,})'
            ids = list(set(re.findall(patron_simple, html)))
            for est_id in ids:
                if est_id not in vistos:
                    estudiantes.append({'id': est_id, 'nombre': f'Estudiante_{est_id[:8]}'})
                    vistos.add(est_id)
        
        return estudiantes
    
    def extraer_archivos_de_estudiante(self, clase_id, tarea_id, estudiante_id):
        """
        Navega a la entrega de un estudiante específico y extrae sus archivos.
        CORREGIDO: Fuerza la recarga para evitar duplicar el archivo del primer alumno.
        """
        # 1. Construir URL con el ID del estudiante en el fragmento (#u=...)
        url = f"{self.base_url}/g/tg/{clase_id}/{tarea_id}#u={estudiante_id}&t=f"
        
        # 2. Navegar
        self.page.goto(url, wait_until="domcontentloaded")
        
        # --- FIX CRÍTICO: FORZAR RECARGA ---
        # Classroom es una SPA (Single Page App). Si solo cambiamos el #hash, 
        # a veces no actualiza el DOM y seguimos viendo al alumno anterior.
        # El reload obliga a traer los datos nuevos.
        self.page.reload(wait_until="domcontentloaded")
        self.esperar(5) # Espera generosa para que aparezcan los adjuntos (el icono del ojo)
        
        archivos = []
        ids_vistos = set()
        
        # Buscar el div específico que encontraste (clmEye)
        # Este div contiene el data-url con el enlace al archivo
        try:
            elementos_ojo = self.page.query_selector_all('div.clmEye[data-url]')
            
            for elem in elementos_ojo:
                try:
                    url_archivo = elem.get_attribute('data-url')
                    if url_archivo:
                        # Limpieza básica de la URL
                        url_archivo = url_archivo.replace('&amp;', '&')
                        
                        # Extraemos el ID del fichero (lo que va después de /d/)
                        id_match = re.search(r'/d/([A-Za-z0-9_-]+)', url_archivo)
                        
                        if id_match:
                            file_id = id_match.group(1)
                            
                            if file_id not in ids_vistos:
                                ids_vistos.add(file_id)
                                archivos.append({
                                    'id': file_id,
                                    'url': url_archivo,
                                    'url_pdf': f"https://drive.google.com/uc?export=download&id={file_id}"
                                })
                except:
                    continue
        except Exception as e:
            print(f"Error buscando clmEye: {e}")

        # Si no encontró nada con clmEye, intentamos un escaneo general por seguridad
        if not archivos:
            html = self.page.content()
            # Patrón para documentos de google
            patron_data_url = r'data-url="(https://docs\.google\.com/[^"]+)"'
            matches = re.findall(patron_data_url, html)
            
            for url_archivo in matches:
                url_archivo = url_archivo.replace('&amp;', '&')
                id_match = re.search(r'/d/([A-Za-z0-9_-]+)', url_archivo)
                if id_match and id_match.group(1) not in ids_vistos:
                    file_id = id_match.group(1)
                    ids_vistos.add(file_id)
                    archivos.append({
                        'id': file_id,
                        'url': url_archivo,
                        'url_pdf': f"https://drive.google.com/uc?export=download&id={file_id}"
                    })

        return archivos
    
    def extraer_todas_entregas(self, clase_id, tarea_id, nombre_tarea=""):
        """
        Extrae todas las entregas de todos los estudiantes de una tarea.
        Incluye nombre del alumno y URLs para descargar.
        """
        print(f"\n📥 Extrayendo entregas de tarea: {nombre_tarea or tarea_id[:15]}...")
        
        # Obtener lista de estudiantes con nombres
        estudiantes = self.obtener_lista_estudiantes(clase_id, tarea_id)
        print(f"✓ Encontrados {len(estudiantes)} estudiantes")
        
        todas_entregas = []
        
        for i, est in enumerate(estudiantes, 1):
            est_id = est['id']
            nombre = est['nombre']
            print(f"  [{i}/{len(estudiantes)}] 👤 {nombre}")
            
            archivos = self.extraer_archivos_de_estudiante(clase_id, tarea_id, est_id)
            
            if archivos:
                print(f"              📎 {len(archivos)} archivo(s)")
            
            todas_entregas.append({
                'estudiante_id': est_id,
                'nombre_alumno': nombre,
                'archivos': archivos
            })
            
            # Pequeña pausa para no sobrecargar
            self.esperar(1)
        
        return todas_entregas
    
    def descargar_como_pdf(self, entregas, carpeta_destino="descargas_TArea_manual"):
        """
        Descarga los archivos convirtiendo Google Docs a PDF.
        Guarda todo en una única carpeta con el formato: "NombreAlumno_ID.pdf"
        """
        print(f"\n📥 Iniciando descargas en: '{carpeta_destino}'...")
        
        # Crear la carpeta si no existe
        if not os.path.exists(carpeta_destino):
            os.makedirs(carpeta_destino)
            print(f"✓ Carpeta creada: {carpeta_destino}")
        
        total_descargados = 0
        
        for entrega in entregas:
            nombre_alumno = entrega['nombre_alumno']
            archivos = entrega['archivos']
            
            if not archivos:
                continue
            
            # Limpiar nombre del alumno para usarlo en el archivo
            # Quitamos caracteres raros y espacios extra
            nombre_clean = re.sub(r'[<>:"/\\|?*]', '', nombre_alumno).strip()
            
            print(f"⬇ Procesando: {nombre_clean}")
            
            for archivo in archivos:
                file_id = archivo['id']
                url_original = archivo['url']
                
                # 1. Determinar URL de exportación a PDF según el tipo
                url_export = ""
                
                if 'docs.google.com/document' in url_original:
                    # Es un documento de texto -> Exportar a PDF
                    url_export = f"https://docs.google.com/document/d/{file_id}/export?format=pdf"
                    
                elif 'docs.google.com/presentation' in url_original:
                    # Es una presentación -> Exportar a PDF
                    url_export = f"https://docs.google.com/presentation/d/{file_id}/export/pdf"
                    
                elif 'docs.google.com/spreadsheets' in url_original:
                    # Es una hoja de cálculo -> Exportar a PDF
                    url_export = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=pdf"
                    
                else:
                    # Es un PDF, imagen o archivo binario en Drive -> Descarga directa
                    url_export = f"https://drive.google.com/uc?export=download&id={file_id}"

                # 2. Definir nombre del archivo final
                # Formato: NombreAlumno_ID.pdf
                nombre_archivo_final = f"{nombre_clean}_{file_id[:6]}.pdf"
                ruta_completa = os.path.join(carpeta_destino, nombre_archivo_final)
                
                # 3. Descargar
                try:
                    # Iniciamos la descarga esperando el evento 'download'
                    with self.page.expect_download(timeout=60000) as download_info:
                        # Navegamos a la URL de exportación
                        # Usamos try/except interno por si la navegación da timeout pero la descarga inicia
                        try:
                            self.page.goto(url_export, wait_until="commit")
                        except:
                            pass
                    
                    download = download_info.value
                    
                    # Guardar el archivo en la ruta destino
                    download.save_as(ruta_completa)
                    
                    print(f"   ✓ Guardado: {nombre_archivo_final}")
                    total_descargados += 1
                    
                except Exception as e:
                    print(f"   ⚠ Error descargando {file_id}: {e}")
                    
                # Pequeña pausa para no saturar
                self.esperar(1)
        
        print(f"\n✓ PROCESO TERMINADO. {total_descargados} archivos descargados en '{carpeta_destino}'")
        return total_descargados
    
    def guardar_json(self, datos, archivo):
        """Guarda datos en JSON"""
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print(f"✓ Guardado en {archivo}")
    
    def cerrar(self):
        """Cierra el navegador"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("   BOT DE ENTREGAS - GOOGLE CLASSROOM (v3)")
    print("   Extrae archivos entregados por alumnos CON NOMBRES")
    print("   Opción de descargar todo en PDF")
    print("=" * 60)
    
    EMAIL = os.environ.get('GOOGLE_EMAIL', '')
    PASSWORD = os.environ.get('GOOGLE_PASSWORD', '')
    
    if not EMAIL:
        EMAIL = input("📧 Email de Google: ")
    if not PASSWORD:
        PASSWORD = input("🔑 Contraseña: ")
    
    bot = ClassroomEntregasBot(EMAIL, PASSWORD)
    
    try:
        bot.iniciar_navegador(headless=False)
        
        if not bot.login():
            print("✗ Error en login")
            return
        
        bot.ir_a_classroom()
        
        # 1. Listar clases
        print("\n" + "=" * 50)
        print("📚 CLASES DISPONIBLES")
        print("=" * 50)
        
        clases = bot.listar_clases()
        
        if not clases:
            print("✗ No se encontraron clases")
            return
        
        for i, c in enumerate(clases, 1):
            print(f"  {i}. {c['nombre']}")
        
        sel = input("\nNúmero de clase: ")
        clase = clases[int(sel) - 1]
        clase_id = clase['id']
        clase_nombre = clase['nombre']
        
        # 2. Ir a trabajo de clase y listar tareas
        print("\n" + "=" * 50)
        print(f"📝 TAREAS EN '{clase_nombre}'")
        print("=" * 50)
        
        bot.ir_a_trabajo_de_clase(clase_id)
        tareas = bot.listar_tareas()
        
        if not tareas:
            print("✗ No se encontraron tareas")
            print("Tip: Navega manualmente a la tarea y copia su ID de la URL")
            
            tarea_id = input("\nIntroduce el ID de la tarea manualmente (o 'q' para salir): ")
            if tarea_id.lower() == 'q':
                return
            tarea_nombre = "Tarea_manual"
        else:
            for i, t in enumerate(tareas, 1):
                print(f"  {i}. {t['nombre']}")
            
            sel = input("\nNúmero de tarea: ")
            tarea = tareas[int(sel) - 1]
            tarea_id = tarea['id']
            tarea_nombre = tarea['nombre']
        
        # 3. Extraer entregas
        print("\n" + "=" * 50)
        print("📥 EXTRAYENDO ENTREGAS DE ALUMNOS")
        print("=" * 50)
        
        entregas = bot.extraer_todas_entregas(clase_id, tarea_id, tarea_nombre)
        
        # Estadísticas
        total_alumnos = len(entregas)
        alumnos_con_archivos = sum(1 for e in entregas if e['archivos'])
        total_archivos = sum(len(e['archivos']) for e in entregas)
        
        print(f"\n✓ Procesados {total_alumnos} estudiantes")
        print(f"✓ {alumnos_con_archivos} con archivos entregados")
        print(f"✓ Total de archivos: {total_archivos}")
        
        # Mostrar resumen
        print("\n📋 RESUMEN DE ENTREGAS:")
        print("-" * 50)
        for e in entregas:
            nombre = e['nombre_alumno']
            n_archivos = len(e['archivos'])
            estado = "✅" if n_archivos > 0 else "❌"
            print(f"  {estado} {nombre}: {n_archivos} archivo(s)")
        
        # Guardar JSON
        # Limpiar nombre de tarea para nombre de archivo
        tarea_nombre_limpio = re.sub(r'[<>:"/\\|?*]', '_', tarea_nombre)[:30]
        nombre_archivo = f"entregas_{tarea_nombre_limpio}.json"
        
        datos_json = {
            'clase': clase_nombre,
            'clase_id': clase_id,
            'tarea': tarea_nombre,
            'tarea_id': tarea_id,
            'total_alumnos': total_alumnos,
            'alumnos_con_archivos': alumnos_con_archivos,
            'total_archivos': total_archivos,
            'entregas': entregas
        }
        bot.guardar_json(datos_json, nombre_archivo)
        
       # 4. Preguntar si descargar (o hacerlo directo)
        print("\n" + "=" * 50)
        descargar = input("¿Descargar archivos como PDF? (s/n): ").lower()
        
        if descargar == 's':
            # FORZAMOS EL NOMBRE DE LA CARPETA QUE PEDISTE
            carpeta = "descargas_Tarea_manual"
            bot.descargar_como_pdf(entregas, carpeta)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrumpido")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPulsa Enter para cerrar...")
        bot.cerrar()


if __name__ == "__main__":
    main()
