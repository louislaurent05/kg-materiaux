"""
Knowledge Graph Materiaux - Airbus LMP (exemple)
Usage :
    pip install neo4j
    python build_kg.py            -> cree/complete le graphe + verifications
    python build_kg.py --reset    -> efface TOUT le graphe avant de recreer
"""
import os
import sys
from neo4j import GraphDatabase

URI = os.getenv("NEO4J_URI", "neo4j+s://6761ef10.databases.neo4j.io")
def load_env(path=None):
    """Charge le fichier .env (cle=valeur) situe a cote de ce script."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
if not os.getenv("NEO4J_PASSWORD"):
    sys.exit("NEO4J_PASSWORD manquant : renseignez-le dans le fichier .env")
AUTH = (os.getenv("NEO4J_USER", "6761ef10"), os.environ["NEO4J_PASSWORD"])
DATABASE = os.getenv("NEO4J_DATABASE", "6761ef10")

# ----------------------------------------------------------------------
# 1. CONTRAINTES
# ----------------------------------------------------------------------
LABELS_UNIQUE = ["Famille", "SousFamille", "Nuance", "EtatMetallurgique", "Propriete",
                 "Mesure", "Procede", "Piece", "Assemblage", "Programme", "ZoneAvion",
                 "Norme", "Fournisseur", "Environnement", "Risque", "Unite"]

CONSTRAINTS = [
    f"CREATE CONSTRAINT {l.lower()}_id IF NOT EXISTS FOR (n:{l}) REQUIRE n.id IS UNIQUE"
    for l in LABELS_UNIQUE
] + [
    "CREATE INDEX nuance_nom IF NOT EXISTS FOR (n:Nuance) ON (n.nom)",
    "CREATE INDEX piece_nom IF NOT EXISTS FOR (n:Piece) ON (n.nom)",
]

# ----------------------------------------------------------------------
# 2. DONNEES + CREATION
# ----------------------------------------------------------------------
STEPS = []

def step(name, query, **params):
    STEPS.append((name, query, params))

step("Familles", """
UNWIND $rows AS f
MERGE (n:Famille {id:f.id}) SET n.nom = f.nom
""", rows=[
    {"id": "FAM-01", "nom": "Alliages d aluminium"},
    {"id": "FAM-02", "nom": "Alliages de titane"},
    {"id": "FAM-03", "nom": "Aciers et superalliages"},
    {"id": "FAM-04", "nom": "Composites a matrice organique"},
    {"id": "FAM-05", "nom": "Polymeres et elastomeres"},
    {"id": "FAM-06", "nom": "Ceramiques et verres"},
    {"id": "FAM-07", "nom": "Revetements et traitements de surface"},
])

step("Sous-familles", """
UNWIND $rows AS s
MATCH (f:Famille {id:s.fam})
MERGE (sf:SousFamille {id:s.id}) SET sf.nom = s.nom
MERGE (sf)-[:APPARTIENT_A]->(f)
""", rows=[
    {"id": "SF-AL-2XXX", "nom": "Al serie 2xxx (Al-Cu)", "fam": "FAM-01"},
    {"id": "SF-AL-7XXX", "nom": "Al serie 7xxx (Al-Zn)", "fam": "FAM-01"},
    {"id": "SF-AL-LI", "nom": "Al-Li", "fam": "FAM-01"},
    {"id": "SF-TI-ALPHABETA", "nom": "Ti alpha-beta", "fam": "FAM-02"},
    {"id": "SF-TI-BETA", "nom": "Ti beta", "fam": "FAM-02"},
    {"id": "SF-ACIER-HR", "nom": "Aciers haute resistance", "fam": "FAM-03"},
    {"id": "SF-INOX-PH", "nom": "Inox a durcissement structural", "fam": "FAM-03"},
    {"id": "SF-SUPER-NI", "nom": "Superalliages base nickel", "fam": "FAM-03"},
    {"id": "SF-CFRP", "nom": "CFRP (carbone/epoxy)", "fam": "FAM-04"},
    {"id": "SF-GFRP", "nom": "GFRP (verre/epoxy)", "fam": "FAM-04"},
    {"id": "SF-THERMOPL", "nom": "Thermoplastiques hautes performances", "fam": "FAM-05"},
    {"id": "SF-ELASTO", "nom": "Elastomeres et joints", "fam": "FAM-05"},
    {"id": "SF-CMC", "nom": "Composites a matrice ceramique", "fam": "FAM-06"},
    {"id": "SF-VERRE", "nom": "Verres aeronautiques", "fam": "FAM-06"},
    {"id": "SF-ANOD", "nom": "Conversion et anodisation", "fam": "FAM-07"},
    {"id": "SF-PEINT", "nom": "Peintures et primaires", "fam": "FAM-07"},
    {"id": "SF-BTH", "nom": "Barrieres thermiques", "fam": "FAM-07"},
])

step("Unites", """
UNWIND $rows AS u
MERGE (x:Unite {id:u.id}) SET x.symbole=u.symbole, x.grandeur=u.grandeur
""", rows=[
    {"id": "U-MPA", "symbole": "MPa", "grandeur": "contrainte"},
    {"id": "U-GPA", "symbole": "GPa", "grandeur": "module"},
    {"id": "U-GCM3", "symbole": "g/cm3", "grandeur": "masse volumique"},
    {"id": "U-PCT", "symbole": "%", "grandeur": "allongement"},
    {"id": "U-MPAM", "symbole": "MPa.m^0.5", "grandeur": "tenacite"},
    {"id": "U-C", "symbole": "degC", "grandeur": "temperature"},
    {"id": "U-WMK", "symbole": "W/m.K", "grandeur": "conductivite thermique"},
    {"id": "U-UMMK", "symbole": "um/m.K", "grandeur": "dilatation"},
])

step("Proprietes", """
UNWIND $rows AS p
MATCH (u:Unite {id:p.unite})
MERGE (x:Propriete {id:p.id}) SET x.nom=p.nom, x.categorie=p.categorie
MERGE (x)-[:EXPRIMEE_EN]->(u)
""", rows=[
    {"id": "P-RM", "nom": "Resistance a la traction (Rm)", "categorie": "mecanique", "unite": "U-MPA"},
    {"id": "P-RP02", "nom": "Limite elastique (Rp0.2)", "categorie": "mecanique", "unite": "U-MPA"},
    {"id": "P-E", "nom": "Module d Young (E)", "categorie": "mecanique", "unite": "U-GPA"},
    {"id": "P-A", "nom": "Allongement a rupture (A%)", "categorie": "mecanique", "unite": "U-PCT"},
    {"id": "P-K1C", "nom": "Tenacite (K1c)", "categorie": "mecanique", "unite": "U-MPAM"},
    {"id": "P-RHO", "nom": "Masse volumique", "categorie": "physique", "unite": "U-GCM3"},
    {"id": "P-LAMBDA", "nom": "Conductivite thermique", "categorie": "thermique", "unite": "U-WMK"},
    {"id": "P-ALPHA", "nom": "Coefficient de dilatation", "categorie": "thermique", "unite": "U-UMMK"},
    {"id": "P-TMAX", "nom": "Temperature max d utilisation", "categorie": "thermique", "unite": "U-C"},
])

step("Nuances", """
UNWIND $rows AS n
MATCH (sf:SousFamille {id:n.sf})
MERGE (x:Nuance {id:n.id}) SET x.nom=n.nom, x.statut=n.statut, x.note=n.note
MERGE (x)-[:APPARTIENT_A]->(sf)
""", rows=[
    {"id": "N-2024", "nom": "2024", "sf": "SF-AL-2XXX", "statut": "actif", "note": "Al-Cu-Mg"},
    {"id": "N-2014", "nom": "2014", "sf": "SF-AL-2XXX", "statut": "obsolescent", "note": "remplace progressivement"},
    {"id": "N-7075", "nom": "7075", "sf": "SF-AL-7XXX", "statut": "actif", "note": "Al-Zn-Mg-Cu"},
    {"id": "N-7050", "nom": "7050", "sf": "SF-AL-7XXX", "statut": "actif", "note": "Al-Zn-Mg-Cu-Zr"},
    {"id": "N-2198", "nom": "2198", "sf": "SF-AL-LI", "statut": "actif", "note": "Al-Cu-Li"},
    {"id": "N-TI64", "nom": "Ti-6Al-4V", "sf": "SF-TI-ALPHABETA", "statut": "actif", "note": "alpha-beta"},
    {"id": "N-TI5553", "nom": "Ti-5553", "sf": "SF-TI-BETA", "statut": "actif", "note": "Ti-5Al-5V-5Mo-3Cr"},
    {"id": "N-300M", "nom": "300M", "sf": "SF-ACIER-HR", "statut": "actif", "note": "acier bas alliage THR"},
    {"id": "N-15-5PH", "nom": "15-5PH", "sf": "SF-INOX-PH", "statut": "actif", "note": "inox martensitique PH"},
    {"id": "N-IN718", "nom": "Inconel 718", "sf": "SF-SUPER-NI", "statut": "actif", "note": "base Ni"},
    {"id": "N-IM7-8552", "nom": "IM7/8552", "sf": "SF-CFRP", "statut": "actif", "note": "carbone IM / epoxy 8552"},
    {"id": "N-T800-M21", "nom": "T800/M21", "sf": "SF-CFRP", "statut": "actif", "note": "carbone / epoxy M21"},
    {"id": "N-GFRP-E", "nom": "Verre E / epoxy", "sf": "SF-GFRP", "statut": "actif", "note": "stratifie verre"},
    {"id": "N-PEEK", "nom": "PEEK", "sf": "SF-THERMOPL", "statut": "actif", "note": "polyetheretherketone"},
    {"id": "N-PEKK", "nom": "PEKK", "sf": "SF-THERMOPL", "statut": "actif", "note": "polyetherketoneketone"},
    {"id": "N-FKM", "nom": "FKM (Viton)", "sf": "SF-ELASTO", "statut": "actif", "note": "fluoroelastomere"},
    {"id": "N-SIC-SIC", "nom": "SiC/SiC", "sf": "SF-CMC", "statut": "emergent", "note": "CMC chaud moteur"},
    {"id": "N-VERRE-AERO", "nom": "Verre aeronautique", "sf": "SF-VERRE", "statut": "actif", "note": "pare-brise / hublots"},
    {"id": "N-AAS", "nom": "Anodisation sulfurique tartrique", "sf": "SF-ANOD", "statut": "actif", "note": "TSA, alternative au chromique"},
    {"id": "N-PRIM-EPOXY", "nom": "Primaire epoxy", "sf": "SF-PEINT", "statut": "actif", "note": "protection corrosion"},
    {"id": "N-YSZ", "nom": "YSZ (zircone yttriee)", "sf": "SF-BTH", "statut": "actif", "note": "barriere thermique"},
])

step("Alias nuances", """
UNWIND $rows AS r
MATCH (n:Nuance {id:r.id}) SET n.alias = r.alias
""", rows=[
    {"id": "N-TI64", "alias": ["TA6V", "Ti64", "Ti-6-4", "Grade 5"]},
    {"id": "N-IN718", "alias": ["Alliage 718", "UNS N07718"]},
    {"id": "N-15-5PH", "alias": ["Z6CNU15-05", "UNS S15500"]},
])

step("Etats metallurgiques", """
UNWIND $rows AS e
MATCH (n:Nuance {id:e.nuance})
MERGE (x:EtatMetallurgique {id:e.id}) SET x.code=e.code, x.description=e.desc
MERGE (n)-[:A_POUR_ETAT]->(x)
""", rows=[
    {"id": "E-7075-T7351", "nuance": "N-7075", "code": "T7351", "desc": "Mise en solution, detensionne, survieilli"},
    {"id": "E-7075-T651", "nuance": "N-7075", "code": "T651", "desc": "Mise en solution, detensionne, revenu"},
    {"id": "E-7050-T7451", "nuance": "N-7050", "code": "T7451", "desc": "Survieilli, forte tenacite"},
    {"id": "E-2024-T351", "nuance": "N-2024", "code": "T351", "desc": "Mise en solution, detensionne, murit naturellement"},
    {"id": "E-2198-T8", "nuance": "N-2198", "code": "T8", "desc": "Ecrouissage et revenu"},
    {"id": "E-TI64-REC", "nuance": "N-TI64", "code": "Recuit", "desc": "Mill-annealed"},
    {"id": "E-TI5553-STA", "nuance": "N-TI5553", "code": "STA", "desc": "Solution traite et vieilli"},
    {"id": "E-300M-THR", "nuance": "N-300M", "code": "THR", "desc": "Trempe et revenu tres haute resistance"},
    {"id": "E-IN718-STA", "nuance": "N-IN718", "code": "STA", "desc": "Mise en solution et vieillissement"},
])

step("Normes", """
UNWIND $rows AS n
MERGE (x:Norme {id:n.id}) SET x.reference=n.ref, x.type=n.type, x.titre=n.titre, x.statut=n.statut
""", rows=[
    {"id": "NRM-001", "ref": "AMS 4078 (exemple)", "type": "AMS", "titre": "Plaques 7075-T7351", "statut": "en vigueur"},
    {"id": "NRM-002", "ref": "AMS 4050 (exemple)", "type": "AMS", "titre": "Plaques 7050-T7451", "statut": "en vigueur"},
    {"id": "NRM-003", "ref": "AMS 4037 (exemple)", "type": "AMS", "titre": "Tole 2024", "statut": "en vigueur"},
    {"id": "NRM-004", "ref": "AIMS 03-04-xxx (exemple)", "type": "AIMS", "titre": "Al-Li 2198", "statut": "en vigueur"},
    {"id": "NRM-005", "ref": "AMS 4911 (exemple)", "type": "AMS", "titre": "Tole Ti-6Al-4V recuit", "statut": "en vigueur"},
    {"id": "NRM-006", "ref": "AMS 4965 (exemple)", "type": "AMS", "titre": "Ti-5553 forge", "statut": "en vigueur"},
    {"id": "NRM-007", "ref": "AMS 6417 (exemple)", "type": "AMS", "titre": "Acier 300M", "statut": "en vigueur"},
    {"id": "NRM-008", "ref": "AMS 5662 (exemple)", "type": "AMS", "titre": "Inconel 718", "statut": "en vigueur"},
    {"id": "NRM-009", "ref": "AIPS 02-01-xxx (exemple)", "type": "AIPS", "titre": "Anodisation TSA", "statut": "en vigueur"},
    {"id": "NRM-010", "ref": "AIPS 04-02-xxx (exemple)", "type": "AIPS", "titre": "Procede de peinture", "statut": "en vigueur"},
    {"id": "NRM-011", "ref": "REACH", "type": "Reglementaire", "titre": "Restriction chrome VI", "statut": "en vigueur"},
])

step("Conformite etats -> normes", """
UNWIND $rows AS r
MATCH (e:EtatMetallurgique {id:r[0]}), (n:Norme {id:r[1]})
MERGE (e)-[:EST_CONFORME_A]->(n)
""", rows=[
    ["E-7075-T7351", "NRM-001"], ["E-7050-T7451", "NRM-002"], ["E-2024-T351", "NRM-003"],
    ["E-2198-T8", "NRM-004"], ["E-TI64-REC", "NRM-005"], ["E-TI5553-STA", "NRM-006"],
    ["E-300M-THR", "NRM-007"], ["E-IN718-STA", "NRM-008"],
])

step("Conformite nuances -> normes", """
UNWIND $rows AS r
MATCH (a:Nuance {id:r[0]}), (n:Norme {id:r[1]})
MERGE (a)-[:EST_CONFORME_A]->(n)
""", rows=[["N-AAS", "NRM-009"], ["N-AAS", "NRM-011"], ["N-PRIM-EPOXY", "NRM-010"]])

step("Mesures (etats)", """
UNWIND $rows AS m
MATCH (e:EtatMetallurgique {id:m.cible}), (p:Propriete {id:m.prop})
OPTIONAL MATCH (n:Norme {id:m.source})
MERGE (x:Mesure {id:m.id})
  SET x.valeur_min=m.min, x.valeur_typique=m.typ, x.valeur_max=m.max,
      x.conditions=m.cond, x.statut=m.statut, x.date_validation=date('2025-01-15')
