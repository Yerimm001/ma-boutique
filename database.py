import sqlite3

# Connexion à la base de données
# Si le fichier n'existe pas, SQLite le crée automatiquement
def get_db():
    conn = sqlite3.connect('boutique.db')
    # row_factory permet d'accéder aux colonnes par leur nom
    # ex: utilisateur['nom'] au lieu de utilisateur[0]
    conn.row_factory = sqlite3.Row
    return conn

# Créer les tables au démarrage
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prix REAL NOT NULL,
            stock INTEGER,
            image TEXT DEFAUTL 'default.jpg'
        )
    ''')
    conn.execute('''
                 CREATE TABLE IF NOT EXISTS utilisateurs(
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     nom TEXT NOT NULL,
                     email TEXT UNIQUE NOT NULL,
                     mot_de_passe TEXT NOT NULL
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
    # Sauvegarder les changements
    conn.commit()
    conn.close()
    
def ajouter_produits():
    conn = get_db()
    produits = conn.execute('SELECT COUNT(*) FROM produits').fetchone()[0]
    if produits == 0:
        conn.execute('''
            INSERT INTO produits (nom, prix, stock, image) VALUES
            ('T-shirt', 19.99, 50, 'default.jpg'),
            ('Jean', 49.99, 30, 'default.jpg'),
            ('Chaussures', 79.99, 20, 'default.jpg'),
            ('Veste', 99.99, 15, 'default.jpg')
        ''')
        conn.commit()
    conn.close()



