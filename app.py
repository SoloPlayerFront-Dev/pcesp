from flask import Flask, render_template, request, redirect, session, url_for, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from db import db
import os
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
app.config.from_object(Config)

# Pastas de Upload
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'fotos_perfil')
app.config['EVIDENCE_FOLDER'] = os.path.join('static', 'evidencias')

# Criar pastas se não existirem
os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), app.config['UPLOAD_FOLDER']), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), app.config['EVIDENCE_FOLDER']), exist_ok=True)

# Tipos de arquivos permitidos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

# --- IMPORTAÇÃO DOS MODELOS ---
from models.users import Usuario, Promocao, Cargo, Advertencia, LogAtividade
from models.pessoas import Pessoa
from models.boletins import Boletim, AnexoBoletim
from models.auto_prisao import AutoPrisao
from models.crimes import Crime
from models.armas import Arma, MovimentacaoArma
from models.acadepol import Comunicado
from models.avisos import Aviso

# --- HELPERS E DECORATORS ---
from functools import wraps

def current_user():
    if 'user_id' in session:
        return Usuario.query.get(session['user_id'])
    return None

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def registrar_log(acao, alvo, detalhes=""):
    user = current_user()
    if user:
        db.session.add(LogAtividade(autor_id=user.id, acao=acao, alvo=str(alvo), detalhes=detalhes))
        db.session.commit()

def pode_alterar_usuario(alvo_user):
    me = current_user()
    if not me: return False
    if me.id == alvo_user.id: return True
    return me.nivel_hierarquico > alvo_user.nivel_hierarquico

