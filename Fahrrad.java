import java.sql.*;
import java.io.*;
import java.util.*;
import java.time.LocalDate;
import java.time.Month;
import Connection_MYSQL; the Connection_MYSQL just needs to be in the same folder
// java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar:. Fahrrad.java

public class Fahrrad {
    Dictionary mysql_Settings = new Hashtable();
    Dictionary fahrrad_values = new Hashtable();
    
    static final String mysqlsettingsfile = "fahrrad_mysql.params";
    //static final Connection conn;
    String DB_URL;
    {   // This code is executed before every constructor.
        mysql_Settings.put("host", "localhost");
        mysql_Settings.put("user", "yourusername");
        mysql_Settings.put("password", "yourpassword");
        mysql_Settings.put("db", "");
    }
    
    public List<String> Load_File(String filename){
        File file = new File(filename);
        List<String> content = new ArrayList<String>();
        try (FileInputStream input = new FileInputStream(file)) {
            // create an empty string builder to store string
           
            // create an object of bufferedReader to read  lines from file
            BufferedReader br = new BufferedReader(new InputStreamReader(input));
 
            String line;
            // store each line one by one until reach end of file
 
            while ((line = br.readLine()) != null) {
                // append string builder with line and with '/n' or '/r' or EOF
                content.add(line);
            }
            //System.out.println(content);            // print string builder object i.e content
        }
 
        // Catch block to handle exceptions
        catch (IOException e) {
            e.printStackTrace();
        }
        
        return content;
    }
    
    public ArrayList<String> Array2ArrayList(String[] input){
        // Convert Array into an Arraylist
        ArrayList<String> output = new ArrayList<String>();
        for (int ii=0; ii<input.length; ii++){
            output.add(input[ii]); }
        return output;
    }
    
    public List<ArrayList<String>> Split_string(List<String> content, String delimiter ){
        List<ArrayList<String>> content_split = new ArrayList<ArrayList<String>>();
            
        content.forEach((content_entry)  -> 
        {
            String[] splitStr = content_entry.trim().split(delimiter);
            ArrayList<String> splitStr_a = Array2ArrayList(splitStr);   // Convert Array into an Arraylist
            content_split.add(splitStr_a);
        }
                );    
            
        return content_split;
    }
    
    public void Load_settings(String filename){
        List<String> content = Load_File(filename);
        List<ArrayList<String>> content_split = Split_string(content, "=");
        for (int ii=0; ii<content_split.size(); ii++){
            ArrayList<String> key_value = content_split.get(ii);
            this.mysql_Settings.put(key_value.get(0).trim(), key_value.get(1).trim());  // trim(): remove leading and trailing whitespace
        }
    }

    public static void main (String[] args)
    {
        try
        {
            Fahrrad obj = new Fahrrad ();     // initialise
            obj.run (args);
        }
        catch (Exception e)
        {
            e.printStackTrace ();
        }
    }

    public Statement Initialise_MYSQL_connection(String DB_URL){
        try (Connection conn = DriverManager.getConnection(DB_URL, (String)mysql_Settings.get("user"), (String)mysql_Settings.get("password"));
            Statement stmt = conn.createStatement();) {
            return stmt;
        } catch (SQLException e) {
            System.out.println("The database connection failed with:");
            e.printStackTrace();
            return null;
        }
    }
    
    public ResultSet MYSQL_query(Statement stmt, String QUERY){
        try (ResultSet rs = stmt.executeQuery(QUERY);) {
            return rs;
        } catch (SQLException e) {
            System.out.println("The following command failed: "+QUERY);
            System.out.println("with:");
            e.printStackTrace();
            return null;
        }
    }
    
    public Boolean MYSQL_execute(Statement stmt, String QUERY){
        // stmt.executeUpdate(QUERY);
        return true;
        /*  // Below doesn't work:
            // error: the try-with-resources resource must either be a variable declaration or an expression denoting a reference to a final or effectively final variable
        final Statement stmt1 = stmt;
        final String QUERY_l = QUERY;
        try (stmt1.executeUpdate(QUERY_l);) {
            return true;
        } catch (SQLException e) {
            System.out.println("The following command failed: "+QUERY);
            System.out.println("with:");
            e.printStackTrace();
            return false;
        }*/
    }
    
    public static boolean isNumeric(String str) {
        return str != null && str.matches("[-+]?\\d*\\.?\\d+");
    }
    
