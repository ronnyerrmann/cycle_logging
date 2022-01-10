<html>
<head>
  <title>Cycle Rides Results</title>
</head>
<body>
<h1>Cycle Rides Results</h1>
<?php
  $root_dir = $_SERVER['DOCUMENT_ROOT'];
  //echo "test ".$root_dir;
  // Path to the settings file: one level above the server settings -> can't be accessed from the internet to keep the password secure, however, needs root access to put the file, tested with Apache
  $mysqlsettingsfile = $root_dir."/../fahrrad_mysql.params";
  
  function format_time($t,$f=':') // t = seconds, f = separator 
  {
     return sprintf("%02d%s%02d%s%02d", floor($t/3600), $f, ($t/60)%60, $f, $t%60);
  }
  
  // create short variable names
  $searchtype=$_POST['searchtype'];
  $startdate=trim($_POST['startdate']);
  $enddate=trim($_POST['enddate']);

  if (!$searchtype || !$startdate || !$enddate) {
     echo 'You have not entered search details.  Please go back and try again.';
     exit;
  }

  if (!get_magic_quotes_gpc()){
    $searchtype = addslashes($searchtype);
    $startdate = addslashes($startdate);
    $enddate = addslashes($enddate);
  }
  echo "<p>searchtype: ".$searchtype."</p>";
  switch ($searchtype) {
   case "Days":
     $searchtype="fahrrad_rides";
     $extratxt="Day";
     $datekey="Date";
     break;
  case "Weeks":
     $searchtype="fahrrad_weekly_summary";
     $extratxt="Week";
     $datekey="Week_starting_on";
     break;
  case "Months":
     $searchtype="fahrrad_monthly_summary";
     $extratxt="Month";
     $datekey="Month_starting_on";
     break;
  case "Years":
     $searchtype="fahrrad_yearly_summary";
     $extratxt="Year";
     $datekey="Year_starting_on";
     break;
  default:
     echo 'Somthing went wrong.  Please go back and try again.';
     exit;
  }
  $mysql_Settings = [
     "host" => 'localhost',
     "user" => "yourusername",
     "password" => "yourpassword",
     "db" => "",
  ];
  // better: save it as variable in another script and include that script: https://stackoverflow.com/questions/17020651/how-to-hide-protect-password-details-in-php/17021458#17021458
  $myfile = fopen($root_dir."../fahrrad_mysql.params", "r") or die("Unable to open file!");
  while(!feof($myfile)) {
     $arrayString = explode("=", fgets($myfile) );
     //Print_r($arrayString);
     if (count($arrayString)==2) {
        $mysql_Settings[trim($arrayString[0])] = trim($arrayString[1]);
     }
  }
  fclose($myfile);

  @ $db = new mysqli($mysql_Settings["host"], $mysql_Settings["user"], $mysql_Settings["password"], $mysql_Settings["db"]);
  if (mysqli_connect_errno()) {
     echo 'Error: Could not connect to database.  Please try again later.';
     exit;
  }

  $query = "SELECT ".$datekey." AS Date, ".$extratxt."KM AS KM, ".$extratxt."Seconds AS Seconds, ".$extratxt."KMH AS KMH FROM ".$searchtype." WHERE ".$datekey." BETWEEN '".$startdate."' AND '".$enddate."'";
  //echo "<p>Query: ".$query."</p>";
  $result = $db->query($query);

  $num_results = $result->num_rows;

  echo "<p>Number of entries found: ".$num_results."</p>";

  for ($i=0; $i <$num_results; $i++) {
     $row = $result->fetch_assoc();
     echo "<p><strong>".($i+1).". Date: ";
     echo htmlspecialchars(stripslashes($row['Date']));
     echo "</strong><br />Distance [km]: ";
     echo stripslashes($row['KM']);
     echo "</strong><br />Time [s -> hh:mm:ss]: ";
     echo stripslashes($row['Seconds'])."  ->  ".format_time($row['Seconds']);
     echo "<br />Speed [km/h]: ";
     echo stripslashes($row['KMH']);
     echo "</p>";
  }

  $result->free();
  $db->close();

?>
</body>
</html>
