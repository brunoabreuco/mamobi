from dotenv import load_dotenv
from flask import send_from_directory
from maes_mobilizadoras.app_factory import create_app

app = create_app()

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'tela-cadastro.html')

if __name__ == "__main__":
    app.run(debug=True)