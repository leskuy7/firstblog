from flask import Flask, render_template, flash, redirect, url_for, session, request
from flask_mysqldb import MySQL
from wtforms.fields import EmailField
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Giriş yapmanız gerekli","danger")
            return redirect(url_for("login"))
    return decorated_function

def register_control(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            flash("Oturum açık, önce çıkış yapın.","danger")
            return redirect(url_for("index"))
        else:
            return f(*args, **kwargs)
    return decorated_function


class RegisterForm(Form):
    name = StringField("İsim", validators=[validators.Length(min=2, max=20), validators.DataRequired()])
    username = StringField("Kullanıcı adı", validators=[validators.Length(min=5, max=25), validators.DataRequired()])
    email = EmailField("E-posta", validators=[validators.Optional()])
    password = PasswordField("Parola", validators=[
        validators.DataRequired("Parola oluşturun"),
        validators.EqualTo(fieldname="confirm", message="Parola uyuşmuyor")
    ])
    confirm = PasswordField("Parola doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı adı")
    password = PasswordField("Parola girin")


app = Flask(__name__)
app.secret_key = "blogum"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blogum"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)
@app.route("/")
def index():
    return render_template("index.html",articles=articles,)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/register", methods = ["GET","POST"])
@register_control
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():

        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        sorgu = "Select * from users where username = %s"
        cursor = mysql.connection.cursor()
        result = cursor.execute(sorgu,(username,))
        if result>0:
            flash("Kullanıcı mevcut, farklı kullanıcı adı deneyin","danger")
            return render_template("register.html", form=form)
        #//render_template yapınca sayfada yazılmış bilgileri silmedi, flash mesajı başarılı, şifre yeri boş

        else:
            cursor = mysql.connection.cursor()
            sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
            cursor.execute(sorgu,(name,email,username,password))
            mysql.connection.commit()
            cursor.close()

            flash("Başarıyla kayıt olundu", "success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)

# @app.route("/articles/<string:id>")
# def detail(id):
#     return "Article ID:"+id
#localhost:5000/articles/ sonrasında yazdığımız herhangi bir string değeri
#"article id: girilen değer" olarak sayfada yazılır
#sayı olması gerekmez fakat id tavsiye edilir
#string yerine int yazılabilir, böylece id yerine int dışı bir değer girilirse kapalı bir sayfaya yönlendirir
#string olarak kalıp fonksiyonda try except blokları ile int(id) ifadesi verilirse hata sonunda yapılacak işlem belirtilir
#işlem bir alt sayfaya yönlendirmek olabilir/ url_for ile adrese yönlendirilebilir

@app.route("/login",methods =["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method =="POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "Select * from users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla giriş yapıldı","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
                #password_entered: Any = form.password.data
                #real_password: Any = data["password"]
#buraya giriş doğrulandığı için giriş yap-kayıt ol ekranları gidecek
#giriş yap yerine kullanıcı adı yaz

            else:
                flash("Parola yanlış","danger")
                return redirect(url_for("login"))
        else:
            flash("Kullanıcı adı yanlış","danger")
            return redirect(url_for("login"))
    return render_template("login.html",form=form)

@app.route("/login-account",methods =["GET","POST"])
def login_account():
    from udemy2.BLOG.templates import account
    account.login_account()
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where id = %s"
    result = cursor.execute(sorgu, (id,))
    try:
        int(id)
        if result > 0:
            article = cursor.fetchone()
            return render_template("article.html", article=article)
        else:
            return render_template("article.html")
    except ValueError:
        return redirect(url_for(id))


# eger session başlatılmış ise fonksiyonu çalıştırır (sayfanın yüklenmesine izin verir çünkü fonksiyon bunu istiyor)
#önce decorator çalışır login_required fonksiyonu session kontrol eder. başarılı ise account fonksiyonunu çalıştırır
@app.route("/account")
@login_required
def account():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author=%s"
    #articles içindeki author mysql
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("account.html", articles=articles)
    else:
        return render_template("account.html")

#hesap bilgilerinde e-posta, isim, kullanıcı adı görüntüle, makale sayısı ekle
    
@app.route("/addarticle",methods=["GET","POST"])
@login_required
def addarticle():
    form = ArticleFrom(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content,))
        mysql.connection.commit()
        cursor.close()
        flash("Makale oluşturuldu","success")
        return redirect(url_for("account"))
    return render_template("addarticle.html",form=form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
    try:
        int(id)
        if result > 0:
            sorgu2 = "Delete from articles where id = %s"
            cursor.execute(sorgu2, (id,))
            # cursor.execute("SET @newid=0")
            # cursor.execute("UPDATE articles SET id = (@newid:=@newid+1) ORDER BY id;")
            # cursor.execute("ALTER TABLE articles AUTO_INCREMENT = 1")
            mysql.connection.commit()
            flash("Makale silindi", "danger")
            return redirect(url_for("account"))
        else:
            flash("Silinemedi", "danger")
            return redirect(url_for("account"))
    except ValueError:
        return redirect(url_for("account"))


@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * From articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))
        try:
            int(id)
            if result == 0:
                flash("Bu işlemi yapma yetkiniz yok", "danger")
                return redirect(url_for("account"))

            else:
                article = cursor.fetchone()
                form = ArticleFrom()
                form.title.data = article["title"]
                form.content.data = article["content"]
                return render_template("edit.html", form=form)
        except ValueError:
            return redirect(url_for("account"))
    else:
        form = ArticleFrom(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        sorgu2 = "Update articles Set title=%s, content =%s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()

        flash("Makale güncellendi","success")
        return redirect(url_for("account"))


class ArticleFrom(Form):
    title = StringField("Makale başlığı",validators=[validators.Length(min=5,max=100),validators.DataRequired()])
    content = TextAreaField("Makale içeriği",validators=[validators.Length(min=20,max=10000),validators.DataRequired()])

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = f"Select * From articles where title like '%{keyword}%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Makale başlığı bulunamadı","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)



if __name__ == "__main__":
    app.run(debug=True)


#1 giriş yapıldığı zaman kayıt ol yazısı gitsin
#1 block endblock ifadeleri ile
#1 extends ile navbardan veri alarak
