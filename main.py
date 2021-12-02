from flask import Flask, request, jsonify
import json
import sqlite3

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False

@app.route('/name', methods=['GET'])
def test01():
    user = request.args.get('user')
    return 'Hello, ' + user

if __name__ == '__main__':
    app.run(debug=True)