from flask import Flask, flash, render_template, request, request_started, url_for, redirect, session
from flask_mysqldb import MySQL, MySQLdb
import MySQLdb.cursors
from flask_bcrypt import bcrypt
import urllib.request 
import os
import base64
import requests
import shippo
from math import *

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = set(['png','jpg','jpeg'])

shippo.config.api_key= 'shippo_test_2845605548ab80ffe2adc5af39b62af53128a99e'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'store'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

app.config['SECRET_KEY'] = "your secret key"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def array_merge( first_array , second_array ):
	if isinstance( first_array , list ) and isinstance( second_array , list ):
		return first_array + second_array
	elif isinstance( first_array , dict ) and isinstance( second_array , dict ):
		return dict( list( first_array.items() ) + list( second_array.items() ) )
	elif isinstance( first_array , set ) and isinstance( second_array , set ):
		return first_array.union( second_array )
	return False	

def uploadImage(image_file):
    image_b64 = base64.b64encode(image_file.read()).decode('ascii')
    try:
        r = requests.post(
            url = 'https://api.imgbb.com/1/upload',
            files = {'key':'6ac77157273a6d5698c99778f7982c6d'},
            data = {
                'key' : '6ac77157273a6d5698c99778f7982c6d',
                'image' : image_b64
            }).json()
        return r['data']['display_url']
    except Exception as e:
        print(e)
        return None        

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r #iki lih? iyoo lid, tak tonton ning gugel long lat jakarta

@app.route('/')
@app.route('/home')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products Order BY tanggal DESC LIMIT 10;")
    data = cur.fetchall()
    cur.close()
    return render_template('home.html', products=data)

@app.route('/all-product')
def allproduct():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products Order BY tanggal DESC;")
    data = cur.fetchall()
    cur.close()
    return render_template('all-product.html', allproducts=data)

@app.route('/products/<id>')
def detail(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products JOIN accounts ON products.user_id = accounts.uid WHERE products.pid=%s", (id,))
    data = cur.fetchall()
    cur.close()
    return render_template('product_detail.html', products=data)

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM accounts WHERE email=%s",(email,))
        accounts = cur.fetchone()
        cur.close()

        if len(accounts) > 0:
            if bcrypt.hashpw(password, accounts["password"].encode('utf-8')) == accounts["password"].encode('utf-8'):
                session['id'] = accounts['uid']
                session['name'] = accounts['name']
                session['email'] = accounts['email']
                session['loggedin'] = True
                return redirect(url_for('home'))
            else:
                return "Error password and email not match"
        else:
            return "Error user not found"
    else:
        return render_template("login.html")
    
@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        nama = request.form['name']
        email = request.form['email']
        password = request.form['password'].encode('utf-8')
        hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO accounts (name, email, password) VALUES (%s,%s,%s)",(nama,email,hash_password,))
        mysql.connection.commit()
        return redirect(url_for('login'))
        
@app.route('/profile', methods=["GET", "POST"])
def profile():
    if 'loggedin' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM accounts WHERE uid=(%s)", (session['id'],))
        user = cur.fetchone()
        cur.close()
        return render_template('user-detail.html', user=user)
    return redirect(url_for('login'))    

@app.route("/profile/edit", methods =['GET', 'POST'])
def update():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            username = request.form['name']
            email = request.form['email']
            password = request.form['password'].encode('utf-8')
            hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET name =% s, email =% s, password =% s  WHERE id=%s",(username,email,hash_password,(session['id'], ),))
            mysql.connection.commit()
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/user-product')
def userProduct():
    if 'loggedin' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE user_id=(%s)", (session['id'],))
        user = cur.fetchall()
        cur.close()
        return render_template('list-product.html', products=user)
    return redirect(url_for('login'))    

@app.route('/user-product/tambah-data', methods = ['POST'])
def insertProduct():
    if 'loggedin' in session:
        nama = request.form['nama']
        deskripsi = request.form['deskripsi']
        harga = request.form['harga']
        stok = request.form['stock']
        url = uploadImage(request.files['image_product'])
        #if image_product and allowed_file(image_product.filename):
            #filename = secure_filename(image_product.filename)
            #image_product.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO products (nama, stock, deskripsi, harga, image_product, user_id) VALUES (%s,%s,%s,%s,%s,%s)", (nama, stok, deskripsi, harga, url, session['id'],))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('userProduct'))
    return redirect(url_for('login'))    

@app.route('/user-product/edit-data', methods=["POST"])
def updateProduct():
    if 'loggedin' in session:
        id = request.form['pid']
        nama = request.form['nama']
        deskripsi = request.form['deskripsi']
        harga = request.form['harga']
        stok = request.form['stock']
        url = uploadImage(request.files['image_product'])
        #if image_product and allowed_file(image_product.filename):
            #filename = secure_filename(image_product.filename)
            #image_product.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cur = mysql.connection.cursor()
        cur.execute("UPDATE products SET nama=%s, deskripsi=%s, harga=%s, image_product=%s, stock=%s WHERE pid=(%s)", (nama, deskripsi, harga, url, stok, id,))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('userProduct'))
    return redirect(url_for('login')) 

