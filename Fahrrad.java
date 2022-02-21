import java.sql.*;
import java.io.*;
import java.util.*;
import java.time.LocalDate;
import java.time.Month;
import javaCycle.ConnectionMYSQL;       // necessary when running java Fahrrad.java
import javaCycle.StringModifications;   // necessary when running java Fahrrad.java
// javac -d . StringModifications.java && javac -d . -classpath /usr/share/java/mysql-connector-java-8.0.27.jar:. ConnectionMYSQL.java && java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar:. Fahrrad.java
// javac -d . StringModifications.java && javac -d . ConnectionMYSQL.java && java -classpath /usr/share/java/mysql-connector-java-8.0.27.jar:. Fahrrad.java

public class Fahrrad {
    Dictionary fahrrad_values = new Hashtable();
    static final String mysqlSettingsFile = "fahrrad_mysql.params";

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
    
    public static boolean isNumeric(String str) {
        return str != null && str.matches("[-+]?\\d*\\.?\\d+");
    }
    
    public void getFahrradValues() {
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
        // Open a connection
        ConnectionMYSQL objMYSQL = new ConnectionMYSQL();
        objMYSQL.LoadSettings(mysqlSettingsFile);
        Connection conn = objMYSQL.InitialiseConnectionMYSQL();
        if (conn == null) {
            System.out.println("Connecting to the Database failed -> Exit");
            System.exit(1);
        }
        Statement stmt = conn.createStatement();
        String QUERY = "SELECT Date, DayKM, DaySeconds, TotalKM, TotalSeconds FROM fahrrad_rides";
        ResultSet rs = objMYSQL.MYSQLQuery(stmt, QUERY);
        if (rs == null) {
            System.out.println("Executing of "+QUERY+" failed -> Exit");
            System.exit(1);
        }
        
        // Userinput of the values
        getFahrradValues();
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
