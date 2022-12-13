from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, UserMixin, current_user, logout_user
from flask_admin import Admin,AdminIndexView
from flask_admin.contrib.sqla import ModelView

app = Flask(__name__)
app.config["SECRET_KEY"] = "whatever"
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@localhost:3306/user"
app.config["SQLALCHEMY_TRACK_MODIFICATION"] = True
bootstrap = Bootstrap(app)
loginManager = LoginManager(app)
db = SQLAlchemy(app)


# 数据库模型
# UserMixin表示通过认证的用户
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text)
    password = db.Column(db.Text)

    def get_id(self):
        return self.id


# login页面表单
class LoginForm(FlaskForm):
    userName = StringField("请输入用户名：", validators=[DataRequired()])
    password = PasswordField("请输入密码：", validators=[DataRequired()])
    submit = SubmitField("登录")


# admin视图
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, ** kwargs):
        flash("您没有权限，请先登录")
        return redirect(url_for("login"))


# 添加admin页面
admin = Admin(app, name="后台管理",index_view=MyAdminIndexView())
admin.add_view(ModelView(User, db.session))


# ********不知道干啥的，但是删了会报错**********
#
@loginManager.user_loader
def load_user(username):
    user = User.query.get(username)
    return user


# 未登录时重定向至login
@loginManager.unauthorized_handler
def unauthorized_handler():
    flash("当前未登录")
    return redirect(url_for("login"))


@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    user = current_user
    if user is None:  # 没登录
        # 加了login_required以后进不了这个语句块
        return redirect(url_for("login"))
    else:
        return render_template("index.html", username=user.username)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.get(form.userName.data)
        if user:
            if form.password.data == user.password:
                login_user(user)
                flash("登录成功")
                return redirect(url_for("index"))
            else:
                flash("登录失败: 密码错误")
                form.password.data = ""
                form.userName.data = ""
        else:
            flash("登录失败: 用户不存在")
            form.password.data = ""
            form.userName.data = ""
    return render_template("login.html", form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