@app.route('/user-product/delete-<id>', methods = ['GET'])
def deleteProduct(id):
    if 'loggedin' in session:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM products WHERE pid=(%s)", (id,))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('userProduct'))
    return redirect(url_for('login')) 

@app.route('/addcart', methods = ['POST'])
def addToCart():
    if 'loggedin' in session: 
        pid = request.form['pid']
        uid = session['id']
        quantity = request.form['quantity']
        if pid and quantity and uid and request.method == 'POST':
            cur = mysql.connection.cursor()
            cur.execute("CALL addcarts(%s,%s,%s)",(pid,uid,quantity,))
            #cur.execute('INSERT INTO carts (product_id,user_id,quantity) VALUES (%s, %s,%s)',(pid,uid,quantity,))
            cur.execute("UPDATE products SET stock=stock-%s WHERE pid = %s", (quantity,pid,))
            #cur.execute("UPDATE carts SET total=(SELECT harga from products WHERE pid = %s)*%s WHERE user_id = %s", (pid,quantity,uid,))
            mysql.connection.commit()
            return redirect(url_for('home')) 
        else:
            return 'Error'
            
    return redirect(url_for('login'))

@app.route('/cart')
def cart():
    if 'loggedin' in session:
        uid = session['id'] 
        cur = mysql.connection.cursor() 
        cur.execute("SELECT * FROM carts RIGHT JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid, ))
        cart=cur.fetchall()
        sum = mysql.connection.cursor() 
        sum.execute("SELECT SUM(harga*quantity) FROM carts JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid, )) 
        total=sum.fetchall()
        print(total) 
        return render_template('cart.html',cart=cart,total=total)
    return redirect(url_for('login'))

@app.route('/updateCart', methods=["POST"]) 
def updateCart():
    uid = session['id']
    id = request.form['pid']
    quantity = request.form['quantity']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE products SET stock=stock-(%s-(SELECT quantity FROM carts WHERE user_id= %s and product_id = %s)) WHERE pid = %s", (quantity,uid,id,id,))
    cur.execute("UPDATE carts SET quantity = %s WHERE product_id=(%s) and user_id = %s", (quantity, id, uid,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('cart'))

@app.route('/deleteCart/<id>', methods = ['GET'])
def deleteCart(id):
    if 'loggedin' in session:
        uid = session['id']
        cur = mysql.connection.cursor()
        cur.execute("UPDATE products SET stock=stock+(SELECT quantity FROM carts WHERE user_id=%s and product_id=%s) WHERE pid = %s", (uid,id,id,))
        cur.execute("DELETE FROM carts WHERE product_id=(%s) and user_id = %s", (id,uid))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('cart'))
    return redirect(url_for('login')) 

@app.route('/emptyCart')
def emptyCart():
    session.clear()
    return redirect(url_for('home')) 

@app.route('/checkout')
def checkout():
    uid = session['id']
    lat1 = mysql.connection.cursor() 
    lat1.execute("SELECT latitude FROM detail_kota JOIN accounts ON detail_kota.kota = accounts.kota WHERE uid=%s", (uid,)) 
    lat_asal = lat1.fetchall()
    lng1 = mysql.connection.cursor() 
    lng1.execute("SELECT longitude FROM detail_kota JOIN accounts ON detail_kota.kota = accounts.kota WHERE uid=%s", (uid,)) 
    lng_asal = lng1.fetchall()
    lat2 = mysql.connection.cursor() 
    lat2.execute("SELECT latitude FROM detail_kota JOIN accounts ON detail_kota.kota = accounts.kota JOIN carts carts.user_id = accounts.uid WHERE user_id=%s", (uid,)) 
    lat_tujuan = lat2.fetchall()
    lng2 = mysql.connection.cursor() 
    lng2.execute("SELECT * FROM carts WHERE user_id=%s", (uid,))  #semangat pak ketua, eh pak koor deng raenek
    lng_tujuan = lng2.fetchall()
    co = haversine(float(lng_asal), float(lat_asal), float(lng_tujuan), float(lat_tujuan))
    return render_template('checkout.html',co=co) 

@app.route('/about-us')
def aboutUs():
    return render_template('about-us.html')

@app.route('/contact-us')
def contactUs():
    return render_template('contact-us.html')

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)