package javaCycle;
import java.sql.*;
import java.io.*;
import java.util.*;
//import stringModifications.StringModifications;   // doesn't need the import, if included, then compilation of Fahrrad.java fails, probably as in a folder
// javac -d . -classpath /usr/share/java/mysql-connector-java-8.0.27.jar:. ConnectionMYSQL.java

public class ConnectionMYSQL {
    Dictionary mysqlSettings = new Hashtable();
    
    static final String mysqlSettingsFile = "fahrrad_mysql.params";
    //static final Connection conn;
    Connection conn;
    String DB_URL;
    {   // This code is executed before every constructor.
        // fill array with dummy values
        mysqlSettings.put("host", "localhost");
        mysqlSettings.put("user", "yourusername");
        mysqlSettings.put("password", "yourpassword");
        mysqlSettings.put("db", "");
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
    
    public void LoadSettings(String filename){
        List<String> content = Load_File(filename);
        List<ArrayList<String>> contentSplit = StringModifications.SplitStringTrim(content, "=");
        for (int ii=0; ii<contentSplit.size(); ii++){
            ArrayList<String> key_value = contentSplit.get(ii);
            this.mysqlSettings.put(key_value.get(0).trim(), key_value.get(1).trim());  // trim(): remove leading and trailing whitespace
        }
    }
    
    public Connection ConnectionMYSQL_aa()     // was a try that didn't work
    {
        DB_URL = "jdbc:mysql://" + this.mysqlSettings.get("host");
        if (this.mysqlSettings.get("db") != "") {DB_URL += "/" + this.mysqlSettings.get("db");}
       
        try(Connection temp_conn = DriverManager.getConnection(DB_URL, (String)mysqlSettings.get("user"), (String)mysqlSettings.get("password"));
            Statement stmt = temp_conn.createStatement();
            //return temp_conn; // illegal
        ) {
           return temp_conn;
        } catch (SQLException e) {
            e.printStackTrace();
            return null;
        }
        
    }
    
    public Connection InitialiseConnectionMYSQL()
    {
        DB_URL = "jdbc:mysql://" + this.mysqlSettings.get("host");
        if (this.mysqlSettings.get("db") != "") {DB_URL += "/" + this.mysqlSettings.get("db");}
        try {
            Connection temp_conn = DriverManager.getConnection(DB_URL, (String)mysqlSettings.get("user"), (String)mysqlSettings.get("password"));
            Statement stmt = temp_conn.createStatement();
            return temp_conn;
        } catch (SQLException e) {
            e.printStackTrace();
            return null;
        }
        
    }
    
    public ResultSet MYSQLQuery(Statement stmt, String QUERY){
        try (ResultSet rs = stmt.executeQuery(QUERY);) {
            return rs;
        } catch (SQLException e) {
            System.out.println("The following command failed: "+QUERY);
            System.out.println("with:");
            e.printStackTrace();
            return null;
        }
    }
    
    public Boolean MYSQLExecute(Statement stmt, String QUERY){
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
    
    public static void main (String[] args)
    {
        try
        {
            ConnectionMYSQL obj = new ConnectionMYSQL ();     // initialise
            obj.run (args);
        }
        catch (Exception e)
        {
            e.printStackTrace ();
        }
    }

    public void run (String[] args) throws Exception
    {
        
        LoadSettings(mysqlSettingsFile);       // will be stored in mysqlSettings and replace standard values
        
        /*Enumeration enu = mysqlSettings.keys();    // Creating an empty enumeration to store
        while (enu.hasMoreElements()) {
            String key = (String)enu.nextElement();     // otherwise it would call nextElement twice when printing key and value
            System.out.println( key + ":" +  mysqlSettings.get(key) );
        }*/
        
        // Open a connection
        //Class.forName("com.mysql.jdbc.Driver");     // depreciation warning
        Class.forName("com.mysql.cj.jdbc.Driver");      // java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar ConnectionMYSQL.java
        // 202202020: trying to get conn back from ConnectionMYSQL();
        /*Connection conn = ConnectionMYSQL_aa();
        Statement stmt = conn.createStatement();    // fails, as the connection is already closed       */
        // 202202020: trying to get conn back from ConnectionMYSQL();
        Connection conn = InitialiseConnectionMYSQL();
        Statement stmt = conn.createStatement();
        
        System.out.print("222: ");
        // ConnectionMYSQL();                      // this could replace the try - catch below
        DB_URL = "jdbc:mysql://" + mysqlSettings.get("host");
        if (mysqlSettings.get("db") != "") {DB_URL += "/" + mysqlSettings.get("db");}
        try(Connection conn1 = DriverManager.getConnection(DB_URL, (String)mysqlSettings.get("user"), (String)mysqlSettings.get("password"));
            Statement stmt1 = conn.createStatement();
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
        }
        
    }
    
    
       
}
