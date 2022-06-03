from flask import Flask, flash, render_template, request, request_started, url_for, redirect, session
from flask_mysqldb import MySQL, MySQLdb
import MySQLdb.cursors
from flask_bcrypt import bcrypt
import urllib.request 
import os
import base64
import requests
import json
from math import *

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
    return c * r 

def getOngkir(kode, jarak, initial_price):
    if (kode == 1): 
        ongkos_kirim = initial_price + (jarak * 200)  
        ongkir = round(ongkos_kirim, -3)
    elif (kode == 2): 
        ongkos_kirim = initial_price + (jarak * 160) 
        ongkir = round(ongkos_kirim, -3)
    elif (kode == 3):
        ongkos_kirim = initial_price + (jarak * 100) 
        ongkir = round(ongkos_kirim, -3)
    return ongkir

@app.template_filter()
def rupiah(value):
    value = float(value)
    x = "Rp{:,.2f}".format(value)
    replaceRupiah = str(x).replace(',','.')
    rupiah = replaceRupiah[:-3]
    return rupiah

@app.template_filter() #woakwaokwaok asem, kok 4 tok
def rating_rapi(value):
    value = float(value)
    x = "{:,.2f}".format(value)
    replaceRupiah = str(x)
    rating = replaceRupiah[:-1]
    return rating

app.template_filter()
def qty():
    if 'loggedin' in session:
        uid = session['id'] 
        sum = mysql.connection.cursor() 
        sum.execute("SELECT COUNT(*) FROM carts WHERE carts.user_id=%s", (uid,)) 
        sum.fetchone()
        print(sum)
        return sum
    return redirect(url_for('home'), sum=sum)

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

