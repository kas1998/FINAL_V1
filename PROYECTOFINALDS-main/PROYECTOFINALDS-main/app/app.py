from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from flask_weasyprint import HTML, render_pdf
from models.models import Usuario, agregar_usuario, obtener_usuario_por_correo, existe_usuario
from pymongo import MongoClient
import openai
import time
# Conexión a MongoDB

app = Flask(__name__, static_folder='static')
app.secret_key = 'tu_clave_secreta_aqui'
client = MongoClient('mongodb://localhost:27017/')
db = client['C']  # Cambia al nombre de tu BD
openai.api_key = 'sk-proj-yMrGjlehKO6eqjh6BrIXT3BlbkFJFDf47VGlWYlygrp8DVZu'

@app.route('/')
def index():
    return render_template('Index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombres_completos']
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        if existe_usuario(correo):
            flash('El correo electrónico ya está registrado.', 'error')
        else:
            nuevo_usuario = Usuario(nombre, correo, contraseña)
            agregar_usuario(nuevo_usuario)
            flash('Registro exitoso. Por favor inicie sesión.', 'success')
        return redirect(url_for('index'))
    return render_template('Index.html')

@app.route('/inicio_sesion', methods=['GET', 'POST'])
def inicio_sesion():
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        usuario = obtener_usuario_por_correo(correo)
        if usuario and usuario.verificar_contraseña(contraseña):
            session['usuario_logueado'] = usuario.correo
            return redirect(url_for('funcionamiento'))
        else:
            flash('Correo electrónico o contraseña incorrecta.', 'error')
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/funcionamiento')
def funcionamiento():
    if 'usuario_logueado' not in session:
        flash('Por favor, inicie sesión para ver esta página.', 'warning')
        return redirect(url_for('index'))
    correo = session['usuario_logueado']
    usuario = obtener_usuario_por_correo(correo)
    return render_template('funcionamiento.html', usuario=usuario)

@app.route('/principal')
def principal():
    return render_template('principal.html')

@app.route('/guardar_respuesta', methods=['POST'])
def guardar_respuesta():
    data = request.get_json()
    texto = data['texto']
    imagen_actual = data['imagen_actual']
    db.respuestas.insert_one({
        'etiqueta': imagen_actual,
        'texto': texto
    })
    return jsonify({"mensaje": "Guardado exitosamente"})


@app.route('/perfil')
def perfil():
    return render_template('perfil.html')


@app.route('/descargar_resultados')
def descargar_resultados():
    # Asegúrate de que el usuario esté logueado
    if 'usuario_logueado' not in session:
        flash('Por favor, inicie sesión para acceder a esta funcionalidad.', 'warning')
        return redirect(url_for('index'))

    # Función para construir el prompt basado en la etiqueta
    def construir_prompt(etiqueta, texto_usuario):
        if etiqueta == "img1":
            descripcion = """Al mirar la imagen las respuestas más frecuentes se orientan a una mariposa, un murciélago, 
                            una polilla. Y en menor medida."""
        elif etiqueta == "img2":
            descripcion = """En este caso es habitual ver dos figuras humanas, sentadas frente a sí y haciendo contacto. En 
                            una mirada más profunda."""
        elif etiqueta == "img3":
            descripcion = """En una respuesta simple y rápida parecen dos personas o dos camareros, que se suelen 
                            identificar como personas de sexo masculino. ."""
        elif etiqueta == "img4":
            descripcion = """Algunos descifran a un hombre visto desde abajo, como la perspectiva del paciente hacia un 
                            superior, lo que denotaría cierta relación de respeto y hasta miedo. Otros simplemente ven 
                            un monstruo o un animal de forma extraña.."""
        elif etiqueta == "img5":
            descripcion = """El consenso reina en la quinta imagen: ¡todos ven una mariposa! No obstante, puede haber 
                            excepciones. """
        elif etiqueta == "img6":
            descripcion = """Presta atención a la figura y piensa qué ves o qué te transmite. La sexta lámina es (en teoría) la 
                            representación de nuestras tendencias sexuales inconscientes.
                           """
        elif etiqueta == "img7":
            descripcion = """Presta atención a la figura y piensa qué ves o qué te transmite. La sexta lámina es (en teoría) la 
                            representación de nuestras tendencias sexuales inconscientes."""
        elif etiqueta == "img8":
            descripcion = """En partes un poco confusa, a los costados, en color rosa, la mayoría advierte dos animales, 
                            especies de felinos. Observar animales en el test se asocia con el sentido común. """
        elif etiqueta == "img9":
            descripcion = """A medida que transcurre el análisis, las manchas generan respuestas más disimiles. La 
                            psicóloga puntualiza que "el color se relaciona con el afecto".
                            ."""
        elif etiqueta == "img10":
            descripcion = """da lugar a varias interpretaciones. Desde un cangrejo y arañas a 
                            comida. Se dice que ayuda a medir la capacidad organizativa del sujeto. "Si una persona no 
                            logra dar muchas respuestas en varias manchas puede ocurrir que esté muy negativa frente 
                            a la prueba y que se resista a nivel inconsciente"."""
           
        # Continúa para las demás etiquetas
        else:
            descripcion = """Actuas como un profesional en psicología, interpretando texto vinculado a etiquetas específicas  de un test de Rorschach. Se le proveerá de la explicación y concepto detrás de cada etiqueta, permitiéndole realizar un análisis general sobre la salud mental, creatividad, habilidades y aptitudes del individuo, y determinar su idoneidad para el empleo.
                            Al interpretar las etiquetas, debe proporcionar retroalimentación detallada, considerada y respetuosa, enfocándose en aspectos positivos y áreas de mejora.
                            Si la información proporcionada es insuficiente para una interpretación clara, puedes basarte de tu criterio o accediento a tu base de datos."""

    
        return f"Interpretar la respuesta '{texto_usuario}' para la imagen {etiqueta}: {descripcion}"

    # Función para generar el diagnóstico con OpenAI
    def generar_diagnostico(texto_prompt):
        while True:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",  # Usando el modelo de chat
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": texto_prompt},
                    ]
                )
                # Ajusta el acceso a la respuesta según la estructura de datos de la API de chat
                return response['choices'][0]['message']['content'].strip()
            except openai.error.RateLimitError:
                print("Rate limit reached. Waiting for 60 seconds before retrying.")
                time.sleep(60)


        
    # Obtener respuestas de la base de datos
    respuestas = db.respuestas.find({})
    diagnosticos = []

    # Generar diagnósticos para cada respuesta
    for respuesta in respuestas:
        etiqueta = respuesta['etiqueta']
        texto_usuario = respuesta['texto']
        prompt = construir_prompt(etiqueta, texto_usuario)
        diagnostico = generar_diagnostico(prompt)
        diagnosticos.append((etiqueta, diagnostico))

    # Renderizar y devolver el PDF
    html = render_template('resultados_pdf.html', diagnosticos=diagnosticos)
    return render_pdf(HTML(string=html))


if __name__ == '__main__':
    app.run(debug=True)

# Path: PROYECTOFINALDS-main/app/models/models.py