    public void get_fahrrad_values() {
        // Get date
        LocalDate currentdate = LocalDate.now();        // Getting the current date value
        int currentDay = currentdate.getDayOfMonth();   // Getting the current day
        int currentMonth = currentdate.getMonth().getValue();    // Getting the current month
        int currentYear = currentdate.getYear();        // getting the current year
        Boolean success = false;
        while (!success){
            System.out.println("Date (dd or dd-mm or dd-mm-yy, empty for today):");
            Scanner myObj1 = new Scanner(System.in);  // Create a Scanner object
            String date_s = myObj1.nextLine();  // Read user input
            if ( isNumeric(date_s) ) {
                currentDay = Integer.valueOf(date_s);
                success = true;
            } else if ( date_s.length() == 0 ) {
                success = true;     // do nothing, keep current values
            } else {
                String[] values_t = date_s.trim().split("-");
                switch (values_t.length) {
                    case 2:
                        if ( isNumeric(values_t[0]) && isNumeric(values_t[1]) ) {
                            currentDay = Integer.valueOf(values_t[0]);
                            currentMonth = Integer.valueOf(values_t[1]);
                            success = true;
                        }
                        break;
                    case 3:
                        if ( isNumeric(values_t[0]) && isNumeric(values_t[1]) && isNumeric(values_t[2]) ) {
                            currentDay = Integer.valueOf(values_t[0]);
                            currentMonth = Integer.valueOf(values_t[1]);
                            currentYear = Integer.valueOf(values_t[2]);
                            success = true;
                        }
                        break;
                    default:
                        System.out.println("Error: Expect dd or dd-mm or dd-mm-yy or empty");
                }
            }
        }
        String date_s = "";
        if ( currentYear < 100) { date_s += "20" + String.valueOf(currentYear) + "-"; }
        else { date_s += String.valueOf(currentYear) + "-"; }
        if (currentMonth < 10) { date_s += "0" + String.valueOf(currentMonth) + "-"; }
        else { date_s += String.valueOf(currentMonth) + "-"; }
        if (currentDay < 10) { date_s += "0" + String.valueOf(currentDay); }
        else { date_s += String.valueOf(currentDay); }
        fahrrad_values.put("Date", date_s);
        //myObj1.close();       // This will close also the other Scanner sessions
        // Get start value
        success = false;
        byte start = 1;
        while (!success){
            System.out.println("Start with which option:");
            System.out.println("  1: Day Kilometres");
            System.out.println("  2: Day Time");
            System.out.println("  3: Total Kilometres");
            System.out.println("  4: Total Time");
            Scanner myObj = new Scanner(System.in);  // Create a Scanner object
            if(myObj.hasNextInt()) {
                start = myObj.nextByte();
                if ((start >= 1) && (start <= 4)){success = true;}
                else {System.out.println("Error: Expect a number between 1 and 4");}
            } else {
                System.out.println("Error: Expect a number between 1 and 4");
            }
        }
        // Make a list with all the values to be asked for, starting at the selected one
        byte index[] = {start, -1, -1, -1};
        byte jj = (byte)(start + 1);
        for (byte ii=1; ii<=3; ii++){
            if (jj > 4) {jj = 1;}
            index[ii] = jj;
            jj ++;
            //System.out.println(ii +", "+ index[ii]);
        }
        // Getting the values
        for (byte ii=0; ii<=3; ii++){
            success = false;
            float value_f;
            String value_s;
            while (!success){
                Scanner myObj = new Scanner(System.in);  // Create a Scanner object
                switch (index[ii]) {
                    case 1:
                        System.out.println("Give Day Kilometres:");
                        if(myObj.hasNextFloat()) {
                            value_f = myObj.nextFloat();  // Read user input
                            success = true;
                            fahrrad_values.put("DayKM", value_f);
                        } else {
                            System.out.println("Error: Expect a float");
                        }
                        break;
                    case 2:
                        System.out.println("Give Day Time (expect ss or mm:ss or hh:mm:ss)");
                        value_s = myObj.nextLine();  // Read user input
                        if ( isNumeric(value_s) ) {
                            Integer value_i = Integer.valueOf(value_s);
                            success = true;
                            fahrrad_values.put("DaySeconds", value_i);
                        } else {
                            String[] values_t = value_s.trim().split(":");
                            switch (values_t.length) {
                                case 2:
                                    if ( isNumeric(values_t[0]) && isNumeric(values_t[1]) ) {
                                        Integer value_i = Integer.valueOf(values_t[0])*60 + Integer.valueOf(values_t[1]);
                                        success = true;
                                        fahrrad_values.put("DaySeconds", value_i);
                                    }
                                    break;
                                case 3:
                                    if ( isNumeric(values_t[0]) && isNumeric(values_t[1])  && isNumeric(values_t[2]) ) {
                                        Integer value_i = Integer.valueOf(values_t[0])*3600 + Integer.valueOf(values_t[1])*60 + Integer.valueOf(values_t[2]);
                                        success = true;
                                        fahrrad_values.put("DaySeconds", value_i);
                                    }
                                    break;
                                default:
                                    System.out.println("Error: Expect ss or mm:ss or hh:mm:ss");
                            }
                        }
                        break;
                    case 3:
                        System.out.println("Give Total Kilometres:");
                        if(myObj.hasNextFloat()) {
                            value_f = myObj.nextFloat();  // Read user input
                            fahrrad_values.put("TotalKM", value_f);
                            success = true;
                        } else {
                            System.out.println("Error: Expect a float");
                        }
                        break;
                    case 4:
                        System.out.println("Give Total Time (expect hh or hh:mm)");
                        value_s = myObj.nextLine();  // Read user input
                        if ( isNumeric(value_s) ) {
                            Integer value_i = Integer.valueOf(value_s)*3600;
                            success = true;
                            fahrrad_values.put("TotalSeconds", value_i);
                        } else {
                            String[] values_t = value_s.trim().split(":");
                            switch (values_t.length) {
                                case 2:
                                    if ( isNumeric(values_t[0]) && isNumeric(values_t[1]) ) {
                                        Integer value_i = Integer.valueOf(values_t[0])*3600 + Integer.valueOf(values_t[1])*60;
                                        success = true;
                                        fahrrad_values.put("TotalSeconds", value_i);
                                    }
                                    break;
                                default:
                                    System.out.println("Error: Expect hh or hh:mm");
                            }
                        }
                        break;
                    default:
                        System.out.println("Error: Mistake in the code: index[ii] = " + index[ii] + " is not coded");
                        System.exit(1);
                }
                
            }
        }

    
    }