@app.route('/products-<id>')
def detail(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products JOIN accounts ON products.user_id = accounts.uid WHERE products.pid=%s", (id,))
    data = cur.fetchall()
    nilai = mysql.connection.cursor()
    nilai.execute("SELECT SUM(rating)/COUNT(*) FROM log_order WHERE rating AND product_id=%s", (id,))
    rating = nilai.fetchone()
    
    return render_template('product_detail.html', products=data, rating=rating)

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
        alamat = request.form['alamat']
        kota = request.form['kota']
        kodepos = request.form['kodepos']
        notelp = request.form['notelp']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO accounts (name, email, password, alamat, kota, kodepos, notelp) VALUES (%s,%s,%s)",(nama,email,hash_password, alamat, kota, kodepos, notelp,))
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

@app.route("/profile/edit/nama", methods =['GET', 'POST'])
def updateNama():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            username = request.form['name']
            
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET name =% sWHERE uid=%s",(username,(session['id'], ),))
            mysql.connection.commit()
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

# @app.route("/profile/edit", methods =['GET', 'POST'])
# def update():
#     if 'loggedin' in session:
#         if request.method == 'GET':
#             return render_template("update.html")
#         else:    
#             username = request.form['name']
#             email = request.form['email']
#             password = request.form['password'].encode('utf-8')
#             alamat = request.form['alamat']
#             kodepos = request.form['kodepos']
#             kota = request.form['kota']
#             hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

#             cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
#             cursor.execute("UPDATE accounts SET name =% s, email =% s, password =%s, alamat=%s, kodepos=%s, kota=%s  WHERE uid=%s",(username,email,hash_password,alamat,kodepos,kota,(session['id'], ),))
#             mysql.connection.commit()
#             return redirect(url_for('profile'))
#     return redirect(url_for('login'))

@app.route("/profile/edit/email", methods =['GET', 'POST'])
def updateEmail():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            email = request.form['email']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET email =% sWHERE uid=%s",(email,(session['id'], ),))
            mysql.connection.commit()
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route("/profile/edit/notelp", methods =['GET', 'POST'])
def updateNotelp():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            notelp = request.form['notelp']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET notelp=%s WHERE uid=%s",(notelp,(session['id'], ),))
            mysql.connection.commit()
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route("/profile/edit/alamat", methods =['GET', 'POST'])
def updateAlamat():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            alamat = request.form['alamat']
            kodepos = request.form['kodepos']
            kota = request.form['kota']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET alamat=%s, kodepos=%s, kota=%s WHERE uid=%s",(alamat,kodepos,kota,(session['id'], ),))
            mysql.connection.commit()
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route("/profile/edit/password", methods =['GET', 'POST'])
def updatePassword():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            password = request.form['password'].encode('utf-8')
            hash_password = bcrypt.hashpw(password, bcrypt.gensalt())

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET password =%sWHERE uid=%s",(hash_password,(session['id'], ),))
            mysql.connection.commit()
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/profile/edit/foto', methods =['GET', 'POST'])
def updateFoto():
    if 'loggedin' in session:
        if request.method == 'GET':
            return render_template("update.html")
        else:    
            foto = uploadImage(request.files['foto'])
            print(request)

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("UPDATE accounts SET foto = %s WHERE uid=%s",(foto,(session['id'], ),))
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
            flash("Berhasil masuk ke keranjang!", "success")
            return redirect('home')
        else:
            return 'Error'
            
    return redirect(url_for('login'))

@app.route('/cart')
def cart():
    if 'loggedin' in session:
        uid = session['id'] 
        cur = mysql.connection.cursor() 
        cur.execute("SELECT * FROM carts JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid, ))
        cart=cur.fetchall()
        sum = mysql.connection.cursor() 
        sum.execute("SELECT SUM(harga*quantity) FROM carts JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid,)) 
        total = sum.fetchone()
        return render_template('cart.html',cart=cart,total=total) 
    return redirect(url_for('login'))

@app.route('/updateCart', methods=["POST"]) 
def updateCart():
    uid = session['id']
    id = request.form['pid']
    quantity = request.form['quantity']
    id_kurir = request.form['kurir'] 
    cur = mysql.connection.cursor()
    cur.execute("UPDATE products SET stock=stock-(%s-(SELECT quantity FROM carts WHERE user_id= %s and product_id = %s)) WHERE pid = %s", (quantity,uid,id,id,))
    cur.execute("UPDATE carts SET quantity = %s WHERE product_id=(%s) and user_id = %s", (quantity, id, uid,))
    cur.execute("UPDATE carts SET kurir_id=%s WHERE user_id = %s AND product_id = %s", (id_kurir,uid,id,))
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
def emptyCart(): #Assalamu'alaikum
    session.clear()
    return redirect(url_for('home')) 

@app.route('/checkout')
def checkout():
    uid = session['id'] 
    cur = mysql.connection.cursor()
    #cur.execute('SELECT * FROM products JOIN accounts ON accounts.uid = products.user_id JOIN detail_kota ON detail_kota.kota = accounts.kota WHERE products.user_id=%s', (uid,))
    cur.execute('''SELECT * FROM detail_kota JOIN accounts ON detail_kota.kota = accounts.kota JOIN carts ON carts.user_id = accounts.uid 
    JOIN products ON products.pid = carts.product_id JOIN couriers ON couriers.kid = carts.kurir_id WHERE carts.user_id=%s''', (uid,))
    checkout = cur.fetchall()
    sum = mysql.connection.cursor() 
    sum.execute("SELECT SUM(harga*quantity+ongkir) FROM carts JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid,)) 
    total = sum.fetchone()
    print(total[0])
    return render_template('checkout.html', checkout=checkout, total=total)

@app.route('/updateKurir', methods = ['POST'])
def updatekurir():
    uid = session['id']
    pid = request.form['pid'] 
    id_kurir = request.form['kurir']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE carts SET kurir_id=%s WHERE user_id = %s AND product_id = %s", (id_kurir,uid,pid,))
    mysql.connection.commit()
    lat1 = mysql.connection.cursor() 
    lat1.execute('''SELECT detail_kota.latitude FROM products JOIN accounts ON accounts.uid = products.user_id 
                JOIN detail_kota ON detail_kota.kota = accounts.kota WHERE products.pid = %s''', (pid,)) 
    lat_asal = lat1.fetchone()
    lng1 = mysql.connection.cursor() 
    lng1.execute('''SELECT detail_kota.longitude FROM products JOIN accounts ON accounts.uid = products.user_id 
                JOIN detail_kota ON detail_kota.kota = accounts.kota WHERE products.pid = %s''', (pid,)) 
    lng_asal = lng1.fetchone()
    lat2 = mysql.connection.cursor() 
    lat2.execute('''SELECT detail_kota.latitude FROM detail_kota JOIN accounts ON detail_kota.kota = accounts.kota 
                JOIN carts ON carts.user_id = accounts.uid WHERE user_id=%s''', (uid,)) 
    lat_tujuan = lat2.fetchone()
    lng2 = mysql.connection.cursor() 
    lng2.execute('''SELECT detail_kota.longitude FROM detail_kota JOIN accounts ON detail_kota.kota = accounts.kota 
                JOIN carts ON carts.user_id = accounts.uid WHERE user_id=%s''', (uid,))
    lng_tujuan = lng2.fetchone()
    kur = mysql.connection.cursor() 
    kur.execute("SELECT kurir_id FROM carts WHERE user_id=%s and product_id=%s", (uid,pid,)) 
    kurir = kur.fetchone()
    price = mysql.connection.cursor() 
    price.execute("SELECT harga_awal FROM carts JOIN couriers ON couriers.kid = carts.kurir_id WHERE user_id=%s and product_id=%s", (uid,pid,)) 
    harga_awal = price.fetchone()
    co = haversine(float(lng_asal[0]), float(lat_asal[0]), float(lng_tujuan[0]), float(lat_tujuan[0]))
    ongkir = getOngkir(kurir[0], co, harga_awal[0])
    sum = mysql.connection.cursor() 
    sum.execute("SELECT SUM(harga*quantity+ongkir) FROM carts JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid,)) 
    total_harga = sum.fetchone()
    print(total_harga[0])
    jumlah = mysql.connection.cursor() 
    jumlah.execute("SELECT quantity FROM carts WHERE carts.user_id=%s AND carts.product_id=%s", (uid,pid)) 
    jumlah_barang = jumlah.fetchone() 
    fee = mysql.connection.cursor()
    fee.execute("UPDATE carts SET ongkir = %s WHERE user_id =%s and product_id = %s", (ongkir,uid,pid,))
    fee.execute("CALL addorderdetails(%s,%s,%s,%s,%s)", (pid,uid,id_kurir,total_harga[0],jumlah_barang[0],))
    mysql.connection.commit()
    mus = mysql.connection.cursor() 
    mus.execute("SELECT SUM(harga*quantity+ongkir) FROM carts JOIN products ON carts.product_id=products.pid WHERE carts.user_id=%s", (uid,)) 
    harga_total = mus.fetchone()
    print(harga_total[0])
    end = mysql.connection.cursor()
    end.execute("UPDATE orderdetails SET total=%s WHERE user_id=%s and product_id = %s", (harga_total[0],uid,pid,))
    mysql.connection.commit()
    fee_ongkir = mysql.connection.cursor()
    fee_ongkir.execute("SELECT ongkir FROM carts WHERE user_id =%s and product_id = %s", (uid,pid,))
    tampil_fee = fee_ongkir.fetchone()
    return redirect(url_for('checkout', ongkir=ongkir, tampil_fee=tampil_fee)) 

@app.route('/bayar')
def bayar():
    uid = session['id'] 
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM carts WHERE user_id = %s", (uid,))
    cur.execute("UPDATE orderdetails SET status = 'Unpaid' WHERE user_id=%s", (uid,)) 
    mysql.connection.commit()
    cur.close()
    flash("Pesanan berhasil! Tunggu pesanan dikirim oleh penjual", "success")
    return redirect('home')

#ini nanti dioff-kan
@app.route('/status')
def status():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute('''SELECT nama, jumlah, total, status, orderdetails.product_id, image_product FROM orderdetails 
                JOIN products ON orderdetails.product_id=products.pid 
                WHERE orderdetails.user_id=%s''', (uid,))
    status = cur.fetchall()
    cur.close()
    return render_template('status.html', status=status)

@app.route('/status-unpaid')
def unpaidBuyer():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute('''SELECT nama, jumlah, total, status, orderdetails.product_id, image_product FROM orderdetails 
                JOIN products ON orderdetails.product_id=products.pid
                WHERE orderdetails.user_id=%s AND status = 'Unpaid' ''', (uid,))
    status = cur.fetchall()
    cur.close()
    return render_template('status-buyer-unpaid.html', status=status)

@app.route('/status-delivered')
def deliveredBuyer():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute('''SELECT nama, jumlah, total, status, orderdetails.product_id, image_product FROM orderdetails 
                JOIN products ON orderdetails.product_id=products.pid 
                WHERE orderdetails.user_id=%s AND status = 'Delivered' ''', (uid,))
    status = cur.fetchall()
    cur.close()
    return render_template('status-buyer-delivered.html', status=status)

@app.route('/status-finished')
def finishedBuyer():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute("SELECT * FROM log_order JOIN products ON log_order.product_id = products.pid WHERE log_order.user_id=%s Order BY log_order.tanggal DESC", (uid,))
    finish = cur.fetchall()
    cur.close()
    return render_template('status-buyer-finished.html', status=finish)

@app.route('/updateOrderStatusBuyer', methods=['POST'])
def updateOrderStatusBuyer():
    uid = session['id']
    pid = request.form['product_id']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE orderdetails SET status='Paid/Finished' WHERE user_id=%s and product_id=%s", (uid,pid,))
    cur.execute("DELETE FROM orderdetails WHERE status='Paid/Finished' and user_id=%s and product_id=%s", (uid,pid,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('finishedBuyer'))

#ini nanti dioff-kan
# @app.route('/status-seller')
# def orderStatusSeller():
#     uid = session['id']
#     cur = mysql.connection.cursor()
#     cur.execute('''SELECT nama, jumlah, total, status, image_product, orderdetails.product_id FROM orderdetails 
#                 JOIN products ON orderdetails.product_id=products.pid 
#                 WHERE products.user_id=%s ''', (uid,))
#     order_status = cur.fetchall()
#     cur.close()
#     return render_template('status-seller.html', order_status=order_status) 

@app.route('/status-seller-unpaid')
def unpaidSeller():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute('''SELECT nama, jumlah, total, status, orderdetails.product_id, image_product FROM orderdetails 
                JOIN products ON orderdetails.product_id=products.pid 
                WHERE products.user_id=%s AND status = 'Unpaid' ''', (uid,))
    status = cur.fetchall()
    cur.close()
    return render_template('status-seller-unpaid.html', status=status)

@app.route('/status-seller-delivered')
def deliveredSeller():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute('''SELECT nama, jumlah, total, status, orderdetails.product_id, image_product FROM orderdetails 
                JOIN products ON orderdetails.product_id=products.pid 
                WHERE products.user_id=%s AND status = 'Delivered' ''', (uid,))
    status = cur.fetchall()
    cur.close()
    return render_template('status-seller-delivered.html', status=status)

@app.route('/status-seller-finished')
def finishedSeller():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute("SELECT * FROM log_order JOIN products ON log_order.product_id = products.pid WHERE products.user_id=%s Order BY log_order.tanggal DESC", (uid,))
    finish = cur.fetchall()
    cur.close()
    return render_template('status-seller-finish.html', status=finish)

@app.route('/updateOrderStatusSeller', methods=['POST'])
def updateOrderStatusSeller():
    uid = session['id']
    pid = request.form['product_id']
    cur = mysql.connection.cursor()
    cur.execute('''UPDATE orderdetails as o, (SELECT orderdetails.user_id FROM orderdetails JOIN products 
                ON orderdetails.product_id = products.pid WHERE products.user_id = %s) as x SET o.status='Delivered' 
                WHERE x.user_id=o.user_id and o.product_id=%s''', (uid,pid,))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('deliveredSeller'))

#ini nanti dioff-kan
@app.route('/finishedOrder')
def finishedOrder():
    uid = session['id']
    cur = mysql.connection.cursor() 
    cur.execute("SELECT * FROM log_order JOIN products ON log_order.product_id = products.pid WHERE log_order.user_id=%s Order BY log_order.tanggal DESC", (uid,))
    finish = cur.fetchall()
    cur.close()
    return render_template('finished-order.html', status=finish)

@app.route('/rating', methods=['GET','POST'])
def rating():
    if request.method == 'POST':
        if 'rating' in request.form: 
            uid = session['id']
            pid = request.form['pid'] 
            content = int(request.form['rating']) 
            #print(content)
            #print(request.form)
            nilai = mysql.connection.cursor() 
            nilai.execute("UPDATE log_order SET rating=%s WHERE product_id = %s AND user_id = %s", (content, pid, uid,))
            nilai.execute("CALL update_rating()")
            mysql.connection.commit()
            nilai.close()
    return redirect(url_for('finishedBuyer'))

@app.route('/about-us')
def aboutUs():
    return render_template('about-us.html')

@app.route('/contact-us')
def contactUs():
    return render_template('contact-us.html')

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)