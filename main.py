from flask import Flask, Response, request, json
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# Configurações de conexão com o Banco de Dados (ajuste conforme necessário)
# Lembre-se de substituir 'usuario', 'senha', 'host' e 'banco'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Senai%40134@127.0.0.1/medidor2'
app.config['JSON_AS_ASCII'] = False # Para garantir que caracteres como '°' sejam exibidos corretamente

mydb = SQLAlchemy(app)

# --- 2. MODELOS (MAPEAMENTO DAS TABELAS PARA CLASSES PYTHON) ---
# Cada classe representa uma tabela do seu banco de dados.

class LocalInstalacao(mydb.Model):
    __tablename__ = 'local_instalacao'
    id = mydb.Column(mydb.Integer, primary_key=True)
    nome = mydb.Column(mydb.String(80), nullable=False)
    descricao = mydb.Column(mydb.String(255))
    latitude = mydb.Column(mydb.Numeric(9, 6))
    longitude = mydb.Column(mydb.Numeric(9, 6))
    
    # Relacionamento: Um local pode ter vários dispositivos
    dispositivos = mydb.relationship('Dispositivo', back_populates='local', lazy=True)

    def to_json(self):
        return {"id": self.id, "nome": self.nome, "descricao": self.descricao, 
                "latitude": str(self.latitude), "longitude": str(self.longitude)}

class Dispositivo(mydb.Model):
    __tablename__ = 'dispositivo'
    id = mydb.Column(mydb.Integer, primary_key=True)
    nome = mydb.Column(mydb.String(80), nullable=False)
    local_id = mydb.Column(mydb.Integer, mydb.ForeignKey('local_instalacao.id'))
    ativo = mydb.Column(mydb.Boolean, default=True)
    
    # Relacionamentos
    local = mydb.relationship('LocalInstalacao', back_populates='dispositivos')
    sensores = mydb.relationship('Sensor', back_populates='dispositivo', lazy='joined') # 'joined' carrega os sensores junto com o dispositivo

    def to_json(self):
        return {"id": self.id, "nome": self.nome, "ativo": self.ativo,
                "local_id": self.local_id,
                # Inclui a lista de sensores deste dispositivo na resposta
                "sensores": [sensor.to_json_simple() for sensor in self.sensores]}

class Metrica(mydb.Model):
    __tablename__ = 'metrica'
    id = mydb.Column(mydb.Integer, primary_key=True)
    codigo = mydb.Column(mydb.String(40), unique=True, nullable=False)
    nome = mydb.Column(mydb.String(80), nullable=False)
    unidade = mydb.Column(mydb.String(20), nullable=False)

    def to_json(self):
        return {"id": self.id, "codigo": self.codigo, "nome": self.nome, "unidade": self.unidade}

class Sensor(mydb.Model):
    __tablename__ = 'sensor'
    id = mydb.Column(mydb.Integer, primary_key=True)
    dispositivo_id = mydb.Column(mydb.Integer, mydb.ForeignKey('dispositivo.id'), nullable=False)
    metrica_id = mydb.Column(mydb.Integer, mydb.ForeignKey('metrica.id'), nullable=False)
    modelo = mydb.Column(mydb.String(80))
    ativo = mydb.Column(mydb.Boolean, default=True)

    # Relacionamentos
    dispositivo = mydb.relationship('Dispositivo', back_populates='sensores')
    metrica = mydb.relationship('Metrica', lazy='joined') # Carrega a métrica junto com o sensor
    leituras = mydb.relationship('Leitura', back_populates='sensor', lazy=True)

    # Versão completa do JSON para quando o sensor é o objeto principal
    def to_json(self):
        return {"id": self.id, "modelo": self.modelo, "ativo": self.ativo,
                "dispositivo_id": self.dispositivo_id,
                "metrica": self.metrica.to_json() if self.metrica else None}

    # Versão simplificada para ser usada dentro de um dispositivo
    def to_json_simple(self):
        return {"id": self.id, "modelo": self.modelo, "ativo": self.ativo,
                "metrica_codigo": self.metrica.codigo if self.metrica else None,
                "metrica_unidade": self.metrica.unidade if self.metrica else None}


