# Lautsprecher-UI – Nutzerfeedback, Review und Bewegungsplan

Datum: 06.10.2026. Ziel: eine hochwertige, angenehme ACK-Studio-Anwendung, mit der man gern einen Lautsprecher entwickelt und deren Zeichnungen direkt lesbar sind.

## Direkte Rückmeldung des Nutzers

> Allgemein finde ich die UI sieht noch sehr technisch aus und ich glaube als Nutzer hätte man nicht wirklich Spaß aktuell, gerade weil man auch die Zeichnungen gar nicht lesen kann, weil alles so klein ist.

Auftrag: die vorherige Review im Repository als Feedback ablegen und um konkrete Animationen ergänzen.

## Grundlage und Prüfumfang

Geprüfter Code: `b2e03d89b4829466dc3838764edd6e30d81e9fa2`, Branch `claude/modest-bell-guqoxu` im Repository `Unternehmen-Lautsprecher-konzepte`. Dies ist ein Snapshot-Review, keine Aussage, dass spätere Commits bereits nachgeprüft sind. Die Rückmeldung wird auf dem aktuellen Entwicklungsbranch abgelegt.

Original-PySide6-Oberfläche lokal unter Qt/Linux offscreen gerendert, mit den mitgelieferten Inter-/Cormorant-Fonts und dem tatsächlichen Berechnungskern. Die Screenshots sind echte Widget-Aufnahmen, kein nachgebautes Mockup. Kein vollständiger Windows-/DPI-, Screenreader- oder Maus-/Tastatur-End-to-End-Test. Native Details können auf Windows anders aussehen; fehlende Pfeilsymbole unter Offscreen wurden nicht als Windowsfehler eingestuft. Akustische Richtigkeit und Fertigungsreife sind kein Ergebnis dieser UI-Review.

## Urteil

Farbwelt und Schriftfamilien passen zum aktuellen ACK-Studio-Paket. Es braucht jedoch eine Überarbeitung von Hierarchie, Arbeitsfläche und Ergebnisdarstellung. Animation allein beseitigt die überladenen Formulare und die zu kleinen Zeichnungen nicht.

Beibehalten: warmer weißer Grund, dunkles Konstruktion-Senfgelb, Serif für ausgewählte Titel, Inter für Bedienung, sichtbare Hauptaktion, optionaler Expertenmodus und die ruhige Diagrammgestaltung.

## Priorisierte Befunde

- **P1 – Veraltete Zeichnung nach Fehlschlag:** Neuberechnung darf keine unmarkierten alten Ergebnisse hinterlassen. Reproduktion: Regallautsprecher-Demo berechnen → unmögliche Demo berechnen → Zeichnungen öffnen.
- **P1 – Formular-/Fensterlayout:** Seitlich abgeschnittene Controls und unnötig große Mindestfenster beheben. Kernangaben und primäre Aktion auf Laptopauflösung erreichbar halten.
- **P1 – Lesbarkeit der Fortschrittsanzeige:** Text #282723 auf gefülltem Akzent #735419 ergibt ca. 2,14:1. Fortschrittstext außerhalb des Balkens oder kontrastreich darstellen.
- **P2 – Ergebnisdarstellung:** Visualisierung plus wenige Kennwerte, Kosten-/Datenqualität und klare Empfehlung. Technische Details einklappbar.
- **P2 – Vergleich und Fehlerführung:** Entscheidungsrelevante Spalten zuerst; lesbare Fehlermeldungen mit Bezug zu Eingaben.
- **P2 – Icons und Markenkonsistenz:** Eigene verständliche Outline-Icons mit Text für Bibliothek, Entwurf, Zeichnungen, Simulation und Export. Alter Footername Ackerschewski_code steht noch im Programm.
- **P3 – Bewegung und Feinschliff:** Keine Website-Slideshow in die Fachanwendung übernehmen. Kurze Rückmeldung bei Berechnung und Aktualisierung genügt. Bewegungsreduktion unterstützen.

## Ansichten und konkrete Verbesserungen

