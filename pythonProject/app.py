from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector

app = Flask(__name__)


db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'Managementul_Unei_Banci'
}


db_connection = mysql.connector.connect(**db_config)
cursor = db_connection.cursor()

def get_table_names():
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    return [table[0] for table in tables]

def get_column_names(table_name):
    cursor.execute(f"SHOW COLUMNS FROM {table_name}")
    columns = cursor.fetchall()
    return [column[0] for column in columns]

def get_primary_key_column(table_name):
    cursor.execute(f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'")
    primary_key = cursor.fetchone()
    if primary_key:
        return primary_key[4]
    else:
        raise Exception(f"Nu s-a găsit cheia primară pentru tabelul {table_name}")

def update_record(table_name, record_id, column_name, new_value):
    try:
        primary_key_column = get_primary_key_column(table_name)
        cursor.execute(f"UPDATE {table_name} SET `{column_name}` = '{new_value}' WHERE {primary_key_column} = {record_id}")
        db_connection.commit()
        return {"status": "success", "message": "Modificarea a fost realizată cu succes."}
    except Exception as e:
        return {"status": "error", "message": f"Eroare la realizarea modificării: {str(e)}"}

def delete_record(table_name, record_id):
    try:
        primary_key_column = get_primary_key_column(table_name)
        cursor.execute(f"DELETE FROM {table_name} WHERE {primary_key_column} = {record_id}")
        db_connection.commit()
        return {"status": "success", "message": "Ștergerea a fost realizată cu succes."}
    except Exception as e:
        return {"status": "error", "message": f"Eroare la realizarea ștergerii: {str(e)}"}

@app.route('/')
def index():
    table_names = get_table_names()
    update_status = request.args.get('update_status')
    return render_template('index.html', table_names=table_names, update_status=update_status)

@app.route('/list_and_sort', methods=['POST'])
def list_and_sort():
    table_name = request.form['table_name']
    sort_column_name = request.form.get('sort_column')
    sort_direction = request.form.get('sort_direction', 'asc')

    table_names = get_table_names()
    cursor.execute(f'SELECT * FROM {table_name} ORDER BY `{sort_column_name}` {sort_direction}')
    result = cursor.fetchall()
    columns = get_column_names(table_name)

    return render_template('index.html', table_name=table_name, table_names=table_names, result=result,
                           sort_column_name=sort_column_name, sort_direction=sort_direction, columns=columns)

@app.route('/get_columns', methods=['POST'])
def get_columns():
    selected_table = request.form['table_name']
    columns = get_column_names(selected_table)
    return jsonify(columns)

@app.route('/edit/<table_name>/<record_id>/', methods=['GET'])
def edit_record_page(table_name, record_id):
    columns = get_column_names(table_name)
    column_name = request.args.get('column_name', columns[0])
    return render_template('edit.html', table_name=table_name, record_id=record_id, columns=columns, column_name=column_name)

@app.route('/update_record', methods=['POST'])
def update_record_route():
    result = update_record(request.form['table_name'], request.form['record_id'], request.form['column_name'], request.form['new_value'])
    return jsonify(result)

@app.route('/delete/<table_name>/<record_id>/', methods=['GET'])
def delete_record_page(table_name, record_id):
    return render_template('delete.html', table_name=table_name, record_id=record_id)

@app.route('/delete_record', methods=['POST'])
def delete_record_route():
    result = delete_record(request.form['table_name'], request.form['record_id'])
    return jsonify(result)

@app.route('/search_results')
def search_results():
    try:
        cursor.execute("""
            SELECT * FROM Tranzactii, Conturi, Clienti
            WHERE Conturi.Stat = 'Activ'
              AND Tranzactii.Suma < 0
              AND Tranzactii.Cont = Conturi.ContID
              AND Conturi.Clienti = Clienti.ClientID
        """)
        search_results = cursor.fetchall()


        columns = ["Tranzactii." + col[0] for col in cursor.description[:len(cursor.description)//3]]
        columns += ["Conturi." + col[0] for col in cursor.description[len(cursor.description)//3:2*len(cursor.description)//3]]
        columns += ["Clienti." + col[0] for col in cursor.description[2*len(cursor.description)//3:]]

        return render_template('search_results.html', search_results=search_results, columns=columns)


    except Exception as e:

        print("Error:", str(e))

        return render_template('search_results.html', error=str(e))

@app.route('/rezultate_sql')
def rezultate_sql():
    try:
        cursor.execute("""
            SELECT C.Nume, C.Prenume, COUNT(Co.ContID) AS Numar_Conturi
            FROM Clienti C
            JOIN Conturi Co ON C.ClientID = Co.Clienti
            GROUP BY C.Nume, C.Prenume
            HAVING Numar_Conturi > 1;
        """)
        rezultate_sql = cursor.fetchall()

        return render_template('rezultate_sql.html', rezultate_sql=rezultate_sql)

    except Exception as e:
        return render_template('rezultate_sql.html', error=str(e))

@app.route('/vizualizare_sume_conturi_moneda')
def vizualizare_sume_conturi_moneda():
    try:
        cursor.execute("SHOW TABLES LIKE 'Vizualizare_Sume_Conturi_Moneda'")
        existing_table = cursor.fetchone()

        if not existing_table:
            cursor.execute("""
            CREATE VIEW Vizualizare_Sume_Conturi_Moneda AS
            SELECT Moneda, SUM(SUMa) AS Suma_Totala
            FROM (
                SELECT Co.Moneda, SUM(T.Suma) AS SUMa
                FROM Conturi Co
                LEFT JOIN Tranzactii T ON Co.ContID = T.Cont
                GROUP BY Co.Moneda, Co.ContID
            ) AS SumeConturi
            GROUP BY Moneda;
        """)
            db_connection.commit()


        cursor.execute("SELECT * FROM Vizualizare_Sume_Conturi_Moneda")
        vizualizare_sume_conturi_moneda = cursor.fetchall()
        columns = ["Moneda", "Suma_Totala"]

        return render_template('vizualizare_sume_conturi_moneda.html', vizualizare_sume_conturi_moneda=vizualizare_sume_conturi_moneda, columns=columns)

    except Exception as e:
        return render_template('error_page.html', error=str(e))


@app.route('/vizualizare_informatii_depozite', methods=['GET', 'POST'])
def vizualizare_informatii_depozite():
    try:
        cursor.execute("SHOW TABLES LIKE 'Vizualizare_Informatii_Depozite'")
        existing_table = cursor.fetchone()

        if not existing_table:
            cursor.execute("""
                CREATE VIEW Vizualizare_Informatii_Depozite AS
                SELECT D.DepozitID, D.Data_Incepere, D.Data_Terminare, D.Penalizare, D.Dobanda,
                       C.Nume AS Nume_Client, C.Prenume AS Prenume_Client,
                       S.Nume AS Nume_Sucursala
                FROM Depozite D
                JOIN Conturi Co ON D.Cont = Co.ContID
                JOIN Clienti C ON Co.Clienti = C.ClientID
                JOIN Sucursale S ON Co.Sucursala = S.SucursalaID;
            """)
            db_connection.commit()


        cursor.execute("SELECT * FROM Vizualizare_Informatii_Depozite")
        vizualizare_data = cursor.fetchall()


        columns = ["DepozitID", "Data_Incepere", "Data_Terminare", "Penalizare", "Dobanda",
                   "Nume_Client", "Prenume_Client", "Nume_Sucursala"]

        return render_template('vizualizare_informatii_depozite.html', vizualizare_data=vizualizare_data,
                               columns=columns)

    except Exception as e:
        return redirect(url_for('index', update_status=f'Eroare la crearea/vizualizarea tabelului: {str(e)}'))

@app.route('/vizualizare_tranzactii', methods=['GET', 'POST'])
def vizualizare_tranzactii():
    try:
        cursor.execute("SHOW TABLES LIKE 'Vizualizare_Tranzactii'")
        existing_table = cursor.fetchone()

        if not existing_table:
            cursor.execute("""
                CREATE VIEW Vizualizare_Tranzactii AS
                SELECT *
                FROM Tranzactii;
            """)
            db_connection.commit()

        return redirect(url_for('vizualizare_tranzactii_page'))

    except Exception as e:
        return redirect(url_for('index', update_status=f'Eroare la crearea vizualizării: {str(e)}'))

@app.route('/vizualizare_tranzactii_page')
def vizualizare_tranzactii_page():
    try:
        cursor.execute("""
            SELECT * FROM Vizualizare_Tranzactii;
        """)
        tranzactii = cursor.fetchall()

        columns = ["Tranzactii." + col[0] for col in cursor.description]

        return render_template('vizualizare_tranzactii.html', tranzactii=tranzactii, columns=columns)

    except Exception as e:
        return redirect(url_for('index', update_status=f'Eroare la afișarea vizualizării: {str(e)}'))


@app.route('/edit_tranzactie/<int:tranzactie_id>', methods=['GET', 'POST'])
def edit_tranzactie(tranzactie_id):
    try:
        cursor.execute(f"SELECT * FROM Vizualizare_Tranzactii WHERE TranzactieID = {tranzactie_id}")
        tranzactie = cursor.fetchone()

        if request.method == 'POST':
            selected_column = request.form['select_column']
            new_value = request.form['new_value']

            result = update_tranzactie(tranzactie_id, selected_column, new_value)

            if result['status'] == 'success':
                return redirect(url_for('vizualizare_tranzactii_page', update_status=result['message']))
            else:
                return render_template('edit_tranzactie.html', tranzactie=tranzactie, error=result['message'],
                                       columns=get_column_names('Vizualizare_Tranzactii'),
                                       selected_column=selected_column)

        return render_template('edit_tranzactie.html', tranzactie=tranzactie,
                               columns=get_column_names('Vizualizare_Tranzactii'))

    except Exception as e:
        return redirect(url_for('index', update_status=f'Eroare la editarea tranzacției: {str(e)}'))

def update_tranzactie(tranzactie_id, column_name, new_value):
    try:
        cursor.execute(f"UPDATE Tranzactii SET `{column_name}` = '{new_value}' WHERE TranzactieID = {tranzactie_id}")
        db_connection.commit()
        return {"status": "success", "message": "Tranzacția a fost actualizată cu succes."}
    except Exception as e:
        return {"status": "error", "message": f"Eroare la actualizarea tranzacției: {str(e)}"}
@app.route('/delete_tranzactie/<int:tranzactie_id>', methods=['GET'])
def delete_tranzactie(tranzactie_id):
    try:
        return render_template('confirm_delete_tranzactie.html', tranzactie_id=tranzactie_id)

    except Exception as e:
        return redirect(url_for('index', update_status=f'Eroare la ștergerea tranzacției: {str(e)}'))

@app.route('/confirm_delete_tranzactie/<int:tranzactie_id>', methods=['POST'])
def confirm_delete_tranzactie(tranzactie_id):
    try:
        result = delete_tranzactie_by_id(tranzactie_id)

        if result['status'] == 'success':
            return redirect(url_for('vizualizare_tranzactii_page', update_status=result['message']))
        else:
            return render_template('confirm_delete_tranzactie.html', tranzactie_id=tranzactie_id, error=result['message'])

    except Exception as e:
        return redirect(url_for('index', update_status=f'Eroare la ștergerea tranzacției: {str(e)}'))

def delete_tranzactie_by_id(tranzactie_id):
    try:
        cursor.execute(f"DELETE FROM Tranzactii WHERE TranzactieID = {tranzactie_id}")
        db_connection.commit()
        return {"status": "success", "message": "Tranzacția a fost ștearsă cu succes."}
    except Exception as e:
        return {"status": "error", "message": f"Eroare la ștergerea tranzacției: {str(e)}"}


if __name__ == '__main__':
    app.run(debug=True)
