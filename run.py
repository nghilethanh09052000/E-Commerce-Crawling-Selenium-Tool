from app.settings import DEBUG
from app import app

if __name__ == "__main__":
    app.run(debug=DEBUG, host="0.0.0.0", port=8000)