    public void run (String[] args) throws Exception
    {
        
        Load_settings(mysqlsettingsfile);       // will be stored in mysql_Settings and replace standard values
        
        /*Enumeration enu = mysql_Settings.keys();    // Creating an empty enumeration to store
        while (enu.hasMoreElements()) {
            String key = (String)enu.nextElement();     // otherwise it would call nextElement twice when printing key and value
            System.out.println( key + ":" +  mysql_Settings.get(key) );
        }*/
        
        // Open a connection
        Class.forName("com.mysql.cj.jdbc.Driver");      // java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar Connection_MYSQL.java
        DB_URL = "jdbc:mysql://" + mysql_Settings.get("host");
        if (mysql_Settings.get("db") != "") {DB_URL += "/" + mysql_Settings.get("db");}
        String QUERY = "SELECT Date, DayKM, DaySeconds, TotalKM, TotalSeconds FROM fahrrad_rides";
        Statement stmt = Initialise_MYSQL_connection(DB_URL);        // stmt is still closed, as the try-catch block is finished
        if (stmt == null) {System.exit(1); }
        // recreating the connection, as Initialise_MYSQL_connection doesn't keep it open
        Connection conn = DriverManager.getConnection(DB_URL, (String)mysql_Settings.get("user"), (String)mysql_Settings.get("password"));
        stmt = conn.createStatement();
        ResultSet rs = MYSQL_query(stmt, QUERY);
        if (rs == null) {System.exit(1); }
        // Extract data from result set
        //while (rs.next()) {
            // Retrieve by column name
        //    System.out.print("ID: " + rs.getInt("id"));
        //    System.out.print(", First: " + rs.getString("first"));
        //}
        
        get_fahrrad_values();
        // check that TotalKM or TotalSeconds not yet in database
        //check_values_with_db(rs);
        
        // check that entry not yet in database
        
        
        QUERY = "INSERT INTO fahrrad_rides (Date, DayKM, DaySeconds, TotalKM, TotalSeconds) VALUES ('";
        QUERY += fahrrad_values.get("Date") + "', " + String.valueOf(fahrrad_values.get("DayKM")) + ", " + String.valueOf(fahrrad_values.get("DaySeconds")) + ", ";
        QUERY += String.valueOf(fahrrad_values.get("TotalKM")) + ", " + String.valueOf(fahrrad_values.get("TotalSeconds")) + ")";
        
        stmt.executeUpdate(QUERY);      // can't try except -> need to catch problems before
        //Boolean success = MYSQL_execute(stmt, QUERY);
        //conn.commit( );       // not necessary when autocommit
        System.out.println("Successfully inserted new values into database");
    }   
}
