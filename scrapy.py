import os
import random
import time
import requests
from fake_useragent import UserAgent
import csv
import concurrent.futures

SESSION_ID = "6666325872%3AL4SSp8AelfLXLv%3A24%3AAYgAswvvRYKRFkHG1WqIk7yTeRX49H0Kt8ISkzRf2w"

def get_user_details(username, session_id):
    headers = {
        "authority": "www.instagram.com",
        "referer": f"https://www.instagram.com/{username}/",
        "user-agent": UserAgent().random,
        'x-ig-app-id': '936619743392459',
        "x-requested-with": "XMLHttpRequest"
    }
    
    cookies = {'sessionid': session_id}
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_data = data.get('data', {}).get('user', {})
            return {
                'user_id': user_data.get('id'),
                'username': user_data.get('username'),
                'follower_count': user_data.get('edge_followed_by', {}).get('count', 0),
                'following_count': user_data.get('edge_follow', {}).get('count', 0),
                "biografia": user_data.get("biography", ""),
                "descripcion": {
                    "nombre_completo": user_data.get("full_name", ""),
                    "categoria": user_data.get("category_name", "")
                }
            }
    except Exception as e:
        print(f"Error obteniendo detalles de {username}: {e}")
    
    return None

def get_all_followers_list(target_username, session_id):

    target_info = get_user_details(target_username, session_id)
    if not target_info:
        print("No se pudo obtener información del usuario objetivo")
        return [], None

    print(f"Objetivo: @{target_info['username']} - {target_info['follower_count']} seguidores - {target_info['following_count']} seguidos")
    
    if target_info['following_count'] == 0:
        print("El usuario no tiene seguidores")
        return [], target_info
    
    all_followers = []
    max_id = None
    page_count = 0
    
    print("Iniciando scraping de seguidores...")
 
    while len(all_followers) < target_info['following_count']:
        try:

            params = {'count': '50', 'search_surface': 'follow_list_page'}
            if max_id:
                params['max_id'] = max_id  # Agregar max_id si existe para paginación
            
            # Headers para la petición
            headers = {
                'accept': '*/*',
                'referer': f'https://www.instagram.com/{target_username}/following/',
                'user-agent': UserAgent().random,
                'x-ig-app-id': '936619743392459',
                'x-requested-with': 'XMLHttpRequest',
            }
            
            cookies = {'sessionid': session_id}
            # URL de la API para obtener seguidores
            url = f'https://www.instagram.com/api/v1/friendships/{target_info["user_id"]}/following/'
            
            # Realizar petición
            response = requests.get(url, headers=headers, cookies=cookies, params=params, timeout=30)
            
            # Verificar si la petición fue exitosa
            if response.status_code != 200:
                print(f"Error HTTP {response.status_code} al obtener seguidos")
                break
            
            data = response.json()  # Convertir respuesta a JSON
            
            # Extraer lista de usuarios
            users = data.get('users', [])
            
            # Si no hay más usuarios, terminar
            if not users:
                print("No se encontraron más seguidos")
                break
            
            # Agregar usernames a la lista
            for user in users:
                if user.get('username'):
                    all_followers.append(user.get('username'))
            
            page_count += 1
            print(f"Página {page_count}: {len(users)} seguidos obtenidos - Total: {len(all_followers)}/{target_info['following_count']}")
            
            # Verificar si hay más páginas
            if not data.get('next_max_id') or not data.get('big_list', True):
                print("Fin de la lista de seguidos")
                break
            
            # Actualizar max_id para la siguiente página
            max_id = data.get('next_max_id')
            # Esperar entre peticiones para evitar ser bloqueado
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            print(f"Error en paginación: {e}")
            break
    
    print(f"Total de seguidores obtenidos: {len(all_followers)}")
    return all_followers, target_info

def process_follower_batch(followers_batch, session_id, batch_num, total_batches):
    """
    Procesa un lote de seguidores para obtener sus detalles
    
    Args:
        followers_batch (list): Lista de usernames a procesar
        session_id (str): ID de sesión para autenticación
        batch_num (int): Número del lote actual
        total_batches (int): Total de lotes
    
    Returns:
        list: Lista de diccionarios con información de los seguidores
    """
    
    batch_data = []  # Datos del lote actual
    processed_count = 0  # Contador de procesados
    
    # Procesar cada seguidor en el lote
    for follower_username in followers_batch:
        # Obtener información del seguidor
        follower_info = get_user_details(follower_username, session_id)
        if follower_info:
            # Agregar información relevante
            batch_data.append({
                'username': follower_info['username'],
                'follower_count': follower_info['follower_count'],
                'following_count': follower_info['following_count'],
                'biografia': follower_info['biografia'],
                'descripcion': follower_info['descripcion']
            })
            processed_count += 1
            
            # Mostrar progreso cada 5 procesados
            if processed_count % 5 == 0:
                print(f"   Lote {batch_num}/{total_batches}: {processed_count}/{len(followers_batch)} procesados")
        
        # Esperar entre peticiones para evitar ser bloqueado
        time.sleep(random.uniform(0.5, 1.5))
    
    print(f"Lote {batch_num}/{total_batches} completado: {len(batch_data)} seguidores procesados")
    return batch_data

