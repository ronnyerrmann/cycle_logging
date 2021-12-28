import java.sql.*;
import java.io.*;
import java.util.*;

public class Connection_MYSQL {
    Dictionary mysql_Settings = new Hashtable();
    
    static final String mysqlsettingsfile = "fahrrad_mysql.params";
    //static final Connection conn;
    Connection conn;
    String DB_URL;
    {
        // This code is executed before every constructor.
        //if (DB != "") {DB_URL += "/" + DB;}
        mysql_Settings.put("host", "localhost");
        mysql_Settings.put("user", "yourusername");
        mysql_Settings.put("password", "yourpassword");
        mysql_Settings.put("db", "");
    }
    
    static final String QUERY = "SELECT Date, DayKM, DaySeconds, TotalKM, TotalSeconds FROM fahrrad_rides";
    
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
    
    public void Connection_MYSQL()
    {
        DB_URL = "jdbc:mysql://" + this.mysql_Settings.get("host");
        if (this.mysql_Settings.get("db") != "") {DB_URL += "/" + this.mysql_Settings.get("db");}
       
        try(Connection temp_conn = DriverManager.getConnection(DB_URL, (String)mysql_Settings.get("user"), (String)mysql_Settings.get("password"));
            Statement stmt = conn.createStatement();
        ) {
           this.conn = temp_conn;
        } catch (SQLException e) {
            e.printStackTrace();}
        
    }
    public static void main (String[] args)
    {
        try
        {
            Connection_MYSQL obj = new Connection_MYSQL ();     // initialise
            obj.run (args);
        }
        catch (Exception e)
        {
            e.printStackTrace ();
        }
    }

    // instance variables here

    public void run (String[] args) throws Exception
    {
        // Open a connection
        Load_settings(mysqlsettingsfile);       // will be stored in mysql_Settings and replace standard values
        
        /*Enumeration enu = mysql_Settings.keys();    // Creating an empty enumeration to store
        while (enu.hasMoreElements()) {
            String key = (String)enu.nextElement();     // otherwise it would call nextElement twice when printing key and value
            System.out.println( key + ":" +  mysql_Settings.get(key) );
        }*/
        
        //Class.forName("com.mysql.jdbc.Driver");     // depreciation warning
        Class.forName("com.mysql.cj.jdbc.Driver");      // java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar Connection_MYSQL.java
        Connection_MYSQL();
        /*
        DB_URL = "jdbc:mysql://" + mysql_Settings.get("host");
        if (mysql_Settings.get("db") != "") {DB_URL += "/" + mysql_Settings.get("db");}
        try(Connection conn = DriverManager.getConnection(DB_URL, (String)mysql_Settings.get("user"), (String)mysql_Settings.get("password"));
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(QUERY);) {
            // Extract data from result set
            while (rs.next()) {
                // Retrieve by column name
                System.out.print("ID: " + rs.getInt("id"));
                System.out.print(", Age: " + rs.getInt("age"));
                System.out.print(", First: " + rs.getString("first"));
                System.out.println(", Last: " + rs.getString("last"));
            }
        } catch (SQLException e) {
            e.printStackTrace();
        } */
    }
    
    public Connection_MYSQL() // Constructor of Class Primes_java_v2
    {
        int testvar = 10;
    }
       
}