class Leitura(mydb.Model):
    __tablename__ = 'leitura'
    id = mydb.Column(mydb.BigInteger, primary_key=True)
    sensor_id = mydb.Column(mydb.Integer, mydb.ForeignKey('sensor.id'), nullable=False)
    ts = mydb.Column(mydb.DateTime, nullable=False, default=datetime.utcnow)
    valor_bruto = mydb.Column(mydb.Numeric(12, 4))
    valor_corrigido = mydb.Column(mydb.Numeric(12, 4))

    # Relacionamento
    sensor = mydb.relationship('Sensor', back_populates='leituras')

    def to_json(self):
        return {"id": self.id, "sensor_id": self.sensor_id, 
                "ts": self.ts.isoformat(), 
                # Converte Decimal para string para serialização JSON segura
                "valor_bruto": str(self.valor_bruto) if self.valor_bruto is not None else None,
                "valor_corrigido": str(self.valor_corrigido) if self.valor_corrigido is not None else None}


# --- 3. FUNÇÃO AUXILIAR PARA RESPOSTAS ---
def gera_resposta(status, conteudo, mensagem=False):
    body = {"dados": conteudo}
    if mensagem:
        body["mensagem"] = mensagem
    return Response(json.dumps(body, default=str), status=status, mimetype="application/json")


# --- 4. ENDPOINTS (ROTAS DA API) ---

# Rota principal para receber dados dos sensores (o caso de uso mais importante)
@app.route('/leituras', methods=['POST'])
def cria_leitura():
    """
    Endpoint para que o dispositivo envie novas leituras.
    O corpo da requisição deve ser um JSON com 'sensor_id' e 'valor'.
    Ex: {"sensor_id": 1, "valor": 25.4}
    """
    dados = request.get_json()

    if not dados or 'sensor_id' not in dados or 'valor' not in dados:
        return gera_resposta(400, {}, "Requisição inválida. 'sensor_id' e 'valor' são obrigatórios.")

    # Verifica se o sensor existe no banco
    sensor = Sensor.query.get(dados.get('sensor_id'))
    if not sensor:
        return gera_resposta(404, {}, f"Sensor com ID {dados.get('sensor_id')} não encontrado.")

    try:
        # Cria a nova leitura. O timestamp (ts) é gerado automaticamente.
        nova_leitura = Leitura(
            sensor_id=dados['sensor_id'],
            valor_bruto=dados['valor'],
            # Aqui você poderia adicionar lógica para o 'valor_corrigido'
            valor_corrigido=dados['valor'] 
        )
        mydb.session.add(nova_leitura)
        mydb.session.commit()
        return gera_resposta(201, nova_leitura.to_json(), "Leitura criada com sucesso.")

    except Exception as e:
        mydb.session.rollback()
        print(f"Erro ao salvar leitura: {e}")
        return gera_resposta(500, {}, "Erro interno ao salvar a leitura.")


# Rota para consultar as últimas leituras de um sensor específico
@app.route('/sensores/<int:sensor_id>/leituras', methods=['GET'])
def get_leituras_por_sensor(sensor_id):
    """
    Retorna as últimas N leituras para um sensor específico.
    Use o parâmetro 'limit' na URL para controlar o número de resultados.
    Ex: /sensores/1/leituras?limit=50
    """
    limite = request.args.get('limit', 100, type=int) # Padrão de 100 leituras
    
    leituras = Leitura.query.filter_by(sensor_id=sensor_id)\
                            .order_by(Leitura.ts.desc())\
                            .limit(limite)\
                            .all()
    
    if not leituras:
        return gera_resposta(404, [], f"Nenhuma leitura encontrada para o sensor ID {sensor_id}.")

    leituras_json = [leitura.to_json() for leitura in leituras]
    return gera_resposta(200, leituras_json)

# Rota para consultar todos os dispositivos e seus sensores
@app.route('/dispositivos', methods=['GET'])
def get_dispositivos():
    """
    Lista todos os dispositivos cadastrados e os sensores em cada um.
    """
    dispositivos = Dispositivo.query.all()
    dispositivos_json = [dispositivo.to_json() for dispositivo in dispositivos]
    return gera_resposta(200, dispositivos_json, "Lista de dispositivos")

# --- 5. EXECUÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    app.run(debug=True)