Per realizzare un port OpenIPC effettivamente funzionante sulla tua videocamera Hi3516A, mi servono soprattutto informazioni ricavate dall'hardware acceso. Il firmware che hai già fornito contiene buona parte della configurazione originale, quindi non è necessario ripetere l'analisi da zero.

Distinguerei due obiettivi: una prima versione con Linux, Ethernet e streaming RTSP; successivamente il supporto completo di PTZ, zoom, autofocus e delle eventuali uscite video.

## 1. Informazioni necessarie, in ordine di priorità

| Priorità                | Informazione richiesta                                                         | A cosa serve                                                                             |
| ----------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| 1 — Indispensabile      | Log seriale completo dall'accensione fino al login Linux                       | Identificare SoC, RAM, SPI flash, bootloader, periferiche e problemi di inizializzazione |
| 1 — Indispensabile      | Output di `/proc/mtd`, `/proc/cmdline`, `fw_printenv`                          | Ricostruire il layout reale della flash e preparare un avvio sicuro                      |
| 1 — Indispensabile      | Fotografie ad alta risoluzione della scheda elettronica, su entrambi i lati    | Identificare chip DDR, SPI NOR, PHY Ethernet e circuiti esterni                          |
| 1 — Indispensabile      | Backup integrale della SPI flash e metodo di ripristino                        | Evitare di rendere inutilizzabile la videocamera durante i test                          |
| 2 — Video               | Log di inizializzazione del sensore MN34220, risoluzioni e frequenze operative | Configurare driver ISP, MIPI/LVDS e Majestic                                             |
| 2 — PTZ                 | Tracce della comunicazione UART tra Hi3516A e STM32                            | Ricostruire il protocollo di controllo dei motori                                        |
| 3 — Funzioni aggiuntive | Identificazione dei chip HDMI/SDI e requisiti NDI                              | Valutare la possibilità di mantenere le funzionalità professionali                       |

## 2. Comandi da eseguire sulla videocamera

Se hai accesso SSH, Telnet o alla console Linux originale, puoi raccogliere le informazioni diagnostiche con questo script. I comandi sono di sola lettura rispetto al firmware e alla flash; viene scritto soltanto un file temporaneo.

```
(
echo "=== KERNEL ==="
uname -a

echo "=== CPU ==="
cat /proc/cpuinfo

echo "=== MEMORY ==="
cat /proc/meminfo

echo "=== COMMAND LINE ==="
cat /proc/cmdline

echo "=== MTD PARTITIONS ==="
cat /proc/mtd

echo "=== BOOTLOADER ENVIRONMENT ==="
fw_printenv 2>&1

echo "=== LOADED MODULES ==="
cat /proc/modules

echo "=== MOUNT POINTS ==="
mount

echo "=== DEVICES ==="
ls -l /dev/ttyAMA* /dev/i2c* /dev/mtd* 2>/dev/null

echo "=== HARDWARE LOGS ==="
dmesg

) > /tmp/openipc_probe.txt
```

Il file `/tmp/openipc_probe.txt` è il primo elemento che mi serve. Prima di condividerlo, elimina password, token, numeri di serie, indirizzi MAC e altri identificativi riservati eventualmente presenti.

## 3. Accesso alla console seriale

Dal firmware originale sappiamo che la console è configurata come:

```
ttyAMA0,115200
```

Vorrei acquisire il log seriale completo tramite un adattatore USB-UART, con parametri 115200 baud, 8N1.

|---|---|---|
|<img src="https://github.com/user-attachments/assets/eff1bff7-1e60-406b-ba25-1fb163c7bc7b" width="33%" />|<img src="https://github.com/user-attachments/assets/0cb6c529-012f-47cb-8c92-f37603427b09" width="33%" />|<img src="https://github.com/user-attachments/assets/d881cbce-d1d7-4fae-b79b-3547ce4965d2" width="33%" />|

6

Il log permette di verificare la configurazione effettiva di U-Boot, oltre a capire se possiamo caricare un kernel OpenIPC temporaneamente via TFTP senza modificare la flash.

Occorre misurare prima i livelli elettrici della UART: non collegare direttamente un'interfaccia RS-232 o segnali a 5 V.

## 4. La questione del sensore MN34220

Qui abbiamo già un vantaggio: OpenHisilicon elenca MN34220 per Hi3516AV100. Tuttavia la disponibilità del sorgente non significa che la libreria venga automaticamente compilata e installata nella configurazione firmware. Il progetto mantiene infatti un tracciamento specifico dell'integrazione dei driver sensore.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Dal firmware abbiamo già recuperato:

- Identificazione MN34220 e bus I²C0.
- Clock del sensore a 37,125 MHz.
- Configurazione ISP originale.
- Script di inizializzazione dei registri e del pinmux.

Restano da confermare sull'hardware l'interfaccia fisica effettiva del sensore, la modalità operativa, i segnali di reset e alimentazione e l'inizializzazione completa. Queste informazioni serviranno per verificare lo streaming reale, non soltanto la compilazione.

## 5. Per il PTZ serve un'acquisizione separata

L'analisi ha identificato un microcontrollore STM32 collegato a `/dev/ttyAMA1`, ma non abbiamo ancora decodificato il protocollo seriale.

Il modo più affidabile per ricostruirlo è registrare passivamente le comunicazioni mentre il firmware originale esegue alcuni comandi: STOP, brevi movimenti Pan/Tilt, zoom avanti/indietro, focus e richiamo di un preset.

Servono frame esadecimali, timestamp, parametri UART e indicazione del comando corrispondente. Con questi dati possiamo sviluppare un demone Linux che dialoghi con lo STM32, mantenendo invariato il firmware del microcontrollore.

## 6. Cosa posso sviluppare con i primi dati

La configurazione OpenIPC ufficiale `hi3516av100_lite` esiste, ma prevede una flash da 8 MiB, mentre la mappa del firmware originale richiede almeno 25 MiB. Bisogna quindi produrre una configurazione specifica della scheda.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Sequenza di realizzazione proposta

1. Configurazione Buildroot/OpenIPC personalizzata, kernel e avvio temporaneo con console seriale.
2. Inizializzazione Ethernet, memoria e filesystem; accesso SSH.
3. Integrazione MN34220, ISP e Majestic per ottenere RTSP/H.264.
4. Bridge UART STM32 per Pan/Tilt/Zoom/Focus e successiva integrazione ONVIF.
5. Validazione, recupero e generazione dell'immagine installabile, con eventuale supporto alle uscite video esterne.

La compilazione di una prima versione è possibile anche prima di avere tutto il materiale. La conferma del funzionamento e la produzione di un'immagine installabile in sicurezza richiedono però prove ripetute sulla videocamera reale.

## Da dove partire

Per il prossimo passaggio sono sufficienti:

1. Il file `openipc_probe.txt` generato dai comandi sopra.
2. Due fotografie nitide della scheda elettronica.
3. Il log seriale completo di una normale accensione, se puoi acquisirlo.

Infine, una distinzione importante: vuoi ottenere una videocamera OpenIPC con RTSP e controllo PTZ tramite ONVIF/VISCA, oppure è indispensabile conservare anche NDI, HDMI e SDI? La seconda opzione amplia sensibilmente il lavoro, perché OpenIPC non garantisce automaticamente queste funzionalità.