MERGE (e)-[:A_MESURE]->(x)
MERGE (x)-[:MESURE_DE]->(p)
FOREACH (_ IN CASE WHEN n IS NULL THEN [] ELSE [1] END | MERGE (x)-[:SOURCE]->(n))
""", rows=[
    {"id": "M-001", "cible": "E-7075-T7351", "prop": "P-RM", "min": 435, "typ": 490, "max": None, "cond": "Direction L, 20C", "statut": "garanti", "source": "NRM-001"},
    {"id": "M-002", "cible": "E-7075-T7351", "prop": "P-RP02", "min": 360, "typ": 420, "max": None, "cond": "Direction L, 20C", "statut": "garanti", "source": "NRM-001"},
    {"id": "M-003", "cible": "E-7075-T7351", "prop": "P-K1C", "min": None, "typ": 30, "max": None, "cond": "L-T, 20C", "statut": "typique", "source": None},
    {"id": "M-004", "cible": "E-7050-T7451", "prop": "P-RM", "min": 485, "typ": 520, "max": None, "cond": "Direction L, 20C", "statut": "garanti", "source": "NRM-002"},
    {"id": "M-005", "cible": "E-7050-T7451", "prop": "P-K1C", "min": None, "typ": 35, "max": None, "cond": "L-T, 20C", "statut": "typique", "source": None},
    {"id": "M-006", "cible": "E-2024-T351", "prop": "P-RM", "min": 425, "typ": 470, "max": None, "cond": "Direction L, 20C", "statut": "garanti", "source": "NRM-003"},
    {"id": "M-007", "cible": "E-2198-T8", "prop": "P-RM", "min": 420, "typ": 460, "max": None, "cond": "Direction L, 20C", "statut": "garanti", "source": "NRM-004"},
    {"id": "M-008", "cible": "E-TI64-REC", "prop": "P-RM", "min": 895, "typ": 950, "max": None, "cond": "20C", "statut": "garanti", "source": "NRM-005"},
    {"id": "M-009", "cible": "E-TI64-REC", "prop": "P-RP02", "min": 825, "typ": 880, "max": None, "cond": "20C", "statut": "garanti", "source": "NRM-005"},
    {"id": "M-010", "cible": "E-TI64-REC", "prop": "P-TMAX", "min": None, "typ": 350, "max": None, "cond": "Usage continu", "statut": "indicatif", "source": None},
    {"id": "M-011", "cible": "E-TI5553-STA", "prop": "P-RM", "min": 1100, "typ": 1250, "max": None, "cond": "20C", "statut": "garanti", "source": "NRM-006"},
    {"id": "M-012", "cible": "E-300M-THR", "prop": "P-RM", "min": 1930, "typ": 1990, "max": None, "cond": "20C", "statut": "garanti", "source": "NRM-007"},
    {"id": "M-013", "cible": "E-IN718-STA", "prop": "P-RM", "min": 1240, "typ": 1350, "max": None, "cond": "20C", "statut": "garanti", "source": "NRM-008"},
    {"id": "M-014", "cible": "E-IN718-STA", "prop": "P-TMAX", "min": None, "typ": 650, "max": None, "cond": "Usage continu", "statut": "indicatif", "source": None},
])

step("Mesures (nuances)", """
UNWIND $rows AS m
MATCH (n:Nuance {id:m.cible}), (p:Propriete {id:m.prop})
MERGE (x:Mesure {id:m.id})
  SET x.valeur_min=m.min, x.valeur_typique=m.typ, x.valeur_max=m.max,
      x.conditions=m.cond, x.statut=m.statut, x.date_validation=date('2025-01-15')
