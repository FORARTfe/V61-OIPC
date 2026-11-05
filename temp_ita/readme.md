# PTZOptics 12x 3G-SDI/NDI Gen 2: guida alla raccolta hardware per OpenIPC

Versione 1.0 - 5 novembre 2026

## 1. Obiettivo e ordine di lavoro

Questa guida serve a documentare la telecamera reale mentre utilizza ancora il firmware originale: avvio, memorie, sensore, controllo PTZ, uscite video e configurazione. Non installa OpenIPC e non contiene comandi per programmare flash, bootloader o microcontrollore.

Il materiale raccolto permette di sviluppare e verificare un porting specifico della scheda. Non garantisce da solo la conservazione di ogni funzione: servono prove fisiche e, per NDI, una verifica separata del runtime e delle condizioni di integrazione.

Il manuale allegato descrive uso e porte esterne, non smontaggio, punti UART interni o livelli elettrici. Le misure seguenti sono una proposta di laboratorio, non una procedura di assistenza approvata da PTZOptics. Il costruttore avverte di non rimuovere il coperchio e segnala rischi elettrici e conseguenze sulla garanzia. Affida le operazioni interne a una persona competente in elettronica. [F1, pagina i]

| Fase | Attività | Risultato |
| --- | --- | --- |
| A - senza aprire | Inventario, backup ufficiale e documentazione dello stato originale | Tutela dei parametri e riferimento iniziale |
| B - lettura del sistema | Diagnostica autorizzata; inventario e copie MTD se possibili | Configurazione reale di Linux e memoria |
| C - intervento interno | Foto, identificazione elettrica, UART ed eventualmente U-Boot | Identificazione della scheda e percorso di recupero |
| D - osservazione funzionale | Tracce passive PTZ e prove HDMI/SDI/RTSP/NDI | Specifiche per implementazione e collaudo |

Se hai soltanto l'interfaccia web, completa A e le prove video non invasive. Se hai già una shell autorizzata, completa B prima di aprire. In assenza di shell, puoi raccogliere foto e avvio UART, ma non devi aggirare l'autenticazione o modificare il boot per ottenerla.

Non occorre completare tutto prima del primo invio: inventario, foto e log disponibili sono già utili.

### Dati ancora da verificare

La prima analisi riporta indizi software su MN34220, `ttyAMA0`, `ttyAMA1`, un controllore STM32 e componenti HDMI/SDI. Sono piste da verificare, non un pinout. Non assumere RAM da 256/512 MiB, flash da 32 MiB, segnali tutti a 3,3 V o identità fra firmware in esecuzione e IMG allegato. Il rapporto precedente segnala anche un nome software di modello diverso: etichetta e schermate devono chiarire la corrispondenza. [F2]

## 2. Prepara il banco

Scollega la camera dalla rete di produzione. Usa una LAN di laboratorio isolata e un piano stabile con tutta la corsa pan/tilt libera. Non ruotare la testa a mano, non sollevare la camera dalla testa e non bloccare i motori. L'avvio prevede un movimento di inizializzazione, eventualmente seguito dal richiamo del preset 0. [F1, pp. 1 e 3]

Per intervenire all'interno: spegni e scollega alimentatore, PoE, USB, HDMI, SDI e altri collegamenti prima di spostare sonde o connettori. Non aprire l'alimentatore di rete. Per misure alimentate occorrono schede fissate, puntali isolati e cavi lontani dagli organi mobili. Non appoggiare una scheda alimentata su un sacchetto antistatico.

| Attività | Strumenti |
| --- | --- |
| Raccolta iniziale | PC, alimentazione originale, telecomando, rete isolata e fotocamera |
| Comandi della guida | Bash su Linux, OpenSSH; Python 3.9+ per lo script di backup |
| Backup ufficiale | Utility PTZOptics compatibile; la procedura citata documenta il backup su Windows |
| Misure interne | Attrezzatura ESD, utensili, multimetro e oscilloscopio con sonde appropriate |
| Console | USB-UART con livelli I/O documentati e compatibili con quelli misurati |
| Protocollo PTZ | Analizzatore logico, almeno due canali simultanei e soglie compatibili |
| Video | Ricevitore/acquisitore HDMI e 3G-SDI compatibile con i formati provati; FFmpeg facoltativo |

Non scegliere programmatore flash o adattatore di tensione dal solo nome del SoC: prima identifica memoria e circuito.

In questa guida `PC` indica il terminale del computer, `TELECAMERA` la shell Linux originale, `U-BOOT` il prompt del bootloader. Non sono intercambiabili. Gli IP degli esempi non sono quelli accertati della tua camera.

## 3. Organizza i file sul PC

Estrai il pacchetto allegato e apri un terminale nella directory `ptzoptics_raccolta_hardware`. Esegui sul PC:

```bash
umask 077
BASE="$HOME/ptzoptics_evidenze_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BASE"/{00_inventario,01_backup_ufficiale,02_foto,03_uart,04_linux,05_flash,06_ptz,07_video,08_recovery}
cp modelli/README_CONSEGNA.md "$BASE/"
cp modelli/inventario.md "$BASE/00_inventario/"
cp modelli/componenti.csv "$BASE/02_foto/"
cp modelli/eventi_ptz.csv "$BASE/06_ptz/"
cp modelli/risultati_video.csv "$BASE/07_video/"
printf 'Cartella del caso: %s\n' "$BASE"
```

Annota il percorso: una nuova sessione non conserva automaticamente `BASE`. Conserva gli originali senza ritocchi; usa copie separate per annotazioni e anonimizzazione.

## 4. Documenta identità e stato originale

A camera chiusa e funzionante:

1. Fotografa etichetta, pannello posteriore, selettore video e alimentatore. Registra codice prodotto completo e revisione. Conserva seriale e MAC completi nel dossier riservato.
2. Accedi alla web UI con credenziali legittime. Acquisisci schermate di informazioni/versioni, video, audio, rete, PTZ e NDI, quando presenti. Registra anche la versione MCU/ARM se mostrata. Non premere `Apply`, `Restore` o `Upgrade`.
3. Annota selettore, codec e risoluzioni dei due stream, porte, indirizzo VISCA, baud rate seriale esterno, autofocus, orientamento, limiti e preset in uso.
4. Registra un breve filmato dell'avvio e il menu informativo OSD, inquadrando una scena senza persone o documenti riservati.

Il manuale descrive due stream RTSP e porte di controllo configurabili. Non confondere il baud della RS-232 esterna con quello della console o del collegamento SoC-MCU. [F1, pp. 15, 33, 36 e 41-43]

Per NDI registra sorgente, stato di attivazione visibile e versione del ricevitore, senza inviare chiavi o password. Compila `00_inventario/inventario.md` e indica se la versione in esecuzione corrisponde all'IMG già fornito.

## 5. Salva le impostazioni con il backup ufficiale

Questo backup è distinto dal dump flash. PTZOptics indica che contiene dati di fuoco, preset, MAC, seriale, IP e altri parametri specifici della singola camera. Non va ripristinato su una camera diversa. [W1]

La procedura ufficiale citata distingue due edizioni di Upgrade Tool v2.8C, per prefissi MAC `D4:E0:8E` e `DC:ED:84`, e avverte che l'utility errata può modificare il MAC. Documenta inoltre limitazioni del backup nella versione Mac v2.7. Verifica abbinamento di utility, modello e MAC con il supporto ufficiale; se non corrisponde, fermati. [W1]

1. Con PC e camera sulla LAN di laboratorio, apri l'utility ufficiale compatibile, seleziona l'interfaccia e cerca la camera.
2. Verifica identità e IP, poi seleziona la camera e il comando `Backup`.
3. Nella scheda di backup avvia soltanto il salvataggio. Conserva tutti i file prodotti in `01_backup_ufficiale`, con un nome univoco.
4. Salva versione dell'utility, schermata del risultato ed eventuali errori. Fermati prima di `Upgrade`. Non provare `Restore` per verificare il backup.

Un backup completato non equivale a un ripristino collaudato. Se il backup non è disponibile, annotalo e prosegui soltanto con i rilievi non modificanti.

## 6. Raccogli la diagnostica Linux

### 6.1 Con SSH già disponibile

Verifica di poter accedere con un account autorizzato. Non assumere che esista SSH o che le credenziali web valgano per Linux. Non abilitare servizi aggiuntivi e non modificare globalmente gli algoritmi SSH: conserva eventuali errori di connessione.

Lo script allegato legge informazioni di sistema e le scrive sul proprio output; non crea file sulla camera, non apre la UART PTZ e non legge contenuti raw della flash. I risultati possono contenere informazioni sensibili.

Esegui sul PC, sostituendo utente e indirizzo:

```bash
CAM='utente_autorizzato@192.168.50.90'
ssh -T "$CAM" 'sh -s' \
  < scripts/collect_stock_stdout.sh \
  > "$BASE/04_linux/stock_diagnostics.txt" \
  2> "$BASE/04_linux/ssh_diagnostics.stderr.txt"
printf 'Esito SSH: %s\n' "$?"
```

La redirezione viene eseguita dal PC e non consuma spazio sulla flash. L'accesso può comunque generare log, e il firmware può scrivere autonomamente: "sola lettura" descrive lo script, non garantisce immutabilità dell'intera camera.

Verifica che compaiano `FINE_RACCOLTA`, `/proc/mtd`, `/proc/cmdline`, informazioni sulle memorie e log kernel. Conserva anche le sezioni mancanti e gli errori.

### 6.2 Con console o Telnet già autorizzati

Attiva il logging sul PC. Esegui sulla TELECAMERA, uno alla volta:

```sh
uname -a
cat /proc/cpuinfo
cat /proc/cmdline
cat /proc/meminfo
cat /proc/iomem
cat /proc/mtd
cat /proc/partitions
cat /proc/modules
cat /proc/mounts
dmesg
ps
ls -l /dev
ls -l /home/ko /home/ko/extdrv
ls -l /proc/umap /proc/msp
```

Per gli attributi MTD:

```sh
for d in /sys/class/mtd/mtd[0-9]*; do
    [ -d "$d" ] || continue
    n=${d##*/}; number=${n#mtd}
    case "$number" in ''|*[!0-9]*) continue ;; esac
    for a in name type size erasesize writesize oobsize offset; do
        if [ -r "$d/$a" ]; then
            printf '\n%s\n' "$d/$a"
            cat "$d/$a"
        fi
    done
done
```

Sysfs documenta tipo, dimensione e geometria delle MTD; `offset` può mancare nei kernel vecchi. Il solo `MemTotal` non ricostruisce RAM fisica e riserve multimedia: occorre correlare boot log, argomenti e configurazioni. [W2; valutazione tecnica]

Usa Telnet soltanto nella rete isolata e non includere credenziali nel dossier. Senza shell, salta questa fase: non serve ottenere accesso a tutti i costi.

## 7. Fotografa le schede a camera disalimentata

Fase riservata a un operatore competente: nei materiali disponibili non esiste una procedura verificata di smontaggio per la tua revisione.

Documenta ogni passaggio prima di rimuovere viti o connettori. Non forzare clip, flat cable, testa o ottica. Non rimuovere dissipatori o aprire il blocco sensore solo per fotografarlo. Indica cosa rimane nascosto e fermati se l'accesso richiede smontaggi rischiosi.

Realizza foto originali ad alta risoluzione, perpendicolari, con luce diffusa. Per entrambe le facce accessibili includi vista generale, orientamento e primi piani:

| Area | Informazioni da raccogliere |
| --- | --- |
| PCB principale | Codice e revisione serigrafati, SoC, sigle complete RAM |
| Flash/EEPROM | Marcatura, contenitore, riferimento `U...`, pin 1 e posizione |
| Controllore PTZ | Sigla MCU, quarzo, connettori verso motori/testa e test point |
| HDMI e SDI | IC vicini alle uscite, marcature e collegamenti visibili |
| Testa/ottica | Schede e connettori accessibili senza aprire il modulo ottico |
| Interfacce | Header, test point, transceiver RS-232/RS-485 e altri controllori |

Usa nomi come `pcb_base_top_01.jpg`, `pcb_base_bottom_01.jpg`, `U12_marcatura.jpg`. Compila `02_foto/componenti.csv`. Non dedurre pinout dall'ordine dei pad o dai colori dei fili. Una sigla nel firmware non prova che il chip sia montato.

## 8. Acquisisci la console UART, inizialmente solo in ricezione

### 8.1 Identifica massa e livelli

La mini-DIN RS-232 posteriore è un'interfaccia di controllo, non una console Linux documentata. Non collegarvi direttamente un adattatore UART a livelli logici. [F1, pp. 7 e 14-15]

Un tecnico deve identificare una massa digitale certa e il possibile TX usando documentazione, continuità a scheda disalimentata e osservazione strumentale. Non assumere che una schermatura sia massa digitale; non usare resistenza/continuità su circuiti alimentati.

Il multimetro può indicare un livello statico, ma non identifica da solo una UART o distingue con certezza dati e alimentazione. Conferma attività e ampiezza con strumenti appropriati. Prima di connettere USB/oscilloscopio verifica riferimenti di massa e isolamento: una massa errata può danneggiare camera, strumento e PC. Non eliminare la terra di protezione dell'oscilloscopio. [W3]

Annota punto, GND, tensioni bassa/alta, livello a riposo e strumento. Se massa o tensione restano incerte, invia i rilievi senza proseguire.

### 8.2 Collega solo GND e RX

Dopo la verifica elettrica, a camera disalimentata:

| Camera | Adattatore |
| --- | --- |
| GND digitale certa | GND |
| TX console identificato | RX compatibile con la tensione misurata |
| RX console | Non collegato |
| VCC/alimentazione | Non collegato |
| Reset, DTR, RTS | Non collegati |

L'adattatore non deve alimentare la camera. Non basta una scritta "3,3 V": il selettore potrebbe riguardare il pin di alimentazione e non tutti i livelli I/O. Verifica il datasheet del modello e la compatibilità anche dell'ingresso RX. Non unire due uscite TX.

### 8.3 Registra due avvii normali

Apri il terminale seriale sul PC, disattiva flow control hardware/software ed eco locale, attiva la registrazione prima dell'accensione. Come primo tentativo usa `115200, 8N1`: è un indizio della prima analisi, non una conferma per qualsiasi seriale interna. [F2]

