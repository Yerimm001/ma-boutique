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
ADMIN_EMAIL = 'diengyerim01@gmail.com'  


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

init_db()
ajouter_produits()

@app.route('/')
def accueil():
    return render_template('index.html')

@app.route('/produits')
def produits():
    conn = get_db()
    liste_produits = conn.execute('SELECT * FROM produits').fetchall()
    conn.close()
    return render_template('produits.html', produits=liste_produits)

# <int:id> récupère l'id du produit dans l'URL
@app.route('/commander/<int:id>')
def commander(id):
    # Vérifier si l'utilisateur est connecté
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn = get_db()
    produit = conn.execute('SELECT * FROM produits WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('commande.html', produit=produit)
# POST = reçoit les données du formulaire

@app.route('/passer_commande', methods=['POST'])
def passer_commande():
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    
    conn = get_db()
    produit_id = request.form['produit_id']
    # Utilise le nom de la session au lieu du formulaire
    nom = session['utilisateur_nom']
    quantite = int(request.form['quantite'])
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    produit = conn.execute('SELECT * FROM produits WHERE id = ?', (produit_id,)).fetchone()
    
    if quantite > produit['stock']:
        conn.close()
        return render_template('erreur.html', message='Stock insuffisant !')
    
    conn.execute('''
        INSERT INTO commandes (utilisateur_id, produit_id, quantite, date_commande, statut)
        VALUES (?, ?, ?, ?, 'en attente')
    ''', (session['utilisateur_id'], produit_id, quantite, date))
    
    conn.execute('UPDATE produits SET stock = stock - ? WHERE id = ?', (quantite, produit_id))
    conn.commit()
    conn.close()
    
    return render_template('confirmation.html', nom=nom, produit=produit, quantite=quantite)
@app.route('/commandes')
def commandes():
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn=get_db()
    
    liste_commandes=conn.execute('''
                                 SELECT
                                    commandes.utilisateur_id AS nom_client,
                                    produits.nom AS nom_produit,
                                    commandes.quantite,
                                    commandes.date_commande,
                                    (commandes.quantite * produits.prix) AS prix_total
                                 FROM commandes
                                 JOIN produits ON commandes.produit_id = produits.id
                                 ''').fetchall()
    conn.close()
    return render_template('commandes.html',commandes=liste_commandes)


@app.route('/inscription',methods=['GET','POST'])
def inscription():
    if request.method == 'POST':
        nom=request.form['nom']
        email=request.form['email']

        mot_de_passe=generate_password_hash(request.form['mot_de_passe'])
        conn=get_db()
        try:
            conn.execute('INSERT INTO utilisateurs(nom,email,mot_de_passe) VALUES(?,?,?)',
                         (nom,email,mot_de_passe))
            conn.commit()
            conn.close()
            return redirect('/connexion')
        except:
            conn.close()
            return render_template('inscription.html',erreur='Email déjà utilisé !')
    return render_template('inscription.html')


@app.route('/connexion',methods=['GET','POST'])
def connexion():
    if request.method == 'POST':
        email=request.form['email']
        mot_de_passe=request.form['mot_de_passe']
        conn=get_db()
        utilisateur=conn.execute('SELECT * FROM utilisateurs WHERE email = ?',(email,)).fetchone()
        conn.close()
        if utilisateur and check_password_hash(utilisateur['mot_de_passe'],mot_de_passe):
            session['utilisateur_id']=utilisateur['id']
            session['utilisateur_nom']=utilisateur['nom']
            if utilisateur['email']==ADMIN_EMAIL:
                session['est_admin'] =True
            return redirect('/produits')
        return render_template('connexion.html',erreur='Email ou mot de passe incorrect !')
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
    
    commandes = conn.execute('''
        SELECT commandes.id, commandes.utilisateur_id AS nom_client,
               produits.nom AS nom_produit, commandes.quantite,
               commandes.date_commande, commandes.statut,
               (commandes.quantite * produits.prix) AS prix_total
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
    ''').fetchall()
    
    produits = conn.execute('SELECT * FROM produits').fetchall()
    
    # Statistiques
    chiffre_affaires = conn.execute('''
        SELECT SUM(commandes.quantite * produits.prix)
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
        WHERE commandes.statut = 'validée'
    ''').fetchone()[0] or 0

    produit_top = conn.execute('''
        SELECT produits.nom, SUM(commandes.quantite) AS total
        FROM commandes
        JOIN produits ON commandes.produit_id = produits.id
        GROUP BY produits.nom
        ORDER BY total DESC
        LIMIT 1
    ''').fetchone()

    nb_utilisateurs = conn.execute('SELECT COUNT(*) FROM utilisateurs').fetchone()[0]
    nb_commandes = conn.execute('SELECT COUNT(*) FROM commandes').fetchone()[0]

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
    
    # Gérer l'image
    image = 'default.jpg'
    if 'image' in request.files:
        fichier = request.files['image']
        if fichier and allowed_file(fichier.filename):
            filename = secure_filename(fichier.filename)
            fichier.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = filename
    
    conn = get_db()
    conn.execute('INSERT INTO produits (nom, prix, stock, image) VALUES (?, ?, ?, ?)',
                (nom, prix, stock, image))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/valider/<int:id>')
def valider_commande(id):
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    conn.execute("UPDATE commandes SET statut = 'validée' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/annuler/<int:id>')
def annuler_commande(id):
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    # Remettre le stock
    commande = conn.execute('SELECT * FROM commandes WHERE id = ?', (id,)).fetchone()
    conn.execute('UPDATE produits SET stock = stock + ? WHERE id = ?',
                (commande['quantite'], commande['produit_id']))
    conn.execute("UPDATE commandes SET statut = 'annulée' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/supprimer/<int:id>')
def supprimer_produit(id):
    if not session.get('est_admin'):
        return redirect('/')
    conn = get_db()
    conn.execute('DELETE FROM produits WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/mes_commandes')
def mes_commandes():
    if 'utilisateur_id' not in session:
        return redirect('/connexion')
    conn = get_db()
    commandes = conn.execute('''
        SELECT 
            commandes.id,
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
    conn.execute('UPDATE produits SET prix = ?, stock = ? WHERE id = ?', (prix, stock, id))
    conn.commit()
    conn.close()
    return redirect('/admin')
# Lance le serveur
# debug=True recharge automatiquement quand vous modifiez le code
if __name__ == '__main__':
    app.run(debug=True)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