### 1 · Einstieg – Überarbeitungsbedürftig

![1 · Einstieg](evidence/2026-10-06-ack-ui/01-start.png)

**Beobachtet:** Die warmweiße Fläche, Cormorant-Titel und der Konstruktion-Akzent stimmen mit ACK Studio überein. Die beiden großen leeren Ergebnisfelder wirken dagegen unfertig. Das Klangprofil als eine der drei Haupteingaben liegt unterhalb des sichtbaren Formularbereichs. Rechts abgeschnittene Eingabefelder sind bereits bei 1500 × 920 sichtbar.

**Ändern:** Leeren Ergebnisraum durch kurze Anleitung und ein Beispiel ersetzen. Typ, maximale Maße und Klangprofil gemeinsam sichtbar machen. Formularspalten an verfügbare Breite anpassen; primäre Aktion unten erreichbar lassen.

### 2 · Berechneter Entwurf – Funktioniert, schlecht aufbereitet

![2 · Berechneter Entwurf](evidence/2026-10-06-ack-ui/02-result.png)

**Beobachtet:** Der Regallautsprecher-Demolauf liefert drei Varianten aus 1992 geprüften Kandidaten. Die Auswahl funktioniert, doch Ergebnisdetails sind ein dichter HTML-Bericht mit Unicode-Balken und vielen gleichgewichtigen Zeilen. Kosten sind unbekannt und mehrere Qualitätskriterien unbewertet; trotzdem wirkt 66/100 wie eine umfassende Qualitätsnote. Die permanente 100%-Leiste beansprucht Platz und hat dunkle Schrift auf dunklem Senf.

**Ändern:** Oben Visualisierung, Maße, F3, Kostenstatus und Datenqualität zeigen. Score als Teilbewertung kennzeichnen; berechnete/fehlende Kriterien explizit anzeigen. Details einklappen. Fortschrittsleiste nach Abschluss durch kurzen Status ersetzen. Native Balken statt Textzeichen verwenden.

### 3 · Variantenvergleich – Deutlich überarbeitungsbedürftig

![3 · Variantenvergleich](evidence/2026-10-06-ack-ui/03-comparison.png)

**Beobachtet:** Die drei Zeilen stehen in einer elfspaltigen Tabelle mit sehr breiten automatisch angepassten Spalten. Chassisnamen, Kosten, Budget und Hinweise sind teilweise nur durch horizontales Scrollen erreichbar. Der Großteil der Höhe bleibt ungenutzt.

**Ändern:** Standardansicht auf Variante, Gehäuse, Maße, F3, Gesamtkosten und Prüfstatus begrenzen. Namen umbrechen, relevante Unterschiede hervorheben; Zusatzwerte per Detailansicht. Eingabepanel für den Vergleich einklappbar machen.

### 4 · Zeichnungen – Grundfunktion gut, Arbeitsfläche zu klein

![4 · Zeichnungen](evidence/2026-10-06-ack-ui/04-drawings.png)

**Beobachtet:** Gesamtzeichnung, Maßblatt, Innenaufbau und Einzelteilplan sind sinnvoll getrennt. Zoom und Einpassen sind vorhanden. Die Gesamtzeichnung wird aber nur mit 29 % dargestellt; Beschriftungen sind kaum lesbar. Das große Eingabeformular und zwei Reiterleisten reduzieren die Zeichenfläche.

**Ändern:** Ergebnis-/Zeichnungsmodus mit einklappbarem Formular und größerer Zeichenfläche. Seitenbreite, 100 % und Einpassen als klare Zoomoptionen. Kennwerte auch außerhalb des Druckblatts lesbar anzeigen; Druckzeichnung separat behandeln.

### 5 · Simulation – Visuell am stimmigsten

![5 · Simulation](evidence/2026-10-06-ack-ui/05-simulation.png)

**Beobachtet:** Zwei gut gegliederte Diagramme, passende Papierfläche und Akzentkurve. Einheiten und Grenzlinie sind sichtbar, Zusatzdiagramme optional. Die zugrunde gelegte Leistung und die Grenzen einer relativen Tieftonkurve sind in dieser Ansicht nicht ausreichend präsent.

