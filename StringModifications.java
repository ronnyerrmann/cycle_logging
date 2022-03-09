package javaCycle;
import java.io.*;
import java.util.*;
// javac -d . StringModifications.java
// -d . will create stringModifications/StringModifications.class, which then can be included with  import stringModifications.StringModifications;  and called with  StringModifications.Split_string(par);

public class StringModifications {

    public static ArrayList<String> Array2ArrayList(String[] input){
        // Convert Array into an Arraylist
        ArrayList<String> output = new ArrayList<String>();
        for (int ii=0; ii<input.length; ii++){
            output.add(input[ii]); }
        return output;
    }

    public static List<ArrayList<String>> SplitStringTrim(List<String> content, String delimiter ){
        // Split each entry in a list of strings by a delimiter
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
}
