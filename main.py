from flask import Flask, request, jsonify
import json
import sqlite3
import uuid

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False



@app.route('/image', methods=['GET'])
def getimage():

    if 'nsfw' in request.args:
        nsfw = request.args.get('nsfw')       
    else:
        nsfw = False

    if 'tags' in request.args:
         tags = request.args.get('tags')      
    else:
        tags = None
   
    
    conn = sqlite3.connect('images_data.db')
    c = conn.cursor()
    c.execute('SELECT * FROM images')
    data = c.fetchall()
    conn.close()
    



@app.route('/addimage', methods=['GET'])
def addimage():
    image = request.args.get('image')
    conn = sqlite3.connect('images_data.db')
    c = conn.cursor()




if __name__ == '__main__':
    app.run(debug=True)