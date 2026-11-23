<?php
ini_set('display_errors', '0');
error_reporting(E_ALL);
ob_start();
header('Content-Type: application/json; charset=utf-8');

function aiJsonResponse(array $payload, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    if (ob_get_level() > 0) {
        ob_clean();
    }
    $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    echo $json === false ? '{"error":"Erreur de sérialisation JSON."}' : $json;
}

set_error_handler(static function (int $severity, string $message, string $file, int $line): bool {
    if (!(error_reporting() & $severity)) {
        return false;
    }
    throw new ErrorException($message, 0, $severity, $file, $line);
});
set_exception_handler(static function (Throwable $exception): void {
    error_log('ai.php uncaught: ' . $exception->getMessage());
    aiJsonResponse(['error' => $exception->getMessage()], 500);
});
register_shutdown_function(static function (): void {
    $lastError = error_get_last();
    $fatalTypes = [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR, E_USER_ERROR, E_RECOVERABLE_ERROR];
    if ($lastError !== null && in_array($lastError['type'], $fatalTypes, true)) {
        error_log('ai.php fatal: ' . $lastError['message']);
        aiJsonResponse(['error' => $lastError['message']], 500);
    }
});

function handleAIRequest(): void
{
    require_once __DIR__ . '/config.php';
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        aiJsonResponse(['error' => 'Méthode non autorisée.'], 405);
        return;
    }

    $rawInput = file_get_contents('php://input');
    $input = json_decode($rawInput === false ? '' : $rawInput, true);
    $question = is_array($input) && isset($input['question']) && is_string($input['question']) ? trim($input['question']) : '';
    $questionLength = function_exists('mb_strlen') ? mb_strlen($question, 'UTF-8') : strlen($question);
    if ($question === '' || $questionLength > 1000) {
        aiJsonResponse(['error' => 'Question vide ou trop longue (1 000 caractères maximum).'], 400);
        return;
    }
    if (session_status() === PHP_SESSION_ACTIVE) {
        session_write_close();
    }

    $schema = <<<'SCHEMA'