**Ändern:** Leistung, Datenquelle und Gültigkeitsbereich direkt über den Diagrammen nennen. Diese Farb-/Rastergestaltung als Vorbild für die übrigen technischen Ergebnisansichten verwenden.

### 6 · Kleineres Fenster – Problematisch

![6 · Kleineres Fenster](evidence/2026-10-06-ack-ui/06-small-window.png)

**Beobachtet:** Eine angeforderte Größe von 1280 × 720 wird auf 1280 × 733 begrenzt. Der Pflichtteil zum Bauraum verschwindet fast vollständig unter dem Scrollbereich. Eingabefelder werden weiterhin seitlich abgeschnitten. Zwei unabhängig scrollende Arbeitsbereiche erschweren den Überblick.

**Ändern:** Minimumbreiten der Formularinhalte und QFormLayout prüfen. Unter definierten Breiten Formular/Ergebnis umschaltbar machen oder untereinander anordnen. Zieltest: 1280 × 720 ohne seitlich abgeschnittene Controls; zusätzlich Windows 125 % und 150 % Skalierung prüfen.

### 7 · Expertenmodus – Fachlich umfangreich, gestalterisch unfertig

![7 · Expertenmodus](evidence/2026-10-06-ack-ui/07-expert.png)

**Beobachtet:** Das Fenster erweitert sich auf etwa 1651 × 900. Links stehen sehr viele Eingabefelder, rechts überwiegend unstrukturierter Ergebnistext mit englischen internen Bezeichnungen wie sealed, Back, Top und woofer. Warnungen, Berechnungsstand und Kennwerte wiederholen sich in mehreren Leisten.

**Ändern:** Expertenmodus in klar getrennte Aufgaben gliedern. Ergebnisse als echte Kennwerte, Tabellen und Warnungsliste statt als Textausdruck. Deutsche sichtbare Begriffe; Detailbezeichnungen für Fachwerte mit Tooltips. Maximal verfügbare Bildschirmgröße beachten.

### 8 · Nicht machbare Vorgaben – Teilweise gut

![8 · Nicht machbare Vorgaben](evidence/2026-10-06-ack-ui/08-impossible.png)

**Beobachtet:** Die unmögliche Demo wird abgewiesen; Export und Speichern sind deaktiviert. Die Meldung enthält aber ungefilterte englische Solvertexte. Änderungsvorschläge bleiben allgemein; die leere Variantenliste beansprucht weiterhin Höhe.

**Ändern:** Fehler auf die betroffene Eingabe zurückführen. Verständliches Deutsch, technische Originalmeldung in aufklappbaren Details. Konkrete Grenzwerte nur nennen, wenn vom Solver belegt. Leere Variantenliste ausblenden und Abhilfen neben den Feldern zeigen.

### 9 · Zeichnung nach fehlgeschlagener Neuberechnung – Hohe Priorität: widersprüchlicher Zustand

![9 · Zeichnung nach fehlgeschlagener Neuberechnung](evidence/2026-10-06-ack-ui/09-old-drawing-after-failure.png)

**Beobachtet:** Nach dem Wechsel vom erfolgreich berechneten Regalmodell zur unmöglichen Subwoofer-Demo zeigt der Reiter Zeichnungen weiterhin das alte Regalmodell. Laufzeitprüfung: designs ist leer, der SVG-Renderer enthält weiterhin eine gültige Zeichnung, Export ist gesperrt. Banner und angezeigte Geometrie beziehen sich damit auf verschiedene Projekte.

**Ändern:** Beim Start bzw. Fehlschlag alle Ergebnisansichten konsistent invalidieren. Alte Ergebnisse entweder löschen oder ausdrücklich als vorherigen, nicht aktuellen Entwurf kennzeichnen. Dasselbe für Simulation, Stückliste und Zuschnitt prüfen; Export-Sperre beibehalten.

## Zielbild: angenehm entwickeln statt Formulare abarbeiten

