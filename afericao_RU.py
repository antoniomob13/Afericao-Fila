import tkinter as tk
from tkinter import ttk, messagebox
import time
from datetime import datetime
import csv
import os

class MonitorFilaServidorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Fila e Servidor - Avaliação de Desempenho (Lenovo LOQ)")
        self.root.geometry("980x710")
        self.root.resizable(False, False)

        # Diretório onde o script Python está localizado
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_filepath = os.path.join(self.base_dir, "log_fila_servidor.csv")
        self.txt_filepath = os.path.join(self.base_dir, "log_fila_servidor.txt")

        # Registro de data e horário em que o programa foi aberto
        now = datetime.now()
        self.program_start_date = now.strftime("%Y-%m-%d")
        self.program_start_time = now.strftime("%H:%M:%S")
        self.session_start_str = "Não iniciada"

        # Variáveis de controle do Cronômetro Geral
        self.running = False
        self.paused = False
        self.elapsed_time = 0.0
        self.last_tick = 0.0

        # Variáveis de Estado do Servidor ("Ocioso", "Ocupado", "Desligado")
        self.server_state = "Desligado"
        self.total_busy_time = 0.0
        self.total_idle_time = 0.0
        self.current_state_duration = 0.0
        self.service_count = 0

        # Variáveis da Fila e Clientes
        self.queue = []
        self.next_person_id = 1
        self.current_customer = None
        self.abandon_count = 0
        self.total_arrivals = 0

        self._init_csv()
        self._build_ui()
        self._bind_keyboard_shortcuts()
        self._update_clock()

    def _bind_keyboard_shortcuts(self):
        """
        Configura os atalhos de teclado adaptados para o layout do Lenovo LOQ Essential:
        - Iniciar Atendimento: Seta Esquerda (Left) ou Home (Fn + Left)
        - Término de Atendimento: Seta Direita (Right) ou End (Fn + Right)
        - Adicionar Pessoa na Fila: '+' do Numpad (KP_Add), '+' (plus) ou '=' (tecla +/= sem Shift)
        """
        # Iniciar Atendimento: ← (Left) ou Home
        self.root.bind("<Left>", self._shortcut_start_service)
        self.root.bind("<Home>", self._shortcut_start_service)
        self.root.bind("<KP_Home>", self._shortcut_start_service)

        # Término de Atendimento: → (Right) ou End
        self.root.bind("<Right>", self._shortcut_end_service)
        self.root.bind("<End>", self._shortcut_end_service)
        self.root.bind("<KP_End>", self._shortcut_end_service)

        # Adicionar Pessoa na Fila: + (Numpad ou fileira superior, com ou sem Shift)
        self.root.bind("<KP_Add>", self._shortcut_add_queue)
        self.root.bind("<plus>", self._shortcut_add_queue)
        self.root.bind("<equal>", self._shortcut_add_queue)

    def _shortcut_start_service(self, event=None):
        if self.running and not self.paused and self.server_state == "Ocioso" and len(self.queue) > 0:
            self.start_service()

    def _shortcut_end_service(self, event=None):
        if self.running and not self.paused and self.server_state == "Ocupado":
            self.end_service()

    def _shortcut_add_queue(self, event=None):
        if self.running and not self.paused:
            self.add_person_to_queue()

    def _init_csv(self):
        """Cria o arquivo CSV com cabeçalho atualizado para incluir dados da fila e dos clientes."""
        file_exists = os.path.isfile(self.csv_filepath)
        with open(self.csv_filepath, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            if not file_exists:
                writer.writerow([
                    "Data_Evento",
                    "Horario_Evento",
                    "Inicio_Sessao",
                    "Tempo_Cronometro_s",
                    "Tempo_Cronometro_Fmt",
                    "Estado_Servidor",
                    "Tamanho_Fila",
                    "ID_Pessoa",
                    "Evento_Acao",
                    "Tempo_Espera_Fila_s",
                    "Duracao_Estado_ou_Servico_s",
                    "Tempo_Ocioso_Acumulado_s",
                    "Tempo_Ocupado_Acumulado_s",
                    "Total_Chegadas",
                    "Atendimentos_Concluidos",
                    "Total_Desistencias",
                    "Detalhes"
                ])

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # 0. Barra Superior: Informações da Execução e Atalhos
        info_frame = ttk.LabelFrame(self.root, text=" Dados da Execução e Atalhos do Teclado (Lenovo LOQ) ", padding=8)
        info_frame.pack(fill="x", padx=15, pady=(10, 5))

        self.lbl_exec_info = ttk.Label(
            info_frame,
            text=f"📅 Programa aberto em: {self.program_start_date} às {self.program_start_time}   |   "
                 f"🕒 Início da Aferição: {self.session_start_str}",
            font=("Helvetica", 9, "bold")
        )
        self.lbl_exec_info.pack(anchor="w")

        self.lbl_shortcuts_info = ttk.Label(
            info_frame,
            text="⌨️ Atalhos Ativos:   [ + ] Adicionar na Fila   |   [ ← / Home ] Iniciar Atendimento   |   [ → / End ] Término de Atendimento",
            font=("Helvetica", 9, "bold"),
            foreground="#1565c0"
        )
        self.lbl_shortcuts_info.pack(anchor="w", pady=(3, 2))

        self.lbl_path_info = ttk.Label(
            info_frame,
            text=f"📁 Arquivo CSV salvo em: {self.csv_filepath}",
            font=("Helvetica", 8),
            foreground="#555555"
        )
        self.lbl_path_info.pack(anchor="w")

        # Container Principal dividido em Coluna Esquerda (Servidor) e Coluna Direita (Fila)
        main_pane = ttk.Frame(self.root)
        main_pane.pack(fill="x", padx=15, pady=5)

        left_col = ttk.Frame(main_pane)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right_col = ttk.Frame(main_pane, width=390)
        right_col.pack(side="right", fill="both", expand=False)
        right_col.pack_propagate(False)

        # --- COLUNA ESQUERDA: CRONÔMETRO E SERVIDOR ---
        top_frame = ttk.LabelFrame(left_col, text=" Status do Servidor e Cronômetro ", padding=10)
        top_frame.pack(fill="x", pady=(0, 5))

        self.lbl_timer = ttk.Label(top_frame, text="00:00:00.0", font=("Consolas", 30, "bold"))
        self.lbl_timer.pack()

        self.lbl_state = tk.Label(
            top_frame, text="SERVIDOR: DESLIGADO", font=("Helvetica", 11, "bold"),
            bg="#d9d9d9", fg="#333333", padx=10, pady=4, relief="ridge"
        )
        self.lbl_state.pack(pady=5)

        self.lbl_current_cust = ttk.Label(
            top_frame, text="Em atendimento: Nenhum", font=("Helvetica", 10, "bold"), foreground="#0d47a1"
        )
        self.lbl_current_cust.pack(pady=2)

        self.lbl_metrics = ttk.Label(
            top_frame,
            text="Ocioso: 0.0s | Ocupado: 0.0s | Utilização: 0.0%\n"
                 "Chegadas: 0 | Atendidos: 0 | Desistências: 0",
            font=("Helvetica", 9), justify="center"
        )
        self.lbl_metrics.pack(pady=3)

        # Controles do Cronômetro
        ctrl_frame = ttk.LabelFrame(left_col, text=" Controle do Cronômetro ", padding=8)
        ctrl_frame.pack(fill="x", pady=5)

        self.btn_start = ttk.Button(ctrl_frame, text="▶ Ligar / Retomar", command=self.start_timer, takefocus=False)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=4)

        self.btn_pause = ttk.Button(ctrl_frame, text="⏸ Pausar", command=self.pause_timer, state="disabled", takefocus=False)
        self.btn_pause.pack(side="left", expand=True, fill="x", padx=4)

        self.btn_stop = ttk.Button(ctrl_frame, text="⏹ Parar e Finalizar", command=self.stop_timer, state="disabled", takefocus=False)
        self.btn_stop.pack(side="left", expand=True, fill="x", padx=4)

        # Controles de Atendimento do Servidor
        srv_frame = ttk.LabelFrame(left_col, text=" Operação do Servidor ", padding=8)
        srv_frame.pack(fill="x", pady=5)

        self.btn_begin_srv = ttk.Button(
            srv_frame, text="🟢 Iniciar Atendimento [ ← / Home ]",
            command=self.start_service, state="disabled", takefocus=False
        )
        self.btn_begin_srv.pack(side="left", expand=True, fill="x", padx=4, ipady=5)

        self.btn_end_srv = ttk.Button(
            srv_frame, text="🔴 Término de Atendimento [ → / End ]",
            command=self.end_service, state="disabled", takefocus=False
        )
        self.btn_end_srv.pack(side="left", expand=True, fill="x", padx=4, ipady=5)

        # --- COLUNA DIREITA: MONITORAMENTO DA FILA ---
        queue_frame = ttk.LabelFrame(right_col, text=" Monitoramento da Fila de Espera ", padding=8)
        queue_frame.pack(fill="both", expand=True)

        self.btn_add_queue = ttk.Button(
            queue_frame, text="➕ Adicionar Pessoa na Fila [ Tecla + ]",
            command=self.add_person_to_queue, state="disabled", takefocus=False
        )
        self.btn_add_queue.pack(fill="x", pady=(0, 6), ipady=4)

        self.lbl_queue_count = ttk.Label(
            queue_frame, text="Pessoas aguardando na fila: 0", font=("Helvetica", 10, "bold")
        )
        self.lbl_queue_count.pack(anchor="w", pady=(0, 4))

        # Canvas com Scrollbar para listar pessoas na fila com botão individual de desistência
        list_container = ttk.Frame(queue_frame, relief="sunken", borderwidth=1)
        list_container.pack(fill="both", expand=True)

        self.q_canvas = tk.Canvas(list_container, bg="#f7f7f7", highlightthickness=0)
        q_scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.q_canvas.yview)
        self.q_scrollable_frame = tk.Frame(self.q_canvas, bg="#f7f7f7")

        self.q_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.q_canvas.configure(scrollregion=self.q_canvas.bbox("all"))
        )

        self.canvas_window = self.q_canvas.create_window((0, 0), window=self.q_scrollable_frame, anchor="nw")
        self.q_canvas.bind(
            "<Configure>",
            lambda e: self.q_canvas.itemconfig(self.canvas_window, width=e.width)
        )
        self.q_canvas.configure(yscrollcommand=q_scrollbar.set)

        self.q_canvas.pack(side="left", fill="both", expand=True)
        q_scrollbar.pack(side="right", fill="y")

        # --- PARTE INFERIOR: LOG DE EVENTOS ---
        log_frame = ttk.LabelFrame(self.root, text=" Registro de Eventos (Log em Tempo Real) ", padding=8)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(5, 10))

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self.txt_log = tk.Text(
            log_frame, height=8, state="disabled", font=("Consolas", 9),
            yscrollcommand=scrollbar.set, bg="#1e1e1e", fg="#d4d4d4", takefocus=False
        )
        self.txt_log.pack(fill="both", expand=True)
        scrollbar.config(command=self.txt_log.yview)

    def _format_time(self, seconds):
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        return f"{int(hours):02d}:{int(mins):02d}:{secs:04.1f}"

    def _refresh_queue_ui(self):
        """Reconstrói a lista visual de pessoas na fila e atualiza o estado dos botões."""
        self.lbl_queue_count.config(text=f"Pessoas aguardando na fila: {len(self.queue)}")

        for widget in self.q_scrollable_frame.winfo_children():
            widget.destroy()

        if not self.queue:
            lbl_empty = tk.Label(
                self.q_scrollable_frame, text="Fila vazia no momento.",
                bg="#f7f7f7", fg="#777777", font=("Helvetica", 9, "italic"), pady=15
            )
            lbl_empty.pack(fill="x")
        else:
            btn_state = "normal" if (self.running and not self.paused) else "disabled"
            for idx, person in enumerate(self.queue, start=1):
                row = tk.Frame(self.q_scrollable_frame, bg="#ffffff", bd=1, relief="solid")
                row.pack(fill="x", padx=4, pady=3)

                info_txt = (
                    f"{idx}º | Pessoa #{person['id']:02d} "
                    f"(Chegada: {self._format_time(person['arrival_cron'])} | "
                    f"Espera: {person['wait_time']:.1f}s)"
                )
                lbl = tk.Label(
                    row, text=info_txt, bg="#ffffff", fg="#222222",
                    font=("Consolas", 8, "bold"), anchor="w", padx=6, pady=6
                )
                lbl.pack(side="left", fill="x", expand=True)
                person["lbl_widget"] = lbl

                btn_remove = tk.Button(
                    row, text="❌ Desistiu", bg="#ffebee", fg="#c62828",
                    activebackground="#ffcdd2", font=("Helvetica", 8, "bold"),
                    state=btn_state, takefocus=False,
                    command=lambda pid=person['id']: self.remove_person_from_queue(pid)
                )
                btn_remove.pack(side="right", padx=5, pady=3)

        self._update_controls_state()

    def _update_controls_state(self):
        """Gerencia quais botões podem ser clicados de acordo com o estado do servidor e da fila."""
        if not self.running:
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="disabled")
            self.btn_add_queue.config(state="disabled")
            self.btn_begin_srv.config(state="disabled")
            self.btn_end_srv.config(state="disabled")
        elif self.paused:
            self.btn_start.config(state="normal")
            self.btn_pause.config(state="disabled")
            self.btn_stop.config(state="normal")
            self.btn_add_queue.config(state="disabled")
            self.btn_begin_srv.config(state="disabled")
            self.btn_end_srv.config(state="disabled")
        else:
            self.btn_start.config(state="disabled")
            self.btn_pause.config(state="normal")
            self.btn_stop.config(state="normal")
            self.btn_add_queue.config(state="normal")

            if self.server_state == "Ocioso":
                if len(self.queue) > 0:
                    self.btn_begin_srv.config(state="normal")
                else:
                    self.btn_begin_srv.config(state="disabled")
                self.btn_end_srv.config(state="disabled")
            elif self.server_state == "Ocupado":
                self.btn_begin_srv.config(state="disabled")
                self.btn_end_srv.config(state="normal")

    def _write_log(self, event_desc, person_id="", wait_time=0.0, state_duration=0.0, details=""):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S.%f")[:-3]
        cron_fmt = self._format_time(self.elapsed_time)
        q_len = len(self.queue)

        person_str = f" [Pessoa #{person_id:02d}]" if isinstance(person_id, int) else ""
        detail_str = f" | {details}" if details else ""
        log_entry = (
            f"[{date_str} {time_str}] [Cron: {cron_fmt}] "
            f"[Srv: {self.server_state.upper()} | Fila: {q_len}]{person_str} -> {event_desc}{detail_str}\n"
        )

        # 1. Atualiza o Log visual na interface
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", log_entry)
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

        # 2. Grava no arquivo TXT
        with open(self.txt_filepath, "a", encoding="utf-8") as f_txt:
            f_txt.write(log_entry)

        # 3. Grava no arquivo CSV na mesma pasta do programa
        with open(self.csv_filepath, mode="a", newline="", encoding="utf-8-sig") as f_csv:
            writer = csv.writer(f_csv, delimiter=";")
            writer.writerow([
                date_str,
                time_str,
                self.session_start_str,
                f"{self.elapsed_time:.3f}".replace(".", ","),
                cron_fmt,
                self.server_state,
                q_len,
                f"Pessoa_{person_id:02d}" if isinstance(person_id, int) else "-",
                event_desc,
                f"{wait_time:.3f}".replace(".", ","),
                f"{state_duration:.3f}".replace(".", ","),
                f"{self.total_idle_time:.3f}".replace(".", ","),
                f"{self.total_busy_time:.3f}".replace(".", ","),
                self.total_arrivals,
                self.service_count,
                self.abandon_count,
                details
            ])

    def _update_state_badge(self):
        if not self.running:
            self.lbl_state.config(text="SERVIDOR: DESLIGADO", bg="#d9d9d9", fg="#333333")
            self.lbl_current_cust.config(text="Em atendimento: Nenhum")
        elif self.paused:
            self.lbl_state.config(text=f"PAUSADO ({self.server_state.upper()})", bg="#fce8b2", fg="#8a5a00")
        elif self.server_state == "Ocioso":
            self.lbl_state.config(text="SERVIDOR: OCIOSO", bg="#c8e6c9", fg="#1b5e20")
            self.lbl_current_cust.config(text="Em atendimento: Nenhum")
        elif self.server_state == "Ocupado":
            self.lbl_state.config(text="SERVIDOR: OCUPADO", bg="#ffcdd2", fg="#b71c1c")
            if self.current_customer:
                self.lbl_current_cust.config(text=f"Em atendimento: Pessoa #{self.current_customer['id']:02d}")

    def _update_clock(self):
        if self.running and not self.paused:
            now = time.perf_counter()
            dt = now - self.last_tick
            self.last_tick = now
            self.elapsed_time += dt
            self.current_state_duration += dt

            if self.server_state == "Ocupado":
                self.total_busy_time += dt
            elif self.server_state == "Ocioso":
                self.total_idle_time += dt

            for idx, person in enumerate(self.queue, start=1):
                person["wait_time"] += dt
                if "lbl_widget" in person and person["lbl_widget"].winfo_exists():
                    person["lbl_widget"].config(
                        text=f"{idx}º | Pessoa #{person['id']:02d} "
                             f"(Chegada: {self._format_time(person['arrival_cron'])} | "
                             f"Espera: {person['wait_time']:.1f}s)"
                    )

            self.lbl_timer.config(text=self._format_time(self.elapsed_time))

            utilization = (self.total_busy_time / self.elapsed_time * 100) if self.elapsed_time > 0 else 0.0
            self.lbl_metrics.config(
                text=f"Ocioso: {self.total_idle_time:.1f}s | Ocupado: {self.total_busy_time:.1f}s | Utilização: {utilization:.1f}%\n"
                     f"Chegadas: {self.total_arrivals} | Atendidos: {self.service_count} | Desistências: {self.abandon_count}"
            )

        self.root.after(50, self._update_clock)

    # --- AÇÕES DA FILA ---
    def add_person_to_queue(self):
        if self.running and not self.paused:
            pid = self.next_person_id
            self.next_person_id += 1
            self.total_arrivals += 1

            person = {
                "id": pid,
                "arrival_cron": self.elapsed_time,
                "arrival_real": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "wait_time": 0.0
            }
            self.queue.append(person)
            self._refresh_queue_ui()

            self._write_log(
                event_desc="ENTRADA_NA_FILA",
                person_id=pid,
                wait_time=0.0,
                state_duration=0.0,
                details=f"Pessoa #{pid:02d} entrou na fila (Posicao: {len(self.queue)})"
            )

    def remove_person_from_queue(self, person_id):
        """Remove uma pessoa específica da fila por desistência."""
        if self.running and not self.paused:
            target = None
            pos = 0
            for idx, p in enumerate(self.queue, start=1):
                if p["id"] == person_id:
                    target = p
                    pos = idx
                    break

            if target:
                self.queue.remove(target)
                self.abandon_count += 1
                wait_t = target["wait_time"]
                self._refresh_queue_ui()

                self._write_log(
                    event_desc="DESISTENCIA_FILA",
                    person_id=person_id,
                    wait_time=wait_t,
                    state_duration=0.0,
                    details=f"Pessoa #{person_id:02d} desistiu na {pos}a posicao apos esperar {wait_t:.2f}s"
                )

    # --- AÇÕES DO SERVIDOR E CRONÔMETRO ---
    def start_timer(self):
        if not self.running:
            self.running = True
            self.paused = False
            self.elapsed_time = 0.0
            self.total_busy_time = 0.0
            self.total_idle_time = 0.0
            self.current_state_duration = 0.0
            self.service_count = 0
            self.abandon_count = 0
            self.total_arrivals = 0
            self.next_person_id = 1
            self.queue.clear()
            self.current_customer = None
            self.last_tick = time.perf_counter()
            self.server_state = "Ocioso"

            now = datetime.now()
            self.session_start_str = now.strftime("%Y-%m-%d %H:%M:%S")
            self.lbl_exec_info.config(
                text=f"📅 Programa aberto em: {self.program_start_date} às {self.program_start_time}   |   "
                     f"🕒 Início da Aferição: {self.session_start_str}"
            )

            with open(self.txt_filepath, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 95 + "\n")
                f.write(f"SESSÃO DE AFERIÇÃO INICIADA EM: {self.session_start_str}\n")
                f.write("=" * 95 + "\n")

            self._write_log("CRONOMETRO_LIGADO", details="Sistema iniciado (Servidor Ocioso, Fila Vazia)")
            self._refresh_queue_ui()

        elif self.paused:
            self.paused = False
            self.last_tick = time.perf_counter()
            self._write_log("CRONOMETRO_RETOMADO", details=f"Retornando ao estado {self.server_state}")
            self._refresh_queue_ui()

        self._update_state_badge()

    def pause_timer(self):
        if self.running and not self.paused:
            self.paused = True
            self._write_log("CRONOMETRO_PAUSADO", details="Contabilizacao de tempo suspensa")
            self._refresh_queue_ui()
            self._update_state_badge()

    def start_service(self):
        if self.running and not self.paused and self.server_state == "Ocioso":
            if not self.queue:
                return

            customer = self.queue.pop(0)
            self.current_customer = customer
            wait_t = customer["wait_time"]

            duracao_ocioso = self.current_state_duration
            self.server_state = "Ocupado"
            self.current_state_duration = 0.0

            self._refresh_queue_ui()
            self._update_state_badge()

            self._write_log(
                event_desc="INICIO_DE_ATENDIMENTO",
                person_id=customer["id"],
                wait_time=wait_t,
                state_duration=duracao_ocioso,
                details=(
                    f"Pessoa #{customer['id']:02d} saiu da fila para atendimento "
                    f"(Esperou {wait_t:.2f}s na fila | Servidor ficou Ocioso por {duracao_ocioso:.2f}s)"
                )
            )

    def end_service(self):
        if self.running and not self.paused and self.server_state == "Ocupado":
            duracao_atendimento = self.current_state_duration
            cust_id = self.current_customer["id"] if self.current_customer else "-"
            cust_wait = self.current_customer["wait_time"] if self.current_customer else 0.0

            self.server_state = "Ocioso"
            self.service_count += 1
            self.current_state_duration = 0.0
            self.current_customer = None

            self._refresh_queue_ui()
            self._update_state_badge()

            self._write_log(
                event_desc="TERMINO_DE_ATENDIMENTO",
                person_id=cust_id,
                wait_time=cust_wait,
                state_duration=duracao_atendimento,
                details=f"Pessoa #{cust_id:02d} concluiu atendimento (Duracao do servico: {duracao_atendimento:.2f}s)"
            )

    def stop_timer(self):
        if self.running:
            if not self.paused:
                now = time.perf_counter()
                dt = now - self.last_tick
                self.elapsed_time += dt
                self.current_state_duration += dt
                if self.server_state == "Ocupado":
                    self.total_busy_time += dt
                elif self.server_state == "Ocioso":
                    self.total_idle_time += dt
                for person in self.queue:
                    person["wait_time"] += dt

            ultimo_estado_duracao = self.current_state_duration
            if self.server_state == "Ocupado" and self.current_customer:
                self.service_count += 1
                self._write_log(
                    event_desc="ATENDIMENTO_INTERROMPIDO_NO_FIM",
                    person_id=self.current_customer["id"],
                    wait_time=self.current_customer["wait_time"],
                    state_duration=ultimo_estado_duracao,
                    details=f"Atendimento da Pessoa #{self.current_customer['id']:02d} encerrado pelo fim da afericao ({ultimo_estado_duracao:.2f}s)"
                )
                self.current_customer = None

            rem_queue = len(self.queue)
            self.server_state = "Desligado"
            utilization = (self.total_busy_time / self.elapsed_time * 100) if self.elapsed_time > 0 else 0.0
            avg_service = (self.total_busy_time / self.service_count) if self.service_count > 0 else 0.0

            resumo = (
                f"T={self.elapsed_time:.2f}s | B={self.total_busy_time:.2f}s | Ocioso={self.total_idle_time:.2f}s | "
                f"Chegadas={self.total_arrivals} | Atendidos={self.service_count} | "
                f"Desistencias={self.abandon_count} | Restantes_na_Fila={rem_queue} | "
                f"U={utilization:.2f}% | S={avg_service:.2f}s"
            )
            self._write_log("CRONOMETRO_PARADO_FIM", state_duration=self.elapsed_time, details=resumo)

            self.running = False
            self.paused = False
            self.current_state_duration = 0.0
            self.queue.clear()
            self._refresh_queue_ui()
            self._update_state_badge()

            messagebox.showinfo(
                "Resumo da Aferição",
                f"Dados salvos com sucesso em:\n{self.csv_filepath}\n\n"
                f"• Início da Aferição: {self.session_start_str}\n"
                f"• Tempo Total de Observação (T): {self.elapsed_time:.2f} s\n"
                f"• Tempo Total Ocupado (B): {self.total_busy_time:.2f} s\n"
                f"• Tempo Total Ocioso: {self.total_idle_time:.2f} s\n"
                f"• Total de Chegadas na Fila: {self.total_arrivals}\n"
                f"• Total de Atendimentos (C): {self.service_count}\n"
                f"• Total de Desistências: {self.abandon_count}\n"
                f"• Pessoas ainda na fila ao encerrar: {rem_queue}\n"
                f"• Taxa de Utilização do Servidor (U): {utilization:.2f}%\n"
                f"• Tempo Médio de Serviço (S): {avg_service:.2f} s"
            )

if __name__ == "__main__":
    root = tk.Tk()
    app = MonitorFilaServidorApp(root)
    root.mainloop()