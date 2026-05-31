import streamlit as st
import hashlib
import json
import datetime
import os

# Configuración de archivos
USERS_FILE = "data/users.json"
LOGS_FILE = "data/access_logs.json"

def hash_password(password):
    """Hashea la contraseña con SHA-256 (simple pero funcional)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def load_users():
    if not os.path.exists(USERS_FILE):
        # Usuario por defecto para primera ejecución
        default_users = {
            "usuarios": [
                {
                    "username": "admin",
                    "nombre": "Administrador",
                    "area": "TI",
                    "rol": "admin",
                    "password_hash": hash_password("cambiar123")
                }
            ]
        }
        os.makedirs("data", exist_ok=True)
        with open(USERS_FILE, "w") as f:
            json.dump(default_users, f, indent=4)
        return default_users
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def log_access(username, ip, resultado):
    """Registra cada intento de acceso"""
    os.makedirs("data", exist_ok=True)
    logs = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, "r") as f:
            logs = json.load(f)
    
    logs.append({
        "username": username,
        "fecha_hora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": ip,
        "resultado": resultado
    })
    
    # Mantener solo los últimos 10,000 registros (evita crecimiento infinito)
    if len(logs) > 10000:
        logs = logs[-10000:]
    
    with open(LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def login_screen():
    st.title("Acceso al Sistema")
    st.markdown("### Transparencia y Gestión Institucional")
    
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    # Obtener IP (simplificado, en servidor real se obtiene de los headers)
    ip = st.context.headers.get("X-Forwarded-For", "127.0.0.1") if hasattr(st, 'context') else "local"
    
    if st.button("Ingresar"):
        users_db = load_users()
        user_found = None
        for user in users_db["usuarios"]:
            if user["username"] == username:
                user_found = user
                break
        
        if user_found and verify_password(password, user_found["password_hash"]):
            # Login exitoso
            log_access(username, ip, "exito")
            st.session_state["authenticated"] = True
            st.session_state["user"] = {
                "username": user_found["username"],
                "nombre": user_found["nombre"],
                "area": user_found["area"],
                "rol": user_found["rol"]
            }
            st.rerun()
        else:
            # Login fallido
            log_access(username, ip, "fallo")
            st.error("Usuario o contraseña incorrectos")

def Menuprincipal():
    st.sidebar.title(f"Bienvenido, {st.session_state['user']['nombre']}")
    st.sidebar.markdown(f"Área: {st.session_state['user']['area']}")
    st.sidebar.markdown(f"Rol: {st.session_state['user']['rol']}")
    
    if st.sidebar.button("Cerrar sesión"):
        for key in ["authenticated", "user"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Aquí va el contenido principal de tu aplicación
    st.title("Panel de Gestión")
    st.write("Bienvenido al sistema. Aquí irán tus indicadores y análisis.")

# --- Flujo principal ---
# En Controlacceso.py, después del login exitoso
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    login_screen()
else:
    # ✅ Esto NO abre otra página. Ejecuta la función dentro del mismo proceso
    from Menuprincipal import mostrar_menu
    mostrar_menu()