MERGE (n)-[:A_MESURE]->(x)
MERGE (x)-[:MESURE_DE]->(p)
""", rows=[
    {"id": "M-101", "cible": "N-IM7-8552", "prop": "P-RM", "min": None, "typ": 2300, "max": None, "cond": "0 deg, 20C", "statut": "typique"},
    {"id": "M-102", "cible": "N-IM7-8552", "prop": "P-E", "min": None, "typ": 160, "max": None, "cond": "0 deg, 20C", "statut": "typique"},
    {"id": "M-103", "cible": "N-IM7-8552", "prop": "P-RHO", "min": None, "typ": 1.57, "max": None, "cond": "20C", "statut": "typique"},
    {"id": "M-104", "cible": "N-T800-M21", "prop": "P-RM", "min": None, "typ": 2800, "max": None, "cond": "0 deg, 20C", "statut": "typique"},
    {"id": "M-105", "cible": "N-PEEK", "prop": "P-RM", "min": None, "typ": 100, "max": None, "cond": "20C", "statut": "typique"},
    {"id": "M-106", "cible": "N-PEEK", "prop": "P-TMAX", "min": None, "typ": 250, "max": None, "cond": "Usage continu", "statut": "indicatif"},
    {"id": "M-107", "cible": "N-PEKK", "prop": "P-TMAX", "min": None, "typ": 260, "max": None, "cond": "Usage continu", "statut": "indicatif"},
    {"id": "M-108", "cible": "N-SIC-SIC", "prop": "P-TMAX", "min": None, "typ": 1200, "max": None, "cond": "Usage continu", "statut": "indicatif"},
    {"id": "M-109", "cible": "N-7075", "prop": "P-RHO", "min": None, "typ": 2.81, "max": None, "cond": "20C", "statut": "typique"},
    {"id": "M-110", "cible": "N-TI64", "prop": "P-RHO", "min": None, "typ": 4.43, "max": None, "cond": "20C", "statut": "typique"},
    {"id": "M-111", "cible": "N-IN718", "prop": "P-RHO", "min": None, "typ": 8.19, "max": None, "cond": "20C", "statut": "typique"},
    {"id": "M-112", "cible": "N-7050", "prop": "P-RHO", "min": None, "typ": 2.83, "max": None, "cond": "20C", "statut": "typique"},
    {"id": "M-113", "cible": "N-2198", "prop": "P-RHO", "min": None, "typ": 2.69, "max": None, "cond": "20C", "statut": "typique"},
])

# ======================================================================
# BLOC 2 : fournisseurs, procedes, programmes, zones, environnements,
#          pieces, assemblages
# ======================================================================

step("Fournisseurs", """
UNWIND $rows AS f
MERGE (x:Fournisseur {id:f.id}) SET x.nom=f.nom, x.pays=f.pays, x.qualifie=f.qualifie
""", rows=[
    {"id": "F-01", "nom": "Fournisseur Alu A (exemple)", "pays": "France", "qualifie": True},
    {"id": "F-02", "nom": "Fournisseur Alu B (exemple)", "pays": "Allemagne", "qualifie": True},
    {"id": "F-03", "nom": "Fournisseur Titane A (exemple)", "pays": "Etats-Unis", "qualifie": True},
    {"id": "F-04", "nom": "Fournisseur Titane B (exemple)", "pays": "Russie", "qualifie": False},
    {"id": "F-05", "nom": "Fournisseur Acier A (exemple)", "pays": "France", "qualifie": True},
    {"id": "F-06", "nom": "Fournisseur Superalliage A (exemple)", "pays": "Royaume-Uni", "qualifie": True},
    {"id": "F-07", "nom": "Fournisseur Composite A (exemple)", "pays": "Japon", "qualifie": True},
    {"id": "F-08", "nom": "Fournisseur Composite B (exemple)", "pays": "Etats-Unis", "qualifie": True},
    {"id": "F-09", "nom": "Fournisseur Polymere A (exemple)", "pays": "Belgique", "qualifie": True},
    {"id": "F-10", "nom": "Fournisseur Traitement surface A (exemple)", "pays": "France", "qualifie": True},
])

step("Fournisseur -> nuances", """
UNWIND $rows AS r
MATCH (f:Fournisseur {id:r[0]}), (n:Nuance {id:r[1]})
MERGE (f)-[:FOURNIT]->(n)
""", rows=[
    ["F-01", "N-7075"], ["F-01", "N-7050"], ["F-01", "N-2024"],
    ["F-02", "N-7075"], ["F-02", "N-2198"],
    ["F-03", "N-TI64"], ["F-03", "N-TI5553"],
    ["F-04", "N-TI64"],
    ["F-05", "N-300M"], ["F-05", "N-15-5PH"],
    ["F-06", "N-IN718"],
    ["F-07", "N-IM7-8552"], ["F-07", "N-T800-M21"],
    ["F-08", "N-IM7-8552"], ["F-08", "N-GFRP-E"],
    ["F-09", "N-PEEK"], ["F-09", "N-PEKK"], ["F-09", "N-FKM"],
    ["F-10", "N-AAS"], ["F-10", "N-PRIM-EPOXY"],
])

step("Procedes", """
UNWIND $rows AS p
MERGE (x:Procede {id:p.id}) SET x.nom=p.nom, x.type=p.type
""", rows=[
    {"id": "PR-USIN", "nom": "Usinage", "type": "mise en forme"},
    {"id": "PR-FORGE", "nom": "Forgeage", "type": "mise en forme"},
    {"id": "PR-FONDERIE", "nom": "Fonderie", "type": "mise en forme"},
    {"id": "PR-ALM", "nom": "Fabrication additive (ALM)", "type": "mise en forme"},
    {"id": "PR-AFP", "nom": "Depose de fibres automatisee (AFP)", "type": "composite"},
    {"id": "PR-AUTOCLAVE", "nom": "Cuisson autoclave", "type": "composite"},
    {"id": "PR-COLLAGE", "nom": "Collage structural", "type": "assemblage"},
    {"id": "PR-SOUD", "nom": "Soudage (FSW / laser)", "type": "assemblage"},
    {"id": "PR-RIVET", "nom": "Rivetage / boulonnage", "type": "assemblage"},
    {"id": "PR-ANOD", "nom": "Anodisation", "type": "traitement de surface"},
    {"id": "PR-PEINT", "nom": "Peinture", "type": "traitement de surface"},
    {"id": "PR-SHOT", "nom": "Grenaillage de precontrainte", "type": "traitement de surface"},
    {"id": "PR-CND-US", "nom": "Controle ultrasons", "type": "CND"},
    {"id": "PR-CND-RES", "nom": "Controle ressuage", "type": "CND"},
    {"id": "PR-CND-RX", "nom": "Controle radiographique", "type": "CND"},
])

step("Procedes -> nuances compatibles", """
UNWIND $rows AS r
MATCH (p:Procede {id:r[0]}), (n:Nuance {id:r[1]})
MERGE (n)-[:COMPATIBLE_AVEC]->(p)
""", rows=[
    ["PR-USIN", "N-7075"], ["PR-USIN", "N-7050"], ["PR-USIN", "N-2024"], ["PR-USIN", "N-2198"],
    ["PR-USIN", "N-TI64"], ["PR-USIN", "N-300M"], ["PR-USIN", "N-IN718"], ["PR-USIN", "N-PEEK"],
    ["PR-FORGE", "N-7050"], ["PR-FORGE", "N-TI64"], ["PR-FORGE", "N-TI5553"], ["PR-FORGE", "N-300M"],
    ["PR-FONDERIE", "N-IN718"],
    ["PR-ALM", "N-TI64"], ["PR-ALM", "N-IN718"], ["PR-ALM", "N-PEKK"],
    ["PR-AFP", "N-IM7-8552"], ["PR-AFP", "N-T800-M21"],
    ["PR-AUTOCLAVE", "N-IM7-8552"], ["PR-AUTOCLAVE", "N-T800-M21"],
    ["PR-COLLAGE", "N-T800-M21"], ["PR-COLLAGE", "N-2024"],
    ["PR-SOUD", "N-2198"], ["PR-SOUD", "N-TI64"],
    ["PR-ANOD", "N-7075"], ["PR-ANOD", "N-7050"], ["PR-ANOD", "N-2024"], ["PR-ANOD", "N-2198"],
    ["PR-SHOT", "N-7050"], ["PR-SHOT", "N-300M"],
])

step("Programmes", """
UNWIND $rows AS p
MERGE (x:Programme {id:p.id}) SET x.nom=p.nom, x.type=p.type
""", rows=[
    {"id": "PRG-A220", "nom": "A220", "type": "monocouloir"},
    {"id": "PRG-A320", "nom": "A320 Family", "type": "monocouloir"},
    {"id": "PRG-A330", "nom": "A330", "type": "long-courrier"},
    {"id": "PRG-A350", "nom": "A350", "type": "long-courrier"},
    {"id": "PRG-A400M", "nom": "A400M", "type": "militaire"},
])

step("Zones avion", """
UNWIND $rows AS z
MERGE (x:ZoneAvion {id:z.id}) SET x.nom=z.nom
""", rows=[
    {"id": "Z-VOILURE", "nom": "Voilure"},
    {"id": "Z-FUSELAGE", "nom": "Fuselage"},
    {"id": "Z-TRAIN", "nom": "Train d atterrissage"},
    {"id": "Z-MOTEUR", "nom": "Motorisation"},
    {"id": "Z-EMPENNAGE", "nom": "Empennage"},
    {"id": "Z-CABINE", "nom": "Cabine"},
    {"id": "Z-SYSTEMES", "nom": "Systemes (fluides, hydraulique)"},
])

step("Environnements", """
UNWIND $rows AS e
MERGE (x:Environnement {id:e.id}) SET x.nom=e.nom, x.description=e.description
""", rows=[
    {"id": "ENV-MARIN", "nom": "Atmosphere saline", "description": "Exposition brouillard salin / corrosion marine"},
    {"id": "ENV-HUMIDE", "nom": "Chaleur humide", "description": "Humidite et cyclage thermique"},
    {"id": "ENV-CRYO", "nom": "Basse temperature", "description": "Altitude croisiere, -55 degC"},
    {"id": "ENV-FLUIDES", "nom": "Fluides aeronautiques", "description": "Kerosene, hydraulique Skydrol, degivrant"},
    {"id": "ENV-CHAUD", "nom": "Haute temperature", "description": "Proximite moteur, > 200 degC"},
    {"id": "ENV-FATIGUE", "nom": "Fatigue vibratoire", "description": "Chargement cyclique haute frequence"},
    {"id": "ENV-FOUDRE", "nom": "Foudroiement", "description": "Impact de foudre, courants forts"},
])

step("Pieces", """
UNWIND $rows AS p
MATCH (z:ZoneAvion {id:p.zone})
MERGE (x:Piece {id:p.id})
  SET x.nom=p.nom, x.reference=p.ref, x.masse_kg=p.masse, x.criticite=p.crit
