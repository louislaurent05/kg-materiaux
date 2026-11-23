<?php
/** Neo4j configuration and shared helpers. Environment variables override the
 * original working defaults so existing deployments keep working unchanged.
 */

/** Charge le fichier .env (clé=valeur) situé à côté de ce fichier. */
function loadEnvFile(): void
{
    static $done = false;
    if ($done) {
        return;
    }
    $done = true;
    $path = __DIR__ . '/.env';
    if (!is_file($path)) {
        return;
    }
    foreach (file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#' || strpos($line, '=') === false) {
            continue;
        }
        [$key, $val] = explode('=', $line, 2);
        $key = trim($key);
        $val = trim(trim($val), "\"'");
        if ($key !== '' && getenv($key) === false) {
            putenv("$key=$val");
        }
    }
}

function configValue(string $name, string $default): string
{
    loadEnvFile();
    $value = getenv($name);
    return ($value === false || $value === '') ? $default : $value;
}

function loadDependencies(): void
{
    static $loaded = false;
    if ($loaded) {
        return;
    }

    $autoload = __DIR__ . '/vendor/autoload.php';
    if (!is_file($autoload)) {
        throw new RuntimeException('Dépendances Composer absentes : vendor/autoload.php introuvable. Exécutez composer install dans le dossier de l’application.');
    }
    require_once $autoload;
    $loaded = true;
}

function requiredPassword(): string
{
    $password = configValue('NEO4J_PASSWORD', '');
    if ($password === '') {
        throw new RuntimeException('NEO4J_PASSWORD manquant : renseignez-le dans le fichier .env du projet.');
    }
    return $password;
}

function getClient()
{
    loadDependencies();

    // Valeurs de repli reprises de la configuration originale; les variables
    // d’environnement restent prioritaires pour permettre la rotation des secrets.
    $uri = configValue('NEO4J_URI', 'neo4j+s://6761ef10.databases.neo4j.io');
    $user = configValue('NEO4J_USER', '6761ef10');
    $password = requiredPassword();
    $scheme = parse_url($uri, PHP_URL_SCHEME);
    if (!is_string($scheme) || !in_array($scheme, ['neo4j+s', 'neo4j+ssc', 'bolt+s', 'bolt+ssc'], true)) {
        throw new RuntimeException('URI Neo4j invalide : le schéma de connexion doit utiliser TLS.');
    }

    if (!class_exists(\Laudis\Neo4j\ClientBuilder::class) || !class_exists(\Laudis\Neo4j\Authentication\Authenticate::class)) {
        throw new RuntimeException('Le client Laudis Neo4j est absent ou incompatible. Vérifiez composer install et composer.lock.');
    }

    return \Laudis\Neo4j\ClientBuilder::create()
        ->withDriver($scheme, $uri, \Laudis\Neo4j\Authentication\Authenticate::basic($user, $password))
        ->withDefaultDriver($scheme)
        ->build();
}

/**
 * Exécute une requête Cypher via la Query API HTTPS de Neo4j Aura (port 443).
 * Le protocole Bolt (port 7687) est bloqué sur ce réseau, d'où ce passage par HTTPS.
 * Retourne une liste de lignes associatives [champ => valeur].
 */
