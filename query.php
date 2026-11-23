<?php
ini_set('display_errors', '0');
error_reporting(E_ALL);
ob_start();
header('Content-Type: application/json; charset=utf-8');

function queryJsonResponse(array $payload, int $status = 200): void
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
    error_log('query.php uncaught: ' . $exception->getMessage());
    queryJsonResponse(['error' => $exception->getMessage()], 500);
});
register_shutdown_function(static function (): void {
    $lastError = error_get_last();
    $fatalTypes = [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR, E_USER_ERROR, E_RECOVERABLE_ERROR];
    if ($lastError !== null && in_array($lastError['type'], $fatalTypes, true)) {
        error_log('query.php fatal: ' . $lastError['message']);
        queryJsonResponse(['error' => $lastError['message']], 500);
    }
});

try {
    require_once __DIR__ . '/config.php';
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        queryJsonResponse(['error' => 'Méthode non autorisée.'], 405);
    } else {
        $rawInput = file_get_contents('php://input');
        $input = json_decode($rawInput === false ? '' : $rawInput, true);
        if (!is_array($input) || !isset($input['cypher']) || !is_string($input['cypher'])) {
            queryJsonResponse(['error' => 'Corps JSON invalide ou requête absente.'], 400);
        } else {
            $cypher = trim($input['cypher']);
            try {
                assertReadOnlyCypher($cypher);
                $cypher = limitCypherResults($cypher);
                $results = cleanNeo4jValue(runQuery($cypher));
                queryJsonResponse(['results' => $results]);
            } catch (InvalidArgumentException $exception) {
                queryJsonResponse(['error' => $exception->getMessage()], 400);
            }
        }
    }
} catch (Throwable $exception) {
    error_log('query.php: ' . $exception->getMessage());
    queryJsonResponse(['error' => $exception->getMessage()], 500);
}
