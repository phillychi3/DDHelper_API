from flask import Flask, request, jsonify,make_response
import json
import sqlite3
import uuid

app = Flask(__name__)
app.config["DEBUG"] = True
app.config["JSON_AS_ASCII"] = False

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'JPG', 'PNG', 'gif', 'GIF'])
imagepath = "./images/"


def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/image/<isnsfw>', methods=['GET'])
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

@app.route('/getimage/<isnsfw>/<id>', methods=['GET'])
def showimage(isnsfw, id):
    if isnsfw == "nsfw":
        try:
            image_data = open(f"images/nsfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/png'
            return response
        except:
            return jsonify({"error": "image not found"})
    elif isnsfw == "sfw":
        try:
            image_data = open(f"images/sfw/{id}", "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/png'
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
            
        conn = sqlite3.connect('images_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO images (name, tags, nsfw,ext) VALUES ( ?, ?, ?)',(imgname, str(tags), nsfw,ext))
        conn.commit()
        conn.close()

        return jsonify({"success": 0, "msg": "上傳成功"})
    else:
        return jsonify({"error": 87, "msg": "檔案格式不符"})



    


if __name__ == '__main__':
    app.run(debug=True)
