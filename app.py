from flask import Flask, request, jsonify, send_from_directory, render_template
import sqlite3
import os
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64

app = Flask(__name__, static_folder='static')

@app.route('/pltgen.js')
def serve_js():
    return send_from_directory('static', 'pltgen.js') #works on magic

DATABASE = 'formulas.db' #default database
CSV_FILE = 'formulas.csv' #look for csv file

#database is a valid SQLite file
def DatabaseValid(file_path):
    if not os.path.exists(file_path):
        return False
    try:
        conn = sqlite3.connect(file_path)
        conn.execute('SELECT name FROM sqlite_master WHERE type="table";')
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False

#database exists
def Setup():
    if not DatabaseValid(DATABASE):
        print(f"Error: {DATABASE} is not a valid SQLite database.")
        return

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS formulas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        output TEXT NOT NULL,
                        inputs TEXT NOT NULL,
                        expression TEXT NOT NULL
                      )''')
    conn.commit()

    if os.path.exists(CSV_FILE):
        try:
            import pandas as pd
            df = pd.read_csv(CSV_FILE)
            df.to_sql('formulas', conn, if_exists='replace', index=False)
            conn.commit()
            print(f"{CSV_FILE} successfully imported.")
        except Exception as e:
            print(f"Error importing {CSV_FILE}: {e}")
    else:
        print(f"Warning: {CSV_FILE} not found. Using existing database.")

    conn.close()

# Get units from the database
@app.route('/get_units', methods=['GET'])
def GetUnits(): #Currently unused?
    if not DatabaseValid(DATABASE):
        print(f"Error: {DATABASE} is not a valid SQLite database.") #throw if not valid
        return jsonify([])

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT output FROM formulas")
        units = [row[0] for row in cursor.fetchall()]
        return jsonify(units)
    except Exception as e:
        print(f"Database error while fetching units: {e}")
        return jsonify([])
    finally:
        conn.close()

def LoadFormulas():
    if not DatabaseValid(DATABASE):
        print(f"Error: {DATABASE} is not a valid SQLite database.")
        return []

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT output, inputs, expression FROM formulas")
        formulas = []
        for row in cursor.fetchall():
            output, inputs, expression = row
            inputs_list = [x.strip() for x in inputs.split(',')]
            formulas.append({
                "output": output.strip(),
                "inputs": inputs_list,
                "expression": expression.strip()
            })
        return formulas
    except Exception as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

def SolveChain(known_values, desired):
    formulas = LoadFormulas()
    if not formulas:
        return None, "No formulas available to solve the problem."

    while True:
        if desired in known_values:
            return known_values[desired], None
        progress = False
        for f in formulas:
            output = f['output']
            if output in known_values:
                continue
            if all(var in known_values for var in f['inputs']):
                try:
                    result = eval(f['expression'], {}, known_values)
                except Exception as e:
                    continue
                known_values[output] = result
                progress = True
        if not progress:
            break

    if desired not in known_values:
        return None, "Insufficient data or input is too limited to compute the desired unit."
    return known_values[desired], None

@app.route('/')
def Index():
    return send_from_directory('', 'index.html')
    
@app.route('/plot')
def PlotPage():
    return send_from_directory('.', 'pltgen.html')
    
# Upload CSV/JSON for plotting
@app.route('/upload_data', methods=['POST'])
def UserUpload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith('.json'):
            df = pd.read_json(file)
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
        
        data = df.to_dict(orient='records')
        # Automatically generate a plot from the uploaded data.
        return generate_plot_from_data(data)
    except Exception as e:
        return jsonify({'error': f'Failed to process file: {e}'}), 500

@app.route('/generate_plot', methods=['POST'])
def GeneratePlot():
    data = request.json
    return FromData(data.get('points', []), data.get('type', 'line'))

def FromData(points, plot_type='line'):  #Replaced with
    data = request.json
    plot_type = data.get('type', 'line')
    points = data.get('points', [])

    # Debugging log
    print(f"Received plot type: {plot_type}")
    print(f"Received data points: {points}")

    if not points:
        return jsonify({'error': 'No data points provided'}), 400

    fig, ax = plt.subplots()

    try:
        if plot_type in ['line', 'scatter']:
            x_values = [p.get('x') for p in points if 'x' in p and 'y' in p]
            y_values = [p.get('y') for p in points if 'x' in p and 'y' in p]
            if not x_values or not y_values:
                return jsonify({'error': 'Invalid X/Y values'}), 400
            if plot_type == 'line':
                ax.plot(x_values, y_values, marker='o', linestyle='-')
            else:
                ax.scatter(x_values, y_values)
            ax.set_xlabel('X Axis')
            ax.set_ylabel('Y Axis')

        elif plot_type == 'bar':
            labels = [p.get('label', '') for p in points if 'label' in p and 'value' in p]
            values = [p.get('value') for p in points if 'label' in p and 'value' in p]
            if not labels or not values:
                return jsonify({'error': 'Invalid bar chart data'}), 400
            ax.bar(labels, values, color='skyblue')
            ax.set_ylabel('Value')

        elif plot_type == 'pie':
            labels = [p.get('label', '') for p in points if 'label' in p and 'value' in p]
            values = [p.get('value') for p in points if 'label' in p and 'value' in p]
            if not labels or not values:
                return jsonify({'error': 'Invalid pie chart data'}), 400
            ax.pie(values, labels=labels, autopct='%1.1f%%', colors=plt.cm.Paired.colors)

        elif plot_type == 'radar':
            labels = [p.get('label') for p in points if 'label' in p and 'value' in p]
            values = [p.get('value') for p in points if 'label' in p and 'value' in p]
    
            if not labels or not values:
                return jsonify({'error': 'Invalid radar chart data'}), 400

            values += values[:1]  # Close the loop
            num_vars = len(labels)
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            angles += angles[:1]  # Complete the circular plot
        
            fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)

            ax.plot(angles, values, 'o-', linewidth=2)
            ax.fill(angles, values, alpha=0.25)

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels)

        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
        plt.close()

        return jsonify({'plot_url': f'data:image/png;base64,{img_base64}'})
    
    except Exception as e:
        print(f"Plot generation error: {e}")
        return jsonify({'error': 'Failed to generate plot'}), 500


@app.route('/find_formula', methods=['POST'])
def FindCorrect():
    data = request.json
    known_values = data.get('known_values', {})
    desired_unit = data.get('desired_unit', '')

    if not known_values or not desired_unit:
        return jsonify({'error': 'Please provide known values and the desired unit.'}), 400

    result, error = SolveChain(known_values, desired_unit)
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'result': result})

if __name__ == '__main__':
    Setup()
    app.run(host='0.0.0.0', port=5000)