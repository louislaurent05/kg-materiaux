<?php
require_once 'config.php';

// Test de connexion au démarrage
try {
    $count = runQuery("MATCH (n) RETURN count(n) as total");
    $totalNodes = $count[0]['total'] ?? 0;
    $connected = true;
} catch (Exception $e) {
    $connected = false;
    $errorMsg = $e->getMessage();
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Graph - Matériaux</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; }
        body { background: #0f172a; color: #e2e8f0; padding: 20px; }
        h1 { color: #38bdf8; margin-bottom: 10px; }
        .status { padding: 10px; border-radius: 8px; margin-bottom: 20px; font-weight: bold; }
        .status.ok { background: #064e3b; color: #6ee7b7; }
        .status.err { background: #7f1d1d; color: #fca5a5; }
        .panel { background: #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }
        h2 { color: #38bdf8; margin-bottom: 15px; font-size: 1.2em; }
        textarea { width: 100%; height: 80px; background: #0f172a; color: #e2e8f0; border: 1px solid #475569; border-radius: 8px; padding: 10px; font-family: 'Consolas', monospace; font-size: 14px; resize: vertical; }
        button { background: #0ea5e9; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        button:hover { background: #0284c7; }
        .examples { margin-top: 10px; font-size: 0.85em; color: #94a3b8; }
        .examples span { background: #334155; padding: 4px 8px; border-radius: 4px; margin-right: 5px; cursor: pointer; display: inline-block; margin-bottom: 5px; }
        .examples span:hover { background: #475569; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 0.9em; }
        th { background: #334155; padding: 10px; text-align: left; color: #38bdf8; }
        td { padding: 10px; border-bottom: 1px solid #334155; }
        tr:hover { background: #1e293b; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 0.75em; font-weight: bold; }
        .badge-node { background: #7c3aed; color: white; }
        .badge-rel { background: #ea580c; color: white; }
        .loading { display: none; color: #38bdf8; margin-top: 10px; }
        .error { display: none; background: #7f1d1d; color: #fca5a5; padding: 10px; border-radius: 8px; margin-top: 10px; }
        .cypher-box { background: #000; color: #4ade80; padding: 10px; border-radius: 6px; font-family: monospace; margin: 10px 0; white-space: pre-wrap; font-size: 0.9em; }
        input[type="text"] { width: 100%; padding: 12px; background: #0f172a; border: 1px solid #475569; border-radius: 8px; color: white; font-size: 1em; }
        .ai-section { background: #0f172a; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    </style>
</head>
<body>

    <h1>🔬 Knowledge Graph - Matériaux</h1>
    <p style="color:#94a3b8; margin-bottom:15px;">Ontologie RDF + Données Neo4j Aura</p>

    <div class="status <?php echo $connected ? 'ok' : 'err'; ?>">
        <?php echo $connected ? "✅ Connecté à Neo4j Aura - $totalNodes nœuds détectés" : "❌ Erreur : " . htmlspecialchars($errorMsg); ?>
    </div>

    <!-- TERMINAL CYPHER -->
    <div class="panel">
        <h2>💻 Terminal Cypher</h2>
        <textarea id="cypherInput" placeholder="MATCH (n) RETURN n LIMIT 25">MATCH (n) RETURN n LIMIT 25</textarea>
        <button onclick="executeQuery()">▶ Exécuter</button>
        <div class="examples">
            Exemples :
            <span onclick="setQuery('MATCH (f:Famille) RETURN f')">Familles</span>
            <span onclick="setQuery('MATCH (s:SousFamille) RETURN s')">Sous-familles</span>
            <span onclick="setQuery('MATCH (n:Nuance) RETURN n')">Nuances</span>
            <span onclick="setQuery('MATCH (u:Unite) RETURN u')">Unités</span>
            <span onclick="setQuery('MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 20')">Relations</span>
        </div>
        <div id="loading" class="loading">⏳ Exécution en cours...</div>
        <div id="errorBox" class="error"><strong>❌ Erreur :</strong> <span id="errorMsg"></span></div>
    </div>

    <!-- RÉSULTATS -->
    <div class="panel">
        <h2>📊 Résultats <span id="resultCount" style="color:#94a3b8; font-size:0.8em;"></span></h2>
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Label</th>
                    <th>ID</th>
                    <th>Nom</th>
                    <th>Propriétés</th>
                </tr>
            </thead>
            <tbody id="resultsBody">
                <tr><td colspan="5" style="text-align:center; color:#64748b;">Aucun résultat pour le moment</td></tr>
            </tbody>
        </table>
    </div>

    <!-- ASSISTANT IA -->
    <div class="panel">
        <h2>🤖 Assistant IA - Pose ta question en français</h2>
        <p style="color:#94a3b8; font-size:0.9em; margin-bottom:10px;">
            Ex: "Quels matériaux ont une densité supérieure à 5 g/cm³ ?"
        </p>
        <input type="text" id="aiQuestion" placeholder="Ex: Quelles sont les familles de matériaux ?" onkeypress="if(event.key==='Enter') askAI()">
        <button onclick="askAI()">🚀 Demander à l'IA</button>
        <div id="aiLoading" class="loading">🤖 L'IA réfléchit...</div>

        <!-- RÉPONSE IA STRUCTURÉE -->
        <div id="aiResponse" style="display:none; margin-top:20px;">
            <!-- 1. Explication -->
            <div class="ai-section" style="border-left:4px solid #38bdf8;">
                <strong style="color:#38bdf8;">💡 1. Explication de l'analyse :</strong>
                <p id="aiExplication" style="margin-top:8px; color:#cbd5e1; line-height:1.5;"></p>
            </div>

            <!-- 2. Requête Cypher -->
            <div class="ai-section" style="border-left:4px solid #4ade80;">
                <strong style="color:#4ade80;">🔧 2. Requête Cypher générée :</strong>
                <div id="aiCypher" class="cypher-box" style="margin-top:8px;"></div>
            </div>

            <!-- 3. Résultats -->
            <div style="margin-bottom:15px;">
                <strong style="color:#fbbf24;">📊 3. Résultats obtenus :</strong>
                <div id="aiResultCount" style="color:#94a3b8; font-size:0.9em; margin:5px 0;"></div>
            </div>

            <!-- 4. Conclusion -->
            <div class="ai-section" style="border-left:4px solid #f472b6;">
                <strong style="color:#f472b6;">🎯 4. Conclusion métier :</strong>
                <p id="aiConclusion" style="margin-top:8px; color:#e2e8f0; line-height:1.6; font-style:italic;"></p>
            </div>
        </div>

        <div id="aiErrorBox" class="error"><strong>❌ Erreur IA :</strong> <span id="aiErrorMsg"></span></div>
    </div>

<script>
// ============================================
// FONCTION UNIQUE D'AFFICHAGE DES RÉSULTATS
// ============================================
function displayResults(data) {
    const tbody = document.getElementById('resultsBody');
    tbody.innerHTML = '';

    if (!data || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#64748b;">Aucun résultat</td></tr>';
        document.getElementById('resultCount').textContent = '';
        return;
    }

    document.getElementById('resultCount').textContent = `(${data.length} résultat${data.length > 1 ? 's' : ''})`;

    const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

    data.forEach(row => {
        // Une ligne = {champ: valeur}. On repère le nœud et l'éventuelle relation.
        const values = (row && typeof row === 'object') ? Object.values(row) : [];
        const isNode = v => v && typeof v === 'object' && Array.isArray(v.labels);
        const isRel = v => v && typeof v === 'object' && typeof v.type === 'string' && 'startNodeElementId' in v;
        const rel = values.find(isRel);
        const nodes = values.filter(isNode);

        let item, labels, typeBadge;
        if (rel) {
            item = rel;
            const from = nodes[0]?.properties?.nom || nodes[0]?.properties?.id || '?';
            const to = nodes[1]?.properties?.nom || nodes[1]?.properties?.id || '?';
            labels = [`${rel.type} (${from} → ${to})`];
            typeBadge = '<span class="badge badge-rel">RELATION</span>';
        } else if (nodes.length) {
            item = nodes[0];
            labels = item.labels;
            typeBadge = '<span class="badge badge-node">NŒUD</span>';
        } else {
            item = row;
            labels = ['valeur'];
            typeBadge = '<span class="badge badge-node">VALEUR</span>';
        }
        const props = item.properties || item;
        const id = props.id || props.identifiant || '?';
        const nom = props.nom || props.name || props.reference || props.code || id;
        const json = JSON.stringify(props);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${typeBadge}</td>
            <td>${esc(labels.join(', '))}</td>
            <td>${esc(id)}</td>
            <td>${esc(nom)}</td>
            <td><code style="font-size:0.8em; color:#94a3b8;">${esc(json.substring(0, 80))}${json.length > 80 ? '...' : ''}</code></td>
        `;
        tbody.appendChild(tr);
    });
}

// ============================================
// TERMINAL CYPHER MANUEL
// ============================================
async function parseJsonResponse(response) {
    const raw = await response.text();
    try {
        return JSON.parse(raw);
    } catch (error) {
        const preview = raw.slice(0, 300);
        throw new Error(`Réponse non JSON (HTTP ${response.status}) : ${preview || '(réponse vide)'}`);
    }
}

async function executeQuery() {
    const cypher = document.getElementById('cypherInput').value.trim();
    if (!cypher) return alert('Entre une requête Cypher !');

    document.getElementById('loading').style.display = 'block';
    document.getElementById('errorBox').style.display = 'none';

    try {
        const response = await fetch('query.php', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({cypher: cypher})
        });
        const data = await parseJsonResponse(response);
        document.getElementById('loading').style.display = 'none';

        if (data.error) {
            document.getElementById('errorBox').style.display = 'block';
            document.getElementById('errorMsg').textContent = data.error;
            return;
        }

        displayResults(data.results || data);
    } catch (e) {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('errorBox').style.display = 'block';
        document.getElementById('errorMsg').textContent = e.message;
    }
}

// ============================================
// ASSISTANT IA (UNE SEULE FOIS !)
// ============================================
async function askAI() {
    const question = document.getElementById('aiQuestion').value.trim();
    if (!question) return alert('Pose une question !');

    document.getElementById('aiLoading').style.display = 'block';
    document.getElementById('aiResponse').style.display = 'none';
    document.getElementById('aiErrorBox').style.display = 'none';

    try {
        const response = await fetch('ai.php', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({question: question})
        });
        const data = await parseJsonResponse(response);
        document.getElementById('aiLoading').style.display = 'none';

        if (data.error) {
            document.getElementById('aiErrorBox').style.display = 'block';
            document.getElementById('aiErrorMsg').textContent = data.error;
            return;
        }

        // Afficher les 4 sections
        document.getElementById('aiResponse').style.display = 'block';
        document.getElementById('aiExplication').innerText = data.explication || 'Aucune explication générée';
        document.getElementById('aiCypher').innerText = data.cypher || '';
        document.getElementById('aiConclusion').innerText = data.conclusion || 'Aucune conclusion générée';

        // Afficher les résultats dans le tableau principal
        if (data.raw && data.raw.length > 0) {
            displayResults(data.raw);
            document.getElementById('aiResultCount').textContent = data.count + ' résultat(s) trouvé(s) — voir tableau ci-dessus ↑';
        } else {
            document.getElementById('resultsBody').innerHTML = '<tr><td colspan="5" style="text-align:center; color:#64748b;">Aucun résultat trouvé</td></tr>';
            document.getElementById('aiResultCount').textContent = '0 résultat';
        }

    } catch (e) {
        document.getElementById('aiLoading').style.display = 'none';
        document.getElementById('aiErrorBox').style.display = 'block';
        document.getElementById('aiErrorMsg').textContent = 'Erreur: ' + e.message;
    }
}

function setQuery(q) {
    document.getElementById('cypherInput').value = q;
}
</script>
</body>
</html>