1. **Projekt starten:** Name, Lautsprechertyp, maximaler Bauraum und Klangprofil sind in einem überschaubaren Einstieg sichtbar. Seltene Werte liegen unter „Weitere Anforderungen“. Eine kleine Kontextskizze oder später eine geprüfte Gehäusevorschau hilft beim Verständnis; kein riesiger dekorativer Website-Hero.
2. **Entwurf verstehen:** Auf der Ergebnisfläche steht eine große Gehäuseansicht. Daneben höchstens fünf zentrale Kennwerte: Maße, Tiefbass/F3, Preisstatus, Datenqualität und Prüfstatus. „Warum empfohlen?“ erklärt kurz den Vorschlag. Vollständige Herleitung bleibt aufklappbar.
3. **Varianten auswählen:** Drei kompakte Variantenkarten oder eine reduzierte Vergleichstabelle; Unterschiede wie kleiner, tieferer Bass und günstigere bekannte Kosten sind direkt erkennbar. Unbekannte Preise nicht als günstiger behandeln. Die Bewertung muss unbewertete Kriterien nennen und darf keine vollständige Qualitätsfreigabe suggerieren.
4. **Zeichnung bearbeiten:** „Zeichnungsmodus“ klappt die Eingabeseite ein. Papier, Modell und Maßdetails werden ausreichend groß dargestellt. Gesamtblatt dient der Übersicht; jede Ansicht/Einzelteilzeichnung ist separat aufrufbar. Browserartige Dokumentnavigation und native Qt-Zoom/Pan-Funktionen verwenden.
5. **Fertigung vorbereiten:** Prüfstatus und offene Fragen vor dem Export bündeln. Export wird nur nach den bestehenden geometrischen Prüfregeln freigegeben. Eine aktuelle Zeichnung darf nicht mit einem alten oder gescheiterten Berechnungsstand verwechselt werden.

### Lesbare Zeichnungen – höchste gestalterische Priorität

- Zeichnungsarbeitsfläche übernimmt im Fokusmodus den verfügbaren Inhaltsbereich; Formular und lange Statusleisten werden einklappbar.
- Ansicht auf das eigentliche Bauteil/den Schnitt anpassen, statt nur ein vollständiges dichtes Druckblatt winzig einzupassen. Für den Bildschirm eine Lesedarstellung anbieten; PDF-/Druckmaßstab bleibt unverändert.
- Klare Controls: „Einpassen“, „Seitenbreite“, „100 %“, Zoom-Prozent als editierbarer Wert; Zoom per Mausrad am Mauszeiger und Pan mit eindeutiger Bedienhilfe.
- Einzelansichten/Einzelteile über benannte Navigation auswählen. Bemaßungen bei Auswahl zusätzlich in einer lesbaren Detailleiste anzeigen. Keine Maße durch Skalieren des Bildes neu interpretieren oder erfinden.
- Änderungen im Formular markieren vorhandene Unterlagen sofort als veraltet. Fehlschlag leert die neue Ergebnisfläche oder kennzeichnet das vorherige Ergebnis eindeutig inklusive altem Projektnamen/Berechnungsstand.
- Technische Linien, Bemaßung und Text dürfen in der UI andere Bildschirmgrößen haben als im Druckexport, müssen aber dieselben geprüften Modelldaten zeigen.

## Bewegungsplan für eine hochwertige Oberfläche

Die folgenden Werte sind konkrete Startwerte für die Umsetzung, keine bereits eingebauten Funktionen. Mit Qt `QPropertyAnimation`, `QVariantAnimation` oder äquivalenten nativen Mitteln umsetzen. Eine Animation darf niemals die Berechnung oder Bedienung blockieren.