Lascia avviare normalmente senza inviare tasti. Registra dall'alimentazione alla comparsa dell'immagine e al termine dei movimenti. Ripeti un secondo avvio senza cambiare configurazione.

Salva `03_uart/boot_01.log`, `boot_02.log`, foto dei collegamenti e `uart_setup.txt` con adattatore, tensioni e impostazioni. Se il testo è illeggibile, conserva l'acquisizione e verifica baud, livelli, inversione e integrità del segnale: non inviare sequenze casuali e non provare altri pad alla cieca.

## 9. Leggi U-Boot solo dopo la console verificata

Facoltativo nel primo invio. La trasmissione PC -> camera richiede RX console certo e livelli compatibili. Collegala solo a camera disalimentata, lasciando scollegati VCC, reset, DTR e RTS.

Al successivo avvio interrompi l'autoboot soltanto con il tasto indicato. Non tentare password o sequenze sconosciute. Al prompt U-Boot, se disponibili:

```text
version
help
printenv
bdinfo
```

`printenv` visualizza variabili e `bdinfo` informazioni della scheda. La disponibilità dipende dalla compilazione: conserva eventuali "unknown command" senza sostituirli con comandi di scrittura. [W4, W5]

Salva `03_uart/uboot_info.log`. Non eseguire `setenv`, `saveenv`, `env default`, `erase`, `sf write`, `nand write`, `mw`, `mtest` o script di installazione. Non caricare immagini TFTP e non cambiare indirizzi di avvio.

Torna al normale avvio senza salvare modifiche, usando esclusivamente il percorso originale già identificato. Se non sai come uscire, fermati e conserva il log.

## 10. Copia le MTD dopo aver verificato il tipo

### 10.1 Inventario prima del dump

IMG di aggiornamento, backup dell'utility e dump MTD sono diversi. Una MTD può rappresentare una partizione, un chip o dispositivi concatenati: sommare le dimensioni non prova la copertura dell'intera flash. Il contenuto di un MCU separato non è automaticamente incluso. [W2; valutazione tecnica]

La lettura MTD richiede normalmente root o permessi specifici: un account della web UI non basta. In assenza di tali permessi, fermati alla diagnostica accessibile. Con SSH autorizzato, esegui sul PC:

```bash
python3 scripts/backup_nor_via_ssh.py \
  --host "$CAM" \
  --out "$BASE/05_flash/inventario"
```

Senza `--read-nor` lo script legge solo `/proc/mtd` e sysfs, producendo `inventory.json` e log. Non legge il contenuto delle partizioni. La destinazione deve essere nuova; per una porta diversa usa `--port NUMERO`.

La lettura gestisce deliberatamente solo NOR classica: `type=nor`, `writesize=1`, `oobsize=0` e geometrie coerenti. NAND, UBI, tipi ignoti o attributi mancanti non vanno forzati.

### 10.2 Due letture NOR direttamente sul PC

Durante il backup non muovere la camera e non modificare impostazioni o preset. Non arrestare servizi, programma video o watchdog per "congelare" il sistema.

Sul PC:

```bash
python3 scripts/backup_nor_via_ssh.py \
  --host "$CAM" \
  --out "$BASE/05_flash/copied_nor" \
  --read-nor
```

Lo script verifica tutte le MTD prima della prima lettura raw, preferisce il nodo carattere di sola lettura se presente e trasferisce i byte al PC senza pseudo-console SSH. Sulla camera esegue `dd` solo con `if=`, mai con `of=`. Non richiede Python sulla camera e non sovrascrive directory esistenti.

Effettua due letture, controlla dimensioni e calcola SHA-256 sul PC. Restituisce `0` per inventario completato/copie uguali, `3` per letture diverse e un errore se trasferimento o verifiche falliscono. Eventuali richieste ripetute di password dipendono dall'autenticazione: non mettere password nello script.

Conserva `lettura_A`, `lettura_B`, `inventory.json`, `comparison.json`, `SHA256SUMS.txt` e log. Un file `.partial` non è una copia verificata.

Due hash uguali provano uguaglianza delle letture, non ripristinabilità. Le partizioni scrivibili possono cambiare mentre Linux gira; una differenza può derivare da scritture originali o da errori. Mantieni entrambe le versioni senza dedurne automaticamente la causa.

### 10.3 NAND, sola console o trasferimento assente

NAND richiede decisioni su ECC, OOB e bad block, oltre alla versione dello strumento. Il sorgente ufficiale di `nanddump` documenta opzioni e trattamenti specifici: la procedura NOR non è trasferibile automaticamente. [W6]

In tal caso invia prima inventario, boot log ed eventualmente `nanddump --help`. Non usare `dd` come presunto backup NAND completo e non ignorare gli errori di lettura.

