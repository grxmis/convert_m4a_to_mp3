<?php
// Η σελίδα που θέλεις να κάνεις ping
 
$target_url ="https://convert-m4a-to-mp3.onrender.com";
// Ρυθμίσεις timeout
$timeout = 10; // δευτερόλεπτα

// Εκτέλεση του request
$ch = curl_init($target_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);

$response = curl_exec($ch);
$httpcode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$curl_error = curl_error($ch);

curl_close($ch);

// Αποθήκευση log (προαιρετικά)
file_put_contents("ping-log.txt", date("Y-m-d H:i:s") . " - HTTP $httpcode - $curl_error\n", FILE_APPEND);

// Επιστρέφουμε πάντα 200 στο cron-job
http_response_code(200);
echo "Ping completed. Target HTTP code: $httpcode";
?>
