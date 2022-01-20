<?php   // general settings and functions
  $root_dir = $_SERVER['DOCUMENT_ROOT'];
  // Path to the settings file: one level above the server settings -> can't be accessed from the internet to keep the password secure, however, needs root access to put the file, tested with Apache
  $mysql_settingsfile = $root_dir."/../fahrrad_mysql.params";
  
  function format_time($t,$f=':') // t = seconds, f = separator 
  {
     return sprintf("%02d%s%02d%s%02d", floor($t/3600), $f, ($t/60)%60, $f, $t%60);
  }
  
  // initiate the DB connection
  $no_problem = True;
  $error_msg = '';
  // read the settings file
  $mysql_Settings = [
     "host" => 'localhost',
     "user" => "yourusername",
     "password" => "yourpassword",
     "db" => "",
  ];
  // better: save it as variable in another script and include that script: https://stackoverflow.com/questions/17020651/how-to-hide-protect-password-details-in-php/17021458#17021458 
  if (file_exists($mysql_settingsfile)) {   
    $myfile = fopen($mysql_settingsfile, "r") or die("Unable to open file!");
    while(!feof($myfile)) {
      $arrayString = explode("=", fgets($myfile) );
      //Print_r($arrayString);
      if (count($arrayString)==2) {
        $mysql_Settings[trim($arrayString[0])] = trim($arrayString[1]);
      }
    }
    fclose($myfile);
  }
  @ $db = new mysqli($mysql_Settings["host"], $mysql_Settings["user"], $mysql_Settings["password"], $mysql_Settings["db"]);
  if (mysqli_connect_errno()) {
     $error_msg .=  'Error: Could not connect to database.  Please try again later.';
     $no_problem = False;
  }
?>

<?php   // do the query
  if ($_SERVER['REQUEST_METHOD'] == 'POST') { 
    $is_post = True;
    // create short variable names
    $searchtype=$_POST['searchtype'];
    $startdate=trim($_POST['startdate']);
    $enddate=trim($_POST['enddate']);

    if (!$searchtype || !$startdate || !$enddate) {
       $error_msg .= 'You have not entered all search details.  Please check and try again. ';
       $no_problem = False;
    }

    if (!get_magic_quotes_gpc()){
      $searchtype = addslashes($searchtype);
      $startdate = addslashes($startdate);
      $enddate = addslashes($enddate);
    }
    //echo "<p>searchtype: ".$searchtype."</p>";
    switch ($searchtype) {
     case "Days":
       $searchtable="fahrrad_rides";
       $extratxt="Day";
       $datekey="Date";
       break;
    case "Weeks":
       $searchtable="fahrrad_weekly_summary";
       $extratxt="Week";
       $datekey="Week_starting_on";
       break;
    case "Months":
       $searchtable="fahrrad_monthly_summary";
       $extratxt="Month";
       $datekey="Month_starting_on";
       break;
    case "Years":
       $searchtable="fahrrad_yearly_summary";
       $extratxt="Year";
       $datekey="Year_starting_on";
       break;
    default:
       $error_msg .= 'Somthing went wrong with input "'.$searchtype.'". Expected: "Days", "Weeks", "Months", or "Years". Please check and try again.';
       $no_problem = False;
    }
    
    if ($no_problem) {
      // not save from injections:
      //$query = "SELECT ".$datekey." AS Date, ".$extratxt."KM AS KM, ".$extratxt."Seconds AS Seconds, ".$extratxt."KMH AS KMH FROM ".$searchtable." WHERE ".$datekey." BETWEEN '".$startdate."' AND '".$enddate."'";
      //echo "<p>Query: ".$query."</p>";
      //$result = $db->query($query);
    
      // safe way:
      $stmt = $db->prepare("SELECT ".$datekey." AS Date, ".$extratxt."KM AS KM, ".$extratxt."Seconds AS Seconds, ".$extratxt."KMH AS KMH FROM ".$searchtable." WHERE ".$datekey." BETWEEN ? AND ?");
      $stmt->bind_param('ss', $startdate, $enddate); // 'is' => 'interger, string', string can be used for date
      $stmt->execute();
      $result = $stmt->get_result();

      $num_results = $result->num_rows;
      // results are shown below search

      $db->close();
    }
  }
  else {
    $is_post = False;
    // Get mimimum and maximum year from data base
    if ($no_problem) {
      $stmt = $db->prepare("SELECT MIN(Year_starting_on) AS result FROM fahrrad_yearly_summary");
      $stmt->execute();
      $result = $stmt->get_result();
      if ($result->num_rows > 0){
        $startdate = $result->fetch_assoc()["result"];
      }
      $stmt = $db->prepare("SELECT MAX(Date) AS result FROM fahrrad_rides");
      $stmt->execute();
      $result = $stmt->get_result();
      if ($result->num_rows > 0){
        $enddate = $result->fetch_assoc()["result"];
      }
    }
  }
?>

<html>
<head>
  <title>Cycle rides</title>
  <link rel="stylesheet" href="cycle.css">
</head>

<body>
  <h1>Search</h1>
  
  
  <form method="post">
  <!-- <form action="cycle_logging.php" method="post"> -->
    <table  class="table_no_borders">
      <tr>
        <td>Type</td>
        <td>
          <select name="searchtype">
            <option value="Days" <?php if($searchtype=="Days"){echo "selected";} ?> >Days</option>
            <option value="Weeks" <?php if($searchtype=="Weeks"){echo "selected";} ?> >Weeks</option>
            <option value="Months" <?php if($searchtype=="Months"){echo "selected";} ?> >Months</option>
            <option value="Years" <?php if($searchtype=="Years"){echo "selected";} ?> >Years</option>
          </select>
        </td>
      </tr>
      <tr>
        <td>Start Date</td>
        <td><input name="startdate" type="date" size="10" value="<?php echo htmlspecialchars($startdate); ?>" /></td>
      </tr>
      <tr>
        <td>End Date</td>
        <td><input name="enddate" type="date" size="10"  value="<?php echo htmlspecialchars($enddate); ?>" /></td>
      </tr>
    </table> 
    
    <input type="submit" name="submit" value="Search"/>
  </form>

</body>
</html>

<?php   // results or errors
  if ($is_post){
    if ($no_problem) { 
      echo "<h1>Results</h1>";
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
    } else {
      echo $error_msg;
    }
  }
?>