Con la sola UART/Telnet salva testo, ma non inviare dump binari attraverso il log del terminale. Non assumere che `/tmp` sia RAM o `/mnt/usb` un supporto esterno. Un'eventuale chiavetta richiede verifica di dispositivo, filesystem montato, origine esterna e spazio libero. Senza queste evidenze rinvia il dump, senza attivare nuovi server o montare destinazioni alla cieca.

Gli script del pacchetto precedente non distinguono NOR/NAND; il solo mountpoint non dimostra che il supporto sia esterno. Qui usa il percorso sul PC oppure fermati all'inventario. [F2, verifica degli script]

## 11. Documenta la pipeline sensore/video attiva

Serve capire la configurazione effettiva di sensore, ricevitore, ISP, encoder e uscite. Il nome `hi_mipi.ko` non dimostra da solo l'interfaccia fisica del sensore: correla dati runtime e scheda, senza scegliere MN34220/MIPI dal solo nome della libreria.

Conserva prima l'elenco delle directory diagnostiche. Se esistono report di stato riconoscibili, leggili uno alla volta sulla TELECAMERA, con logging attivo, ad esempio:

```sh
cat /proc/umap/vi
cat /proc/umap/isp
cat /proc/umap/vpss
cat /proc/umap/venc
cat /proc/umap/vo
cat /proc/umap/vb
cat /proc/umap/sys
```

Sono percorsi condizionati alla loro presenza, non garantiti. Annota file mancanti; interrompi una lettura bloccata senza ripeterla automaticamente. Non leggere ricorsivamente tutto `/proc` e non scrivere nei report per cambiare il debug.

Conserva, quando disponibili, dimensioni/frame rate, modalità d'ingresso, ISP, clock, buffer MMZ/VB e timing VO. Acquisisci lo stato originale e, dopo i backup, un secondo stato con una modalità video documentata nella sezione 13.

Per identificare le librerie realmente caricate e i dispositivi aperti dal programma video/PTZ, individua il PID con `ps`. Solo dopo averlo verificato, esegui sulla TELECAMERA, sostituendo il numero di esempio:

```sh
PID=123
tr '\000' ' ' < "/proc/$PID/cmdline"
printf '\n'
cat "/proc/$PID/maps"
ls -l "/proc/$PID/fd"
```

Si leggono metadati del processo: non aprire i dispositivi indicati nei link `fd`. Conserva l'output e segnala eventuali credenziali nella riga di comando prima di condividerlo. [W13]

Non eseguire `himm`, `devmem`, `i2cdetect`, `i2cdump`, utility SPI/GPIO o script di caricamento per "vedere cosa fanno". Non scaricare moduli e non aprire la UART PTZ con `cat`, interferendo con il processo che la usa.

## 12. Acquisisci passivamente il protocollo PTZ

### 12.1 Collegamento e decodifica

`ttyAMA1` è una pista della prima analisi: non identifica pad, baud o tutti i percorsi di controllo. Non assumere che il protocollo SoC-MCU sia VISCA. [F2]

Dopo verifica elettrica, osserva in parallelo il collegamento originale, senza interromperlo:

```text
Linea candidata SoC -> MCU  ---- ingresso CH0
Linea candidata MCU -> SoC  ---- ingresso CH1
Massa digitale verificata  ---- GND strumento
```

Con direzione non provata usa i nomi `linea_A` e `linea_B`. Non collegare TX di adattatori, alimentazioni o generatori. Per bus differenziali/livelli non supportati fermati e identifica il transceiver.

Acquisisci entrambi i canali simultaneamente. Determina dai segnali baud, dati, parità, stop e polarità. Non trasferire il baud della console alla seriale motori. Come margine operativo proposto usa almeno dieci campioni per bit: ad esempio 2 MS/s per una UART realmente a 115200 bit/s. Verifica soglie e limiti del tuo strumento. [W3, W7; margine proposto]

### 12.2 Prove controllate con il firmware originale

Usa web UI o controllore originale funzionante. Inizia lontano dai finecorsa a bassa velocità. Per movimenti continui usa impulsi brevi, indicativamente 0,3-0,5 secondi, seguiti da stop, adattandoli al banco. Se lo stop fallisce, interrompi la prova; non afferrare la testa.

| ID | Prova | Annotazioni |
| --- | --- | --- |
| T00 | Avvio e homing normale | Alimentazione, fine homing, immagine disponibile |
| T01 | Riposo, circa 20 secondi | Stato iniziale e messaggi periodici |
| T02-T03 | Pan sinistra/destra con stop | Durata e velocità; tre ripetizioni |
| T04-T05 | Tilt su/giù con stop | Come sopra, senza raggiungere i limiti |
| T06-T07 | Zoom tele/wide con stop | Stato iniziale e velocità |
| T08-T09 | Focus near/far in manuale, poi auto | Stato AF/MF prima e dopo |
| T10 | Richiamo preset esistente e sicuro | Numero e movimento osservato |
| T11 | Richiesta posizione con controllore già funzionante | Richiesta e risposta esterne, se disponibili |
| T12 | Seconda velocità pan/tilt e zoom | Cambiare un solo parametro |

