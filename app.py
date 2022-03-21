from flask import Flask, render_template, request, url_for, redirect, session
from flask_mysqldb import MySQL, MySQLdb
import MySQLdb.cursors
from flask_bcrypt import bcrypt
import re

app = Flask(__name__)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'store'

mysql = MySQL(app)

app.config['SECRET_KEY'] = "your secret key"

@app.route('/')
@app.route('/home')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products Order BY tanggal DESC LIMIT 10;")
    data = cur.fetchall()
    cur.close()
    return render_template('home.html', products=data)

@app.route('/products/<id>')
def detail(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (id,))
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
        session['name'] = request.form['name']
        session['email'] = request.form['email']
        return redirect(url_for('login'))
        
@app.route('/profile', methods=["GET", "POST"])
def profile():
    if 'loggedin' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM accounts WHERE name=(%s)", (session['name'],))
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
            session['name'] = request.form['name']
            session['email'] = request.form['email']
            session['password'] = request.form['password']
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/about-us')
def aboutUs():
    return render_template('about-us.html')

@app.route('/contact-us')
def contactUs():
    return render_template('contact-us.html')

if __name__ == '__main__':
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True)