| Anlass | Bewegung | Dauer / Kurve | Zweck und Regeln |
|---|---|---|---|
| Hover über wichtige Aktion | dezenter Wechsel von Hintergrund/Rahmen; keine Größe ändern | 120–160 ms, EaseOut | klickbares Element erkennbar; Mausbewegung nicht mit starkem Springen beantworten |
| Button ausgelöst | kurze visuelle Druckrückmeldung, dann Zustand „Berechnung läuft“ | 80–120 ms | Klick sofort bestätigen; kein künstliches Warten |
| Optionale Anforderungen | Höhe weich öffnen/schließen, Inhalt anschließend erreichbar | 180–220 ms, OutCubic | Aufbau bleibt nachvollziehbar; Fokus darf nicht in unsichtbaren Feldern hängen bleiben |
| Eingabepanel einklappen | Splitterbreite weich reduzieren; Zeichnung währenddessen nicht teuer neu berechnen | 220–280 ms, OutCubic | Zeichenfläche spürbar vergrößern; nach Ende genau einmal einpassen |
| Ergebnisreiter wechseln | sehr kurzer Crossfade im Inhaltsbereich | 120–180 ms, EaseOut | Zusammenhang erhalten; keine horizontalen Reiseanimationen oder verschobenen Bedienelemente |
| Variante wählen | Auswahlmarkierung weich ändern; Preview kurz überblenden | 160–220 ms | Wechsel klar zeigen; Kennwerte, Zeichnung und Prüfstatus müssen zum selben Ergebnis gehören |
| Neue Berechnung abgeschlossen | Preview und Kennwerte gemeinsam einblenden, optional höchstens 6 px Weg | 180–240 ms, OutCubic | neues Ergebnis hervorheben; keine rollenden Zahlen oder künstlich hochzählenden Messergebnisse |
| Einpassen / Zoom-Button | kontrollierter Übergang zur Zielansicht | 140–200 ms | räumliche Orientierung behalten; Mausrad-/Drag-Zoom folgt dagegen unmittelbar der Eingabe |
| Berechnung läuft | echter Fortschritt und kurzer Schrittext; dezenter Spinner nur bei unbekanntem Fortschritt | solange tatsächlich erforderlich | keine erfundenen Prozente, keine durchlaufende Ablenkung in fertigen Ansichten; Abbrechen bleibt sofort erreichbar |
| Speichern / Export | kurze Bestätigung mit Icon und Dateipfad/Öffnen-Aktion | Einblendung 120–180 ms | Erfolg zeigen; Meldung lange genug lesbar und bei Fehler persistent |
| Eingabefehler | Rahmen und erklärender Text erscheinen | maximal 120 ms | kein Schütteln, Blinken oder ausschließlich farbliche Kennzeichnung; Fokus sinnvoll zum Fehler führen |

### Bewegungsregeln

- Einstellung „Animationen reduzieren“ und soweit verfügbar die Betriebssystempräferenz berücksichtigen. Reduziert: alle Positions-/Zoom-/Größenanimationen sofort ausführen; Rückmeldung bleibt als statischer Text/Status erhalten.
- Zustandsänderung ist maßgeblich, nicht das Ende der Animation. Mehrfachklicks, schnelle Variantenwechsel, erneute Berechnung und Abbrechen dürfen keine konkurrierenden Timer oder veraltete Resultate produzieren.
- Kein bewegtes Hintergrundbild, keine Website-Slideshow, kein Autoplay und keine ständig pulsierenden Buttons im Konstruktionsprogramm.
- Hover, Tastaturfokus und Auswahl müssen getrennt erkennbar sein. Tastaturbedienung braucht keine Hover-Animation.
- Bei Animationen von Splittern und Zeichnungen teure SVG-/Plot-Erzeugung vermeiden; vorhandenen Inhalt transformieren/überblenden und am Ende aktualisieren. Fokus bleibt stabil.
- Mit 60-Hz-Ziel auf normalem Laptop testen. Wenn eine komplexe Zeichnung ruckelt, die Animation vereinfachen oder weglassen statt die Fachfunktion zu verlangsamen.

## Konkrete Arbeitspakete für Claude / Umsetzung

### A · Ergebniszustände und Layout zuerst (P1)

Betroffene Stellen: `ui/assistant_window.py` (`_build_wizard`, `_build_results`, `_completed`, `_select_variant`), `ui/main_window.py`, `ui/theme.py`.