Salvare un preset modifica dati persistenti: fallo solo dopo i backup e su un numero certamente libero. Non usare preset speciali o il preset 0 come area di prova. Senza slot verificato rinvia il salvataggio. Non cancellare preset/limiti e non avviare calibrazioni.

Per ciascuna prova salva progetto nativo, traccia digitale originale e, se decodificabile, CSV con timestamp, canale/direzione, byte esadecimali ed errori di framing. Screenshot o byte senza tempi non bastano. Compila `06_ptz/eventi_ptz.csv` e un file di metadati:

```text
ID prova:
Foto dei punti di connessione:
CH0/CH1 e direzione, oppure direzione non verificata:
Tensione e soglia logica:
Frequenza di campionamento:
Baud, bit dati, parita, stop, inversione:
Controllore e versione:
Stato iniziale e operazione:
Riferimento temporale dell'azione:
Movimento realmente osservato:
File nativo, traccia grezza e CSV:
Errori o anomalie:
```

Per comandi dal PC è utile una cattura della sola sessione di controllo, annotando interfaccia, porte e tempi. Non presumere che una porta switch mostri traffico fra altri dispositivi. Spiega come hai correlato PC e analizzatore, senza dichiararli sincronizzati se non lo sono. PCAP e log HTTP possono contenere credenziali: trattali come riservati.

## 13. Rileva HDMI, SDI, RTSP, audio e NDI

### 13.1 Modalità video e acquisitori

Prima acquisisci lo stato originale. Dopo i backup prova un formato per volta senza cambiare simultaneamente codec e altre impostazioni.

Il manuale associa `6` a 1080p30, `7` a 1080p25, `0` a 1080p60 e `1` a 1080p50 e richiede un riavvio dopo il cambio. Per la prova annota il valore originale, spegni, cambia selettore e riaccendi; ripristinalo alla fine. Il manuale qualifica i formati frazionari 59,94/29,97 come beta: non confonderli con 60/30 esatti. [F1, p. 3]

| Prova | HDMI e SDI | IP |
| --- | --- | --- |
| V00 | Stato originale | Stream 1 e 2, prima uno alla volta |
| V01 | 1080p30 | RTSP contemporaneo alle uscite fisiche |
| V02 | 1080p60 | RTSP contemporaneo alle uscite fisiche |
| V03 | 1080p25 o 50, se richiesto | RTSP contemporaneo |
| V04 | Configurazione originale | NDI con ricevitore compatibile, se attivo |

Annota acquisitore e firmware, collegamento diretto/convertitori, formato d'ingresso rilevato, frame rate, interlacciamento, audio e perdite di aggancio. Un file registrato a 60 fps non prova che l'ingresso fosse 60 fps: l'acquisitore può convertirlo. Distingui "non provato" da "non funzionante".

Per SDI registra 1,5G/3G e Level A/B se mostrati. Per HDMI conserva EDID del ricevitore e parametri colore/profondità solo se ottenibili con strumenti già disponibili. Non effettuare scansioni I2C.

### 13.2 RTSP dal PC

Il manuale riporta `/1` e `/2` sulla porta predefinita 554. Usa IP e porta reali e non disabilitare l'autenticazione. [F1, pp. 36 e 41-42]

Sul PC, per uno stream accessibile senza credenziali nel comando:

```bash
IP_CAM='192.168.50.90'
ffprobe -v error -rtsp_transport tcp \
  -show_streams -show_format -of json \
  "rtsp://${IP_CAM}:554/1" \
  > "$BASE/07_video/rtsp1_originale.json" \
  2> "$BASE/07_video/rtsp1_originale_errori.txt"
```

Ripeti per `/2` cambiando anche il nome dei file. `ffprobe` descrive il flusso, ma non dimostra stabilità prolungata. [W8, W9]

Campione senza ricodifica, sul PC:

```bash
ffmpeg -nostdin -n -rtsp_transport tcp \
  -i "rtsp://${IP_CAM}:554/1" \
  -t 30 -map 0:v:0 -map '0:a?' -c copy \
  "$BASE/07_video/rtsp1_originale_30s.mkv" \
  2> "$BASE/07_video/rtsp1_originale_30s.log"
```

Con autenticazione richiesta e senza un metodo adeguato per gestire le credenziali, usa il ricevitore già configurato. Password negli URL possono comparire in processi, log e JSON: non inserirle nel dossier condiviso. Non modificare il firmware per far funzionare gli esempi.

### 13.3 Audio, controllo e NDI

Usa una sorgente a livello linea, non un'uscita amplificata, e un evento visivo/sonoro riconoscibile. Registra canali, codec/frequenza e sincronismo osservato. Verifica separatamente HDMI, SDI e IP: non presumere audio su tutte le uscite. Il manuale contiene indicazioni non uniformi sull'audio, quindi documenta il comportamento reale. [F1, pp. 4, 6 e 7]

