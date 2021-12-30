import java.sql.*;
import java.io.*;
import java.util.*;
//import Connection_MYSQL; the Connection_MYSQL just needs to be in the same folder

public class Fahrrad {
    Dictionary mysql_Settings = new Hashtable();
    Dictionary fahrrad_values = new Hashtable();
    
    static final String mysqlsettingsfile = "fahrrad_mysql.params";
    //static final Connection conn;
    String DB_URL;
    {
        // This code is executed before every constructor.
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
    
    public void get_fahrrad_values() {
        Scanner myObj = new Scanner(System.in);  // Create a Scanner object
        Boolean success = false;
        while (!success){
            System.out.println("Start with which option:");
            System.out.println("  1: Day Kilometres");
            System.out.println("  2: Day Time");
            System.out.println("  3: Total Kilometres");
            System.out.println("  4: Total Time");
            Byte start = myObj.nextByte();  // Read user input
            if ((start >= 1) && (start <= 4)){success = true;}
        }
        Byte index[] = {start, start, start, start};
        Byte jj = start + 1;
        for (Byte ii=1; ii<=3; ii++){
            if (jj > 4) {jj = 1;}
            index[ii] = jj;
            jj ++;
        }
        System.out.println(index);  // Output user input
    
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
        fahrrad_values = 
        
        QUERY = "INSERT INTO fahrrad_rides (Date, DayKM, DaySeconds, TotalKM, TotalSeconds) VALUES (";
        QUERY += ", ";
        stmt.executeUpdate(QUERY);
        //Boolean success = MYSQL_execute(stmt, QUERY);
        
    }   
}