function runQuery(string $cypher, array $params = []): array
{
    if (!function_exists('curl_init')) {
        throw new RuntimeException('Extension cURL absente de PHP.');
    }
    $uri = configValue('NEO4J_URI', 'neo4j+s://6761ef10.databases.neo4j.io');
    $host = parse_url($uri, PHP_URL_HOST);
    if (!is_string($host) || $host === '') {
        throw new RuntimeException('URI Neo4j invalide.');
    }
    $user = configValue('NEO4J_USER', '6761ef10');
    $password = requiredPassword();
    $database = configValue('NEO4J_DATABASE', '6761ef10');

    $body = ['statement' => $cypher];
    if ($params) {
        $body['parameters'] = $params;
    }
    $ch = curl_init('https://' . $host . '/db/' . rawurlencode($database) . '/query/v2');
    $options = [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 10,
        CURLOPT_TIMEOUT => 30,
        CURLOPT_USERPWD => $user . ':' . $password,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Accept: application/json'],
        CURLOPT_POSTFIELDS => json_encode($body, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE),
    ];
    // Utilise le magasin de certificats de Windows (WAMP n'a pas de bundle CA).
    if (defined('CURLSSLOPT_NATIVE_CA')) {
        $options[CURLOPT_SSL_OPTIONS] = CURLSSLOPT_NATIVE_CA;
    }
    curl_setopt_array($ch, $options);
    $response = curl_exec($ch);
    $curlError = curl_error($ch);
    $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($response === false) {
        throw new RuntimeException('Connexion à Neo4j Aura impossible : ' . $curlError);
    }
    $data = json_decode($response, true);
    if ($status === 401) {
        throw new RuntimeException('Neo4j : identifiant ou mot de passe refusé.');
    }
    if (!is_array($data)) {
        throw new RuntimeException('Réponse Neo4j illisible (HTTP ' . $status . ').');
    }
    if (!empty($data['errors'])) {
        $error = $data['errors'][0];
        throw new RuntimeException('Neo4j : ' . ($error['message'] ?? 'erreur inconnue') . (isset($error['code']) ? ' (' . $error['code'] . ')' : ''));
    }
    if ($status >= 400) {
        throw new RuntimeException('Neo4j : erreur HTTP ' . $status . '.');
    }

    $fields = $data['data']['fields'] ?? [];
    $records = [];
    foreach ($data['data']['values'] ?? [] as $row) {
        $record = [];
        foreach ($fields as $i => $field) {
            $record[$field] = $row[$i] ?? null;
        }
        $records[] = $record;
    }
    return $records;
}

/** Bloque les opérations d'écriture et les requêtes multiples évidentes. */
function assertReadOnlyCypher(string $cypher): void
{
    $query = trim($cypher);
    if ($query === '' || strlen($query) > 10000 || preg_match('/[;`]|\/\/|\/\*|\*\//', $query)) {
        throw new InvalidArgumentException('Requête vide, trop longue ou syntaxe non autorisée.');
    }
    if (!preg_match('/^(?:OPTIONAL\s+)?MATCH\b/i', $query)) {
        throw new InvalidArgumentException('Seules les requêtes Cypher de lecture commençant par MATCH sont autorisées.');
    }
    if (preg_match('/\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|CALL|USE|FOREACH|GRANT|DENY|REVOKE)\b/i', $query)) {
        throw new InvalidArgumentException('La requête contient une opération non autorisée.');
    }
}

function limitCypherResults(string $cypher, int $maximum = 100): string
{
    if (preg_match('/\bLIMIT\s+(\d+)\s*$/i', trim($cypher), $match)) {
        return preg_replace('/\bLIMIT\s+\d+\s*$/i', 'LIMIT ' . min((int)$match[1], $maximum), trim($cypher));
    }
    return rtrim($cypher) . ' LIMIT ' . $maximum;
}

function cleanNeo4jValue($value)
{
    if (is_array($value)) {
        $out = [];
        foreach ($value as $key => $item) {
            $out[$key] = cleanNeo4jValue($item);
        }
        return $out;
    }
    if (is_object($value)) {
        if (method_exists($value, 'toArray')) {
            return cleanNeo4jValue($value->toArray());
        }
        if (method_exists($value, 'getProperties')) {
            return [
                'labels' => method_exists($value, 'getLabels') ? $value->getLabels() : [],
                'properties' => cleanNeo4jValue($value->getProperties()),
            ];
        }
        if ($value instanceof JsonSerializable) {
            return cleanNeo4jValue($value->jsonSerialize());
        }
        return '[valeur Neo4j non sérialisable]';
    }
    if (is_resource($value)) {
        return '[ressource]';
    }
    return $value;
}