@app.context_processor
def inject_helpers():
    return dict(
        pode_gerenciar=lambda: current_user() and current_user().nivel_hierarquico >= 80,
        current_user=current_user, 
        pode_alterar_usuario=pode_alterar_usuario
    )

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(matricula=request.form['matricula']).first()
        if user and check_password_hash(user.senha, request.form['senha']):
            session['user_id'] = user.id
            registrar_log('Login', 'Sistema', 'Acesso realizado')
            flash(f'Bem-vindo, {user.nome}.', 'success')
            return redirect(url_for('dashboard'))
        flash('Credenciais inválidas.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# --- DASHBOARD E AVISOS ---

@app.route('/dashboard')
@login_required
def dashboard():
    # Busca avisos ordenados por data (mais recentes primeiro)
    avisos = Aviso.query.order_by(Aviso.data_criacao.desc()).limit(10).all()
    
    # Dados para o resumo lateral (Contadores em Tempo Real)
    contadores = {
        'bo_pendentes': Boletim.query.filter_by(status='Pendente').count(),
        # Conta tanto 'Em Uso' (Patrimônio) quanto 'Transito' (Evidência)
        'armas_cautela': Arma.query.filter(Arma.status.in_(['Em Uso', 'Transito'])).count(),
        'efetivo_ativo': Usuario.query.count()
    }
    
    return render_template('dashboard.html', usuario=current_user(), avisos=avisos, contadores=contadores)

@app.route('/dashboard/aviso/criar', methods=['POST'])
@login_required
def criar_aviso():
    # Apenas chefia ou admin pode criar avisos (Nível >= 60)
    if current_user().nivel_hierarquico < 60:
        flash('Permissão insuficiente para publicar avisos.', 'danger')
        return redirect(url_for('dashboard'))
        
    novo_aviso = Aviso(
        titulo=request.form['titulo'],
        conteudo=request.form['conteudo'],
        prioridade=request.form['prioridade'],
        autor_id=current_user().id
    )
    db.session.add(novo_aviso)
    db.session.commit()
    registrar_log('Novo Aviso', novo_aviso.titulo, novo_aviso.prioridade)
    flash('Aviso publicado no mural.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/dashboard/aviso/excluir/<int:id>')
@login_required
def excluir_aviso(id):
    aviso = Aviso.query.get_or_404(id)
    # Apenas quem criou ou chefia pode apagar
    if aviso.autor_id == current_user().id or current_user().nivel_hierarquico >= 80:
        db.session.delete(aviso)
        db.session.commit()
        flash('Aviso removido.', 'success')
    else:
        flash('Sem permissão.', 'danger')
    return redirect(url_for('dashboard'))

# --- MÓDULO: PESSOAS ---

@app.route('/pessoas')
@login_required
def banco_pessoas():
    busca = request.args.get('q')
    if busca:
        pessoas = Pessoa.query.filter(Pessoa.nome.contains(busca)).all()
    else:
        pessoas = Pessoa.query.all()
    return render_template('banco_pessoas.html', pessoas=pessoas)

@app.route('/pessoas/cadastrar', methods=['GET','POST'])
@login_required
def cadastrar_pessoa():
    if request.method == 'POST':
        p = Pessoa(
            nome=request.form['nome'],
            rg=request.form['rg'],
            data_nascimento=request.form['data_nascimento'],
            nome_mae=request.form['nome_mae'],
            endereco=request.form['endereco'],
            antecedentes=request.form['antecedentes']
        )
        try:
            db.session.add(p)
            db.session.commit()
            flash('Cidadão cadastrado com sucesso.', 'success')
            return redirect(url_for('banco_pessoas'))
        except:
            db.session.rollback()
            flash('Erro: RG já cadastrado.', 'danger')
    return render_template('cadastrar_pessoa.html')

# --- MÓDULO: CRIMES (TIPIFICAÇÃO) ---

@app.route('/crimes')
@login_required
def gerenciar_crimes():
    crimes = Crime.query.all()
    return render_template('crimes.html', crimes=crimes)

@app.route('/crimes/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar_crime():
    if request.method == 'POST':
        c = Crime(
            nome=request.form['nome'], 
            artigo=request.form['artigo'], 
            pena=request.form['pena']
        )
        db.session.add(c)
        db.session.commit()
        flash('Crime adicionado ao catálogo.', 'success')
        return redirect(url_for('gerenciar_crimes'))
    return render_template('cadastrar_crime.html')

# --- MÓDULO: BOLETINS DE OCORRÊNCIA ---

@app.route('/boletins')
@login_required
def boletins():
    boletins = Boletim.query.order_by(Boletim.data.desc()).all()
    return render_template('boletins.html', boletins=boletins)

@app.route('/boletins/cadastrar', methods=['GET','POST'])
@login_required
def cadastrar_boletim():
    oficiais = Usuario.query.all()
    crimes = Crime.query.all()

    if request.method == 'POST':
        # Salvar Anexo Principal (Capa)
        arquivo_nome = None
        if 'evidencia' in request.files:
            file = request.files['evidencia']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"capa_bo_{datetime.now().timestamp()}_{filename}"
                file.save(os.path.join(app.config['EVIDENCE_FOLDER'], filename))
                arquivo_nome = filename

        natureza = request.form.get('natureza_crime')
        desc_texto = request.form['descricao']
        descricao_final = f"[Natureza: {natureza}] \n{desc_texto}" if natureza else desc_texto

        b = Boletim(
            autor=request.form['autor'], 
            vitima=request.form['vitima'], 
            descricao=descricao_final, 
            policial_responsavel=request.form.get('policial_responsavel', current_user().nome),
            status='Pendente',
            arquivo_evidencia=arquivo_nome
        )
        db.session.add(b)
        db.session.commit()
        flash('Boletim registrado com sucesso.', 'success')
        # Redireciona para detalhes para permitir adicionar mais anexos
        return redirect(url_for('detalhes_boletim', id=b.id))
    
    return render_template('cadastrar_boletim.html', oficiais=oficiais, crimes=crimes)

@app.route('/boletins/detalhes/<int:id>')
@login_required
def detalhes_boletim(id):
    boletim = Boletim.query.get_or_404(id)
    return render_template('detalhes_boletim.html', boletim=boletim)

@app.route('/boletins/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_boletim(id):
    boletim = Boletim.query.get_or_404(id)
    oficiais = Usuario.query.all()
    crimes = Crime.query.all()

    if request.method == 'POST':
        boletim.autor = request.form['autor']
        boletim.vitima = request.form['vitima']
        boletim.descricao = request.form['descricao']
        boletim.policial_responsavel = request.form['policial_responsavel']
        
        if 'status' in request.form:
            boletim.status = request.form['status']
        
        if 'evidencia' in request.files:
            file = request.files['evidencia']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = f"capa_bo_{datetime.now().timestamp()}_{filename}"
                file.save(os.path.join(app.config['EVIDENCE_FOLDER'], filename))
                boletim.arquivo_evidencia = filename

        db.session.commit()
        flash('Ocorrência atualizada.', 'success')
        return redirect(url_for('detalhes_boletim', id=boletim.id))

    return render_template('cadastrar_boletim.html', boletim=boletim, oficiais=oficiais, crimes=crimes)

@app.route('/boletins/resolver/<int:id>')
@login_required
def resolver_boletim(id):
    boletim = Boletim.query.get_or_404(id)
    if boletim.status == 'Pendente':
        boletim.status = 'Concluído'
        flash('Caso marcado como Concluído.', 'success')
    else:
        boletim.status = 'Pendente'
        flash('Caso reaberto.', 'warning')
    db.session.commit()
    return redirect(url_for('detalhes_boletim', id=id))

@app.route('/boletins/anexar/<int:id>', methods=['POST'])
@login_required
def adicionar_anexo_boletim(id):
    boletim = Boletim.query.get_or_404(id)
    if 'novo_anexo' in request.files:
        file = request.files['novo_anexo']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"anexo_bo_{boletim.id}_{datetime.now().timestamp()}_{filename}"
            
            tipo = 'Imagem' if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')) else 'Documento'
            
            file.save(os.path.join(app.config['EVIDENCE_FOLDER'], filename))
            novo_anexo = AnexoBoletim(boletim_id=boletim.id, arquivo=filename, tipo=tipo)
            db.session.add(novo_anexo)
            db.session.commit()
            flash('Arquivo anexado ao dossiê.', 'success')
    return redirect(url_for('detalhes_boletim', id=id))

@app.route('/boletins/anexo/excluir/<int:id>')
@login_required
def excluir_anexo_boletim(id):
    anexo = AnexoBoletim.query.get_or_404(id)
    boletim_id = anexo.boletim_id
    try:
        os.remove(os.path.join(app.config['EVIDENCE_FOLDER'], anexo.arquivo))
    except: pass
    db.session.delete(anexo)
    db.session.commit()
    flash('Anexo removido.', 'success')
    return redirect(url_for('detalhes_boletim', id=boletim_id))

# --- MÓDULO: AUTOS DE PRISÃO ---

@app.route('/autos')
@login_required
def autos():
    autos = AutoPrisao.query.all()
    return render_template('auto_prisao.html', autos=autos)

@app.route('/autos/cadastrar', methods=['GET','POST'])
@login_required
def cadastrar_auto():
    crimes = Crime.query.all()
    if request.method == 'POST':
        natureza = request.form.get('natureza_crime')
        desc_texto = request.form['descricao']
        descricao_final = f"[Autuado por: {natureza}] \n{desc_texto}" if natureza else desc_texto

        a = AutoPrisao(
            preso=request.form['preso'], 
            descricao_fato=descricao_final, 
            testemunhas=request.form['testemunhas'], 
            policial_responsavel=current_user().nome
        )
        db.session.add(a)
        db.session.commit()
        flash('Prisão registrada.', 'success')
        return redirect(url_for('autos'))
    return render_template('cadastrar_auto.html', crimes=crimes)

@app.route('/autos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_auto(id):
    auto = AutoPrisao.query.get_or_404(id)
    crimes = Crime.query.all()
    if request.method == 'POST':
        auto.preso = request.form['preso']
        auto.descricao_fato = request.form['descricao']
        auto.testemunhas = request.form['testemunhas']
        if request.form.get('natureza_crime'):
             auto.descricao_fato = f"[Natureza: {request.form.get('natureza_crime')}] \n{request.form['descricao']}"
        
        db.session.commit()
        flash('Auto atualizado.', 'success')
        return redirect(url_for('autos'))
    return render_template('cadastrar_auto.html', auto=auto, crimes=crimes)

# --- MÓDULO: MEMBROS E PERFIL ---

@app.route('/membros')
@login_required
def gerenciar_membros():
    usuarios = Usuario.query.all()
    return render_template('gerenciar_membros.html', usuarios=usuarios)

@app.route('/perfil/<int:id>')
@login_required
def perfil_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    promocoes = Promocao.query.filter_by(usuario_id=id).order_by(Promocao.data_promocao.desc()).all()
    advertencias = Advertencia.query.filter_by(usuario_id=id).order_by(Advertencia.data_aplicacao.desc()).all()
    cargos = Cargo.query.order_by(Cargo.nivel.desc()).all()
    return render_template('perfil_usuario.html', usuario=usuario, promocoes=promocoes, advertencias=advertencias, cargos=cargos)

@app.route('/membros/cadastrar', methods=['GET','POST'])
@login_required
def cadastrar_membros():
    cargos = Cargo.query.order_by(Cargo.nivel.desc()).all()
    if request.method == 'POST':
        cargo_id = int(request.form['cargo_id'])
        cargo_selecionado = Cargo.query.get(cargo_id)
        
        if cargo_selecionado.nivel >= current_user().nivel_hierarquico:
            flash('Você não tem permissão para cadastrar este nível de patente.', 'danger')
            return render_template('cadastrar_membros.html', cargos=cargos)

        try:
            foto_filename = 'default.jpg'
            if 'foto_perfil' in request.files:
                file = request.files['foto_perfil']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    foto_filename = filename

            u = Usuario(
                nome=request.form['nome'], 
                matricula=request.form['matricula'], 
                senha=generate_password_hash(request.form['senha']), 
                cargo_id=cargo_id, 
                foto_perfil=foto_filename, 
                delegacia=request.form.get('delegacia'), 
                departamento=request.form.get('departamento'), 
                endereco=request.form.get('endereco'), 
                observacoes=request.form.get('observacoes')
            )
            db.session.add(u)
            db.session.commit()
            registrar_log('Cadastro Membro', u.nome, f'Matrícula {u.matricula}')
            flash('Membro cadastrado.', 'success')
            return redirect(url_for('gerenciar_membros'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao cadastrar: {str(e)}', 'danger')
            
    return render_template('cadastrar_membros.html', cargos=cargos)

@app.route('/membros/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_membro(id):
    usuario = Usuario.query.get_or_404(id)
    cargos = Cargo.query.order_by(Cargo.nivel.desc()).all()

    if not pode_alterar_usuario(usuario):
        flash('Acesso negado. Você não pode modificar este perfil.', 'danger')
        return redirect(url_for('perfil_usuario', id=id))

    if request.method == 'POST':
        usuario.nome = request.form['nome']
        usuario.matricula = request.form['matricula']
        
        novo_cargo_id = int(request.form['cargo_id'])
        if novo_cargo_id != usuario.cargo_id:
            novo_cargo_obj = Cargo.query.get(novo_cargo_id)
            
            if novo_cargo_obj.nivel >= current_user().nivel_hierarquico:
                flash('Permissão insuficiente para promover a este cargo.', 'danger')
                return render_template('cadastrar_membros.html', usuario=usuario, cargos=cargos)

            promocao = Promocao(
                usuario_id=usuario.id, 
                cargo_anterior=usuario.cargo, 
                novo_cargo=novo_cargo_obj.nome, 
                motivo="Alteração de Cadastro"
            )
            db.session.add(promocao)
            usuario.cargo_id = novo_cargo_id
        
        usuario.delegacia = request.form['delegacia']
        usuario.departamento = request.form['departamento']
        usuario.endereco = request.form['endereco']
        usuario.observacoes = request.form['observacoes']

        if request.form.get('senha'):
            usuario.senha = generate_password_hash(request.form.get('senha'))
            
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                usuario.foto_perfil = filename
                
        db.session.commit()
        registrar_log('Edição de Perfil', usuario.nome)
        flash('Ficha atualizada.', 'success')
        return redirect(url_for('perfil_usuario', id=usuario.id))
            
    return render_template('cadastrar_membros.html', usuario=usuario, cargos=cargos)

@app.route('/promover/<int:id>', methods=['POST'])
@login_required
def adicionar_promocao(id):
    usuario = Usuario.query.get_or_404(id)
    if not pode_alterar_usuario(usuario):
        flash('Sem permissão.', 'danger')
        return redirect(url_for('perfil_usuario', id=id))

    novo_cargo_id = int(request.form['novo_cargo_id'])
    cargo_novo = Cargo.query.get(novo_cargo_id)
    
    if cargo_novo.nivel >= current_user().nivel_hierarquico:
        flash('Você não pode promover para uma patente igual ou superior à sua.', 'danger')
        return redirect(url_for('perfil_usuario', id=id))

    promo = Promocao(
        usuario_id=usuario.id, 
        cargo_anterior=usuario.cargo, 
        novo_cargo=cargo_novo.nome, 
        motivo=request.form['motivo']
    )
    usuario.cargo_id = novo_cargo_id
    
    db.session.add(promo)
    db.session.commit()
    registrar_log('Promoção Registrada', usuario.nome, cargo_novo.nome)
    flash('Promoção registrada com sucesso.', 'success')
    return redirect(url_for('perfil_usuario', id=id))

@app.route('/advertir/<int:id>', methods=['POST'])
@login_required
def aplicar_advertencia(id):
    usuario = Usuario.query.get_or_404(id)
    if not pode_alterar_usuario(usuario):
        flash('Sem permissão hierárquica.', 'danger')
        return redirect(url_for('perfil_usuario', id=id))
        
    adv = Advertencia(
        usuario_id=id,
        autor_id=current_user().id,
        tipo=request.form['tipo'],
        descricao=request.form['descricao']
    )
    db.session.add(adv)
    db.session.commit()
    registrar_log('Aplicação de Advertência', usuario.nome, request.form['tipo'])
    flash('Registro disciplinar adicionado.', 'warning')
    return redirect(url_for('perfil_usuario', id=id))

@app.route('/membros/excluir/<int:id>')
@login_required
def excluir_membro(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user().id or not pode_alterar_usuario(usuario):
        flash('Ação não permitida.', 'danger')
        return redirect(url_for('gerenciar_membros'))
        
    nome_removido = usuario.nome
    db.session.delete(usuario)
    db.session.commit()
    registrar_log('Exclusão de Membro', nome_removido)
    flash('Membro removido.', 'success')
    return redirect(url_for('gerenciar_membros'))

# --- GESTÃO DE CARGOS ---

@app.route('/cargos')
@login_required
def gerenciar_cargos():
    if current_user().nivel_hierarquico < 80:
        flash('Acesso restrito à chefia.', 'danger')
        return redirect(url_for('dashboard'))
    cargos = Cargo.query.order_by(Cargo.nivel.desc()).all()
    return render_template('gerenciar_cargos.html', cargos=cargos)

@app.route('/cargos/adicionar', methods=['POST'])
@login_required
def adicionar_cargo():
    if current_user().nivel_hierarquico < 80:
        return redirect(url_for('dashboard'))
    
    if Cargo.query.filter_by(nome=request.form['nome']).first():
        flash('Cargo já existe.', 'danger')
    else:
        c = Cargo(nome=request.form['nome'], nivel=int(request.form['nivel']))
        db.session.add(c)
        db.session.commit()
        registrar_log('Criar Cargo', c.nome)
        flash('Cargo criado com sucesso.', 'success')
    return redirect(url_for('gerenciar_cargos'))

# --- MÓDULO: ARMARIA ---

@app.route('/armaria')
@login_required
def armaria():
    acervo = request.args.get('acervo')
    armas = Arma.query.filter_by(acervo=acervo).all() if acervo else Arma.query.all()
    return render_template('armaria.html', armas=armas, filtro_atual=acervo)

@app.route('/armaria/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar_arma():
    pre_boletim_id = request.args.get('boletim_id')
    pre_auto_id = request.args.get('auto_id')
    
    if request.method == 'POST':
        serie = request.form['numero_serie'] or f"INT-{int(datetime.now().timestamp())}"
        nova_arma = Arma(
            acervo=request.form['acervo'],
            tipo=request.form['tipo'],
            modelo=request.form['modelo'],
            marca=request.form['marca'],
            calibre=request.form['calibre'],
            numero_serie=serie,
            status='Disponivel' if request.form['acervo'] == 'Patrimonio' else 'Custodia',
            localizacao_atual='Armário Central',
            boletim_id=request.form.get('boletim_id') or None,
            auto_prisao_id=request.form.get('auto_prisao_id') or None
        )
        try:
            db.session.add(nova_arma)
            db.session.commit()
            
            log = MovimentacaoArma(
                arma_id=nova_arma.id,
                usuario_responsavel_id=current_user().id,
                tipo_movimentacao='Entrada',
                destinatario='Estoque',
                observacao='Cadastro Inicial'
            )
            db.session.add(log)
            db.session.commit()
            
            if request.form.get('boletim_id'): return redirect(url_for('detalhes_boletim', id=request.form['boletim_id']))
            if request.form.get('auto_prisao_id'): return redirect(url_for('editar_auto', id=request.form['auto_prisao_id']))
            
            flash('Item cadastrado.', 'success')
            return redirect(url_for('armaria'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'danger')

    boletins = Boletim.query.order_by(Boletim.id.desc()).limit(20).all()
    autos = AutoPrisao.query.order_by(AutoPrisao.id.desc()).limit(20).all()
    return render_template('cadastrar_arma.html', boletins=boletins, autos=autos, pre_boletim_id=pre_boletim_id, pre_auto_id=pre_auto_id)

@app.route('/armaria/movimentar/<int:id>', methods=['GET', 'POST'])
@login_required
def movimentar_arma(id):
    arma = Arma.query.get_or_404(id)
    # Carrega todos os oficiais para o select
    oficiais = Usuario.query.order_by(Usuario.nome).all()
    
    if request.method == 'POST':
        tipo = request.form['tipo_movimentacao']
        
        # Lógica para pegar o destinatário correto
        dest = request.form.get('destinatario_select')
        if dest == 'OUTRO':
            dest = request.form.get('destinatario_manual')
        if not dest:
            dest = request.form.get('destinatario') 

        if tipo == 'Retirada':
            arma.status = 'Em Uso' if arma.acervo == 'Patrimonio' else 'Transito'
            arma.localizacao_atual = dest
        elif tipo == 'Devolucao':
            arma.status = 'Disponivel' if arma.acervo == 'Patrimonio' else 'Custodia'
            arma.localizacao_atual = 'Armário Central'
            
        log = MovimentacaoArma(
            arma_id=arma.id, 
            usuario_responsavel_id=current_user().id, 
            tipo_movimentacao=tipo, 
            destinatario=dest, 
            observacao=request.form['observacao']
        )
        db.session.add(log)
        db.session.commit()
        flash('Movimentação registrada.', 'success')
        return redirect(url_for('armaria'))
        
    return render_template('movimentar_arma.html', arma=arma, oficiais=oficiais)

@app.route('/armaria/historico/<int:id>')
@login_required
def historico_arma(id):
    arma = Arma.query.get_or_404(id)
    historico = MovimentacaoArma.query.filter_by(arma_id=id).order_by(MovimentacaoArma.data_movimentacao.desc()).all()
    return render_template('historico_arma.html', arma=arma, historico=historico)

# --- MÓDULO: ACADEPOL ---

@app.route('/acadepol')
def acadepol_publico():
    query = Comunicado.query.filter_by(ativo=True).order_by(Comunicado.data_publicacao.desc())
    if request.args.get('categoria'): query = query.filter_by(categoria=request.args.get('categoria'))
    if request.args.get('q'): query = query.filter(Comunicado.titulo.contains(request.args.get('q')))
    return render_template('acadepol_publico.html', comunicados=query.all())

@app.route('/acadepol/admin')
@login_required
def acadepol_admin():
    if current_user().nivel_hierarquico < 80:
        flash('Acesso restrito.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('acadepol_admin.html', comunicados=Comunicado.query.order_by(Comunicado.data_publicacao.desc()).all())

@app.route('/acadepol/publicar', methods=['GET', 'POST'])
@login_required
def acadepol_publicar():
    if request.method == 'POST':
        arquivo_nome = None
        if 'anexo' in request.files:
            file = request.files['anexo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"acad_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config['EVIDENCE_FOLDER'], filename))
                arquivo_nome = filename

        comunicado = Comunicado(
            titulo=request.form['titulo'],
            conteudo=request.form['conteudo'],
            categoria=request.form['categoria'],
            arquivo_anexo=arquivo_nome,
            autor_id=current_user().id
        )
        db.session.add(comunicado)
        db.session.commit()
        flash('Publicado com sucesso.', 'success')
        return redirect(url_for('acadepol_admin'))
    return render_template('acadepol_form.html')

@app.route('/acadepol/excluir/<int:id>')
@login_required
def acadepol_excluir(id):
    c = Comunicado.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash('Publicação removida.', 'success')
    return redirect(url_for('acadepol_admin'))

# --- ROTA DE ARQUIVOS ---
@app.route('/evidencias/<filename>')
@login_required
def baixar_evidencia(filename):
    return send_from_directory(app.config['EVIDENCE_FOLDER'], filename)

# --- INICIALIZAÇÃO COM SEED ---
if __name__ == '__main__':
    app.secret_key = Config.SECRET_KEY
    with app.app_context():
        db.create_all()
        
        if not Cargo.query.first():
            cargos_iniciais = [
                ('Delegado Geral', 100),
                ('Delegado Titular', 90),
                ('Delegado de Polícia', 80),
                ('Investigador Chefe', 60),
                ('Escrivão Chefe', 60),
                ('Investigador', 40),
                ('Escrivão', 40),
                ('Agente Policial', 20),
                ('Carcereiro', 20),
                ('Administrativo', 10)
            ]
            for nome, nivel in cargos_iniciais:
                db.session.add(Cargo(nome=nome, nivel=nivel))
            db.session.commit()
            
            admin_cargo = Cargo.query.filter_by(nome='Delegado Geral').first()
            if admin_cargo and not Usuario.query.filter_by(matricula='admin').first():
                admin = Usuario(
                    nome="Administrador Sistema", matricula="admin", senha=generate_password_hash("admin"), 
                    cargo_id=admin_cargo.id, delegacia="DGP - Geral", departamento="Tecnologia da Informação"
                )
                db.session.add(admin)
                db.session.commit()
                print("--- SISTEMA INICIALIZADO: Login: admin | Senha: admin ---")

    app.run(debug=True)