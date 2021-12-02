from flask import Flask, request, jsonify
import json
import sqlite3

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False


@app.route('/name', methods=['GET'])
def get_par01():
    user = request.args.get('user')
    return 'Hello, ' + user


@app.route('/image', methods=['GET'])
def get_par02():
    user = request.args.get('user')
    return 'Hello, ' + user


@app.route("/json", methods=["GET"])
def jsonall():
    with open("image.json", "r") as jsonFile: 
        data = json.load(jsonFile) 
    return jsonify(data)

@app.route('/jsones', methods=['GET'])
def lol():
    with open("image.json", "r") as jsonFile: 
        data = json.load(jsonFile) 
    if 'image_data' in request.args:
        image_data = request.args['image_data']        
    else:
        return "nodata lol"
    results = []

    for image in data:
        if image["image_data-data"]["data_value"]["id"] == image_data:
            results.append(image)


    return jsonify(results)
@app.route('/jsonesid', methods=['GET'])
def lol2():
    with open("image.json", "r") as jsonFile: 
        data = json.load(jsonFile) 
    if 'image_data' in request.args:
        image_data = request.args['image_data']        
    else:
        return "nodata lol"
    results = []

    for image in data:
        if image["image_id"] == image_data:
            results.append(image)


    return jsonify(results)

@app.route('/dbtest', methods=['GET'])
def lol3():
    dbfile = "test/test.db"
    conn = sqlite3.connect(dbfile)
    print ("Opened database successfully")
    rows = conn.execute("SELECT * from images")
    print ("load database successfully")
    rv=rows.fetchall()
    row_headers=[x[0] for x in rows.description]
    json_data=[]
    for result in rv:
        json_data.append(dict(zip(row_headers,result)))
    return jsonify(json_data)    
    print( json.dumps(json_data))
    conn.close()

if __name__ == '__main__':
    app.run(debug=True)
