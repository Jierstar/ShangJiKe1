from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, UserMixin, current_user, logout_user
from flask_admin import Admin, AdminIndexView
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
    username: object = db.Column(db.Text)
    password = db.Column(db.Text)
    authority = db.Column(db.Integer)

    def get_id(self):
        return self.id


class Candidate(db.Model):
    __tablename__ = "candidate"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    votes = db.Column(db.Integer)
    intro = db.Column(db.Text)
    theme_id = db.Column(db.Text)


class VoteTheme(db.Model):
    __tablename__ = "votetheme"
    id = db.Column(db.Integer, primary_key=True)
    theme = db.Column(db.Text)


class VoteLog(db.Model):
    __tablename__ = "votelog"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    theme_id = db.Column(db.Integer)


# login页面表单
class LoginForm(FlaskForm):
    userName = StringField("请输入用户名：", validators=[DataRequired()])
    password = PasswordField("请输入密码：", validators=[DataRequired()])
    submit = SubmitField("登录")


# 创建候选人表单
class CandidateForm(FlaskForm):
    themeId = StringField("投票主题编号：", validators=[DataRequired()])
    id = StringField("编号：", validators=[DataRequired()])
    name = StringField("名字：", validators=[DataRequired()])
    intro = StringField("介绍：")
    submit = SubmitField("完成")


# 创建头投票主题表单
class ThemeForm(FlaskForm):
    id = StringField("编号：", validators=[DataRequired()])
    theme = StringField("主题：", validators=[DataRequired()])
    submit = SubmitField("完成")


# admin视图
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.authority >= 2

    def inaccessible_callback(self, name, **kwargs):
        flash("您没有权限")
        return redirect(url_for("index"))


# 添加admin页面
admin = Admin(app, name="后台管理", index_view=MyAdminIndexView())
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Candidate, db.session))


# ********不知道干啥的，但是删了会报错**********
@loginManager.user_loader
def load_user(id):
    user = User.query.get(id)
    return user


# 未登录时重定向至login
@loginManager.unauthorized_handler
def unauthorized_handler():
    flash("当前未登录")
    return redirect(url_for("login"))


# 主页
@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    user = current_user
    return render_template("index.html", username=user.username)


# 登录
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(User.username == form.userName.data).first()
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
    return render_template("login.html", form=form, title="登录")


# 登出
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


class VoteQueryForm(FlaskForm):
    id = StringField("请输入需要查看的投票id：", validators=[DataRequired()])
    submit = SubmitField("查看")


@app.route("/voteHomepage", methods=["GET", "POST"])
@login_required
def voteHomepage():
    form = VoteQueryForm()
    if form.validate_on_submit():
        theme = VoteTheme.query.get(form.id.data)
        if theme:
            return redirect(url_for("voteTable", id=theme.id))
        else:
            flash("未找到相关投票")
            form.id.data = ""
    return render_template("table.html", form=form, tilte="查找投票")


@app.route("/voteTable/<id>", methods=["GET", "POST"])
@login_required
def voteTable(id):
    theme = VoteTheme.query.get(id)
    candidateList = Candidate.query.filter_by(theme_id=id).all()

    return render_template("voteTable.html", candidateList=candidateList, title=theme.theme)


@app.route("/vote/<id>", methods=["GET", "POST"])
@login_required
def vote(id):
    user = current_user
    candidate = Candidate.query.get(id)
    # 生成id
    log = VoteLog.query.get((10007*user.id+candidate.theme_id*10009)%10039)
    print(user.id,candidate.theme_id,(10007*user.id+candidate.theme_id*10009)%10039)
    if log:
        flash("您已投票，请勿重复投票")
        return redirect(url_for("voteTable", id=candidate.theme_id))
    else:
        candidate.votes += 1
        db.session.commit()
        flash("You have successfully voted for " + candidate.name)
        db.session.add(
            VoteLog(id=(10007*user.id+candidate.theme_id*10009)%10039, user_id=user.id, theme_id=candidate.theme_id)
        )
        db.session.commit()
        return redirect(url_for("voteTable", id=candidate.theme_id))


@app.route("/creatCandidate", methods=["GET", "POST"])
@login_required
def creatCand():
    if current_user.authority < 1:
        flash("您没有权限，如需升级权限请联系管理员")
        return redirect(url_for("index"))

    form = CandidateForm()
    if form.validate_on_submit():
        theme = VoteTheme.query.get(form.themeId.data)
        if theme:
            db.session.add(
                Candidate(id=form.id.data, name=form.name.data, intro=form.intro.data, votes=0, theme_id=theme.id)
            )
            db.session.commit()
            flash("Committed successfully.")
            return redirect(url_for('voteTable', id=theme.id))
        else:
            flash("No vote theme found!")
            form.themeId.data = ""

    return render_template("table.html", form=form, title="新建候选人")


@app.route("/creatTheme", methods=["GET", "POST"])
@login_required
def creatTheme():
    if current_user.authority < 1:
        flash("您没有权限，如需升级权限请联系管理员")
        return redirect(url_for("index"))
    form = ThemeForm()
    if form.validate_on_submit():
        db.session.add(
            VoteTheme(id=form.id.data, theme=form.theme.data)
        )
        db.session.commit()
        flash("Committed successfully.")
        return redirect(url_for('voteHomepage'))
    return render_template("table.html", form=form, title="创建新投票主题")


# 新用户
class SignForm(FlaskForm):
    id = StringField("用户id：", validators=[DataRequired()])
    username = StringField("用户名", validators=[DataRequired()])
    newPassword = PasswordField("密码：", validators=[DataRequired()])
    confirmPassword = PasswordField("重复密码：", validators=[DataRequired()])
    submit = SubmitField("创建用户")


@app.route("/sign", methods=["GET", "POST"])
def sign():
    form = SignForm()
    if form.validate_on_submit():
        if User.query.get(form.id.data):
            flash("此id已被占用！")
        elif form.confirmPassword.data == form.newPassword.data:
            db.session.add(
                User(id=form.id.data, username=form.username.data, password=form.newPassword.data, authority=0)
            )
            db.session.commit()
            flash("创建成功,请登录")
            flash("新用户权限等级为0，如需升级请联系管理员")
            return redirect(url_for("login"))
        else:
            flash("请检查密码")

    return render_template("table.html", form=form, title="新用户")


# 重设密码表单
class ResetForm(FlaskForm):
    formerPassword = PasswordField("原密码：", validators=[DataRequired()])
    newPassword = PasswordField("新密码：", validators=[DataRequired()])
    confirmPassword = PasswordField("重复新密码：", validators=[DataRequired()])
    submit = SubmitField("确定修改")


# 重设密码
@app.route("/resetPassword", methods=["GET", "POST"])
@login_required
def resetPassword():
    form = ResetForm()
    if form.validate_on_submit():
        user = current_user
        if user.password == form.formerPassword.data:
            if form.confirmPassword.data == form.newPassword.data:
                user.password = form.newPassword.data
                db.session.commit()
                flash("修改成功,请重新登录")
                return redirect(url_for("logout"))
            else:
                flash("修改失败: 请检查新密码")
                form.newPassword.data = ""
                form.confirmPassword.data = ""
        else:
            flash("修改失败: 原密码错误")
            form.formerPassword.data = ""
            form.newPassword.data = ""
            form.confirmPassword.data = ""
    return render_template("table.html", form=form, title="修改密码")


if __name__ == "__main__":
    app.run(debug=True)