Per il requisito "tutte le funzioni", annota anche necessità di IR, VISCA rete, RS-232/RS-485, ONVIF, Pelco, RTMP(S), multicast, CVBS, PoE, freeze, orientamento e preset. Non attivare servizi solo per completare una tabella: marca quelli non usati/non provati e registra i controller utilizzati.

Per NDI conserva schermate, metadati del ricevitore, video/audio e funzionamento PTZ, indicando se conservarlo è indispensabile. La documentazione ufficiale presenta NDI Advanced come licenza commerciale per integrazione hardware/software. Avere una camera attivata non dimostra trasferibilità del runtime al nuovo firmware. Non inviare chiavi e non tentare riattivazioni. [W10; valutazione tecnica]

Compila `07_video/risultati_video.csv` anche per le misure non eseguite.

### 13.4 Tracce dei bus di controllo: seconda fase, solo se necessaria

Dopo aver identificato chip e pinout, un tecnico potrebbe acquisire passivamente i bus di controllo dei trasmettitori o del sensore: SDA/SCL per I2C oppure clock, chip-select, MOSI e MISO per SPI, con livelli e campionamento verificati. Registra un avvio e un cambio di formato autorizzato, salvando progetto nativo, tracce, direzioni e sequenza delle operazioni. Questa raccolta serve a ricostruire le scritture effettuate dal firmware originale; non usare un bus master per generarle.

Non collegare un analizzatore generico ai segnali video ad alta velocità (MIPI/LVDS, HDMI/TMDS, SDI) o alla DDR. La misura dei bus di controllo non va confusa con quella del flusso video. Senza punti e requisiti elettrici verificati, rinvia questa fase: non è un requisito del primo invio.

## 14. Documenta il recupero senza sperimentare scritture

Prima di installazioni future servono flash certa, geometria/mappa, copie verificate e recupero compatibile con la scheda. Le MTD esposte possono non includere aree non mappate, altre memorie, OTP o EEPROM: annota l'incertezza invece di usare la dimensione dell'IMG come prova. [W2; valutazione tecnica]

In `08_recovery` registra accesso alla console/bootloader, `help`, sigle delle memorie, attrezzatura disponibile e limiti. Non dimostrare il recupero sovrascrivendo la camera funzionante.

La lettura dell'intero chip con programmatore esterno va progettata dopo l'identificazione. Una clip non garantisce isolamento: il programmatore può alimentare parzialmente altre parti della scheda e creare contesa sul bus. Non aggiungere una seconda alimentazione e non collegare un programmatore generico per tentativi. [W11]

Non collegare ST-Link/SWD/JTAG al PTZ in questa fase e non eseguire sblocchi RDP, option byte o erase: alcune procedure STM32 cancellano la memoria. Preservare firmware e parametri del MCU è un obiettivo. Un file di aggiornamento MCU nella flash principale non è automaticamente il dump del controllore montato. [W12; valutazione tecnica]

## 15. Verifica e prepara la consegna

Invia per primi riepilogo, inventario, schermate versioni, foto e log disponibili. Per i backup includi inizialmente esito, dimensioni e hash: non occorre caricare subito ogni contenuto integrale.

| Materiale | Requisito |
| --- | --- |
| Foto | Originali leggibili, orientamento e riferimenti PCB/IC |
| UART | Log completo, impostazioni e punti documentati |
| Linux | Output originale, inclusi errori e assenze |
| Flash | Tipo/dimensioni, copie complete, hash e differenze esplicitate |
| PTZ | Due canali, traccia nativa, tempi e azioni esatte |
| Video | Configurato distinto da misurato e registrato |
| Recupero | Metodo e limiti, senza dichiarare prove non eseguite |

Flash, backup ufficiali e PCAP possono contenere credenziali, certificati, chiavi e identificativi. Mantienili inizialmente in un archivio privato cifrato con seconda copia. Non pubblicarli in issue GitHub e non caricarli indiscriminatamente: prima si valutano contenuti necessari e condivisibili. Anonimizza copie dei documenti testuali, non alterare i dump originali; ricalcola gli hash delle copie modificate.

Crea sul PC una cartella per i soli file autorizzati:

```bash
SHARE="$HOME/ptzoptics_condivisione_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SHARE"
```

Dopo avervi copiato i file selezionati, esegui sul PC:

```bash
(
  cd "$SHARE" || exit 1
  find . -type f ! -name SHA256SUMS.txt -print0 \
    | sort -z \
    | xargs -0 -r sha256sum > SHA256SUMS.txt
  sha256sum -c SHA256SUMS.txt
) &&
tar -C "$(dirname "$SHARE")" -czf "${SHARE}.tar.gz" "$(basename "$SHARE")"
```

