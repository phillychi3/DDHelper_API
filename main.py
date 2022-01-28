from flask import Flask, request, jsonify,make_response
import json
import sqlite3
import uuid
import random

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'gif', 'GIF'])
imagepath = "./images/"


def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/getimage/<isnsfw>', methods=['GET'])
def getimage(isnsfw):



    if 'tags' in request.args:
        tags = request.args.get('tags')
    else:
        tags = None

    conn = sqlite3.connect('images_data.db')
    c = conn.cursor()
    if tags == None:

        c.execute('SELECT * FROM images')
    else:
        if isnsfw == "nsfw":
            c.execute('SELECT * FROM images WHERE tags LIKE "%' +
                      tags + '%" AND nsfw = True')
        else:
            c.execute('SELECT * FROM images WHERE tags LIKE "%' + tags + '%"')

    data = c.fetchall()
    conn.close()
    return jsonify(data)


@app.route("/image/<isnsfw>", methods=["GET"])
def image(isnsfw):

    if 'tags' in request.args:
        tags = request.args.get('tags')
    else:
        tags = None

    conn = sqlite3.connect('images_data.db')
    c = conn.cursor()
    if tags == None:
        if isnsfw == "nsfw":
            c.execute('SELECT * FROM images WHERE nsfw = "True"')
        else:
            c.execute('SELECT * FROM images WHERE nsfw = "False"')
            
        
    else:
        if isnsfw == "nsfw":
            c.execute(f'SELECT * FROM images WHERE tags LIKE "%{tags}%" AND nsfw = "True"')
        else:
            c.execute(f'SELECT * FROM images WHERE tags LIKE "%{tags}%" AND nsfw = "False"')

    data = c.fetchall()
    conn.close()
    if len(data) == 0:
        return jsonify({"error": "no images in gat"})
    rand = random.randint(0, len(data)-1)
    print(data[rand][4])
    print(data)
    id = data[rand][1] + '.' + data[rand][4]

    if isnsfw == "nsfw":
        try:
            if data[rand][4] == "jpg":
                head="jpeg"
            elif data[rand][4] == "png":
                head="png"
            elif data[rand][4] == "gif":
                head="gif"
            else:
                head="png"

            image_data = open(f"images/nsfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            return response
        except:
            return jsonify({"error": "image not found"})
    else:
        try:
            if data[rand][4] == "jpg":
                head="jpeg"
            elif data[rand][4] == "png":
                head="png"
            elif data[rand][4] == "gif":
                head="gif"
            else:
                head="png"
            image_data = open(f"images/sfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            return response
        except:
            return jsonify({"error": "image not found"})


@app.route('/showimage/<isnsfw>/<id>', methods=['GET'])
def showimage(isnsfw, id):
    if isnsfw == "nsfw":
        try:
            ext = id.rsplit('.', 1)[1]
            if ext == "jpg":
                head="jpeg"
            elif ext == "png":
                head="png"
            elif ext == "gif":
                head="gif"
            else:
                head="png"  
            image_data = open(f"images/nsfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            response.headers['cross-origin-resource-policy'] = 'cross-origin'
            response.headers['access-control-allow-origin'] = '*'
            return response
        except:
            return jsonify({"error": "image not found"})
    elif isnsfw == "sfw":
        try:
            ext = id.rsplit('.', 1)[1]
            if ext == "jpg":
                head="jpeg"
            elif ext == "png":
                head="png"
            elif ext == "gif":
                head="gif"
            else:
                head="png"              
            image_data = open(f"images/sfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = f'image/{head}'
            response.headers['cross-origin-resource-policy'] = 'cross-origin'
            response.headers['access-control-allow-origin'] = '*'
            return response
        except:
            return jsonify({"error": "image not found"})
    else:
        return jsonify({"error": "Invalid image type"})

@app.route('/addimage', methods=['post'],strict_slashes=False)
def addimage():

    img = request.files.get('photo')
    tag = request.form.get("tag")
    nsfw = request.form.get("isnsfw")
    selftag = request.form.get('selftag')
    print(img)
    
    print(nsfw)
    print(selftag)
    tags=[]
    tags.append(tag) 
    if selftag != '':
        tags.append(selftag) 
    print(tags)
    if img == None:
        return jsonify({"error": 87, "msg": "檔案都沒了"})
    if allowed_file(img.filename):

        imgname = (str(uuid.uuid4()))[36:-13:-1]
        ext = img.filename.rsplit('.', 1)[1]

        if nsfw == "True":
            img.save(imagepath +"nsfw/" +imgname + "."+ext)
        else:
            img.save(imagepath +"sfw/" +imgname + "."+ext)
        
        if nsfw != "True":
            nsfw = "False"
            
        conn = sqlite3.connect('images_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO images (name, tags, nsfw,ext) VALUES ( ?, ?, ?, ?)',(imgname, str(tags), nsfw,ext))
        conn.commit()
        conn.close()

        return jsonify({"success": 0, "msg": "上傳成功"})
    else:
        return jsonify({"error": 87, "msg": "檔案格式不符"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500,ssl_context=('certificate.crt', 'private.key'))
    #app.run(host='0.0.0.0', port=5500)
