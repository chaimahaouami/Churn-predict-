import pickle
import os
import pandas as pd
import oracledb
import psycopg2
from flask import Flask, render_template, request, redirect, flash, session

# Initialisation flask app
app = Flask(__name__)
app.secret_key = 'secret key'  



import oracledb
#cnx oracle
try:
    connection = oracledb.connect(
        user="pfe",
        password="chaimapfe",
        dsn = "localhost:1521/orclpdb"

    )
except Exception as e:
    print("Erreur de connexion Oracle :", e)
    connection = None

if connection is not None:
    cursor = connection.cursor()
else:
    print("Connexion non établie")


# Variables globales
users = {}


@app.route('/', methods=['GET', 'POST'])
def connexion_consultant():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
# Connexion à la base PostgreSQL
        try:
            conn = psycopg2.connect(
                host="localhost",       
                database="Tunisie_telecom",
                user="postgres",
                password="postgres"
            )
            cursor = conn.cursor()

            # Vérification de l’utilisateur
            cursor.execute("SELECT email FROM users WHERE email=%s AND password=%s", (email, password))
            users = cursor.fetchone()

            cursor.close()
            conn.close()

            if users:
                session['user'] = email
                flash('Connexion réussie !')
                return redirect('/accueil')
            else:
                flash("Email ou mot de passe incorrect.")
                return redirect(request.referrer or '/')

        except Exception as e:
            print("Erreur de connexion :", e)
            flash("Une erreur est survenue lors de la connexion à la base.")
            return redirect(request.referrer or '/')

    return render_template('login.html')


# Route : Login via Microsoft 
@app.route('/login_microsoft')
def login_microsoft():
    return redirect('https://account.microsoft.com/')




# Route : Upload de fichier et insertion Oracle
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    # Vérifie si l'utilisateur est connecté
    if 'user' not in session:
        flash("Veuillez vous connecter pour accéder à cette page.", 'danger')
        return redirect('/')

    # Bloque l'accès si l'email contient "décideur" ou "decideur"
    if 'décideur' in session['user'].lower() or 'decideur' in session['user'].lower():
        flash("Accès refusé : les décideurs ne peuvent pas actualiser la base.", 'danger')
        return redirect('/accueil')

    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            try:
                # Lecture du fichier
                if uploaded_file.filename.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                elif uploaded_file.filename.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file)
                else:
                    flash('Format non supporté. Veuillez charger un fichier .csv ou .xlsx.')
                    return redirect(request.url)

                cursor = connection.cursor()
                cursor.execute('TRUNCATE TABLE SOURCE_DATA')

                def normalize_col(col):
                    return (col.strip().upper()
                            .replace("É", "E").replace("È", "E").replace("À", "A")
                            .replace("Ù", "U").replace("Ô", "O").replace("Ç", "C")
                            .replace("Â", "A").replace("Ê", "E").replace("Ë", "E")
                            .replace("Ï", "I").replace("Î", "I").replace("Œ", "OE")
                            .replace(" ", "_"))

                df.columns = [normalize_col(col) for col in df.columns]
                df = df.fillna(0)

                columns = df.columns.tolist()
                if not columns:
                    flash(f"{uploaded_file.filename} : Aucune colonne valide trouvée.")
                    return redirect(request.url)

                col_str = ', '.join([f'"{col}"' for col in columns])
                bind_vars = ', '.join([f":{i+1}" for i in range(len(columns))])
                insert_sql = f"INSERT INTO SOURCE_DATA ({col_str}) VALUES ({bind_vars})"

                for _, row in df.iterrows():
                    values = [row[col] for col in columns]
                    cursor.execute(insert_sql, values)

                connection.commit()
                flash('Fichier inséré avec succès dans la table SOURCE_DATA.')

            except oracledb.DatabaseError as e:
                error, = e.args
                flash(f"Erreur Oracle : {error.message}")
                connection.rollback()
        else:
            flash('Aucun fichier sélectionné.')
        return redirect(request.url)

    return render_template('upload.html')

# Chargement du modèle ML
with open("randomForest.pkl", "rb") as file:
    model = pickle.load(file)

# Route : Formulaire pour prédiction
@app.route('/form')
def form():
    return render_template('form.html')

# Route : Résultat de prédiction
@app.route('/predict', methods=["POST"])
def predict():
    try:
        features = [
            float(request.form['Ancienneté']),
            float(request.form['durée_appel_jour(minutes)']),
            float(request.form['nb_appel_jour']),
            float(request.form['durée_appel_soirée(minutes)']),
            float(request.form['nb_appel_soirée']),
            float(request.form['durée_appel_nuit(minutes)']),
            float(request.form['nb_appel_nuit']),
            float(request.form['durée_appel_inter(minutes)']),
            float(request.form['nb_appel_inter']),
            float(request.form['Message vocal']),
            float(request.form['nb_msg_vocaux']),
            float(request.form['nb_reclamation']),
            float(request.form['Nb_total_SMS']),
            float(request.form['Volume_DATA']),
        ]
        prediction = model.predict([features])[0]
        result = "Client en churn" if prediction == 1 else "Client non churn"
        return render_template("form.html", prediction=result)
    except Exception as e:
        flash(f"Erreur dans la prédiction : {str(e)}")
        return redirect('/form')

# Route : Tableau de bord
@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")

# Route : Page d'accueil
@app.route('/accueil')
def accueil():
    return render_template('accueil.html')

# Lancer l'application
if __name__ == '__main__':
    app.run(debug=True)
