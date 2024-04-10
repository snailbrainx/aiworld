<?php
$host = 'xxxxx';
$db   = 'aiworld';
$user = 'xxxx';
$pass = 'xxxx';
$dsn = "mysql:host=$host;dbname=$db";
$pdo = new PDO($dsn, $user, $pass);
$pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
$sql = "
    SELECT
        a1.entity,
        a1.position,
        a1.id,
        a1.thought,
        a1.talk,
        a1.time,
        a1.health_points,
        a1.ability AS ability_target,
        e.image,
        e.ability AS entity_ability
    FROM
        aiworld a1
    INNER JOIN
        (SELECT entity, MAX(time) max_time FROM aiworld GROUP BY entity) a2
    ON
        (a1.entity = a2.entity AND a1.time = a2.max_time)
    INNER JOIN entities e ON e.name = a1.entity";
$stmt = $pdo->query($sql);
$data = $stmt->fetchAll();
header('Content-Type: application/json');
echo json_encode($data);
?>
