from flask import Flask, flash, render_template, request, url_for, redirect, session
from flask_mysqldb import MySQL, MySQLdb
import MySQLdb.cursors
from flask_bcrypt import bcrypt
import pymysql
import urllib.request 
import os
import base64
import requests

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = set(['png','jpg','jpeg'])

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
    cur.execute("SELECT * FROM products JOIN accounts ON products.user_id = accounts.id WHERE products.id=%s", (id,))
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
                session['id'] = accounts['id']
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
        cur.execute("SELECT * FROM accounts WHERE id=(%s)", (session['id'],))
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
        id = request.form['id']
        nama = request.form['nama']
        deskripsi = request.form['deskripsi']
        harga = request.form['harga']
        stok = request.form['stock']
        url = uploadImage(request.files['image_product'])
        #if image_product and allowed_file(image_product.filename):
            #filename = secure_filename(image_product.filename)
            #image_product.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cur = mysql.connection.cursor()
        cur.execute("UPDATE products SET nama=%s, deskripsi=%s, harga=%s, image_product=%s, stock=%s WHERE id=(%s)", (nama, deskripsi, harga, url, stok, id,))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('userProduct'))
    return redirect(url_for('login')) 

@app.route('/user-product/delete-<id>', methods = ['GET'])
def deleteProduct(id):
    if 'loggedin' in session:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM products WHERE id=(%s)", (id,))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('userProduct'))
    return redirect(url_for('login')) 

@app.route('/products/addcart', methods = ['POST'])
def addToCart():
    if 'loggedin' in session:
        id = request.form['id']
        quantity = request.form['stock']
        if id and quantity and request.method == 'POST':
            cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cur.execute("SELECT * FROM products WHERE id=%s", id)
            row = cur.fetchone
            itemQuery = { row['id'] : {'nama' : row['nama'], 'id' : row['id'], 'stock' : quantity, 'harga' : row['harga'], 
                        'image_product' : row['image_product'], 'total_price': quantity * row['harga']}}
            session.modified = True
            if 'cart_item' in session:
                if row['id'] in session['cart_item']:
                    for key in session['cart_item'].items():
                        if row['id'] == key:
                            old_quantity = session['cart_item'][key]['stock']
                            total_quantity = old_quantity + quantity
                            session['cart_item'][key]['stock'] = total_quantity
                            session['cart_item'][key]['total_price'] = total_quantity * row['harga']
                else:
                    session['cart_item'] = array_merge(session['cart_item'], itemQuery)
            else:
                session['cart_item'] = itemQuery
                
            return redirect(url_for('detail')) 
        else:
            return 'Error'
    return redirect(url_for('login'))

@app.route('/cart')
def cart():
    if 'loggedin' in session:
        all_total_price = 0
        all_total_quantity = 0
        session.modified = True
        if 'cart_item' not in session:
            return redirect(request.referrer)
        elif 'cart_item' in session:
            for key, value in session['cart_item'].items():
                individual_quantity = int(session['cart_item'][key]['quantity'])
                individual_price = float(session['cart_item'][key]['total_price'])
                all_total_quantity = all_total_quantity + individual_quantity
                all_total_price = all_total_price + individual_price
        else:
            session['all_total_quantity'] = all_total_quantity
            session['all_total_price'] = all_total_price
        return render_template("cart.html")
    return redirect(url_for('login'))

@app.route('/updateCart/<id>', methods=["POST"])
def updateCart(id):
    if 'cart_item' not in session and len(session['cart_item']) <= 0:
        return redirect(url_for('home'))
    if request.method == "POST":
        quantity = request.form['stock']
        session.modified = True
        for key, products in session['cart_item'].items():
            if int(key) == id:
                products['stock'] = quantity
                return redirect(url_for('cart'))

@app.route('/deleteCart/<id>')
def deleteCart(id):
    all_total_price = 0
    all_total_quantity = 0
    session.modified = True
    for item in session['cart_item'].items():
        if item[0] == id:    
            session['cart_item'].pop(item[0], None)
            if 'cart_item' in session:
                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quantity'])
                    individual_price = float(session['cart_item'][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
                break
        if all_total_quantity == 0:
            session.clear()
        else:
            session['all_total_quantity'] = all_total_quantity
            session['all_total_price'] = all_total_price
        return redirect(url_for('detail'))

@app.route('/emptyCart')
def emptyCart():
    session.clear()
    return redirect(url_for('home'))

@app.route('/about-us')
def aboutUs():
    return render_template('about-us.html')

@app.route('/contact-us')
def contactUs():
    return render_template('contact-us.html')

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)