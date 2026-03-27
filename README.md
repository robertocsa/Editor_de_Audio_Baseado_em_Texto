# Editor_de_Audio_Baseado_em_Texto
Edição automática de áudio p/ texto c/ WhisperX: transcreva, edite palavras e gere áudio limpo automaticamente c/ alinhamento preciso e corte inteligente.

# 🎧 Editor de Áudio por Palavras (WhisperX + Python)

Uma ferramenta inteligente para **edição de áudio baseada em texto**, permitindo remover gagueiras, repetições e vícios de linguagem de forma automatizada.

---

## 🚀 Visão Geral

Este projeto utiliza **WhisperX** para transcrever áudio com alinhamento temporal por palavra, permitindo que o usuário edite o conteúdo em formato textual e gere automaticamente um novo áudio limpo.

### 🔑 Diferencial

> Você edita o áudio **editando texto**, não waveform.

---

## 🧠 Como Funciona

Pipeline simplificado:

Áudio → Transcrição → Alinhamento → Texto → Edição → Comparação → Corte → Áudio final


---

## ⚙️ Tecnologias Utilizadas

- Python
- Tkinter (interface gráfica)
- WhisperX (transcrição + alinhamento)
- Pydub (manipulação de áudio)
- difflib (comparação de texto)
- JSON (persistência de dados)

---

## 📦 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/audio-editor-palavras.git
cd audio-editor-palavras

2. Crie um ambiente virtual (recomendado)

python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

3. Instale as dependências
pip install whisperx pydub

⚠️ Dependências adicionais podem ser necessárias para o WhisperX (como ffmpeg e PyTorch).
▶️ Como Usar
1. Execute a aplicação
python main.py
2. Fluxo de uso
🔹 Passo 1: Selecionar áudio
Escolha um arquivo (.wav, .mp3, etc.)
🔹 Passo 2: Transcrever
Gera:
words.json
narracao_original.txt
🔹 Passo 3: Editar texto

Crie:

narracao_editado.txt
Remova:
Gagueiras
Repetições
Interjeições
🔹 Passo 4: Debug (opcional)

Gera:

debug_removidas.txt
Mostra palavras que serão removidas
🔹 Passo 5: Gerar áudio final

Output:

audio_final.wav
📁 Estrutura de Arquivos
.
├── main.py
├── words.json
├── narracao_original.txt
├── narracao_editado.txt
├── debug_removidas.txt
├── audio_final.wav
🔍 Lógica Principal
🧩 1. Normalização de texto

Remove variações para comparação robusta:

unicodedata.normalize('NFKD', text)
🔄 2. Comparação inteligente

Combina:

Diff estrutural (difflib)
Similaridade (threshold: 0.75)

✂️ 3. Corte de áudio

Cada palavra possui:

{
  "word": "exemplo",
  "start": 1.23,
  "end": 1.56
}

Esses timestamps permitem remoção precisa.

🎚️ 4. Suavização
Buffer: ~15ms
Crossfade: ~10ms

Evita cortes abruptos no áudio final.

✅ Boas Práticas
Não reescreva frases completamente
Apenas remova palavras indesejadas
Use o debug antes de gerar o áudio final
Trabalhe com áudio de boa qualidade

⚠️ Limitações
Alterações profundas no texto podem afetar o alinhamento
Dependência de qualidade da transcrição
Processamento pode ser lento em CPU

💡 Possíveis Melhorias
Interface web (React + API)
Suporte a GPU
Edição sincronizada texto-áudio
Exportação para múltiplos formatos

📊 Casos de Uso
🎥 YouTube
🎙️ Podcasts
📚 Audiobooks
🎓 Cursos online
📄 Licença

Este projeto está sob a licença MIT.

🤝 Contribuição

Pull requests são bem-vindos! Para mudanças maiores, abra uma issue primeiro.

⭐ Se este projeto te ajudou

Deixe uma estrela no repositório!

