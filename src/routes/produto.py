import uuid
from base64 import b64encode
from flask import Blueprint, flash, redirect, url_for, render_template, request, Response, abort
from flask_login import login_required
from werkzeug.exceptions import NotFound
from src.forms.produto import ProdutoForm
from src.models.categoria import Categoria
from src.models.produto import Produto
from src.modules import db

bp = Blueprint('produto', __name__, url_prefix='/produto')


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if Categoria.is_empty():
        flash("Impossível adicionar produto. Adicione pelo menos uma categoria", category='warning')
        return redirect(url_for('categoria.add'))

    form = ProdutoForm()
    form.submit.label.text = "Adicionar Produto"
    categorias = db.session.execute(db.select(Categoria).order_by(Categoria.nome)).scalars()
    form.categoria.choices = [(str(i.id), i.nome) for i in categorias]

    if form.validate_on_submit():
        produto = Produto(nome=form.nome.data, preco=form.preco.data, ativo=form.ativo.data, estoque=form.estoque.data)
        if form.foto.data:
            produto.possui_foto = True
            produto.foto_base64 = b64encode(request.files[form.foto.name].read()).decode('ascii')
            produto.foto_mime = request.files[form.foto.name].mimetype
        else:
            produto.possui_foto = False
            produto.foto_base64 = None
            produto.foto_mime = None

        categoria = Categoria.get_by_id(form.categoria.data)
        if categoria is None:
            flash('Categoria inexistente!', category='danger')
            return redirect(url_for('produto.add'))
        produto.categoria = categoria

        db.session.add(produto)
        db.session.commit()
        flash("Produto adicionado com sucesso!")
        return redirect(url_for('index'))

    return render_template('produto/add.jinja2', form=form, title="Adicionar novo Produto")


@bp.route('/edit/<uuid:produto_id>', methods=['GET', 'POST'])
def edit(produto_id):
    produto = Produto.get_by_id(produto_id)
    if produto is None:
        flash("Produto inexistente!", category='danger')
        return redirect(url_for('produto.lista'))

    form = ProdutoForm(obj=produto)
    form.submit.label.text = "Alterar Produto"
    categorias = db.session.execute(db.select(Categoria).order_by(Categoria.nome)).scalars()
    form.categoria.choices = [(str(i.id), i.nome) for i in categorias]
    if form.validate_on_submit():
        produto.nome = form.nome.data
        produto.preco = form.preco.data
        produto.estoque = form.estoque.data
        produto.ativo = form.ativo.data
        categoria = Categoria.get_by_id(form.categoria.data)

        if form.removerfoto.data:
            produto.possui_foto = False
            produto.foto_base64 = None
            produto.foto_mime = None
        elif form.foto.data:
            produto.possui_foto = True
            produto.foto_base64 = (b64encode(request.files[form.foto.name].read()).decode('ascii'))
            produto.foto_mime = request.files[form.foto.name].mimetype

        if categoria is None:
            flash('Categoria inexistente!', category='danger')
            return redirect(url_for('produto.add'))

        produto.categoria = categoria
        db.session.commit()
        flash("Produto alterado", category='success')
        return redirect(url_for('produto.lista'))

    form.categoria.process_data(str(produto.categoria_id))
    return render_template('produto/edit.jinja2', form=form, title="Alterar um produto", produto=produto)


@bp.route('/delete/<uuid:produto_id>', methods=["GET"])
@login_required
def delete(produto_id):
    produto = Produto.get_by_id(produto_id)
    if produto is None:
        flash("Produto inexistente!", category='danger')
        return redirect(url_for('produto.lista'))

    db.session.delete(produto)
    db.session.commit()
    flash("Produto removido!", category='success')

    return redirect(url_for('produto.lista'))


@bp.route('/lista', methods=['GET', 'POST'])
@bp.route('/', methods=['GET', 'POST'])
def lista():
    page = request.args.get('page', type=int, default=1)
    pp = request.args.get('pp', type=int, default=25)
    q = request.args.get('q', type=str, default="")
    categoria_id = request.args.get('categoria_id', type=str, default="")
    preco_min = request.args.get('preco_min', type=float, default=None)
    preco_max = request.args.get('preco_max', type=float, default=None)

    sentenca = db.select(Produto).order_by(Produto.nome)

    if q != "":
        sentenca = sentenca.filter(Produto.nome.ilike(f"%{q}%"))

    if categoria_id:
        try:
            categoria_uuid = uuid.UUID(categoria_id)
            sentenca = sentenca.filter(Produto.categoria_id == categoria_uuid)
        except ValueError:
            flash("Categoria inválida!", category='danger')
            return redirect(url_for('produto.lista'))

    if preco_min is not None:
        sentenca = sentenca.filter(Produto.preco >= preco_min)

    if preco_max is not None:
        sentenca = sentenca.filter(Produto.preco <= preco_max)

    try:
        rset = db.paginate(sentenca, page=page, per_page=pp, error_out=True)
    except NotFound:
        flash(f"Não temos produtos na página {page}. Apresentando página 1")
        page = 1
        rset = db.paginate(sentenca, page=page, per_page=pp, error_out=False)

    categorias = db.session.execute(db.select(Categoria).order_by(Categoria.nome)).scalars()

    return render_template('produto/lista.jinja2', title="Lista de produtos", rset=rset, page=page, pp=pp, q=q,
                           categorias=categorias, categoria_id=categoria_id, preco_min=preco_min, preco_max=preco_max)


@bp.route('/imagem/<uuid:id_produto>', methods=['GET'])
def imagem(id_produto):
    produto = Produto.get_by_id(id_produto)
    if produto is None:
        return abort(404)
    conteudo, tipo = produto.imagem
    return Response(conteudo, mimetype=tipo)


@bp.route('/thumbnail/<uuid:id_produto>/<int:size>', methods=['GET'])
@bp.route('/thumbnail/<uuid:id_produto>', methods=['GET'])
def thumbnail(id_produto, size=128):
    produto = Produto.get_by_id(id_produto)
    if produto is None:
        return abort(404)
    conteudo, tipo = produto.thumbnail(size)
    return Response(conteudo, mimetype=tipo)
