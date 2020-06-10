# Simple Flask web server to satisfy Heroku's requirement for a PORT
from app.imports import *

app = Flask(__name__)
app.run(os.getenv("PORT"))