MERGE (x)-[:SITUEE_DANS]->(z)
""", rows=[
    {"id": "PC-001", "nom": "Lisse de voilure", "ref": "ABC-1001", "zone": "Z-VOILURE", "masse": 4.2, "crit": "elevee"},
    {"id": "PC-002", "nom": "Longeron de voilure", "ref": "ABC-1002", "zone": "Z-VOILURE", "masse": 38.0, "crit": "critique"},
    {"id": "PC-003", "nom": "Panneau de fuselage", "ref": "ABC-2001", "zone": "Z-FUSELAGE", "masse": 12.5, "crit": "elevee"},
    {"id": "PC-004", "nom": "Cadre de fuselage", "ref": "ABC-2002", "zone": "Z-FUSELAGE", "masse": 6.8, "crit": "elevee"},
    {"id": "PC-005", "nom": "Ferrure d attache moteur", "ref": "ABC-3001", "zone": "Z-MOTEUR", "masse": 22.0, "crit": "critique"},
    {"id": "PC-006", "nom": "Peau de caisson central", "ref": "ABC-4001", "zone": "Z-VOILURE", "masse": 55.0, "crit": "critique"},
    {"id": "PC-007", "nom": "Fut de train principal", "ref": "ABC-5001", "zone": "Z-TRAIN", "masse": 140.0, "crit": "critique"},
    {"id": "PC-008", "nom": "Panneau d empennage", "ref": "ABC-6001", "zone": "Z-EMPENNAGE", "masse": 18.0, "crit": "elevee"},
    {"id": "PC-009", "nom": "Aube de turbine", "ref": "ABC-3002", "zone": "Z-MOTEUR", "masse": 0.9, "crit": "critique"},
    {"id": "PC-010", "nom": "Joint de circuit hydraulique", "ref": "ABC-7002", "zone": "Z-SYSTEMES", "masse": 0.05, "crit": "elevee"},
    {"id": "PC-011", "nom": "Support structural ALM", "ref": "ABC-3003", "zone": "Z-MOTEUR", "masse": 1.8, "crit": "elevee"},
    {"id": "PC-012", "nom": "Support de cabine", "ref": "ABC-7001", "zone": "Z-CABINE", "masse": 1.1, "crit": "faible"},
])

step("Piece -> nuance", """
UNWIND $rows AS r
MATCH (p:Piece {id:r[0]}), (n:Nuance {id:r[1]})
MERGE (p)-[:FABRIQUEE_EN]->(n)
""", rows=[
    ["PC-001", "N-7075"], ["PC-002", "N-7050"], ["PC-003", "N-2198"], ["PC-004", "N-2024"],
    ["PC-005", "N-TI64"], ["PC-006", "N-IM7-8552"], ["PC-007", "N-300M"], ["PC-008", "N-T800-M21"],
    ["PC-009", "N-IN718"], ["PC-010", "N-FKM"], ["PC-011", "N-TI64"], ["PC-012", "N-PEEK"],
])

step("Piece -> etat", """
UNWIND $rows AS r
MATCH (p:Piece {id:r[0]}), (e:EtatMetallurgique {id:r[1]})
MERGE (p)-[:A_ETAT]->(e)
""", rows=[
    ["PC-001", "E-7075-T7351"], ["PC-002", "E-7050-T7451"], ["PC-003", "E-2198-T8"], ["PC-004", "E-2024-T351"],
    ["PC-005", "E-TI64-REC"], ["PC-007", "E-300M-THR"], ["PC-009", "E-IN718-STA"], ["PC-011", "E-TI64-REC"],
])

step("Piece -> procedes", """
UNWIND $rows AS r
MATCH (p:Piece {id:r[0]}), (pr:Procede {id:r[1]})
MERGE (p)-[:UTILISE_PROCEDE]->(pr)
""", rows=[
    ["PC-001", "PR-USIN"], ["PC-001", "PR-ANOD"], ["PC-001", "PR-PEINT"], ["PC-001", "PR-CND-RES"],
    ["PC-002", "PR-FORGE"], ["PC-002", "PR-USIN"], ["PC-002", "PR-SHOT"], ["PC-002", "PR-CND-US"],
    ["PC-003", "PR-USIN"], ["PC-003", "PR-SOUD"], ["PC-003", "PR-ANOD"], ["PC-003", "PR-PEINT"],
    ["PC-004", "PR-USIN"], ["PC-004", "PR-ANOD"], ["PC-004", "PR-RIVET"],
    ["PC-005", "PR-FORGE"], ["PC-005", "PR-USIN"], ["PC-005", "PR-CND-US"],
    ["PC-006", "PR-AFP"], ["PC-006", "PR-AUTOCLAVE"], ["PC-006", "PR-CND-US"],
    ["PC-007", "PR-FORGE"], ["PC-007", "PR-USIN"], ["PC-007", "PR-SHOT"], ["PC-007", "PR-CND-RES"],
    ["PC-008", "PR-AFP"], ["PC-008", "PR-AUTOCLAVE"], ["PC-008", "PR-COLLAGE"],
    ["PC-009", "PR-FONDERIE"], ["PC-009", "PR-CND-RX"],
    ["PC-011", "PR-ALM"], ["PC-011", "PR-USIN"], ["PC-011", "PR-CND-RX"],
])

step("Piece -> programmes", """
UNWIND $rows AS r
MATCH (p:Piece {id:r[0]}), (g:Programme {id:r[1]})
MERGE (p)-[:EQUIPE]->(g)
""", rows=[
    ["PC-001", "PRG-A320"], ["PC-001", "PRG-A330"], ["PC-002", "PRG-A320"], ["PC-002", "PRG-A330"],
    ["PC-003", "PRG-A220"], ["PC-003", "PRG-A350"], ["PC-004", "PRG-A320"],
    ["PC-005", "PRG-A350"], ["PC-005", "PRG-A330"], ["PC-006", "PRG-A350"],
    ["PC-007", "PRG-A330"], ["PC-007", "PRG-A400M"], ["PC-008", "PRG-A350"],
    ["PC-009", "PRG-A320"], ["PC-010", "PRG-A320"], ["PC-010", "PRG-A350"],
    ["PC-011", "PRG-A350"], ["PC-012", "PRG-A320"],
])

step("Piece -> environnements", """
UNWIND $rows AS r
MATCH (p:Piece {id:r[0]}), (e:Environnement {id:r[1]})
MERGE (p)-[:EXPOSEE_A]->(e)
""", rows=[
    ["PC-001", "ENV-MARIN"], ["PC-001", "ENV-FATIGUE"],
    ["PC-002", "ENV-MARIN"], ["PC-002", "ENV-FATIGUE"], ["PC-002", "ENV-CRYO"],
    ["PC-003", "ENV-HUMIDE"], ["PC-003", "ENV-CRYO"], ["PC-003", "ENV-FOUDRE"],
    ["PC-004", "ENV-HUMIDE"],
    ["PC-005", "ENV-CHAUD"], ["PC-005", "ENV-FATIGUE"],
    ["PC-006", "ENV-CRYO"], ["PC-006", "ENV-FOUDRE"], ["PC-006", "ENV-FLUIDES"],
    ["PC-007", "ENV-MARIN"], ["PC-007", "ENV-FLUIDES"], ["PC-007", "ENV-FATIGUE"],
    ["PC-008", "ENV-CRYO"], ["PC-008", "ENV-FOUDRE"],
    ["PC-009", "ENV-CHAUD"], ["PC-009", "ENV-FATIGUE"],
    ["PC-010", "ENV-FLUIDES"], ["PC-010", "ENV-CRYO"],
    ["PC-011", "ENV-CHAUD"], ["PC-011", "ENV-FATIGUE"],
])

step("Assemblages", """
UNWIND $rows AS a
MATCH (z:ZoneAvion {id:a.zone})
MERGE (x:Assemblage {id:a.id}) SET x.nom=a.nom, x.criticite=a.crit
MERGE (x)-[:SITUE_DANS]->(z)
""", rows=[
    {"id": "ASM-01", "nom": "Caisson de voilure", "zone": "Z-VOILURE", "crit": "critique"},
    {"id": "ASM-02", "nom": "Troncon de fuselage", "zone": "Z-FUSELAGE", "crit": "critique"},
    {"id": "ASM-03", "nom": "Pylone moteur", "zone": "Z-MOTEUR", "crit": "critique"},
    {"id": "ASM-04", "nom": "Train d atterrissage principal", "zone": "Z-TRAIN", "crit": "critique"},
    {"id": "ASM-05", "nom": "Plan horizontal arriere", "zone": "Z-EMPENNAGE", "crit": "elevee"},
])

step("Assemblage -> pieces", """
UNWIND $rows AS r
MATCH (a:Assemblage {id:r[0]}), (p:Piece {id:r[1]})
MERGE (a)-[:CONTIENT]->(p)
""", rows=[
    ["ASM-01", "PC-001"], ["ASM-01", "PC-002"], ["ASM-01", "PC-006"],
    ["ASM-02", "PC-003"], ["ASM-02", "PC-004"],
    ["ASM-03", "PC-005"], ["ASM-03", "PC-011"],
    ["ASM-04", "PC-007"], ["ASM-04", "PC-010"],
    ["ASM-05", "PC-008"],
])

# ======================================================================
# BLOC 3 : risques, substitutions, incompatibilites, execution, verifs
# ======================================================================

step("Risques", """
UNWIND $rows AS r
MERGE (x:Risque {id:r.id}) SET x.nom=r.nom, x.gravite=r.gravite, x.description=r.description
""", rows=[
    {"id": "RSK-CORR-GALV", "nom": "Corrosion galvanique", "gravite": "elevee",
     "description": "Couplage de metaux de potentiels differents en milieu humide"},
    {"id": "RSK-CSC", "nom": "Corrosion sous contrainte", "gravite": "critique",
     "description": "Fissuration sous contrainte statique en milieu corrosif"},
    {"id": "RSK-FATIGUE", "nom": "Fatigue", "gravite": "critique",
     "description": "Amorcage et propagation de fissures sous chargement cyclique"},
    {"id": "RSK-DELAM", "nom": "Delaminage", "gravite": "elevee",
     "description": "Decohesion inter-plis des composites"},
    {"id": "RSK-IMPACT", "nom": "Impact basse energie", "gravite": "elevee",
     "description": "Dommage non visible dans les composites"},
    {"id": "RSK-OXYD", "nom": "Oxydation haute temperature", "gravite": "moyenne",
     "description": "Degradation en temperature et atmosphere oxydante"},
    {"id": "RSK-VIEILL", "nom": "Vieillissement humide", "gravite": "moyenne",
     "description": "Absorption d eau et baisse des proprietes de la matrice"},
])

step("Nuance -> risques", """
UNWIND $rows AS r
MATCH (n:Nuance {id:r[0]}), (k:Risque {id:r[1]})
MERGE (n)-[:SENSIBLE_A]->(k)
""", rows=[
    ["N-7075", "RSK-CSC"], ["N-7075", "RSK-CORR-GALV"], ["N-7075", "RSK-FATIGUE"],
    ["N-7050", "RSK-CSC"], ["N-7050", "RSK-FATIGUE"],
    ["N-2024", "RSK-CORR-GALV"], ["N-2024", "RSK-FATIGUE"],
    ["N-2198", "RSK-CORR-GALV"],
    ["N-TI64", "RSK-FATIGUE"],
    ["N-300M", "RSK-CSC"], ["N-300M", "RSK-FATIGUE"],
    ["N-IN718", "RSK-OXYD"], ["N-IN718", "RSK-FATIGUE"],
    ["N-IM7-8552", "RSK-DELAM"], ["N-IM7-8552", "RSK-IMPACT"], ["N-IM7-8552", "RSK-VIEILL"],
    ["N-T800-M21", "RSK-DELAM"], ["N-T800-M21", "RSK-IMPACT"], ["N-T800-M21", "RSK-VIEILL"],
    ["N-GFRP-E", "RSK-VIEILL"],
    ["N-PEEK", "RSK-OXYD"],
])

step("Substitutions possibles", """
UNWIND $rows AS r
MATCH (a:Nuance {id:r[0]}), (b:Nuance {id:r[1]})
MERGE (a)-[s:SUBSTITUABLE_PAR]->(b) SET s.motif=r[2], s.statut='a valider'
""", rows=[
    ["N-7075", "N-7050", "Meilleure tenacite et tenue CSC en fortes epaisseurs"],
    ["N-2024", "N-2198", "Gain de masse, meilleure tolerance aux dommages"],
    ["N-7050", "N-7075", "Alternative en faibles epaisseurs"],
    ["N-IM7-8552", "N-T800-M21", "Alternative composite haute resistance"],
    ["N-PEEK", "N-PEKK", "Alternative thermoplastique haute temperature"],
    ["N-300M", "N-15-5PH", "Alternative en milieu corrosif (resistance moindre)"],
])

step("Incompatibilites", """
UNWIND $rows AS r
MATCH (a:Nuance {id:r[0]}), (b:Nuance {id:r[1]}), (k:Risque {id:r[2]})
MERGE (a)-[i:INCOMPATIBLE_AVEC]->(b) SET i.risque=k.nom, i.mitigation=r[3]
MERGE (i2:Nuance {id:r[1]})
""", rows=[
    ["N-7075", "N-TI64", "RSK-CORR-GALV", "Isolation par primaire et mastic, eviter le contact direct"],
    ["N-2024", "N-TI64", "RSK-CORR-GALV", "Isolation par primaire et mastic, eviter le contact direct"],
    ["N-2198", "N-TI64", "RSK-CORR-GALV", "Isolation par primaire et mastic, eviter le contact direct"],
    ["N-7050", "N-IM7-8552", "RSK-CORR-GALV", "Interposer une couche de verre isolante (carbone/alu)"],
    ["N-7075", "N-IM7-8552", "RSK-CORR-GALV", "Interposer une couche de verre isolante (carbone/alu)"],
    ["N-2024", "N-T800-M21", "RSK-CORR-GALV", "Interposer une couche de verre isolante (carbone/alu)"],
])

# ----------------------------------------------------------------------
# 3. EXECUTION
# ----------------------------------------------------------------------
def run():
    reset = "--reset" in sys.argv
    print("Connexion en cours...")
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        driver.verify_connectivity()
        print("Connexion au serveur reussie.")

        with driver.session(database=DATABASE) as session:
            if reset:
                confirm = input("ATTENTION : --reset efface TOUT le graphe. Taper OUI pour confirmer : ")
                if confirm.strip() != "OUI":
                    print("Annule.")
                    return
                session.run("MATCH (n) DETACH DELETE n").consume()
                print("Graphe efface.")

            for q in CONSTRAINTS:
                session.run(q).consume()
            print(f"{len(CONSTRAINTS)} contraintes/index crees ou deja presents.")

            for name, query, params in STEPS:
                try:
                    session.run(query, **params).consume()
                    print(f"  OK  {name}")
                except Exception as e:
                    print(f"  ERREUR  {name} : {e}")
                    raise

            verifier(session)


# ----------------------------------------------------------------------
# 4. VERIFICATIONS
# ----------------------------------------------------------------------
def verifier(session):
    print("\n=== VERIFICATIONS ===")

    print("\nNoeuds par type :")
    for r in session.run("MATCH (n) RETURN labels(n)[0] AS type, count(*) AS nb ORDER BY nb DESC"):
        print(f"  {r['type']:<20} {r['nb']}")

    print("\nRelations par type :")
    for r in session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS nb ORDER BY nb DESC"):
        print(f"  {r['type']:<22} {r['nb']}")

    print("\nNoeuds orphelins (sans relation) :")
    orphelins = list(session.run(
        "MATCH (n) WHERE NOT (n)--() RETURN labels(n)[0] AS type, coalesce(n.nom, n.id) AS nom"))
    if not orphelins:
        print("  Aucun.")
    for r in orphelins:
        print(f"  {r['type']} : {r['nom']}")

    print("\nExemple 1 - Pieces critiques et leur materiau :")
    for r in session.run("""
        MATCH (p:Piece {criticite:'critique'})-[:FABRIQUEE_EN]->(n:Nuance)
        RETURN p.nom AS piece, n.nom AS nuance ORDER BY piece"""):
        print(f"  {r['piece']:<30} {r['nuance']}")

    print("\nExemple 2 - Risques de corrosion galvanique (couples incompatibles) :")
    for r in session.run("""
        MATCH (a:Nuance)-[i:INCOMPATIBLE_AVEC]->(b:Nuance)
        RETURN a.nom AS a, b.nom AS b, i.mitigation AS mitigation"""):
        print(f"  {r['a']} / {r['b']} -> {r['mitigation']}")

    print("\nExemple 3 - Alternatives a une nuance (ici 7075) :")
    for r in session.run("""
        MATCH (a:Nuance {id:'N-7075'})-[s:SUBSTITUABLE_PAR]->(b:Nuance)
        RETURN b.nom AS alternative, s.motif AS motif"""):
        print(f"  {r['alternative']} : {r['motif']}")

    print("\nExemple 4 - Pieces exposees a un environnement chaud et leur nuance :")
    for r in session.run("""
        MATCH (p:Piece)-[:EXPOSEE_A]->(:Environnement {id:'ENV-CHAUD'}),
              (p)-[:FABRIQUEE_EN]->(n:Nuance)
        RETURN p.nom AS piece, n.nom AS nuance"""):
        print(f"  {r['piece']:<30} {r['nuance']}")

    print("\nExemple 5 - Fournisseurs non qualifies encore utilises :")
    for r in session.run("""
        MATCH (f:Fournisseur {qualifie:false})-[:FOURNIT]->(n:Nuance)
        RETURN f.nom AS fournisseur, n.nom AS nuance"""):
        print(f"  {r['fournisseur']} -> {r['nuance']}")

    print("\nVerifications terminees.")


if __name__ == "__main__":
    run()