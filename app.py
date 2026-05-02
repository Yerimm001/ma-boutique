from flask import Flask, render_template, request, redirect, session
from database import init_db, get_db, ajouter_produits
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = 'ma_cle_secrete_123'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
ADMIN_EMAIL = 'diengyerim01@gmail.com'

DATABASE_URL = os.environ.get('DATABASE_URL')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def query(conn, sql, params=()):
    # Fonction qui gère SQLite et PostgreSQL automatiquement
    if DATABASE_URL:
        cur = conn.cursor()
        cur.execute(sql.replace('?', '%s'), params)
        return cur
    else:
        return conn.execute(sql, params)

init_db()
ajouter_produits()

@app.route('/')
def accueil():
    return render_template('index.html')

@app.route('/produits')
def produits():
    conn = get_db()
    liste_produits = query(conn, 'SELECT * FROM produits').fetchall()
    conn.close()
    return render_template('produits.html', produits=liste_produits)

@app.route('/commander/<int:id>')
def commander(id):
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn = get_db()
    produit = query(conn, 'SELECT * FROM produits WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('commande.html', produit=produit)

@app.route('/passer_commande', methods=['POST'])
def passer_commande():
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn = get_db()
    produit_id = request.form['produit_id']
    nom = session['utilisateur_nom']
    quantite = int(request.form['quantite'])
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    produit = query(conn, 'SELECT * FROM produits WHERE id = ?', (produit_id,)).fetchone()
    if quantite > produit['stock']:
        conn.close()
        return render_template('erreur.html', message='Stock insuffisant !')
    query(conn, '''
        INSERT INTO commandes (utilisateur_id, produit_id, quantite, date_commande, statut)
        VALUES (?, ?, ?, ?, 'en attente')
    ''', (session['utilisateur_id'], produit_id, quantite, date))
    query(conn, 'UPDATE produits SET stock = stock - ? WHERE id = ?', (quantite, produit_id))
    conn.commit()
    conn.close()
    return render_template('confirmation.html', nom=nom, produit=produit, quantite=quantite)

@app.route('/commandes')
def commandes():
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn = get_db()
    liste_commandes = query(conn, '''
        SELECT commandes.utilisateur_id AS nom_client,
               produits.nom AS nom_produit,
               commandes.quantite,
               commandes.date_commande,
               (commandes.quantite * produits.prix) AS prix_total
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
    ''').fetchall()
    conn.close()
    return render_template('commandes.html', commandes=liste_commandes)

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        mot_de_passe = generate_password_hash(request.form['mot_de_passe'])
        conn = get_db()
        try:
            query(conn, 'INSERT INTO utilisateurs(nom,email,mot_de_passe) VALUES(?,?,?)',
                  (nom, email, mot_de_passe))
            conn.commit()
            conn.close()
            return redirect('/connexion')
        except:
            conn.close()
            return render_template('inscription.html', erreur='Email déjà utilisé !')
    return render_template('inscription.html')

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        conn = get_db()
        utilisateur = query(conn, 'SELECT * FROM utilisateurs WHERE email = ?', (email,)).fetchone()
        conn.close()
        if utilisateur and check_password_hash(utilisateur['mot_de_passe'], mot_de_passe):
            session['utilisateur_id'] = utilisateur['id']
            session['utilisateur_nom'] = utilisateur['nom']
            if utilisateur['email'] == ADMIN_EMAIL:
                session['est_admin'] = True
            return redirect('/produits')
        return render_template('connexion.html', erreur='Email ou mot de passe incorrect !')
    return render_template('connexion.html')

@app.route('/deconnexion')
def deconnexion():
    session.clear()
    return redirect('/')

@app.route('/admin')
def admin():
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    commandes = query(conn, '''
        SELECT commandes.id, commandes.utilisateur_id AS nom_client,
               produits.nom AS nom_produit, commandes.quantite,
               commandes.date_commande, commandes.statut,
               (commandes.quantite * produits.prix) AS prix_total
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
    ''').fetchall()
    produits = query(conn, 'SELECT * FROM produits').fetchall()
    chiffre_affaires = query(conn, '''
        SELECT SUM(commandes.quantite * produits.prix)
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
        WHERE commandes.statut = 'validée'
    ''').fetchone()[0] or 0
    produit_top = query(conn, '''
        SELECT produits.nom, SUM(commandes.quantite) AS total
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
        GROUP BY produits.nom
        ORDER BY total DESC
        LIMIT 1
    ''').fetchone()
    nb_utilisateurs = query(conn, 'SELECT COUNT(*) FROM utilisateurs').fetchone()[0]
    nb_commandes = query(conn, 'SELECT COUNT(*) FROM commandes').fetchone()[0]
    conn.close()
    return render_template('admin.html',
                          commandes=commandes,
                          produits=produits,
                          chiffre_affaires=chiffre_affaires,
                          produit_top=produit_top,
                          nb_utilisateurs=nb_utilisateurs,
                          nb_commandes=nb_commandes)

@app.route('/admin/ajouter_produit', methods=['POST'])
def ajouter_produit():
    if not session.get('est_admin'):
        return redirect('/')
    nom = request.form['nom']
    prix = request.form['prix']
    stock = request.form['stock']
    image = 'default.jpg'
    if 'image' in request.files:
        fichier = request.files['image']
        if fichier and allowed_file(fichier.filename):
            filename = secure_filename(fichier.filename)
            fichier.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = filename
    conn = get_db()
    query(conn, 'INSERT INTO produits (nom, prix, stock, image) VALUES (?, ?, ?, ?)',
          (nom, prix, stock, image))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/valider/<int:id>')
def valider_commande(id):
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    query(conn, "UPDATE commandes SET statut = 'validée' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/annuler/<int:id>')
def annuler_commande(id):
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    commande = query(conn, 'SELECT * FROM commandes WHERE id = ?', (id,)).fetchone()
    query(conn, 'UPDATE produits SET stock = stock + ? WHERE id = ?',
          (commande['quantite'], commande['produit_id']))
    query(conn, "UPDATE commandes SET statut = 'annulée' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/supprimer/<int:id>')
def supprimer_produit(id):
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    query(conn, 'DELETE FROM produits WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/mes_commandes')
def mes_commandes():
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn = get_db()
    commandes = query(conn, '''
        SELECT commandes.id,
               produits.nom AS nom_produit,
               commandes.quantite,
               commandes.date_commande,
               commandes.statut,
               (commandes.quantite * produits.prix) AS prix_total
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
        WHERE commandes.utilisateur_id = ?
        ORDER BY commandes.date_commande DESC
    ''', (session['utilisateur_id'],)).fetchall()
    conn.close()
    return render_template('mes_commandes.html', commandes=commandes)

@app.route('/admin/modifier_produit/<int:id>', methods=['POST'])
def modifier_produit(id):
    if not session.get('est_admin'):
        return redirect('/')
    prix = request.form['prix']
    stock = request.form['stock']
    conn = get_db()
    query(conn, 'UPDATE produits SET prix = ?, stock = ? WHERE id = ?', (prix, stock, id))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)