def split_list_into_chunks(lst, num_chunks):
    """
    Divide una lista en chunks aproximadamente del mismo tamaño
    
    Args:
        lst (list): Lista a dividir
        num_chunks (int): Número de chunks a crear
    
    Returns:
        list: Lista de chunks
    """
    
    # Si la lista está vacía, retornar chunks vacíos
    if len(lst) == 0:
        return [[] for _ in range(num_chunks)]
    
    # Calcular tamaño promedio de cada chunk
    avg = len(lst) // num_chunks
    remainder = len(lst) % num_chunks  # Resto para distribuir
    
    chunks = []  # Lista de chunks
    start = 0    # Índice inicial
    
    # Crear cada chunk
    for i in range(num_chunks):
        # Calcular fin del chunk (distribuir el resto en los primeros chunks)
        end = start + avg + (1 if i < remainder else 0)
        chunks.append(lst[start:end])  # Agregar chunk
        start = end  # Actualizar inicio para siguiente chunk
    
    return chunks

def scrape_followers_parallel(target_username, session_id, num_threads):
    """
    Realiza el scraping de seguidores usando múltiples hilos
    
    Args:
        target_username (str): Usuario objetivo a scrapear
        session_id (str): ID de sesión para autenticación
        num_threads (int): Número de hilos a usar
    
    Returns:
        list: Lista con todos los datos obtenidos
    """
    
    print(f"Iniciando scraping paralelo con {num_threads} hilos...")
    
    # Obtener todos los seguidores del usuario objetivo
    all_followers, target_info = get_all_followers_list(target_username, session_id)
    
    # Verificar si se obtuvieron seguidores
    if not all_followers or not target_info:
        print("No se pudieron obtener seguidores")
        return []
    
    # Inicializar lista de datos con el usuario objetivo
    all_data = [{
        'username': target_info['username'],
        'follower_count': target_info['follower_count'],
        'following_count': target_info['following_count'],
        'biografia': target_info['biografia'],
        'descripcion': target_info['descripcion']
    }]
    
    # Dividir seguidores en chunks para procesamiento paralelo
    follower_chunks = split_list_into_chunks(all_followers, num_threads)
    
    print(f"Dividiendo {len(all_followers)} seguidores en {num_threads} lotes...")
    
    # Usar ThreadPoolExecutor para procesamiento paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []  # Lista de futuros (tareas asíncronas)
        
        # Enviar cada chunk a un hilo diferente
        for i, chunk in enumerate(follower_chunks):
            if chunk:  # Solo si el chunk no está vacío
                print(f"Iniciando lote {i+1}/{len(follower_chunks)} con {len(chunk)} seguidos")
                # Enviar tarea al executor
                future = executor.submit(process_follower_batch, chunk, session_id, i+1, len(follower_chunks))
                futures.append(future)
        
        # Recolectar resultados de los hilos
        completed_count = 0
        for future in concurrent.futures.as_completed(futures):
            try:
                batch_data = future.result()  # Obtener resultado del hilo
                all_data.extend(batch_data)   # Agregar a datos totales
                completed_count += 1
                print(f"Progreso general: {completed_count}/{len(futures)} lotes completados")
            except Exception as e:
                print(f"Error en lote: {e}")
                completed_count += 1
    
    print(f"Scraping completado. Total de perfiles obtenidos: {len(all_data)}")
    return all_data

def save_to_csv(data, filename):
    """
    Guarda los datos en un archivo CSV
    
    Args:
        data (list): Lista de diccionarios con datos
        filename (str): Nombre del archivo
    """
    try:
        # Crear directorio si no existe
        os.makedirs('PROFILES_DATA', exist_ok=True)
        filepath = os.path.join('PROFILES_DATA', filename)

        # Escribir datos en CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['username', 'follower_count', 'following_count', 'biografia', 'descripcion'])
            writer.writeheader()  # Escribir encabezados
            writer.writerows(data)  # Escribir datos
        
        print(f"Datos guardados en: {filepath}")
        
    except Exception as e:
        print(f"Error guardando CSV: {e}")

def main():
    target_username = input("Ingresa el username de Instagram a scrapear: ").strip()
    if not target_username:
        print("No se ingresó username")
        return
    
    num_threads = int(input(f"Número de hilos a usar: "))
    
    print(f"\nIniciando scraping de @{target_username}...")
    
    # Realizar scraping paralelo
    all_data = scrape_followers_parallel(target_username, SESSION_ID, num_threads)
    
    # Verificar si se obtuvieron datos
    if not all_data or len(all_data) <= 1:
        print("No se obtuvieron datos suficientes")
        return

    # Mostrar resumen de resultados
    print(f"\nRESULTADOS:")
    print(f"   • Perfiles obtenidos: {len(all_data)}")
    print(f"   • Usuario objetivo: @{all_data[0]['username']}")
    print(f"   • Seguidores objetivo: {all_data[0]['follower_count']}")
    print(f"   • Seguidos objetivo: {all_data[0]['following_count']}")
    print(f"   • Seguidores scrapeados: {len(all_data) - 1}")
    
    # Guardar datos en CSV
    filename = f"{target_username}_followers.csv"
    save_to_csv(all_data, filename)

# Punto de entrada del programa
if __name__ == "__main__":
    main()