<?php   // general settings and functions
  $root_dir = $_SERVER['DOCUMENT_ROOT'];
  // Path to the settings file: one level above the server settings -> can't be accessed from the internet to keep the password secure, however, needs root access to put the file, tested with Apache
  $mysql_settingsfile = $root_dir."/../fahrrad_mysql.params";
  
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
  
  function format_time($t,$f=':') // t = seconds, f = separator 
  {
     return sprintf("%02d%s%02d%s%02d", floor($t/3600), $f, ($t/60)%60, $f, $t%60);
  }
  
  function print_results($data) 
  {
     echo "<h1>Results</h1>";
     echo "<p>Number of entries found: ".sizeof($data)."</p>";
 
     for ($ii=0; $ii < sizeof($data); $ii++) {
        $row = $data[$ii];
        echo "<p><strong>".($ii+1).". Date: ";
        echo htmlspecialchars(stripslashes($row['Date']));
        echo "</strong><br />Distance [km]: ";
        echo stripslashes($row['KM']);
        echo "</strong><br />Time [s -> hh:mm:ss]: ";
        echo stripslashes($row['Seconds'])."  ->  ".format_time($row['Seconds']);
        echo "<br />Speed [km/h]: ";
        echo stripslashes($row['KMH']);
        echo "</p>";
     }
  }
  
  
?>

<?php   // do the query
  if ($_SERVER['REQUEST_METHOD'] == 'POST') { 
    $is_post = True;
    // create short variable names
    $searchtype=$_POST['searchtype'];
    $startdate=trim($_POST['startdate']);
    $enddate=trim($_POST['enddate']);
    $x_axis=trim($_POST['x_axis_temp']);
    $y1_axis=trim($_POST['y1_axis_temp']);
    $graph_type=trim($_POST['graph_type_temp']);

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
      $data = array();      // prepare for javascript
      foreach ($result as $row) {
	    $data[] = $row;
      }
      $result->free(); 
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
    $x_axis="Date";
    $y1_axis="Distance";
    $graph_type = "scatter";
  }
?>

<html>
<head>
  <title>Cycle rides</title>
  <link rel="stylesheet" href="cycle.css?<?=filemtime('cycle.css')?>">      <!-- css is cached in a browser, so this causes it to reload everytime the file is changed-->
  <script type="text/javascript" src="node_modules/jquery.min.js/jquery.min.js"></script>
  <script type="text/javascript" src="node_modules/chart.js/dist/chart.min.js"></script>
  <script type="text/javascript" src="node_modules/chartjs-plugin-zoom/dist/chartjs-plugin-zoom.min.js"></script>
  <script type="text/javascript" src="node_modules/moment/moment.js"></script>
  <script type="text/javascript" src="cycle.js"></script>
  <!-- <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.js"></script>  if not locally installed -->
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
    <input name="x_axis_temp" id="x_axis_temp" type="hidden" value="<?php echo htmlspecialchars($x_axis); ?>" >
    <input name="y1_axis_temp" id="y1_axis_temp"type="hidden"  value="<?php echo htmlspecialchars($y1_axis); ?>" >
    <input name="graph_type_temp" id="graph_type_temp"type="hidden"  value="<?php echo htmlspecialchars($graph_type); ?>" >
    <input type="submit" name="submit" value="Search"/>
  </form>

  <div id="chart-container">
        <canvas id="graphCanvas"></canvas>
        <p id="errormsg"></p>
  </div>

  <form class="hidden-form" method="post">
    <p id="to_log">Select data to show</p>
    <div class="form-group">
      <label for="x_axis">Data in x-axis</label>
      <select id="x_axis" name="x_axis" onchange="update_axis_event(event, 'x_axis')">
        <option value="Date" <?php if($x_axis=="Date"){echo "selected";} ?> >Date</option>
        <option value="Distance" <?php if($x_axis=="Distance"){echo "selected";} ?> >Distance</option>
        <option value="Time" <?php if($x_axis=="Time"){echo "selected";} ?> >Time</option>
        <option value="Speed" <?php if($x_axis=="Speed"){echo "selected";} ?> >Speed</option>
      </select>
      <label for="y1_axis">Data in y-axis</label>
      <select id="y1_axis" name="y1_axis" onchange="update_axis_event(event, 'y1_axis')">
        <option value="Date" <?php if($y1_axis=="Date"){echo "selected";} ?> >Date</option>
        <option value="Distance" <?php if($y1_axis=="Distance"){echo "selected";} ?> >Distance</option>
        <option value="Time" <?php if($y1_axis=="Time"){echo "selected";} ?> >Time</option>
        <option value="Speed" <?php if($y1_axis=="Speed"){echo "selected";} ?> >Speed</option>
      </select> 
      <label for="graph_type">Graph Type</label>
      <select id="graph_type" name="graph_type" onchange="update_axis_event(event, 'graph_type')">
        <option value="scatter" <?php if($graph_type=="scatter"){echo "selected";} ?> >Scatter</option>
        <option value="bar" <?php if($graph_type=="bar"){echo "selected";} ?> >Bar</option>
      </select> 
    </div>
  </form>

  <script>
    var is_post = <?php echo json_encode($is_post); ?>;
    var no_problem = <?php echo json_encode($no_problem); ?>;
    if (is_post && no_problem) {
      $('.hidden-form').show();
      var x_axis = <?php echo json_encode($x_axis); ?>;
      var y1_axis = <?php echo json_encode($y1_axis); ?>;
      var graph_type = <?php echo json_encode($graph_type); ?>;
      var data = <?php echo json_encode($data); ?>;
      var graphTarget = document.querySelector("#graphCanvas");
      update_graph_data(x_axis, y1_axis, graph_type, graphTarget)
    } else {
      $('.hidden-form').hide();
    }
  </script>

</body>
</html>

<?php   // results or errors
  if ($is_post){
    if ($no_problem) { 
      print_results($data);
    } else {
      echo $error_msg;
    }
  }
?>
