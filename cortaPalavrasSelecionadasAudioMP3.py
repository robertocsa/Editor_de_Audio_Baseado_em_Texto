import tkinter as tk
from tkinter import filedialog, messagebox
import whisperx
import difflib
from pydub import AudioSegment
import json
import os
import gc
import datetime
import unicodedata
import string

import traceback
from pydub import silence


class AudioEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Editor de Áudio por Palavras")
        self.root.geometry("590x570")

        self.audio_file = None
        self.words_data = None
        self.removed_indices = None

        # Interface
        tk.Label(root, text="Editor de Áudio por Palavras",
                 font=("Arial", 14, "bold")).pack(pady=10)

        tk.Button(root, text="1. Selecionar áudio", command=self.load_audio,
                  width=70, height=2, bg="#c6d3cf").pack(pady=5)
        tk.Button(root, text="2. Transcrever áudio", command=self.transcribe,
                  width=70, height=2, bg="#f0f33c").pack(pady=5)
        tk.Button(root, text="2a. Carregar transcrição existente, se já tiver feito antes",
                  command=self.load_existing_transcription_manual,
                  width=70, height=2, bg="#f0c338").pack(pady=5)
        tk.Button(root, text="3. Exportar texto", command=self.export_text,
                  width=70, height=2, bg="#d4ddda").pack(pady=5)
        tk.Button(root, text="4. Gerar áudio editado", command=self.process_audio,
                  width=70, height=2, bg="#d4edaa").pack(pady=8)
        tk.Button(root, text="5. Gerar debug (ver palavras a deletar, depois de ter editado o 'narracao_editado.txt' )",
                  command=self.generate_debug_preview,
                  width=70, height=2, bg="#dbbfbf").pack(pady=10)

        self.status = tk.Label(root, text="Status: Aguardando ação...",
                               font=("Arial", 10), wraplength=560, justify="left")
        self.status.pack(pady=15)

        self.try_load_existing_files()

    def try_load_existing_files(self):
        if os.path.exists("words.json") and os.path.exists("narracao_original.txt"):
            self.load_existing_transcription(silent=True)

    def load_audio(self):
        self.audio_file = filedialog.askopenfilename(
            filetypes=[("Arquivos de Áudio", "*.wav *.mp3 *.ogg *.m4a *.flac")]
        )
        if self.audio_file:
            self.status.config(
                text=f"Áudio: {os.path.basename(self.audio_file)}")
            #messagebox.showinfo("Sucesso", "Áudio carregado!")
            self.status.config(text="Sucesso! Áudio carregado!")

    def load_existing_transcription(self, silent=False):
        if not (os.path.exists("words.json") and os.path.exists("narracao_original.txt")):
            if not silent:
                messagebox.showwarning(
                    "Aviso", "Arquivos de transcrição não encontrados.")
            return False
        try:
            with open("words.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            self.words_data = [w for w in data if isinstance(w, dict) and "word" in w
                               and isinstance(w.get("start"), (int, float))
                               and isinstance(w.get("end"), (int, float))]
            if not silent:
                self.status.config(
                    text=f"Transcrição carregada ({len(self.words_data)} palavras)")
            return True
        except Exception as e:
            if not silent:
                messagebox.showerror("Erro", f"Erro ao carregar: {e}")
            return False

    def load_existing_transcription_manual(self):
        self.load_existing_transcription(silent=False)

    def _normalize_for_matching(self, text):
        if not text:
            return ""
        text = unicodedata.normalize('NFKD', text).encode(
            'ASCII', 'ignore').decode('ASCII')
        text = text.lower()
        text = text.translate(str.maketrans('', '', string.punctuation))
        return ' '.join(text.split())
       
     
    def _get_removed_indices(self):
        if not os.path.exists("narracao_editado.txt"):
            return set()

        try:
            with open("narracao_editado.txt", "r", encoding="utf-8") as f:
                edited_text = f.read().strip()

            if not self.words_data:
                raise ValueError("words_data vazio")

            edited_words = self._normalize_for_matching(edited_text).split()

            original_words = [
                self._normalize_for_matching(w.get("word", ""))
                for w in self.words_data
                if w.get("word")
            ]

            matcher = difflib.SequenceMatcher(None, original_words, edited_words)

            removed = set()

            # ---------------------------------
            # 1. DIFF (BASE PRINCIPAL)
            # ---------------------------------
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "delete":
                    removed.update(range(i1, i2))

            # ---------------------------------
            # 2. REPETIÇÃO CONSECUTIVA (leve)
            # mantém último
            # ---------------------------------
            i = 0
            while i < len(original_words):
                j = i + 1
                while j < len(original_words) and original_words[j] == original_words[i]:
                    j += 1

                if j - i > 1:
                    removed.update(range(i, j - 1))

                i = j

            # ---------------------------------
            # 3. GAGUEIRA CLÁSSICA (segura)
            # ex: "fa fa falar"
            # ---------------------------------
            for i in range(len(original_words) - 2):
                if i in removed or (i + 1) in removed:
                    continue

                w1 = original_words[i]
                w2 = original_words[i + 1]
                w3 = original_words[i + 2]

                if (
                    len(w1) <= 3 and
                    w1 == w2 and
                    w3.startswith(w1)
                ):
                    removed.add(i)
                    removed.add(i + 1)

            # ---------------------------------
            # 4. MICRO-PALAVRAS CURTAS (tempo)
            # remove só se MUITO curtas
            # ---------------------------------
            for i, w in enumerate(self.words_data):
                if i in removed:
                    continue

                word = original_words[i]
                duration = w["end"] - w["start"]

                if len(word) <= 2 and duration < 0.08:
                    removed.add(i)

            return removed

        except Exception:
            print(traceback.format_exc())
            return set()
        
    def transcribe(self):
        if not self.audio_file:
            messagebox.showerror(
                "Erro", "Selecione um arquivo de áudio primeiro.")
            return

        if self.load_existing_transcription(silent=True):
            if not messagebox.askyesno("Transcrição Existente", "Já existe transcrição salva.\nDeseja transcrever novamente?"):
                return

        self.status.config(text="Transcrevendo áudio com WhisperX...")
        self.root.update()

        try:
            self.status.config(text="Carregando modelo WhisperX...")
            self.root.update()

            initial_prompt = (
                              "Transcreva fielmente o áudio em português do Brasil, preservando o conteúdo natural da fala. "
                              "Evite repetições desnecessárias e não invente palavras. "
                              "Mantenha apenas repetições reais do áudio."
                              "Exemplos de repetições admissíveis, desde que sem excessos: "
                              " Olha, eu eu, hum, que que, oh, ó..., "
                              "o o , ahn, um um , no no , sabe? Éé... , tipo, né?, tá?, "
                              "Aí, a a , hmmm, pra pra, é é, a a , a a o , da da do..., "
                              " Tá tá! foi foi , ah! Fa fa falar, "
                              "eu eu, que que, a a, o o, na na, do do, da da, né, hum, ah, éé, ahm, hmm."
                             )
            try:
                asr_options = {
                                     "initial_prompt": initial_prompt,
                                     #"temperature": 0.0,
                                     "suppress_blank": False,
                                     "condition_on_previous_text": False,
                                     # No WhisperX, usamos estes para controlar alucinações:
                                     "log_prob_threshold": -1.0, 
                                     "no_speech_threshold": 0.6 
                                    }
                model = whisperx.load_model(
                    "small",
                    "cpu",
                    compute_type="int8",
                    asr_options = asr_options
                    )

                print("✓ Modelo carregado com initial_prompt")

            except Exception as e:
                print("Erro real:", e)
                print("⚠ Carregando modelo sem initial_prompt")
                model = whisperx.load_model(
                    "small", "cpu", compute_type="int8")

            result = model.transcribe(
                self.audio_file, language="pt", batch_size=8)

            self.status.config(text="Alinhando palavras...")
            self.root.update()

            model_a, metadata = whisperx.load_align_model(
                language_code="pt", device="cpu")
            aligned = whisperx.align(
                result["segments"], model_a, metadata, self.audio_file, device="cpu")

            self.words_data = []
            for segment in aligned.get("segments", []):
                self.words_data.extend(segment.get("words", []))

            self.words_data = [w for w in self.words_data if isinstance(w, dict) and "word" in w
                               and isinstance(w.get("start"), (int, float))
                               and isinstance(w.get("end"), (int, float))]

            # Salvar arquivos
            with open("words.json", "w", encoding="utf-8") as f:
                json.dump(self.words_data, f, ensure_ascii=False, indent=2)
            with open("narracao_original.txt", "w", encoding="utf-8") as f:
                f.write(" ".join(w.get("word", "") for w in self.words_data))
            with open("audio_original_path.txt", "w", encoding="utf-8") as f:
                f.write(self.audio_file)

            self.status.config(
                text=f"Transcrição concluída! ({len(self.words_data)} palavras)")
            messagebox.showinfo(
                "Sucesso", f"Transcrição finalizada com {len(self.words_data)} palavras.")

        except Exception as e:
            messagebox.showerror("Erro na transcrição",
                                 f"Ocorreu um erro:\n{str(e)}")
            print(f"Erro detalhado: {e}")
        finally:
            try:
                del model_a
                gc.collect()
            except:
                pass

    def export_text(self):
        if not self.words_data:
            messagebox.showerror("Erro", "Faça a transcrição primeiro.")
            return
        try:
            text = " ".join(w.get("word", "") for w in self.words_data)
            with open("narracao_original.txt", "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Texto Exportado",
                                "Arquivo 'narracao_original.txt' criado!\n\n"
                                "Edite o texto removendo as repetições/gagueiras\n"
                                "e salve como: narracao_editado.txt")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def generate_debug_preview(self):
        if not self.words_data:
            messagebox.showerror(
                "Erro", "Faça a transcrição primeiro (botão 2).")
            return
        if not os.path.exists("narracao_editado.txt"):
            messagebox.showerror(
                "Erro", "Arquivo 'narracao_editado.txt' não encontrado.")
            return

        try:
            removed_indices = self._get_removed_indices()
            self.removed_indices = removed_indices
            self._create_debug_file(removed_indices)
            
        except Exception as e:
            #messagebox.showerror("Erro", f"Erro ao gerar debug:\n{str(e)}")
            
            error_msg = traceback.format_exc()

            messagebox.showerror(
                "Erro",
                f"Erro ao gerar debug:\n\n{error_msg}" )

    def _create_debug_file(self, removed_indices):
        debug_lines = []
        debug_lines.append("=== DEBUG - PALAVRAS A DELETAR ===\n")
        debug_lines.append(
            f"Data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        debug_lines.append(f"Total de palavras: {len(self.words_data)}\n")
        debug_lines.append(
            f"Palavras marcadas para remoção: {len(removed_indices)}\n\n")

        debug_lines.append(
            "ÍNDICE  |  PALAVRA                          |  INÍCIO (s)  |  FIM (s)  |  DURAÇÃO\n")
        debug_lines.append("-" * 85 + "\n")

        total_duration = 0
        removed_list = []

        for i in sorted(removed_indices):
            if i >= len(self.words_data):
                continue
            word = self.words_data[i]
            word_text = word.get("word", "").strip()
            start = word.get("start", 0)
            end = word.get("end", 0)
            duration = int((end - start) * 1000)
            total_duration += duration
            removed_list.append(word_text)

            debug_lines.append(
                f"{i:6d}  |  {word_text:<32} |  {start:8.3f}   |  {end:8.3f}  |  {duration:5d} ms\n"
            )

        debug_lines.append("-" * 85 + "\n")
        debug_lines.append(
            f"\nTempo total removido: {total_duration} ms ({total_duration/1000:.2f} segundos)\n")

        with open("debug_removidas.txt", "w", encoding="utf-8") as f:
            f.writelines(debug_lines)

        self.status.config(text=f"✅ {len(removed_indices)} palavras marcadas")
        messagebox.showinfo("Debug", f"{len(removed_indices)} palavras marcadas para remoção.\n"
                            f"Tempo aproximado: {total_duration/1000:.1f} s")



    def process_audio(self):
        if not self.words_data or not os.path.exists("narracao_editado.txt") or not self.audio_file:
            messagebox.showerror(
                "Erro", "Verifique transcrição, arquivo editado e áudio.")
            return

        try:
            self.status.config(text="Gerando áudio final ...")

            removed_indices = self._get_removed_indices() or set()
            self.removed_indices = removed_indices

            audio = AudioSegment.from_file(self.audio_file)

            # 🔧 PARÂMETROS AJUSTADOS
            buffer_ms = 80
            crossfade_ms = 25
            min_segment_ms = 80

            # ---------------------------------
            # 1. AGRUPAR BLOCOS (fala contínua)
            # ---------------------------------
            blocks = []
            current_block = []

            for i, word in enumerate(self.words_data):
                if i in removed_indices:
                    if current_block:
                        blocks.append(current_block)
                        current_block = []
                    continue

                current_block.append(word)

            if current_block:
                blocks.append(current_block)

            # ---------------------------------
            # 2. GERAR SEGMENTOS AJUSTADOS
            # ---------------------------------
            segments = []

            for block in blocks:
                raw_start = int(block[0]["start"] * 1000)
                raw_end = int(block[-1]["end"] * 1000)

                start_ms = self._find_nearest_silence(audio, raw_start)
                end_ms = self._find_nearest_silence(audio, raw_end)

                start_ms = max(0, start_ms - buffer_ms)
                end_ms = min(len(audio), end_ms + buffer_ms)

                if end_ms <= start_ms:
                    continue

                segment = audio[start_ms:end_ms]

                # 🚫 evita micro segmentos problemáticos
                if len(segment) >= min_segment_ms:
                    segments.append(segment)

            if not segments:
                raise ValueError("Nenhum segmento válido gerado")

            # ---------------------------------
            # 3. JUNÇÃO SEGURA COM CROSSFade
            # ---------------------------------
            final_audio = segments[0]

            for seg in segments[1:]:

                # 🔐 proteção total contra erro de crossfade
                max_cf = min(len(final_audio), len(seg)) - 1

                if max_cf <= 0:
                    final_audio += seg  # fallback seguro
                else:
                    cf = min(crossfade_ms, max_cf)
                    final_audio = final_audio.append(seg, crossfade=cf)

            # ---------------------------------
            # 4. REMOÇÃO DE RESPIRAÇÕES (segura)
            # ---------------------------------
            try:
                final_audio = self._remove_breaths(final_audio)
            except Exception:
                print("Falha ao remover respirações, mantendo áudio original")

            # ---------------------------------
            # 5. EXPORTAR
            # ---------------------------------
            final_audio.export("audio_final.wav", format="wav")

            self.status.config(text="✅ Áudio final gerado com sucesso!")
            messagebox.showinfo("Sucesso", "Áudio salvo como audio_final.wav")

        except Exception as e:
            messagebox.showerror(
                "Erro", f"Erro ao gerar áudio:\n\n{traceback.format_exc()}"
            )

    def _find_nearest_silence(self, audio, target_ms, search_window=150, silence_thresh=-40):
        """
        Ajusta o ponto de corte para o silêncio mais próximo
        """
        start = max(0, target_ms - search_window)
        end = min(len(audio), target_ms + search_window)

        segment = audio[start:end]

        silence_ranges = silence.detect_silence(
            segment,
            min_silence_len=20,
            silence_thresh=silence_thresh
        )

        if not silence_ranges:
            return target_ms

        best = min(
            silence_ranges,
            key=lambda r: abs((start + r[0]) - target_ms)
        )

        return start + best[0]
    
    def _remove_breaths(self, audio):
        """
        Remove respirações curtas entre falas sem destruir o áudio
        """
        from pydub import silence

        silence_ranges = silence.detect_silence(
            audio,
            min_silence_len=60,     # respiração costuma ser curta
            silence_thresh=audio.dBFS - 18  # adaptativo
        )

        if not silence_ranges:
            return audio

        segments = []
        last_end = 0

        for start, end in silence_ranges:
            duration = end - start

            # 🔴 REGRA PRINCIPAL:
            # remove apenas silêncios CURTOS (respirações)
            if duration < 300:
                segments.append(audio[last_end:start])
                last_end = end

        segments.append(audio[last_end:])

        if not segments:
            return audio

        result = segments[0]
        for seg in segments[1:]:
            result = result.append(seg, crossfade=10)

        return result

if __name__ == "__main__":
    root = tk.Tk()
    app = AudioEditorApp(root)
    root.mainloop()
