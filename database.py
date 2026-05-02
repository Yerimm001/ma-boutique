import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Production : PostgreSQL sur Render
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        # Local : SQLite
        import sqlite3
        conn = sqlite3.connect('boutique.db')
        conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = get_db()
    cur = conn.cursor()
    
    if DATABASE_URL:
        # PostgreSQL
        cur.execute('''
            CREATE TABLE IF NOT EXISTS produits (
                id SERIAL PRIMARY KEY,
                nom TEXT NOT NULL,
                prix REAL NOT NULL,
                stock INTEGER,
                image TEXT DEFAULT 'default.jpg'
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS commandes (
                id SERIAL PRIMARY KEY,
                utilisateur_id TEXT,
                produit_id INTEGER,
                quantite INTEGER,
                date_commande TEXT,
                statut TEXT DEFAULT 'en attente'
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id SERIAL PRIMARY KEY,
                nom TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mot_de_passe TEXT NOT NULL
            )
        ''')
    else:
        # SQLite
        conn.execute('''
            CREATE TABLE IF NOT EXISTS produits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                prix REAL NOT NULL,
                stock INTEGER,
                image TEXT DEFAULT 'default.jpg'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS commandes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                utilisateur_id TEXT,
                produit_id INTEGER,
                quantite INTEGER,
                date_commande TEXT,
                statut TEXT DEFAULT 'en attente'
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS utilisateurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                mot_de_passe TEXT NOT NULL
            )
        ''')
    
    conn.commit()
    cur.close() if DATABASE_URL else None
    conn.close()

def ajouter_produits():
    DATABASE_URL = os.environ.get('DATABASE_URL')
    conn = get_db()
    
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM produits')
        count = cur.fetchone()['count']
        if count == 0:
            cur.execute('''
                INSERT INTO produits (nom, prix, stock, image) VALUES
                (%s, %s, %s, %s),
                (%s, %s, %s, %s),
                (%s, %s, %s, %s),
                (%s, %s, %s, %s)
            ''', (
                'T-shirt', 19.99, 50, 'tshirt.jpg',
                'Jean', 49.99, 30, 'jean.jpg',
                'Chaussures', 79.99, 20, 'chaussures.jpg',
                'Veste', 99.99, 15, 'veste.jpg'
            ))
        conn.commit()
        cur.close()
    else:
        produits = conn.execute('SELECT COUNT(*) FROM produits').fetchone()[0]
        if produits == 0:
            conn.execute('''
                INSERT INTO produits (nom, prix, stock, image) VALUES
                ('T-shirt', 19.99, 50, 'tshirt.jpg'),
                ('Jean', 49.99, 30, 'jean.jpg'),
                ('Chaussures', 79.99, 20, 'chaussures.jpg'),
                ('Veste', 99.99, 15, 'veste.jpg')
            ''')
            conn.commit()
    conn.close()