from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/protected", methods=["GET"])
def protected():
    # Later we’ll actually check auth here
    # For now, just pretend it’s protected
    return jsonify({"message": "Prototype protected route"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
