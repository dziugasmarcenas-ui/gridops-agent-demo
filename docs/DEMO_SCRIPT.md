# Demonstracijos scenarijus (90–120 sek.)

Visi šiame projekte naudojami incidentų duomenys ir procedūros yra
sintetiniai. Sistema neturi ir niekada neturėjo prieigos prie jokios realios
energetikos įmonės sistemos ar duomenų.

---

**[0:00–0:10] Įžanga**

„Tai GridOps Agent — sintetinis tinklų incidentų operacijų asistentas.
Jis sujungia struktūrizuotus duomenis PostgreSQL, procedūrų dokumentų
paiešką (RAG), LLM įrankių naudojimą, šaltinių nurodymą ir aiškų žmogaus
patvirtinimo reikalavimą prieš bet kokį veiksmą."

**[0:10–0:40] A srautas — prioritetizavimas**

Paspausti „A: Prioritetai šį rytą".

„Agentas užklausia incidentų duomenų bazę, apskaičiuoja skaidrų
demonstracinį prioriteto balą kiekvienam incidentui ir susiranda
susijusią eskalavimo procedūrą. Dešiniajame skydelyje matote tiksliai,
kokie įrankiai buvo iškviesti, kokie duomenų bazės faktai gauti ir kokia
tiksli procedūros ištrauka su skyriaus numeriu buvo panaudota."

**[0:40–1:10] B srautas — eskalavimo juodraštis**

Paspausti „B: Eskalavimo juodraštis INC-1042".

„Agentas paruošia eskalavimo įrašo juodraštį pagal turimus duomenis ir
procedūrą. Atkreipkite dėmesį į raudoną žymą: JUODRAŠTIS — REIKALINGAS
ŽMOGAUS PATVIRTINIMAS. Niekas nebuvo išsiųsta. Tik paspaudus mygtuką
'Patvirtinti' — atskiru, aiškiu žmogaus veiksmu — įrašas tampa
patvirtintu. Pats agentas savo juodraščio patvirtinti negali."

**[1:10–1:40] C srautas — trūkstamos informacijos pripažinimas**

Paspausti „C: Kas sukėlė INC-1042?".

„Šio incidento patvirtinta priežastis duomenų bazėje yra NULL. Agentas
privalo tai pripažinti, o ne spėlioti. Tai patikrinama ne tik per
instrukciją modeliui, bet ir deterministine kodo patikra, kuri
blokuotų atsakymą, jei jis vis dėlto paminėtų konkrečią priežastį."

**[1:40–2:00] Uždarymas**

„Trys ramsčiai: struktūrizuoti faktai, procedūrų šaltiniai su tiksliomis
citatomis, ir žmogus, kuris visada priima galutinį sprendimą dėl
veiksmo. Visas kodas — trumpas, skaitomas, be papildomų agentų
karkasų — sąmoningai parašytas taip, kad būtų lengvai paaiškinamas."