NŒUDS (propriétés) :
Famille(id, nom) ; SousFamille(id, nom) ; Nuance(id, nom, statut, note, alias) ;
EtatMetallurgique(id, code, description) ; Propriete(id, nom, categorie) ; Unite(id, symbole, grandeur) ;
Mesure(id, valeur_min, valeur_typique, conditions, statut, date_validation) ; Norme(id, reference, titre, type, statut) ;
Fournisseur(id, nom, pays, qualifie) ; Procede(id, nom, type) ; Programme(id, nom, type) ; ZoneAvion(id, nom) ;
Environnement(id, nom, description) ; Piece(id, nom, reference, masse_kg, criticite) ; Assemblage(id, nom, criticite) ;
Risque(id, nom, description, gravite)
RELATIONS :
(SousFamille)-[:APPARTIENT_A]->(Famille) ; (Nuance)-[:APPARTIENT_A]->(SousFamille) ;
(Nuance)-[:A_POUR_ETAT]->(EtatMetallurgique) ; (Nuance)-[:COMPATIBLE_AVEC]->(Procede) ; (Nuance)-[:SENSIBLE_A]->(Risque) ;
(Nuance)-[:SUBSTITUABLE_PAR {statut, motif}]->(Nuance) ; (Nuance)-[:INCOMPATIBLE_AVEC {risque, mitigation}]->(Nuance) ;
(Nuance)-[:A_MESURE]->(Mesure) ; (EtatMetallurgique)-[:A_MESURE]->(Mesure) ; (Mesure)-[:MESURE_DE]->(Propriete) ;
(Propriete)-[:EXPRIMEE_EN]->(Unite) ; (Mesure)-[:SOURCE]->(Norme) ; (Nuance)-[:EST_CONFORME_A]->(Norme) ;
(EtatMetallurgique)-[:EST_CONFORME_A]->(Norme) ; (Fournisseur)-[:FOURNIT]->(Nuance) ;
(Piece)-[:FABRIQUEE_EN]->(Nuance) ; (Piece)-[:A_ETAT]->(EtatMetallurgique) ; (Piece)-[:UTILISE_PROCEDE]->(Procede) ;
(Piece)-[:EQUIPE]->(Programme) ; (Piece)-[:EXPOSEE_A]->(Environnement) ; (Piece)-[:SITUEE_DANS]->(ZoneAvion) ;
(Assemblage)-[:CONTIENT]->(Piece) ; (Assemblage)-[:SITUE_DANS]->(ZoneAvion)
NOTE : les textes sont stockés sans accents (ex. "Alliages d aluminium"). Pour chercher un texte, utilise
toLower(n.nom) CONTAINS toLower('...').
SCHEMA;

    $prompt = "Tu es un expert matériaux et Neo4j. Traduis la question en UNE requête Cypher de lecture.\n"
        . "Schéma du graphe :\n{$schema}\n\n"
        . "Règles : la requête commence par MATCH ; n'utilise que les labels et relations du schéma ; "
        . "pas de point-virgule ni de commentaire ; termine par LIMIT 25.\n\n"
        . "Exemples :\n"
        . "Q: Quelles sont les familles de matériaux ? -> MATCH (f:Famille) RETURN f LIMIT 25\n"
        . "Q: Quelles nuances sont des alliages de titane ? -> MATCH (n:Nuance)-[:APPARTIENT_A]->(:SousFamille)-[:APPARTIENT_A]->(f:Famille) WHERE toLower(f.nom) CONTAINS 'titane' RETURN n LIMIT 25\n"
        . "Q: Quels fournisseurs fournissent le Ti-6Al-4V ? -> MATCH (fo:Fournisseur)-[:FOURNIT]->(n:Nuance) WHERE toLower(n.nom) CONTAINS toLower('Ti-6Al-4V') RETURN fo, n LIMIT 25\n\n"
        . "Question : " . json_encode($question, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE) . "\n"
        . 'Réponds UNIQUEMENT avec ce JSON : {"explication": "...", "cypher": "MATCH ...", "conclusion": "..."}';

    if (!function_exists('curl_init')) {
        throw new RuntimeException('Extension cURL absente.');
    }
    $ch = curl_init('http://localhost:11434/api/generate');
    if ($ch === false) {
        throw new RuntimeException('Impossible d’initialiser la connexion au service IA.');
    }
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS => json_encode([
            'model' => getenv('OLLAMA_MODEL') ?: 'qwen2.5-coder:1.5b',
            'prompt' => $prompt,
            'stream' => false,
            'format' => 'json',
        ], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE),
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 60,
    ]);
    $response = curl_exec($ch);
    $curlError = curl_error($ch);
    $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($response === false || $httpCode !== 200) {
        error_log('ai.php Ollama HTTP ' . $httpCode . ': ' . $curlError);
        aiJsonResponse(['error' => 'Service IA indisponible ou délai dépassé. Réessayez dans un instant.'], 504);
        return;
    }

    $ollamaData = json_decode($response, true);
    $aiText = is_array($ollamaData) && is_string($ollamaData['response'] ?? null) ? $ollamaData['response'] : '';
    $parsed = json_decode($aiText, true);
    if (!is_array($parsed) && preg_match('/\{[\s\S]*\}/', $aiText, $matches)) {
        $parsed = json_decode($matches[0], true);
    }
    // Le petit modèle utilise parfois un autre nom de clé pour la requête.
    $aiCypher = null;
    if (is_array($parsed)) {
        foreach (['cypher', 'requete', 'requete_cypher', 'query', 'cypher_query'] as $key) {
            if (is_string($parsed[$key] ?? null) && trim($parsed[$key]) !== '') {
                $aiCypher = trim(rtrim(trim($parsed[$key]), ';'));
                break;
            }
        }
    }

    $raw = null;
    $cypher = '';
    $params = [];
    $explication = is_array($parsed) && is_string($parsed['explication'] ?? null) ? $parsed['explication'] : '';
    $conclusion = is_array($parsed) && is_string($parsed['conclusion'] ?? null) ? $parsed['conclusion'] : '';

    if ($aiCypher !== null) {
        try {
            assertReadOnlyCypher($aiCypher);
            $cypher = limitCypherResults($aiCypher, 25);
            $raw = cleanNeo4jValue(runQuery($cypher));
        } catch (Throwable $exception) {
            error_log('ai.php requête IA rejetée : ' . $exception->getMessage());
            $raw = null;
        }
    }

    if ($raw === null || $raw === []) {
        // Repli : recherche par mots-clés (paramétrée) dans les textes du graphe.
        $normalized = strtolower(iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $question) ?: $question);
        $words = array_values(array_unique(array_filter(
            preg_split('/[^a-z0-9\-]+/', $normalized) ?: [],
            static fn ($w) => strlen($w) >= 4 && !in_array($w, ['quels', 'quelles', 'quel', 'quelle', 'sont', 'avec', 'dans', 'pour', 'leur', 'leurs', 'materiau', 'materiaux', 'liste', 'donne', 'moi'], true)
        )));
        if ($words) {
            $fallbackCypher = 'MATCH (n) WHERE any(w IN $words WHERE toLower(coalesce(n.nom, n.titre, n.reference, n.code, \'\')) CONTAINS w) RETURN n LIMIT 25';
            $fallbackRaw = cleanNeo4jValue(runQuery($fallbackCypher, ['words' => $words]));
            if ($raw === null || $fallbackRaw !== []) {
                $raw = $fallbackRaw;
                $cypher = $fallbackCypher;
                $params = ['words' => $words];
                $explication = ($aiCypher === null ? "L'IA n'a pas produit de requête exploitable. " : "La requête de l'IA n'a rien donné. ")
                    . 'Recherche par mots-clés : ' . implode(', ', $words) . '.';
                $conclusion = 'Résultats issus d’une recherche textuelle ; reformulez la question pour une réponse plus précise.';
            }
        }
        $raw = $raw ?? [];
    }

    aiJsonResponse([
        'explication' => $explication,
        'cypher' => $cypher,
        'conclusion' => $conclusion,
        'raw' => $raw,
        'count' => count($raw),
    ]);
}

try {
    handleAIRequest();
} catch (InvalidArgumentException $exception) {
    aiJsonResponse(['error' => $exception->getMessage()], 400);
} catch (Throwable $exception) {
    error_log('ai.php: ' . $exception->getMessage());
    aiJsonResponse(['error' => $exception->getMessage()], 500);
}