Questi comandi non cifrano l'archivio. Non eseguirli sulla camera. Includi problemi incontrati, attività non eseguite e funzioni indispensabili.

## 16. Quando fermarsi

Arresta la singola fase per massa/tensione non identificate, pinout incerto, surriscaldamento anomalo, corto sospetto, reset ripetuti, motori che non si fermano, letture fallite o autenticazione assente. Non compensare con tentativi casuali.

Non installare OpenIPC prima della valutazione della mappa reale, dei dati specifici e del recupero. Il passo successivo è definire un avvio recuperabile per questa scheda, non usare comandi generici di un'altra camera Hi3516.

## 17. Verifiche del pacchetto

`collect_stock_stdout.sh` raccoglie testo senza scegliere una destinazione sulla camera. `backup_nor_via_ssh.py` inventaria e, solo su richiesta esplicita, legge due volte le NOR verso il PC: non è uno strumento di ripristino. I modelli sono vuoti, non dati osservati.

Controllati sintassi shell e 14 test su dati simulati: parsing MTD, rifiuto di banner/duplicati/metadati mancanti, geometrie incoerenti, NAND/OOB e sorgenti errate, nomi, dimensioni e SHA-256; inoltre inventario senza dump, due trasferimenti binari e arresto su NAND con trasporto SSH simulato. Nessun accesso alla camera o test elettrico è stato eseguito. I test software non certificano collegamenti o compatibilità sul dispositivo.

Per ripeterli sul PC:

```bash
sh -n scripts/collect_stock_stdout.sh
python3 -m unittest discover -s tests -v
```

## 18. Fonti e provenienza

Le fonti documentano i punti indicati; non sostituiscono misure su questa unità. Script, organizzazione, sequenze di prova e punti di arresto sono proposte operative per questa raccolta, non procedure pubblicate dal produttore.

[F1] Manuale allegato dall'utente: `PTZOptics 12x 3G-SDI_NDI Gen 2 manual.pdf`, rev. 1.7, agosto 2020. Pagine secondo numerazione stampata: pagina 1 = pagina PDF 4. Non viene qualificato come manuale più recente. Copia ufficiale della stessa revisione: `https://ptzoptics.com/wp-content/uploads/2021/01/PT12X-SDI-xx-G2-User-Manual-v1_7-rev-8-20.pdf`.

[F2] Pacchetto precedente `OpenIPC_PTZOptics_G2_bringup_2026-11-05.zip`: `docs/hardware_evidence.md`, `tools/collect_stock_readonly.sh`, `tools/backup_mtd_readonly.sh`, riletti per questa guida. Le conclusioni hardware restano evidenze della precedente analisi software, non misure indipendenti.

[W1] PTZOptics, procedura G2, backup e avvertenze sulle utility: `https://docs.ptzoptics.com/articles/guides/g2-firmware-update/`. Pagina con Rev 1.4 9/21; qui sono usati solo i passaggi di backup.

[W2] Linux, ABI sysfs MTD: `https://raw.githubusercontent.com/torvalds/linux/master/Documentation/ABI/testing/sysfs-class-mtd`.

[W3] Saleae, acquisizione e riferimenti di massa: `https://www.saleae.com/support/troubleshooting/capture-and-recording-issues/captured-data-looks-incorrect`. Verificare comunque il datasheet dello strumento posseduto.

[W4] U-Boot, `env`/`printenv`: `https://docs.u-boot.org/en/latest/usage/cmd/env.html`.

[W5] U-Boot, `bdinfo`: `https://docs.u-boot.org/en/latest/usage/cmd/bdinfo.html`. Non tutte le opzioni correnti sono necessariamente presenti nel bootloader originale.

[W6] Linux MTD, sorgente `nanddump`: `https://kernel.googlesource.com/pub/scm/linux/kernel/git/rw/mtd-utils/+/abcf731e041d8d977b992820c38f6e95ed63fd3b/nanddump.c`.

[W7] Saleae, campionamento: `https://www.saleae.com/support/logic-software/capturing-data/what-sample-rate-is-required`.

[W8] FFmpeg, documentazione ffprobe: `https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/doc/ffprobe.texi`.

[W9] FFmpeg, protocolli/RTSP: `https://raw.githubusercontent.com/FFmpeg/FFmpeg/master/doc/protocols.texi`.

[W10] NDI Advanced SDK: `https://docs.ndi.video/all/developing-with-ndi/advanced-sdk`.

[W11] flashrom, accesso in-system: `https://raw.githubusercontent.com/flashrom/flashrom/main/doc/user_docs/in_system.rst`.

[W12] OpenOCD, Flash Commands, sezioni STM32: `https://openocd.org/doc/html/Flash-Commands.html`.

[W13] Linux, filesystem `/proc` e informazioni dei processi: `https://docs.kernel.org/filesystems/proc.html`.

Fonti web consultate il 5 novembre 2026.
