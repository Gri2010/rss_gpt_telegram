<?php
header('Content-Type: application/json; charset=utf-8');

// Принимаем JSON из формы
$raw = file_get_contents('php://input');
$data = json_decode($raw, true);

if (!$data || empty($data['name']) || empty($data['phone'])) {
    echo json_encode(['ok' => false, 'error' => 'Не заполнены обязательные поля']);
    exit;
}

// ═══ КУДА ОТПРАВЛЯТЬ ЗАЯВКИ ═══
$to = 'info@zelbio.ru';

// Данные из формы
$name    = htmlspecialchars(trim($data['name']),    ENT_QUOTES, 'UTF-8');
$phone   = htmlspecialchars(trim($data['phone']),   ENT_QUOTES, 'UTF-8');
$company = htmlspecialchars(trim($data['company'] ?? ''), ENT_QUOTES, 'UTF-8');
$type    = htmlspecialchars(trim($data['type']    ?? ''), ENT_QUOTES, 'UTF-8');
$form    = $data['form'] ?? 'home';

$formLabels = [
    'home' => 'Дом',
    'biz'  => 'Бизнес',
    'gov'  => 'Учреждение',
];
$formLabel = $formLabels[$form] ?? $form;

// Тема письма
$subject = '=?UTF-8?B?' . base64_encode('Новая заявка ZelBio — ' . $formLabel) . '?=';

// Тело письма
$body  = "Новая заявка с сайта ZelBio\n";
$body .= str_repeat('─', 40) . "\n\n";
$body .= "Тип заявки : $formLabel\n";
$body .= "Имя        : $name\n";
$body .= "Телефон    : $phone\n";
if ($company) $body .= "Компания   : $company\n";
if ($type)    $body .= "Тип        : $type\n";
$body .= "\n" . str_repeat('─', 40) . "\n";
$body .= "Время: " . date('d.m.Y H:i') . " (МСК)\n";

// Заголовки письма
$headers  = "From: =?UTF-8?B?" . base64_encode('Сайт ZelBio') . "?= <noreply@zelbio.ru>\r\n";
$headers .= "Reply-To: $phone\r\n";
$headers .= "Content-Type: text/plain; charset=UTF-8\r\n";
$headers .= "Content-Transfer-Encoding: base64\r\n";

$ok = mail($to, $subject, base64_encode($body), $headers);

echo json_encode(['ok' => (bool)$ok]);
