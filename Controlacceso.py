# Controlacceso.py - Versión para Streamlit Cloud
import streamlit as st
import hashlib
import datetime

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """Carga usuarios desde st.secrets (Streamlit Cloud) o fallback local"""
    try:
        if "users" in st.secrets:
            return {
                "usuarios": [
                    {
                        "username": "admin",
                        "nombre": st.secrets["users"]["admin_nombre"],
                        "area": st.secrets["users"]["admin_area"],
                        "rol": st.secrets["users"]["admin_rol"],
                        "password_hash": st.secrets["users"]["admin_password"]
                    }
                ]
            }
    except:
        pass
    
    # Fallback para desarrollo local (con JSON)
    import json, os
    USERS_FILE = "data/users.json"
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    
    # Si no hay nada, usuario por defecto en memoria
    return {
        "usuarios": [
            {
                "username": "admin",
                "nombre": "Administrador",
                "area": "TI",
                "rol": "admin",
                "password_hash": hash_password("admin")
            }
        ]
    }

def login_screen():
    st.title("Acceso al Sistema")
    st.markdown("### Transparencia y Gestión Institucional")
    
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        users_db = load_users()
        user_found = None
        for user in users_db["usuarios"]:
            if user["username"] == username:
                user_found = user
                break
        
        if user_found and hash_password(password) == user_found["password_hash"]:
            st.session_state["authenticated"] = True
            st.session_state["user"] = {
                "username": user_found["username"],
                "nombre": user_found["nombre"],
                "area": user_found["area"],
                "rol": user_found["rol"]
            }
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

# --- Menú principal (importado desde tu otro archivo) ---
from Menuprincipal import mostrar_menu

# --- Flujo principal ---
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    login_screen()
else:
    mostrar_menu()