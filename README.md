# ⏱️ Monitor de Filas e Servidor (Aferição RU)

Aplicação desktop desenvolvida em Python com **Tkinter** para coleta empírica de dados operacionais em sistemas de atendimento monousuário/servidor único (como guichês, caixas e bandejões de Restaurante Universitário).

O software permite registrar chegadas, tempos de espera, desistências e ciclos de atendimento em tempo real, gerando logs estruturados em **CSV** e **TXT** para posterior modelagem estatística e Teoria das Filas.

---

## 🚀 Funcionalidades

- **Cronometragem de Alta Precisão:** Utiliza `time.perf_counter()` para medição contínua e imune a desvios de relógio de sistema.
- **Rastreamento Individual de Clientes:** Acompanha cada pessoa na fila pelo identificador (`Pessoa #ID`), tempo individual de espera e suporte a registro de desistências pontuais.
- **Máquina de Estados do Servidor:** Alterna explicitamente entre os estados `Desligado`, `Ocioso` e `Ocupado`.
- **Métricas Operacionais em Tempo Real:**
  - Tempo total de observação ($T$)
  - Tempo acumulado ocupado ($B$) e ocioso
  - Taxa de utilização instantânea do servidor ($U = B / T$)
  - Total de chegadas, atendimentos concluídos ($C$) e desistências
- **Exportação Imediata:** Registro de cada evento com separador `;` em arquivo CSV formatado para análise no Excel, R ou Pandas.
- **Atalhos de Teclado:** Otimizado para operação rápida em campo durante aferições presenciais.

---

## ⌨️ Atalhos de Teclado

| Ação | Teclas de Atalho |
| :--- | :--- |
| **Adicionar pessoa à fila** | `+` (Teclado numérico ou superior) ou `=` |
| **Iniciar atendimento** | `Seta Esquerda (←)` ou `Home` |
| **Finalizar atendimento** | `Seta Direita (→)` ou `End` |

---

## 📊 Estrutura dos Dados Gerados (`.csv`)

O arquivo `log_fila_servidor.csv` registra os eventos com as seguintes colunas:

- `Data_Evento` e `Horario_Evento`: Timestamp de ocorrência.
- `Tempo_Cronometro_s` e `Tempo_Cronometro_Fmt`: Tempo decorrido de observação.
- `Estado_Servidor`: Estado no momento do registro (`Ocioso`, `Ocupado`).
- `Tamanho_Fila`: Número de pessoas aguardando após a ação.
- `ID_Pessoa`: Identificador do cliente relacionado ao evento.
- `Evento_Acao`: Descrição do gatilho (`ENTRADA_NA_FILA`, `INICIO_DE_ATENDIMENTO`, `TERMINO_DE_ATENDIMENTO`, `DESISTENCIA_FILA`, etc.).
- `Tempo_Espera_Fila_s`: Tempo que o cliente passou aguardando.
- `Duracao_Estado_ou_Servico_s`: Duração da última transição de estado.
- `Tempo_Ocioso_Acumulado_s` e `Tempo_Ocupado_Acumulado_s`: Métricas agregadas acumuladas.
- `Total_Chegadas`, `Atendimentos_Concluidos` e `Total_Desistencias`.

---

## 🛠️ Como Executar

### Pré-requisitos
- Python 3.8+ instalado (o Tkinter costuma vir embutido na instalação padrão do Python no Windows e macOS).
- Em distribuições Linux baseadas em Debian/Ubuntu, se necessário:
  ```bash
  sudo apt-get install python3-tk