- Alle Views gemeinsam invalidieren, einschließlich Zeichnungen, Simulation, BOM und Zuschnitt.
- Formularfelder an die Viewportbreite anpassen; Mindestbreiten und QFormLayout-Wrapping korrigieren.
- 100%-Fortschrittstext mit ausreichendem Kontrast darstellen; beobachteter Kontrast #282723 auf #735419 ist ca. 2,14:1.
- Alten sichtbaren Footer „Ackerschewski_code“ durch ACK Studio ersetzen.

### B · Zeichnungsmodus und Ergebnisübersicht (P1/P2)

Betroffene Stellen: `ui/zoom_svg.py`, `ui/assistant_window.py`, Zeichnungsansichten. Separate Bildschirmdarstellung verwenden, ohne Exportgeometrie zu verfälschen.

- Fokusmodus und Lesedarstellung umsetzen.
- Große Vorschau + wenige Kennwerte, kompakte Variantenwahl, Herkunft/Unsicherheit und ausklappbare Details.
- Unicode-Textbalken durch echte UI-Balken oder einfache Kennwerte ersetzen.
- Tabellen auf entscheidungsrelevante Standardspalten begrenzen; sekundäre Werte auf Abruf.

### C · Bewegung und visuelle Qualität (P2/P3)

- Zuerst Optionserweiterung, Panelwechsel, Variantenauswahl und Exportbestätigung aus obiger Tabelle umsetzen.
- Einheitliche echte Outline-Icons mit Textlabels verwenden. Keine Emoji-/Unicode-Symbole als Ersatz für die gesamte Navigation.
- Aktuelle Designquelle bleibt `Basis-Ackerschewski-Design-System/packages/ack-studio`; eine reduzierte Bewegungsschicht im Projektprofil dokumentieren, statt neue Farben/Schriften zu erfinden.

## Abnahme / Definition of Done

- [ ] Bei 1280 × 720, 1366 × 768 und 1920 × 1080 keine seitlich abgeschnittenen Hauptcontrols. Windows zusätzlich bei 100/125/150 % Skalierung testen; kleinere nutzbare Flächen funktional abfangen.
- [ ] Die drei Kernangaben Typ, Bauraum und Klangprofil sind ohne langes Suchen erreichbar; Zeichnungsmodus braucht höchstens eine Aktion.
- [ ] Eine Einzelansicht bzw. ein Einzelteil ist im Zeichnungsmodus ohne manuelles extremes Zoomen lesbar. Maßdetails mindestens in normaler UI-Leseschrift, z. B. 14 logische px, verfügbar. Screenshots mit realistischen langen Teilen und vielen Maßen vorlegen.
- [ ] Regaldemo berechnen → unmögliche Demo → alle Ergebnisreiter prüfen: kein unmarkiertes altes Ergebnis; Export bleibt gesperrt.
- [ ] „Warum empfohlen?“ erklärt Kennwerte, unbewertete Kriterien und unbekannte Preise; keine Scheinpräzision.
- [ ] Fortschrittstext erreicht mindestens 4,5:1 oder steht gut lesbar außerhalb des Balkens.
- [ ] Öffnen, Variantenwechsel, Fehlerbehebung und Exportstatus mit Tastatur bedienbar; Fokus geht nicht verloren.
- [ ] Animationsreduktion, schnelle Wechsel und Abbruch während Berechnung getestet; keine zusätzliche Wartezeit und kein flackernder Ergebnisstand.
- [ ] Vorher-/Nachher-Screenshots auf identischer Fenstergröße mit echtem Inhalt; tatsächliche Nutzerprüfung für angenehme Bedienung und Lesbarkeit noch erforderlich.

## Grenzen dieses Feedbacks

Feedback und Bewegungsplan sind abgelegt, die Änderungen sind noch nicht implementiert. Benutzerabnahme, Windows-/DPI-Prüfung und Messvalidierung bleiben offen. Bestehende automatische Berechnungs-, Export- und Geometriegates beibehalten.
